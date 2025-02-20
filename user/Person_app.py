import os
import gc
import sys
import ulab.numpy as np
from libs.PipeLine import PipeLine, ScopedTiming
from libs.Person import PersonDetectionApp, PersonKeyPointApp, FallDetectionApp

# 选择检测模式，可选"person_detection","person_keypoint","fall_detection"
person_mode = "fall_detection"

if __name__=="__main__":
    # 显示模式，默认"hdmi",可以选择"hdmi"和"lcd"
    display_mode="lcd"
    # k230保持不变，k230d可调整为[640,360]
    rgb888p_size = [1920, 1080]

    if display_mode=="hdmi":
        display_size=[1920,1080]
    else:
        display_size=[800,480]

    # 模型路径
    detect_kmodel_path="/sdcard/examples/kmodel/person_detect_yolov5n.kmodel"
    pose_kmodel_path="/sdcard/examples/kmodel/yolov8n-pose.kmodel"
    falldown_kmodel_path = "/sdcard/examples/kmodel/yolov5n-falldown.kmodel"
    # 其它参数设置
    anchors = [10, 13, 16, 30, 33, 23, 30, 61, 62, 45, 59, 119, 116, 90, 156, 198, 373, 326]

    # 初始化PipeLine
    pl=PipeLine(rgb888p_size=rgb888p_size,display_size=display_size,display_mode=display_mode)
    pl.create()

    if person_mode=="person_detection":
        personApp=PersonDetectionApp(detect_kmodel_path,model_input_size=[640,640],labels=["person"],anchors=anchors,confidence_threshold=0.2,nms_threshold=0.6,nms_option=False,strides=[8,16,32],rgb888p_size=rgb888p_size,display_size=display_size,debug_mode=0)
    elif person_mode=="person_keypoint":
        personApp=PersonKeyPointApp(pose_kmodel_path,model_input_size=[320,320],confidence_threshold=0.2,nms_threshold=0.5,rgb888p_size=rgb888p_size,display_size=display_size,debug_mode=0)
    elif person_mode=="fall_detection":
        personApp=FallDetectionApp(falldown_kmodel_path, model_input_size=[640, 640], labels=["Fall","NoFall"], anchors=anchors, confidence_threshold=0.3, nms_threshold=0.45, nms_option=False, strides=[8,16,32], rgb888p_size=rgb888p_size, display_size=display_size, debug_mode=0) 
    
    personApp.config_preprocess()
    
    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total",1):
                # 获取当前帧数据
                img=pl.get_frame()
                # 推理当前帧
                res=personApp.run(img)
                # 绘制结果到PipeLine的osd图像
                personApp.draw_result(pl,res)
                # 显示当前的绘制结果
                pl.show_image()
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        personApp.deinit()
        pl.destroy()