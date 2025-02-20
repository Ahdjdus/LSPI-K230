# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

from machine import Pin
from machine import FPIOA
from media.sensor import *
from media.display import *
from media.media import *

import time, os, sys

# 创建FPIOA对象，用于初始化引脚功能配置
fpioa = FPIOA()

# 设置引脚功能，将指定的引脚配置为普通GPIO功能,
fpioa.set_function(62,FPIOA.GPIO62)
fpioa.set_function(20,FPIOA.GPIO20)
fpioa.set_function(63,FPIOA.GPIO63)
fpioa.set_function(53,FPIOA.GPIO53)

# 实例化Pin62, Pin20, Pin63为输出，分别控制红、绿、蓝灯
LED_R = Pin(62, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
LED_G = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
LED_B = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)

# 按键引脚为53，按下时为高电平，所以这里设置为下拉并设置为输入模式
button = Pin(53, Pin.IN, Pin.PULL_DOWN)  # 使用下拉电阻

LED_R.high()
LED_G.high()
LED_B.high()

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

# 消抖时间 20ms
debounce_time = 20
last_press_time = 0
button_last_state = 0

led_on = False

picture_width = 400
picture_height = 240

sensor_id = 2
sensor = None

Detection_Methods = ["line", "rect", "circle"]

# 设置RGB灯的颜色 
def set_color(r, g, b):
    """设置RGB灯的颜色，使用Pin.high()和Pin.low()控制"""
    if r == 0:
        LED_R.low()  # 红灯亮
    else:
        LED_R.high()  # 红灯灭

    if g == 0:
        LED_G.low()  # 绿灯亮
    else:
        LED_G.high()  # 绿灯灭

    if b == 0:
        LED_B.low()  # 蓝灯亮
    else:
        LED_B.high()  # 蓝灯灭


def Feature_detection(image, method="line"):

    count = 0  # 初始化线段计数器

    if method == "line":
        set_color(0, 1, 1)
        # 可以在此处根据需求先做一些预处理，如灰度化、边缘检测、二值化等

        # 查找线段（LSD算法）
        #  merge_distance=20         # 两线段中心点相距小于20像素则合并
        #  max_theta_diff=10        # 两线段角度差小于10°则合并
        lines = image.find_line_segments(merge_distance=20, max_theta_diff=10)
        print("------线段统计开始------")
        for line in lines:
            image.draw_line(line.line(), color=(1, 147, 230), thickness=3)  # 绘制线段
            print(f"Line {count}: {line}")  # 打印线段信息
            count += 1  # 更新计数器
        print("---------END---------")

    elif method == "rect":
        set_color(1, 0, 1)
        rects = image.find_rects(threshold=5000)
        print("------矩形统计开始------")
        for rect in rects:
             # 若想获取更详细的四个顶点，可使用 rect.corners()，该函数会返回一个有四个元祖的列表，每个元组代表矩形的四个顶点，从左上角开始，按照顺时针排序。
            image.draw_rectangle(rect.rect(), color=(1, 147, 230), thickness=3)  # 绘制线段
            print(f"Rect {count}: {rect}")  # 打印线段信息
            count += 1  # 更新计数器
        print("---------END---------")
    
    elif method == "circle":
        set_color(1, 1, 0)
        # 查找线段并绘制
        circles = image.find_circles(threshold=6000)
        print("------圆形统计开始------")
        for circle in circles:
             # 若想获取更详细的四个顶点，可使用 rect.corners()，该函数会返回一个有四个元祖的列表，每个元组代表圆形的四个顶点，从左上角开始，按照顺时针排序。
            image.draw_circle(circle.circle(), color=(1, 147, 230), thickness=3)  # 绘制线段
            print(f"Circle {count}: {circle}")  # 打印线段信息
            count += 1  # 更新计数器
        print("---------END---------") 
    
    else:
        print("不支持的检测方法")

try:
    # 构造一个具有默认配置的摄像头对象
    sensor = Sensor(id=sensor_id)
    # 重置摄像头sensor
    sensor.reset()

    # 无需进行镜像翻转
    # 设置水平镜像
    # sensor.set_hmirror(False)
    # 设置垂直翻转
    # sensor.set_vflip(False)

    # 设置通道0的输出尺寸为1920x1080
    sensor.set_framesize(width=picture_width, height=picture_height, chn=CAM_CHN_ID_0)
    # 设置通道0的输出像素格式为RGB565
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

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

    while True:
        os.exitpoint()

        # 捕获通道0的图像
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        Feature_detection(img, Detection_Methods[0])
        # 显示捕获的图像，中心对齐，居中显示
        Display.show_image(img, x=int((DISPLAY_WIDTH - picture_width) / 2), y=int((DISPLAY_HEIGHT - picture_height) / 2))

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
    MediaManager.deinit()