import os
import argparse
import numpy as np
from PIL import Image
import onnxsim
import onnx
from onnx import helper
import nncase
import shutil
import math

def parse_model_input_output(model_file,input_shape):
    onnx_model = onnx.load(model_file)
    input_all = [node.name for node in onnx_model.graph.input]
    input_initializer = [node.name for node in onnx_model.graph.initializer]
    input_names = list(set(input_all) - set(input_initializer))
    input_tensors = [
        node for node in onnx_model.graph.input if node.name in input_names]

    # input
    inputs = []
    for _, e in enumerate(input_tensors):
        onnx_type = e.type.tensor_type
        input_dict = {}
        input_dict['name'] = e.name
        # input_dict['dtype'] = onnx.mapping.TENSOR_TYPE_TO_NP_TYPE[onnx_type.elem_type]
        input_dict['dtype'] = helper.tensor_dtype_to_np_dtype(onnx_type.elem_type)
        input_dict['shape'] = [(i.dim_value if i.dim_value != 0 else d) for i, d in zip(
            onnx_type.shape.dim, input_shape)]
        inputs.append(input_dict)

    return onnx_model, inputs


# 旧版本
# def onnx_simplify(model_file, dump_dir,input_shape):
#     onnx_model, inputs = parse_model_input_output(model_file,input_shape)
#     onnx_model = onnx.shape_inference.infer_shapes(onnx_model)
#     input_shapes = {}
#     for input in inputs:
#         input_shapes[input['name']] = input['shape']

#     onnx_model, check = onnxsim.simplify(onnx_model, input_shapes=input_shapes)
#     assert check, "Simplified ONNX model could not be validated"

#     model_file = os.path.join(dump_dir, 'simplified.onnx')
#     onnx.save_model(onnx_model, model_file)
#     return model_file


def onnx_simplify(model_file, dump_dir, input_shape):
    onnx_model, inputs = parse_model_input_output(model_file, input_shape)
    onnx_model = onnx.shape_inference.infer_shapes(onnx_model)  # 显式形状推断[7](@ref)
    
    # 构建输入形状字典（兼容动态/静态）
    input_shapes = {input['name']: input['shape'] for input in inputs}
    
    # 调用简化接口（使用新参数）
    onnx_model, check = onnxsim.simplify(
        onnx_model,
        overwrite_input_shapes=input_shapes,  # 替换为正确参数
        skip_fuse_bn=False,  # 可选：跳过特定优化[4](@ref)
        dynamic_input_shape=False  # 根据需求调整[5](@ref)
    )
    assert check, "Simplified ONNX model validation failed"
    
    # 保存优化后模型
    output_path = os.path.join(dump_dir, 'simplified.onnx')
    onnx.save_model(onnx_model, output_path)
    return output_path


def read_model_file(model_file):
    with open(model_file, 'rb') as f:
        model_content = f.read()
    return model_content


def generate_data(shape, batch, calib_dir):
    img_paths = [os.path.join(calib_dir, p) for p in os.listdir(calib_dir)]
    data = []
    for i in range(batch):
        assert i < len(img_paths), "calibration images not enough."
        img_data = Image.open(img_paths[i]).convert('RGB')
        img_data = img_data.resize((shape[3], shape[2]), Image.BILINEAR)
        img_data = np.asarray(img_data, dtype=np.uint8)
        img_data = np.transpose(img_data, (2, 0, 1))
        data.append([img_data[np.newaxis, ...]])
    return np.array(data)


def convert_image_to_kmodel_bin(image_path, bin_path, target_size):
    """生成 KModel 的 uint8 .bin 文件（无需手动归一化，由模型预处理完成）"""
    image = Image.open(image_path).convert("RGB")
    image = image.resize((target_size[1], target_size[0]), Image.BILINEAR)
    img_np = np.array(image).transpose(2, 0, 1)  # HWC → CHW
    img_np = img_np.astype(np.uint8)
    img_np = img_np[np.newaxis, ...]  # 添加 batch 维度
    img_np.tofile(bin_path)
    print(f"Saved KModel input bin to {bin_path}")


def convert_image_to_onnx_bin(image_path, bin_path, target_size):
    """生成 ONNX 的 float32 .bin 文件（需手动归一化到 [0, 1]）"""
    image = Image.open(image_path).convert("RGB")
    image = image.resize((target_size[1], target_size[0]), Image.BILINEAR)
    img_np = np.array(image).transpose(2, 0, 1)  # HWC → CHW
    img_np = img_np.astype(np.float32) / 255.0    # 归一化到 [0, 1]
    img_np = img_np[np.newaxis, ...]  # 添加 batch 维度
    img_np.tofile(bin_path)
    print(f"Saved ONNX input bin to {bin_path}")


def main():
    parser = argparse.ArgumentParser(prog="nncase")
    parser.add_argument("--target", default="k230",type=str, help='target to run,k230/cpu')
    parser.add_argument("--model",type=str, help='model file')
    parser.add_argument("--dataset_path", type=str, help='calibration_dataset')
    parser.add_argument("--input_width", type=int, default=320, help='model input_width')
    parser.add_argument("--input_height", type=int, default=320, help='model input_height')
    parser.add_argument("--ptq_option", type=int, default=0, help='ptq_option:0,1,2,3,4,5')

    args = parser.parse_args()

    # 更新参数为32倍数
    input_width = int(math.ceil(args.input_width / 32.0)) * 32
    input_height = int(math.ceil(args.input_height / 32.0)) * 32

    # 模型的输入shape，维度要跟input_layout一致
    input_shape=[1,3,input_height,input_width]

    dump_dir = 'tmp'
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)

    # onnx simplify
    model_file = onnx_simplify(args.model, dump_dir,input_shape)

    # 设置CompileOptions
    compile_options = nncase.CompileOptions()
    compile_options.target = args.target

    # 是否采用kmodel模型做预处理
    compile_options.preprocess = True
    # onnx模型需要RGB的，k230上的摄像头给出的数据也是RGB格式的，因此不需要开启交换RB
    compile_options.swapRB = False
    # 输入图像的shape
    compile_options.input_shape = input_shape
    # 模型输入格式‘uint8’或者‘float32’
    compile_options.input_type = 'uint8'

    # 如果输入是‘uint8’格式，输入反量化之后的范围
    compile_options.input_range = [0, 1]
    # 预处理的mean/std值，每个channel一个，该数据由YOLOv8源码获取
    compile_options.mean = [0, 0, 0] 
    compile_options.std = [1, 1, 1]

    # 设置输入的layout，onnx默认‘NCHW’即可
    compile_options.input_layout = "NCHW"

    # 创建Compiler实例
    compiler = nncase.Compiler(compile_options)

    # 导入onnx模型
    model_content = read_model_file(model_file)
    import_options = nncase.ImportOptions()
    compiler.import_onnx(model_content, import_options)

    # 配置量化方式
    ptq_options = nncase.PTQTensorOptions()
    ptq_options.samples_count = 8

    if args.ptq_option == 0:
        ptq_options.calibrate_method = 'NoClip'
        ptq_options.quant_type = 'uint8'
        ptq_options.w_quant_type = 'uint8'
    elif args.ptq_option == 1:
        ptq_options.calibrate_method = 'NoClip'
        ptq_options.quant_type = 'uint8'
        ptq_options.w_quant_type = 'int16'
    elif args.ptq_option == 2:
        ptq_options.calibrate_method = 'NoClip'
        ptq_options.quant_type = 'int16'
        ptq_options.w_quant_type = 'uint8'
    elif args.ptq_option == 3:
        ptq_options.calibrate_method = 'Kld'
        ptq_options.quant_type = 'uint8'
        ptq_options.w_quant_type = 'uint8'
    elif args.ptq_option == 4:
        ptq_options.calibrate_method = 'Kld'
        ptq_options.quant_type = 'uint8'
        ptq_options.w_quant_type = 'int16'
    elif args.ptq_option == 5:
        ptq_options.calibrate_method = 'Kld'
        ptq_options.quant_type = 'int16'
        ptq_options.w_quant_type = 'uint8'
    else:
        pass

    # 设置校正数据
    ptq_options.set_tensor_data(generate_data(input_shape, ptq_options.samples_count, args.dataset_path))
    compiler.use_ptq(ptq_options)

    # 启动编译
    compiler.compile()

    # 生成两个测试用 .bin 文件（取校准数据集第一张图）
    if args.dataset_path and os.listdir(args.dataset_path):
        first_image = os.path.join(args.dataset_path, os.listdir(args.dataset_path)[0])
        
        # KModel 的输入文件（uint8）
        kmodel_bin_path = os.path.join(dump_dir, "test_kmodel_input.bin")
        convert_image_to_kmodel_bin(first_image, kmodel_bin_path, (input_height, input_width))
        
        # ONNX 的输入文件（float32）
        onnx_bin_path = os.path.join(dump_dir, "test_onnx_input.bin")
        convert_image_to_onnx_bin(first_image, onnx_bin_path, (input_height, input_width))
    else:
        print("Warning: No calibration images found. Skipping .bin generation.")

    # 写入kmodel文件
    kmodel = compiler.gencode_tobytes()
    base,ext=os.path.splitext(args.model)
    kmodel_name=base+".kmodel"
    with open(kmodel_name, 'wb') as f:
        f.write(kmodel)


if __name__ == '__main__':
    main()
