import os
import ujson
from libs.PipeLine import ScopedTiming
from media.sensor import *
from media.display import *
from media.media import *
import nncase_runtime as nn
import ulab.numpy as np
import image
import gc

display_mode="hdmi"
if display_mode=="lcd":
    DISPLAY_WIDTH = ALIGN_UP(800, 16)
    DISPLAY_HEIGHT = 480
else:
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080

OUT_RGB888P_WIDTH = ALIGN_UP(1280, 16)
OUT_RGB888P_HEIGH = 720

root_path="/data/"        # root_path要以/结尾
config_path=root_path+"data/cifar10_config.json"
deploy_conf={}
debug_mode=1

def read_deploy_config(config_path):
    # 打开JSON文件以进行读取deploy_config
    with open(config_path, 'r') as json_file:
        try:
            # 从文件中加载JSON数据
            config = ujson.load(json_file)

            # 打印数据（可根据需要执行其他操作）
            #print(config)
        except ValueError as e:
            print("JSON 解析错误:", e)
    return config

# 任务后处理
def softmax(x):
    exp_x = np.exp(x - np.max(x))
    return exp_x / np.sum(exp_x)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def classification():
    print("start")
    # 使用json读取内容初始化部署变量
    deploy_conf=read_deploy_config(config_path)
    kmodel_name=deploy_conf["kmodel_path"]
    labels=deploy_conf["categories"]
    confidence_threshold=deploy_conf["confidence_threshold"]
    model_input_size=deploy_conf["img_size"]
    num_classes=deploy_conf["num_classes"]
    cls_idx=-1
    score=0.0
    # 初始化kpu并加载模型
    kpu = nn.kpu()
    kpu.load_kmodel(root_path+kmodel_name)
    # 初始化ai2d用于预处理
    ai2d = nn.ai2d()
    ai2d.set_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)
    ai2d.set_resize_param(True, nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel )
    ai2d_builder = ai2d.build([1,3,OUT_RGB888P_HEIGH,OUT_RGB888P_WIDTH], [1,3,model_input_size[1],model_input_size[0]])
    # 初始化并配置sensor
    sensor = Sensor()
    sensor.reset()
    # 设置镜像
    sensor.set_hmirror(False)
    # 设置翻转
    sensor.set_vflip(False)
    # 通道0直接给到显示VO，格式为YUV420
    sensor.set_framesize(width = DISPLAY_WIDTH, height = DISPLAY_HEIGHT)
    sensor.set_pixformat(PIXEL_FORMAT_YUV_SEMIPLANAR_420)
    # 通道2给到AI做算法处理，格式为RGB888
    sensor.set_framesize(width = OUT_RGB888P_WIDTH , height = OUT_RGB888P_HEIGH, chn=CAM_CHN_ID_2)
    sensor.set_pixformat(PIXEL_FORMAT_RGB_888_PLANAR, chn=CAM_CHN_ID_2)
    # 绑定通道0的输出到vo
    sensor_bind_info = sensor.bind_info(x = 0, y = 0, chn = CAM_CHN_ID_0)
    Display.bind_layer(**sensor_bind_info, layer = Display.LAYER_VIDEO1)
    if display_mode=="lcd":
        # 设置为ST7701显示，默认800x480
        Display.init(Display.ST7701, to_ide = True)
    else:
        # 设置为LT9611显示，默认1920x1080
        Display.init(Display.LT9611, to_ide = True)

    #创建OSD图像
    osd_img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.ARGB8888)
    # media初始化
    MediaManager.init()
    # 启动sensor
    sensor.run()
    # 初始化变量
    rgb888p_img = None
    ai2d_input_tensor = None
    data = np.ones((1,3,model_input_size[1],model_input_size[0]),dtype=np.uint8)
    ai2d_output_tensor = nn.from_numpy(data)
    while True:
        with ScopedTiming("total",debug_mode > 0):
            rgb888p_img = sensor.snapshot(chn=CAM_CHN_ID_2)
            if rgb888p_img.format() == image.RGBP888:
                ai2d_input = rgb888p_img.to_numpy_ref()
                ai2d_input_tensor = nn.from_numpy(ai2d_input)
                # 使用ai2d进行预处理
                ai2d_builder.run(ai2d_input_tensor, ai2d_output_tensor)
                # 设置模型推理输入
                kpu.set_input_tensor(0, ai2d_output_tensor)
                # 模型推理
                kpu.run()
                # 获取模型推理输出
                results = []
                for i in range(kpu.outputs_size()):
                    output_data = kpu.get_output_tensor(i)
                    result = output_data.to_numpy()
                    del output_data
                    results.append(result)
                if num_classes>2:
                    softmax_res=softmax(results[0][0])
                    cls_idx=np.argmax(softmax_res)
                    if softmax_res[cls_idx]>confidence_threshold:
                        score=softmax_res[cls_idx]
                        print("classification result:")
                        print(labels[cls_idx])
                        print("score",score)
                    else:
                        cls_idx=-1
                        score=0.0
                else:
                    sigmoid_res=sigmoid(results[0][0][0])
                    if sigmoid_res>confidence_threshold:
                        cls_idx=1
                        score=sigmoid_res
                        print("classification result:")
                        print(labels[1])
                        print("score",score)
                    else:
                        cls_idx=0
                        score=1-sigmoid_res
                        print("classification result:")
                        print(labels[0])
                        print("score",score)
            osd_img.clear()
            if cls_idx>=0:
                osd_img.draw_string_advanced(5,5,32,"result:"+labels[cls_idx]+" score:"+str(round(score,3)),color=(0,255,0))
            Display.show_image(osd_img, 0, 0, Display.LAYER_OSD3)
            rgb888p_img = None
            gc.collect() #用于需要调用gc.mem_alloc()的内存
    del ai2d_input_tensor
    del ai2d_output_tensor
    #停止摄像头输出
    sensor.stop()
    #去初始化显示设备
    Display.deinit()
    #释放媒体缓冲区
    MediaManager.deinit()
    gc.collect()
    time.sleep(1)
    nn.shrink_memory_pool()
    print("end")
    return 0

if __name__=="__main__":
    classification()
