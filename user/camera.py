# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

import time, os, sys

from media.sensor import *
from media.display import *
from media.media import *

sensor_id = 2
sensor = None

picture_width = 400
picture_height = 240


# 显示模式选择：可以是 "VIRT"、"LCD" 或 "HDMI"
DISPLAY_MODE = "LCD"

# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    # 3.1寸屏幕模式
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id,width=1920, height=1080)
    # 重置摄像头sensor
    sensor.reset()

    # 无需进行镜像和翻转
    # 设置不要水平镜像
    sensor.set_hmirror(False)
    # 设置不要垂直翻转
    sensor.set_vflip(False)

    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB565，要注意有些案例只支持GRAYSCALE格式
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
    # sensor.set_pixformat(Sensor.GRAYSCALE, chn=CAM_CHN_ID_0)

    # 根据模式初始化显示器
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)

    # 初始化媒体管理器
    MediaManager.init()
    # 启动传感器
    sensor.run()

    fps = time.clock()

    while True:
        fps.tick()
        os.exitpoint()

        # 捕获通道0的图像
        src_img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 在屏幕左上角显示原始图像
        Display.show_image(src_img,x=0,y=0,layer = Display.LAYER_OSD0)

        # 图像处理放到这里
        #--------开始--------
        
        # 这里可以插入各种图像处理逻辑，例如二值化、直方图均衡化、滤波等

        # src_img.histeq() # 调用直方图均衡化方法
        # src_img.gamma_corr(gamma = 3) # 调用 gamma_corr 方法
        # src_img.rotation_corr(0.5) # 旋转图像
        # src_img.lens_corr(3.0)  # 调用 lens_corr 方法
        src_img.laplacian(2,mul=0.2)  # 拉普拉斯边缘检测，窗口大小为 3
        
        # 像素格式 GRAYSCALE
        # src_img.binary([(50, 180)],invert=False)  # 二值化，阈值范围为 (100, 255),不进行像素值反转，需要设置像素输出格式为 GRAYSCALE
        # src_img.find_edges(image.EDGE_CANNY, threshold=(50, 80)) # 边缘检测，使用 Canny 算法，阈值为 (50, 80)
        # src_img.find_edges(image.EDGE_SIMPLE, threshold=(50, 255)) # 边缘检测，使用 SIMPLE 算法，阈值为 (50, 255)

        #--------结束--------

        # 在屏幕右上角显示处理后的图像
        Display.show_image(src_img,x=DISPLAY_WIDTH-picture_width,y=0,layer = Display.LAYER_OSD1)

        # 打印帧率到控制台
        print(fps.fps())

except KeyboardInterrupt as e:
    print("用户停止: ", e)
except BaseException as e:
    print(f"异常: {e}")
finally:
    # 停止传感器运行
    if isinstance(sensor, Sensor):
        sensor.stop()
    # 反初始化显示模块
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # 释放媒体缓冲区
