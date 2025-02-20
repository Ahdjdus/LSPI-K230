import os
import ujson
from libs.PipeLine import ScopedTiming
import nncase_runtime as nn
import ulab.numpy as np
import image
import gc
import utime

root_path="/data/"        # root_path要以/结尾
config_path=root_path+"data/cifar10_config.json"
image_path=root_path+"data/image/cifar10_cls_results/right_pred_1_prob_1.0000_gt_1_3445.png"
deploy_conf={}
debug_mode=1

def read_img(img_path):
    img_data = image.Image(img_path)
    img_data_rgb888=img_data.to_rgb888()
    img_hwc=img_data_rgb888.to_numpy_ref()
    shape=img_hwc.shape
    img_tmp = img_hwc.reshape((shape[0] * shape[1], shape[2]))
    img_tmp_trans = img_tmp.transpose()
    img_res=img_tmp_trans.copy()
    img_return=img_res.reshape((shape[2],shape[0],shape[1]))
    return img_return

# 读取deploy_config.json文件
def read_deploy_config(config_path):
    with open(config_path, 'r') as json_file:
        try:
            config = ujson.load(json_file)
        except ValueError as e:
            print("JSON 解析错误:", e)
    return config

def softmax(x):
    exp_x = np.exp(x - np.max(x))
    return exp_x / np.sum(exp_x)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def classification():
    print("--------------start-----------------")
    # 使用json读取内容初始化部署变量
    deploy_conf=read_deploy_config(config_path)
    kmodel_name=deploy_conf["kmodel_path"]
    labels=deploy_conf["categories"]
    confidence_threshold=deploy_conf["confidence_threshold"]
    model_input_size=deploy_conf["img_size"]
    num_classes=deploy_conf["num_classes"]
    cls_idx=-1

    # ai2d输入输出初始化
    ai2d_input = read_img(image_path)
    ai2d_input_tensor = nn.from_numpy(ai2d_input)
    ai2d_input_shape=ai2d_input.shape
    data = np.ones((1,3,model_input_size[1],model_input_size[0]),dtype=np.uint8)
    ai2d_output_tensor = nn.from_numpy(data)

    # 初始化kpu并加载模型
    kpu = nn.kpu()
    kpu.load_kmodel(root_path+kmodel_name)
    # 初始化ai2d
    ai2d = nn.ai2d()
    ai2d.set_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)
    ai2d.set_resize_param(True, nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel )
    ai2d_builder = ai2d.build([1,3,ai2d_input_shape[1],ai2d_input_shape[2]], [1,3,model_input_size[1],model_input_size[0]])
    with ScopedTiming("total",debug_mode > 0):
        # 使用ai2d对输入进行预处理
        ai2d_builder.run(ai2d_input_tensor, ai2d_output_tensor)
        # 设置模型的输入tensor
        kpu.set_input_tensor(0, ai2d_output_tensor)
        # 模型推理
        kpu.run()
        # 获取模型输出
        results = []
        for i in range(kpu.outputs_size()):
            data = kpu.get_output_tensor(i)
            result = data.to_numpy()
            del data
            results.append(result)
        # 后处理并绘制结果保存图片
        if num_classes>2:
            softmax_res=softmax(results[0][0])
            res_idx=np.argmax(softmax_res)
            if softmax_res[res_idx]>confidence_threshold:
                cls_idx=res_idx
                print("classification result:",labels[res_idx])
                print("score",softmax_res[cls_idx])
                image_draw=image.Image(image_path).to_rgb565()
                image_draw.draw_string_advanced(5,5,20,"result:"+labels[cls_idx]+" score:"+str(round(softmax_res[cls_idx],3)),color=(0,255,0))
                image_draw.compress_for_ide()
                # image_draw.save(root_path+"cls_result.jpg")
            else:
                cls_idx=-1
        else:
            sigmoid_res=sigmoid(results[0][0][0])
            if sigmoid_res>confidence_threshold:
                cls_idx=1
                print("classification result:",labels[cls_idx])
                print("score",sigmoid_res)
                image_draw=image.Image(image_path).to_rgb565()
                image_draw.draw_string_advanced(5,5,20,"result:"+labels[cls_idx]+" score:"+str(round(sigmoid_res,3)),color=(0,255,0))
                image_draw.compress_for_ide()
                # image_draw.save(root_path+"cls_result.jpg")
            else:
                cls_idx=0
                print("classification result:",labels[cls_idx])
                print("score",1-sigmoid_res)
                image_draw=image.Image(image_path).to_rgb565()
                image_draw.draw_string_advanced(5,5,20,"result:"+labels[cls_idx]+" score:"+str(round(1-sigmoid_res,3)),color=(0,255,0))
                image_draw.compress_for_ide()
                # image_draw.save(root_path+"cls_result.jpg")
    del ai2d_input_tensor
    del ai2d_output_tensor
    print("---------------end------------------")
    gc.collect()
    nn.shrink_memory_pool()

if __name__=="__main__":
    classification()
