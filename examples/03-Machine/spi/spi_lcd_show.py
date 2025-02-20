import time, image
from machine import FPIOA, Pin, SPI, SPI_LCD

fpioa = FPIOA()

fpioa.set_function(19, FPIOA.GPIO19)
pin_cs = Pin(19, Pin.OUT, pull=Pin.PULL_NONE, drive=15)
pin_cs.value(1)

fpioa.set_function(20, FPIOA.GPIO20)
pin_dc = Pin(20, Pin.OUT, pull=Pin.PULL_NONE, drive=15)
pin_dc.value(1)

fpioa.set_function(44, FPIOA.GPIO44, pu = 1)
pin_rst = Pin(44, Pin.OUT, pull=Pin.PULL_UP, drive=15)

# spi
fpioa.set_function(15, fpioa.QSPI0_CLK)
fpioa.set_function(16, fpioa.QSPI0_D0)

spi1 = SPI(1,baudrate=1000*1000*50, polarity=1, phase=1, bits=8)


lcd = SPI_LCD(spi1, pin_dc, pin_cs, pin_rst)

lcd.configure(320, 240, hmirror = False, vflip = True, bgr = False)

print(lcd)

img = lcd.init()
print(img)

img.clear()
img.draw_string_advanced(0,0,32, "RED, 你好世界~", color = (255, 0, 0))
img.draw_string_advanced(0,40,32, "GREEN, 你好世界~", color = (0, 255, 0))
img.draw_string_advanced(0,80,32, "BLUE, 你好世界~", color = (0, 0, 255))

lcd.show()
