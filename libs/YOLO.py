from libs.PipeLine import ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
from libs.Utils import *
import os
import ujson
from media.media import *
from time import *
import nncase_runtime as nn
import ulab.numpy as np
import time
import utime
import image
import random
import gc
import sys
import aidemo

class YOLOv5(AIBase):
    def __init__(self,task_type="detect",mode="video",kmodel_path="",labels=[],rgb888p_size=[320,320],model_input_size=[320,320],display_size=[1920,1080],conf_thresh=0.5,nms_thresh=0.45,mask_thresh=0.5,max_boxes_num=50,debug_mode=0):
        if task_type not in ["classify","detect","segment"]:
            print("Please select the correct task_type parameter, including 'classify', 'detect', 'segment'.")
            return
        super().__init__(kmodel_path,model_input_size,rgb888p_size,debug_mode)
        self.task_type=task_type
        self.mode=mode
        self.kmodel_path=kmodel_path
        self.labels=labels
        self.class_num=len(labels)
        if mode=="video":
            self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        else:
            self.rgb888p_size=[rgb888p_size[0],rgb888p_size[1]]
        self.model_input_size=model_input_size
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]

        self.conf_thresh=conf_thresh
        self.nms_thresh=nms_thresh
        self.mask_thresh=mask_thresh
        self.max_boxes_num=max_boxes_num
        self.debug_mode=debug_mode

        self.scale=1.0
        self.colors=get_colors(len(self.labels))
        self.masks=None
        if self.task_type=="segment":
            if self.mode=="image":
                self.masks=np.zeros((1,self.rgb888p_size[1],self.rgb888p_size[0],4),dtype=np.uint8)
            elif self.mode=="video":
                self.masks=np.zeros((1,self.display_size[1],self.display_size[0],4),dtype=np.uint8)
        # Ai2d实例，用于实现模型预处理
        self.ai2d=Ai2d(self.debug_mode)
        # 设置Ai2d的输入输出格式和类型
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)

    # 配置预处理操作，这里使用了resize，Ai2d支持crop/shift/pad/resize/affine，具体代码请打开/sdcard/app/libs/AI2D.py查看
    def config_preprocess(self,input_image_size=None):
        with ScopedTiming("set preprocess config",self.debug_mode > 0):
            # 初始化ai2d预处理配置，默认为sensor给到AI的尺寸，您可以通过设置input_image_size自行修改输入尺寸
            ai2d_input_size=input_image_size if input_image_size else self.rgb888p_size
            if self.task_type=="classify":
                top,left,m=center_crop_param(self.rgb888p_size)
                self.ai2d.crop(left,top,m,m)
            elif self.task_type=="detect":
                # 计算padding参数
                top,bottom,left,right,self.scale=letterbox_pad_param(self.rgb888p_size,self.model_input_size)
                # 配置padding预处理
                self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [128,128,128])
            elif self.task_type=="segment":
                top,bottom,left,right,scale=letterbox_pad_param(self.rgb888p_size,self.model_input_size)
                self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [128,128,128])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            # build参数包含输入shape和输出shape
            self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],[1,3,self.model_input_size[1],self.model_input_size[0]])

    def postprocess(self,results):
        with ScopedTiming("postprocess",self.debug_mode > 0):
            if self.task_type=="classify":
                softmax_res=softmax(results[0][0])
                res_idx=np.argmax(softmax_res)
                cls_res=(-1,0.0)
                # 如果类别分数大于阈值，返回当前类别和分数
                if softmax_res[res_idx]>self.conf_thresh:
                    cls_res=(res_idx,softmax_res[res_idx])
                return cls_res
            elif self.task_type=="detect":
                output_data = results[0][0]
                boxes_ori = output_data[:,0:4]
                score_ori = output_data[:,4]
                class_ori = output_data[:,5:]
                class_res=np.argmax(class_ori,axis=-1)
                scores_ = score_ori*np.max(class_ori,axis=-1)
                boxes,inds,scores=[],[],[]
                for i in range(len(boxes_ori)):
                    if scores_[i]>self.conf_thresh:
                        x,y,w,h=boxes_ori[i][0],boxes_ori[i][1],boxes_ori[i][2],boxes_ori[i][3]
                        x1 = int((x - 0.5 * w)/self.scale)
                        y1 = int((y - 0.5 * h)/self.scale)
                        x2 = int((x + 0.5 * w)/self.scale)
                        y2 = int((y + 0.5 * h)/self.scale)
                        boxes.append([x1,y1,x2,y2])
                        inds.append(class_res[i])
                        scores.append(scores_[i])
                if len(boxes)==0:
                    return []
                boxes = np.array(boxes)
                scores = np.array(scores)
                inds = np.array(inds)
                # NMS过程
                keep = self.nms(boxes,scores,self.nms_thresh)
                dets = np.concatenate((boxes, scores.reshape((len(boxes),1)), inds.reshape((len(boxes),1))), axis=1)
                det_res = []
                for keep_i in keep:
                    det_res.append(dets[keep_i])
                det_res = np.array(det_res)
                det_res = det_res[:self.max_boxes_num, :]
                return det_res
            elif self.task_type=="segment":
                if self.mode=="image":
                    seg_res = aidemo.yolov5_seg_postprocess(results[0][0],results[1][0],[self.rgb888p_size[1],self.rgb888p_size[0]],[self.model_input_size[1],self.model_input_size[0]],[self.rgb888p_size[1],self.rgb888p_size[0]],len(self.labels),self.conf_thresh,self.nms_thresh,self.mask_thresh,self.masks)
                elif self.mode=="video":
                    seg_res = aidemo.yolov5_seg_postprocess(results[0][0],results[1][0],[self.rgb888p_size[1],self.rgb888p_size[0]],[self.model_input_size[1],self.model_input_size[0]],[self.display_size[1],self.display_size[0]],len(self.labels),self.conf_thresh,self.nms_thresh,self.mask_thresh,self.masks)
                return seg_res

    def draw_result(self,res,img):
        with ScopedTiming("draw result",self.debug_mode > 0):
            if self.mode=="video":
                if self.task_type=="classify":
                    ids,score=res[0],res[1]
                    if ids!=-1:
                        img.clear()
                        mes=self.labels[ids]+" "+str(round(score,3))
                        img.draw_string_advanced(5,5,32,mes,color=(0,255,0))
                    else:
                        img.clear()
                elif self.task_type=="detect":
                    if res:
                        img.clear()
                        for det in res:
                            x1, y1, x2, y2 = map(lambda x: int(round(x, 0)), det[:4])
                            x= x1*self.display_size[0] // self.rgb888p_size[0]
                            y= y1*self.display_size[1] // self.rgb888p_size[1]
                            w = (x2 - x1) * self.display_size[0] // self.rgb888p_size[0]
                            h = (y2 - y1) * self.display_size[1] // self.rgb888p_size[1]
                            img.draw_rectangle(x,y, w, h, color=self.colors[int(det[5])],thickness=4)
                            img.draw_string_advanced( x , y-50,32," " + self.labels[int(det[5])] + " " + str(round(det[4],2)) , color=self.colors[int(det[5])])
                    else:
                        img.clear()
                elif self.task_type=="segment":
                    if res[0]:
                        img.clear()
                        mask_img=image.Image(self.display_size[0], self.display_size[1], image.ARGB8888,alloc=image.ALLOC_REF,data=self.masks)
                        img.copy_from(mask_img)
                        dets,ids,scores = res[0],res[1],res[2]
                        for i, det in enumerate(dets):
                            x1, y1, w, h = map(lambda x: int(round(x, 0)), det)
                            img.draw_string_advanced(x1,y1-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.colors[int(ids[i])])
                    else:
                        img.clear()
                else:
                    pass
            elif self.mode=="image":
                if self.task_type=="classify":
                    ids,score=res[0],res[1]
                    if ids!=-1:
                        mes=self.labels[ids]+" "+str(round(score,3))
                        img.draw_string_advanced(5,5,32,mes,color=(0,255,0))
                    img.compress_for_ide()
                elif self.task_type=="detect":
                    if res:
                        for det in res:
                            x1, y1, x2, y2 = map(lambda x: int(round(x, 0)), det[:4])
                            x,y=int(x1),int(y1)
                            w = int(x2 - x1)
                            h = int(y2 - y1)
                            img.draw_rectangle(x,y,w,h,color=self.colors[int(det[5])],thickness=4)
                            img.draw_string_advanced( x , y-25,20," " + self.labels[int(det[5])] + " " + str(round(det[4],2)) , color=self.colors[int(det[5])])
                    img.compress_for_ide()
                elif self.task_type=="segment":
                    if res[0]:
                        mask_rgb=self.masks[0,:,:,1:4]
                        mask_img=image.Image(self.rgb888p_size[0], self.rgb888p_size[1], image.RGB888,alloc=image.ALLOC_REF,data=mask_rgb.copy())
                        dets,ids,scores = res[0],res[1],res[2]
                        for i, det in enumerate(dets):
                            x, y, w, h = map(lambda x: int(round(x, 0)), det)
                            mask_img.draw_string_advanced(x,y-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.colors[int(ids[i])])
                        mask_img.compress_for_ide()
                else:
                    pass


    # 多目标检测 非最大值抑制方法实现
    def nms(self,boxes,scores,thresh):
        """Pure Python NMS baseline."""
        x1,y1,x2,y2 = boxes[:, 0],boxes[:, 1],boxes[:, 2],boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = np.argsort(scores,axis = 0)[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            new_x1,new_y1,new_x2,new_y2,new_areas = [],[],[],[],[]
            for order_i in order:
                new_x1.append(x1[order_i])
                new_x2.append(x2[order_i])
                new_y1.append(y1[order_i])
                new_y2.append(y2[order_i])
                new_areas.append(areas[order_i])
            new_x1 = np.array(new_x1)
            new_x2 = np.array(new_x2)
            new_y1 = np.array(new_y1)
            new_y2 = np.array(new_y2)
            xx1 = np.maximum(x1[i], new_x1)
            yy1 = np.maximum(y1[i], new_y1)
            xx2 = np.minimum(x2[i], new_x2)
            yy2 = np.minimum(y2[i], new_y2)
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            new_areas = np.array(new_areas)
            ovr = inter / (areas[i] + new_areas - inter)
            new_order = []
            for ovr_i,ind in enumerate(ovr):
                if ind < thresh:
                    new_order.append(order[ovr_i])
            order = np.array(new_order,dtype=np.uint8)
        return keep


class YOLOv8(AIBase):
    def __init__(self,task_type="detect",mode="video",kmodel_path="",labels=[],rgb888p_size=[320,320],model_input_size=[320,320],display_size=[1920,1080],conf_thresh=0.5,nms_thresh=0.45,mask_thresh=0.5,max_boxes_num=50,debug_mode=0):
        if task_type not in ["classify","detect","segment"]:
            print("Please select the correct task_type parameter, including 'classify', 'detect', 'segment'.")
            return
        super().__init__(kmodel_path,model_input_size,rgb888p_size,debug_mode)
        self.task_type=task_type
        self.mode=mode
        self.kmodel_path=kmodel_path
        self.labels=labels
        self.class_num=len(labels)
        if mode=="video":
            self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        else:
            self.rgb888p_size=[rgb888p_size[0],rgb888p_size[1]]
        self.model_input_size=model_input_size
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]

        self.conf_thresh=conf_thresh
        self.nms_thresh=nms_thresh
        self.mask_thresh=mask_thresh
        self.max_boxes_num=max_boxes_num
        self.debug_mode=debug_mode

        self.scale=1.0
        self.colors=get_colors(len(self.labels))
        self.masks=None
        if self.task_type=="segment":
            if self.mode=="image":
                self.masks=np.zeros((1,self.rgb888p_size[1],self.rgb888p_size[0],4),dtype=np.uint8)
            elif self.mode=="video":
                self.masks=np.zeros((1,self.display_size[1],self.display_size[0],4),dtype=np.uint8)
        # Ai2d实例，用于实现模型预处理
        self.ai2d=Ai2d(self.debug_mode)
        # 设置Ai2d的输入输出格式和类型
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)

    # 配置预处理操作，这里使用了resize，Ai2d支持crop/shift/pad/resize/affine，具体代码请打开/sdcard/app/libs/AI2D.py查看
    def config_preprocess(self,input_image_size=None):
        with ScopedTiming("set preprocess config",self.debug_mode > 0):
            # 初始化ai2d预处理配置，默认为sensor给到AI的尺寸，您可以通过设置input_image_size自行修改输入尺寸
            ai2d_input_size=input_image_size if input_image_size else self.rgb888p_size
            if self.task_type=="classify":
                top,left,m=center_crop_param(self.rgb888p_size)
                self.ai2d.crop(left,top,m,m)
            elif self.task_type=="detect":
                # 计算padding参数
                top,bottom,left,right,self.scale=letterbox_pad_param(self.rgb888p_size,self.model_input_size)
                # 配置padding预处理
                self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [128,128,128])
            elif self.task_type=="segment":
                top,bottom,left,right,scale=letterbox_pad_param(self.rgb888p_size,self.model_input_size)
                self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [128,128,128])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            # build参数包含输入shape和输出shape
            self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],[1,3,self.model_input_size[1],self.model_input_size[0]])

    def postprocess(self,results):
        with ScopedTiming("postprocess",self.debug_mode > 0):
            if self.task_type=="classify":
                scores=results[0][0]
                max_score=np.max(scores)
                res_idx=np.argmax(scores)
                cls_res=(-1,0.0)
                # 如果类别分数大于阈值，返回当前类别和分数
                if max_score>self.conf_thresh:
                    cls_res=(res_idx,max_score)
                return cls_res
            elif self.task_type=="detect":
                output_data = results[0][0]
                output_data=output_data.transpose()
                boxes_ori = output_data[:,0:4]
                class_ori = output_data[:,4:]
                class_res=np.argmax(class_ori,axis=-1)
                scores_ = np.max(class_ori,axis=-1)
                boxes,inds,scores=[],[],[]
                for i in range(len(boxes_ori)):
                    if scores_[i]>self.conf_thresh:
                        x,y,w,h=boxes_ori[i][0],boxes_ori[i][1],boxes_ori[i][2],boxes_ori[i][3]
                        x1 = int((x - 0.5 * w)/self.scale)
                        y1 = int((y - 0.5 * h)/self.scale)
                        x2 = int((x + 0.5 * w)/self.scale)
                        y2 = int((y + 0.5 * h)/self.scale)
                        boxes.append([x1,y1,x2,y2])
                        inds.append(class_res[i])
                        scores.append(scores_[i])
                if len(boxes)==0:
                    return []
                boxes = np.array(boxes)
                scores = np.array(scores)
                inds = np.array(inds)
                # NMS过程
                keep = self.nms(boxes,scores,self.nms_thresh)
                dets = np.concatenate((boxes, scores.reshape((len(boxes),1)), inds.reshape((len(boxes),1))), axis=1)
                det_res = []
                for keep_i in keep:
                    det_res.append(dets[keep_i])
                det_res = np.array(det_res)
                det_res = det_res[:self.max_boxes_num, :]
                return det_res
            elif self.task_type=="segment":
                new_result=results[0][0].transpose()
                if self.mode=="image":
                    seg_res = aidemo.yolov8_seg_postprocess(new_result.copy(),results[1][0],[self.rgb888p_size[1],self.rgb888p_size[0]],[self.model_input_size[1],self.model_input_size[0]],[self.rgb888p_size[1],self.rgb888p_size[0]],len(self.labels),self.conf_thresh,self.nms_thresh,self.mask_thresh,self.masks)
                elif self.mode=="video":
                    seg_res = aidemo.yolov8_seg_postprocess(new_result.copy(),results[1][0],[self.rgb888p_size[1],self.rgb888p_size[0]],[self.model_input_size[1],self.model_input_size[0]],[self.display_size[1],self.display_size[0]],len(self.labels),self.conf_thresh,self.nms_thresh,self.mask_thresh,self.masks)
                return seg_res

    def draw_result(self,res,img):
        with ScopedTiming("draw result",self.debug_mode > 0):
            if self.mode=="video":
                if self.task_type=="classify":
                    ids,score=res[0],res[1]
                    if ids!=-1:
                        img.clear()
                        mes=self.labels[ids]+" "+str(round(score,3))
                        img.draw_string_advanced(5,5,32,mes,color=(0,255,0))
                    else:
                        img.clear()
                elif self.task_type=="detect":
                    if res:
                        img.clear()
                        for det in res:
                            x1, y1, x2, y2 = map(lambda x: int(round(x, 0)), det[:4])
                            x= x1*self.display_size[0] // self.rgb888p_size[0]
                            y= y1*self.display_size[1] // self.rgb888p_size[1]
                            w = (x2 - x1) * self.display_size[0] // self.rgb888p_size[0]
                            h = (y2 - y1) * self.display_size[1] // self.rgb888p_size[1]
                            img.draw_rectangle(x,y, w, h, color=self.colors[int(det[5])],thickness=4)
                            img.draw_string_advanced( x , y-50,32," " + self.labels[int(det[5])] + " " + str(round(det[4],2)) , color=self.colors[int(det[5])])
                    else:
                        img.clear()
                elif self.task_type=="segment":
                    if res[0]:
                        img.clear()
                        mask_img=image.Image(self.display_size[0], self.display_size[1], image.ARGB8888,alloc=image.ALLOC_REF,data=self.masks)
                        img.copy_from(mask_img)
                        dets,ids,scores = res[0],res[1],res[2]
                        for i, det in enumerate(dets):
                            x1, y1, w, h = map(lambda x: int(round(x, 0)), det)
                            img.draw_string_advanced(x1,y1-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.colors[int(ids[i])])
                    else:
                        img.clear()
                else:
                    pass
            elif self.mode=="image":
                if self.task_type=="classify":
                    ids,score=res[0],res[1]
                    if ids!=-1:
                        mes=self.labels[ids]+" "+str(round(score,3))
                        img.draw_string_advanced(5,5,32,mes,color=(0,255,0))
                    img.compress_for_ide()
                elif self.task_type=="detect":
                    if res:
                        for det in res:
                            x1, y1, x2, y2 = map(lambda x: int(round(x, 0)), det[:4])
                            x,y=int(x1),int(y1)
                            w = int(x2 - x1)
                            h = int(y2 - y1)
                            img.draw_rectangle(x,y,w,h,color=self.colors[int(det[5])],thickness=4)
                            img.draw_string_advanced( x , y-25,20," " + self.labels[int(det[5])] + " " + str(round(det[4],2)) , color=self.colors[int(det[5])])
                    img.compress_for_ide()
                elif self.task_type=="segment":
                    if res[0]:
                        mask_rgb=self.masks[0,:,:,1:4]
                        mask_img=image.Image(self.rgb888p_size[0], self.rgb888p_size[1], image.RGB888,alloc=image.ALLOC_REF,data=mask_rgb.copy())
                        dets,ids,scores = res[0],res[1],res[2]
                        for i, det in enumerate(dets):
                            x, y, w, h = map(lambda x: int(round(x, 0)), det)
                            mask_img.draw_string_advanced(x,y-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.colors[int(ids[i])])
                        mask_img.compress_for_ide()
                else:
                    pass


    # 多目标检测 非最大值抑制方法实现
    def nms(self,boxes,scores,thresh):
        """Pure Python NMS baseline."""
        x1,y1,x2,y2 = boxes[:, 0],boxes[:, 1],boxes[:, 2],boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = np.argsort(scores,axis = 0)[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            new_x1,new_y1,new_x2,new_y2,new_areas = [],[],[],[],[]
            for order_i in order:
                new_x1.append(x1[order_i])
                new_x2.append(x2[order_i])
                new_y1.append(y1[order_i])
                new_y2.append(y2[order_i])
                new_areas.append(areas[order_i])
            new_x1 = np.array(new_x1)
            new_x2 = np.array(new_x2)
            new_y1 = np.array(new_y1)
            new_y2 = np.array(new_y2)
            xx1 = np.maximum(x1[i], new_x1)
            yy1 = np.maximum(y1[i], new_y1)
            xx2 = np.minimum(x2[i], new_x2)
            yy2 = np.minimum(y2[i], new_y2)
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            new_areas = np.array(new_areas)
            ovr = inter / (areas[i] + new_areas - inter)
            new_order = []
            for ovr_i,ind in enumerate(ovr):
                if ind < thresh:
                    new_order.append(order[ovr_i])
            order = np.array(new_order,dtype=np.uint8)
        return keep


class YOLO11(AIBase):
    def __init__(self,task_type="detect",mode="video",kmodel_path="",labels=[],rgb888p_size=[320,320],model_input_size=[320,320],display_size=[1920,1080],conf_thresh=0.5,nms_thresh=0.45,mask_thresh=0.5,max_boxes_num=50,debug_mode=0):
        if task_type not in ["classify","detect","segment"]:
            print("Please select the correct task_type parameter, including 'classify', 'detect', 'segment'.")
            return
        super().__init__(kmodel_path,model_input_size,rgb888p_size,debug_mode)
        self.task_type=task_type
        self.mode=mode
        self.kmodel_path=kmodel_path
        self.labels=labels
        self.class_num=len(labels)
        if mode=="video":
            self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        else:
            self.rgb888p_size=[rgb888p_size[0],rgb888p_size[1]]
        self.model_input_size=model_input_size
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]

        self.conf_thresh=conf_thresh
        self.nms_thresh=nms_thresh
        self.mask_thresh=mask_thresh
        self.max_boxes_num=max_boxes_num
        self.debug_mode=debug_mode

        self.scale=1.0
        self.colors=get_colors(len(self.labels))
        self.masks=None
        if self.task_type=="segment":
            if self.mode=="image":
                self.masks=np.zeros((1,self.rgb888p_size[1],self.rgb888p_size[0],4),dtype=np.uint8)
            elif self.mode=="video":
                self.masks=np.zeros((1,self.display_size[1],self.display_size[0],4),dtype=np.uint8)
        # Ai2d实例，用于实现模型预处理
        self.ai2d=Ai2d(self.debug_mode)
        # 设置Ai2d的输入输出格式和类型
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)

    # 配置预处理操作，这里使用了resize，Ai2d支持crop/shift/pad/resize/affine，具体代码请打开/sdcard/app/libs/AI2D.py查看
    def config_preprocess(self,input_image_size=None):
        with ScopedTiming("set preprocess config",self.debug_mode > 0):
            # 初始化ai2d预处理配置，默认为sensor给到AI的尺寸，您可以通过设置input_image_size自行修改输入尺寸
            ai2d_input_size=input_image_size if input_image_size else self.rgb888p_size
            if self.task_type=="classify":
                top,left,m=center_crop_param(self.rgb888p_size)
                self.ai2d.crop(left,top,m,m)
            elif self.task_type=="detect":
                # 计算padding参数
                top,bottom,left,right,self.scale=letterbox_pad_param(self.rgb888p_size,self.model_input_size)
                # 配置padding预处理
                self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [128,128,128])
            elif self.task_type=="segment":
                top,bottom,left,right,scale=letterbox_pad_param(self.rgb888p_size,self.model_input_size)
                self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [128,128,128])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            # build参数包含输入shape和输出shape
            self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],[1,3,self.model_input_size[1],self.model_input_size[0]])

    def postprocess(self,results):
        with ScopedTiming("postprocess",self.debug_mode > 0):
            if self.task_type=="classify":
                scores=results[0][0]
                max_score=np.max(scores)
                res_idx=np.argmax(scores)
                cls_res=(-1,0.0)
                # 如果类别分数大于阈值，返回当前类别和分数
                if max_score>self.conf_thresh:
                    cls_res=(res_idx,max_score)
                return cls_res
            elif self.task_type=="detect":
                output_data = results[0][0]
                output_data=output_data.transpose()
                boxes_ori = output_data[:,0:4]
                class_ori = output_data[:,4:]
                class_res=np.argmax(class_ori,axis=-1)
                scores_ = np.max(class_ori,axis=-1)
                boxes,inds,scores=[],[],[]
                for i in range(len(boxes_ori)):
                    if scores_[i]>self.conf_thresh:
                        x,y,w,h=boxes_ori[i][0],boxes_ori[i][1],boxes_ori[i][2],boxes_ori[i][3]
                        x1 = int((x - 0.5 * w)/self.scale)
                        y1 = int((y - 0.5 * h)/self.scale)
                        x2 = int((x + 0.5 * w)/self.scale)
                        y2 = int((y + 0.5 * h)/self.scale)
                        boxes.append([x1,y1,x2,y2])
                        inds.append(class_res[i])
                        scores.append(scores_[i])
                if len(boxes)==0:
                    return []
                boxes = np.array(boxes)
                scores = np.array(scores)
                inds = np.array(inds)
                # NMS过程
                keep = self.nms(boxes,scores,self.nms_thresh)
                dets = np.concatenate((boxes, scores.reshape((len(boxes),1)), inds.reshape((len(boxes),1))), axis=1)
                det_res = []
                for keep_i in keep:
                    det_res.append(dets[keep_i])
                det_res = np.array(det_res)
                det_res = det_res[:self.max_boxes_num, :]
                return det_res
            elif self.task_type=="segment":
                new_result=results[0][0].transpose()
                if self.mode=="image":
                    seg_res = aidemo.yolov8_seg_postprocess(new_result.copy(),results[1][0],[self.rgb888p_size[1],self.rgb888p_size[0]],[self.model_input_size[1],self.model_input_size[0]],[self.rgb888p_size[1],self.rgb888p_size[0]],len(self.labels),self.conf_thresh,self.nms_thresh,self.mask_thresh,self.masks)
                elif self.mode=="video":
                    seg_res = aidemo.yolov8_seg_postprocess(new_result.copy(),results[1][0],[self.rgb888p_size[1],self.rgb888p_size[0]],[self.model_input_size[1],self.model_input_size[0]],[self.display_size[1],self.display_size[0]],len(self.labels),self.conf_thresh,self.nms_thresh,self.mask_thresh,self.masks)
                return seg_res

    def draw_result(self,res,img):
        with ScopedTiming("draw result",self.debug_mode > 0):
            if self.mode=="video":
                if self.task_type=="classify":
                    ids,score=res[0],res[1]
                    if ids!=-1:
                        img.clear()
                        mes=self.labels[ids]+" "+str(round(score,3))
                        img.draw_string_advanced(5,5,32,mes,color=(0,255,0))
                    else:
                        img.clear()
                elif self.task_type=="detect":
                    if res:
                        img.clear()
                        for det in res:
                            x1, y1, x2, y2 = map(lambda x: int(round(x, 0)), det[:4])
                            x= x1*self.display_size[0] // self.rgb888p_size[0]
                            y= y1*self.display_size[1] // self.rgb888p_size[1]
                            w = (x2 - x1) * self.display_size[0] // self.rgb888p_size[0]
                            h = (y2 - y1) * self.display_size[1] // self.rgb888p_size[1]
                            img.draw_rectangle(x,y, w, h, color=self.colors[int(det[5])],thickness=4)
                            img.draw_string_advanced( x , y-50,32," " + self.labels[int(det[5])] + " " + str(round(det[4],2)) , color=self.colors[int(det[5])])
                    else:
                        img.clear()
                elif self.task_type=="segment":
                    if res[0]:
                        img.clear()
                        mask_img=image.Image(self.display_size[0], self.display_size[1], image.ARGB8888,alloc=image.ALLOC_REF,data=self.masks)
                        img.copy_from(mask_img)
                        dets,ids,scores = res[0],res[1],res[2]
                        for i, det in enumerate(dets):
                            x1, y1, w, h = map(lambda x: int(round(x, 0)), det)
                            img.draw_string_advanced(x1,y1-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.colors[int(ids[i])])
                    else:
                        img.clear()
                else:
                    pass
            elif self.mode=="image":
                if self.task_type=="classify":
                    ids,score=res[0],res[1]
                    if ids!=-1:
                        mes=self.labels[ids]+" "+str(round(score,3))
                        img.draw_string_advanced(5,5,32,mes,color=(0,255,0))
                    img.compress_for_ide()
                elif self.task_type=="detect":
                    if res:
                        for det in res:
                            x1, y1, x2, y2 = map(lambda x: int(round(x, 0)), det[:4])
                            x,y=int(x1),int(y1)
                            w = int(x2 - x1)
                            h = int(y2 - y1)
                            img.draw_rectangle(x,y,w,h,color=self.colors[int(det[5])],thickness=4)
                            img.draw_string_advanced( x , y-25,20," " + self.labels[int(det[5])] + " " + str(round(det[4],2)) , color=self.colors[int(det[5])])
                    img.compress_for_ide()
                elif self.task_type=="segment":
                    if res[0]:
                        mask_rgb=self.masks[0,:,:,1:4]
                        mask_img=image.Image(self.rgb888p_size[0], self.rgb888p_size[1], image.RGB888,alloc=image.ALLOC_REF,data=mask_rgb.copy())
                        dets,ids,scores = res[0],res[1],res[2]
                        for i, det in enumerate(dets):
                            x, y, w, h = map(lambda x: int(round(x, 0)), det)
                            mask_img.draw_string_advanced(x,y-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.colors[int(ids[i])])
                        mask_img.compress_for_ide()
                else:
                    pass


    # 多目标检测 非最大值抑制方法实现
    def nms(self,boxes,scores,thresh):
        """Pure Python NMS baseline."""
        x1,y1,x2,y2 = boxes[:, 0],boxes[:, 1],boxes[:, 2],boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = np.argsort(scores,axis = 0)[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            new_x1,new_y1,new_x2,new_y2,new_areas = [],[],[],[],[]
            for order_i in order:
                new_x1.append(x1[order_i])
                new_x2.append(x2[order_i])
                new_y1.append(y1[order_i])
                new_y2.append(y2[order_i])
                new_areas.append(areas[order_i])
            new_x1 = np.array(new_x1)
            new_x2 = np.array(new_x2)
            new_y1 = np.array(new_y1)
            new_y2 = np.array(new_y2)
            xx1 = np.maximum(x1[i], new_x1)
            yy1 = np.maximum(y1[i], new_y1)
            xx2 = np.minimum(x2[i], new_x2)
            yy2 = np.minimum(y2[i], new_y2)
            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            new_areas = np.array(new_areas)
            ovr = inter / (areas[i] + new_areas - inter)
            new_order = []
            for ovr_i,ind in enumerate(ovr):
                if ind < thresh:
                    new_order.append(order[ovr_i])
            order = np.array(new_order,dtype=np.uint8)
        return keep