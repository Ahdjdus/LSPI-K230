'''

该文件是人脸识别的示例代码集合。使用方法通过指定 facial_mode 运行指定的 demo.
关于自定义人脸相关的类在 /sdcard/libs 下。目前以有 bug 如下

1.停止运行后，在注销类时需要指定对应的 demo 类，否则停止后会报错。通过修改使用对应的 deinit 
  可以解决，不过太麻烦啦。

2.关于人脸识别的 demo 所使用的人脸检测类和别的 demo 不同，问题在 人脸检测 的 run 返回的值
  数量不对，除了人脸识别的需要返回两个参数，其他都是一个。待解决！！！

目前只运行 人脸识别，要执行其他的 demo 需要修改 \sdcard\libs\Facial 的 人脸检测 run  返回值为 1个

'''


from libs.PipeLine import PipeLine, ScopedTiming
from libs.Facial import FaceDetApp, FaceParse, FaceLandMark, FaceMesh, FacePose, FaceRegistration, FaceRecognition, EyeGaze
import os
import ujson
from media.media import *
from time import *
import nncase_runtime as nn
import ulab.numpy as np
import time
import image
import aidemo
import random
import gc
import sys
import math

# 模式有八种选择，分别是：
# facial_detection：人脸检测
# facial_landmark：人脸关键点检测
# facial_parse：人脸分割
# facial_mesh：人脸网格
# facial_pose：人脸姿态
# facial_registration：人脸注册
# facial_recognition：人脸识别
# facial_eyeGaze: 眼睛注视
# 注意：执行人脸识别任务之前，需要先执行人脸注册任务进行人脸身份注册生成feature数据库
facial_mode = "facial_recognition"

if __name__=="__main__":
    # 显示模式，默认"hdmi",可以选择"hdmi"和"lcd"
    display_mode="lcd"
    # k230保持不变，k230d可调整为[640,360]
    rgb888p_size = [1920, 1080]

    if display_mode=="hdmi":
        display_size=[1920,1080]
    else:
        display_size=[800,480]
        # 其它参数

    # 模型
    face_det_kmodel_path = "/sdcard/examples/kmodel/face_detection_320.kmodel"
    face_det_input_size=[320,320]
    face_parse_kmodel_path = "/sdcard/examples/kmodel/face_parse.kmodel"
    face_parse_input_size=[320,320]
    face_landmark_kmodel_path="/sdcard/examples/kmodel/face_landmark.kmodel"
    face_landmark_input_size=[192,192]
    face_mesh_kmodel_path="/sdcard/examples/kmodel/face_alignment.kmodel"
    face_mesh_post_kmodel_path="/sdcard/examples/kmodel/face_alignment_post.kmodel"
    face_mesh_input_size=[120,120]
    face_pose_kmodel_path="/sdcard/examples/kmodel/face_pose.kmodel"
    face_pose_input_size=[120,120]
    # 人脸注册模型路径
    face_reg_kmodel_path="/sdcard/examples/kmodel/face_recognition.kmodel"
    face_reg_input_size=[112,112]
    # 人脸注视估计模型路径
    eye_gaze_kmodel_path="/sdcard/examples/kmodel/eye_gaze.kmodel"
    eye_gaze_input_size=[448,448]

    # 其它参数
    database_dir="/data/data/image/face_register/db/"
    database_img_dir="/data/data/image/face_register/db_img/"
    confidence_threshold = 0.5
    nms_threshold = 0.2
    anchor_len = 4200
    det_dim = 4
    face_recognition_threshold = 0.75        # 人脸识别阈值
    anchors_path = "/sdcard/examples/utils/prior_data_320.bin"

    anchors = np.fromfile(anchors_path, dtype=np.float)
    anchors = anchors.reshape((anchor_len,det_dim))

    # 初始化PipeLine，只关注传给AI的图像分辨率，显示的分辨率
    pl=PipeLine(rgb888p_size=rgb888p_size,display_size=display_size,display_mode=display_mode)
    pl.create()

    if facial_mode=="facial_detection":
        FacialApp=FaceDetApp(face_det_kmodel_path, model_input_size=face_det_input_size, anchors=anchors, confidence_threshold=confidence_threshold, nms_threshold=nms_threshold, rgb888p_size=rgb888p_size, display_size=display_size, debug_mode=0)
        FacialApp.config_preprocess()  # 配置预处理
    elif facial_mode=="facial_parse":
        FacialApp=FaceParse(face_det_kmodel_path,face_parse_kmodel_path,det_input_size=face_det_input_size,parse_input_size=face_parse_input_size,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,rgb888p_size=rgb888p_size,display_size=display_size)
    elif facial_mode=="facial_landmark":
        FacialApp=FaceLandMark(face_det_kmodel_path,face_landmark_kmodel_path,det_input_size=face_det_input_size,landmark_input_size=face_landmark_input_size,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,rgb888p_size=rgb888p_size,display_size=display_size)
    elif facial_mode=="facial_mesh":
        FacialApp=FaceMesh(face_det_kmodel_path,face_mesh_kmodel_path,face_mesh_post_kmodel_path,det_input_size=face_det_input_size,mesh_input_size=face_mesh_input_size,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,rgb888p_size=rgb888p_size,display_size=display_size)
    elif facial_mode=="facial_pose":
        FacialApp=FacePose(face_det_kmodel_path,face_pose_kmodel_path,det_input_size=face_det_input_size,pose_input_size=face_pose_input_size,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,rgb888p_size=rgb888p_size,display_size=display_size)
    elif facial_mode=="facial_recognition":
        FacialApp=FaceRecognition(face_det_kmodel_path,face_reg_kmodel_path,det_input_size=face_det_input_size,reg_input_size=face_reg_input_size,database_dir=database_dir,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,face_recognition_threshold=face_recognition_threshold,rgb888p_size=rgb888p_size,display_size=display_size)
#    elif facial_mode=="facial_register":
#        FacialApp=FaceRegistration(face_det_kmodel_path,face_reg_kmodel_path,det_input_size=face_det_input_size,reg_input_size=face_reg_input_size,database_dir=database_dir,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold)
    elif facial_mode=="facial_eyeGaze":
        FacialApp=EyeGaze(face_det_kmodel_path,eye_gaze_kmodel_path,det_input_size=face_det_input_size,eye_gaze_input_size=eye_gaze_input_size,anchors=anchors,confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,rgb888p_size=rgb888p_size,display_size=display_size)

    try:
        # if facial_mode == "facial_register":
        # # 获取图像列表
        #     img_list = os.listdir(database_img_dir)
        #     for img_file in img_list:
        #         #本地读取一张图像
        #         full_img_file = database_img_dir + img_file
        #         print(full_img_file)
        #         img = image.Image(full_img_file)
        #         img.compress_for_ide()
        #         # 转rgb888的chw格式
        #         rgb888p_img_ndarry = FacialApp.image2rgb888array(img)
        #         # 人脸注册
        #         FacialApp.run(rgb888p_img_ndarry,img_file)
        #         gc.collect()
        # else:
        while True:
            os.exitpoint()
            with ScopedTiming("total", 1):
                img=pl.get_frame()                      # 获取当前帧
                det_boxes,recg_res=FacialApp.run(img)          # 推理当前帧
                FacialApp.draw_result(pl,det_boxes,recg_res)   # 绘制推理结果
                pl.show_image()                         # 展示推理效果
                gc.collect()
    except Exception as e:
        sys.print_exception(e)
    finally:
        FacialApp.face_det.deinit()
        if facial_mode == "EyeGaze":
            FacialApp.eye_gaze.deinit()
        else:
            FacialApp.face_reg.deinit()
        pl.destroy()
