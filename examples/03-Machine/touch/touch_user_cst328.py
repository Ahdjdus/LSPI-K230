import os, time
from machine import FPIOA, I2C, TOUCH

fpioa = FPIOA()

# gpio52 i2c3 SCL
fpioa.set_function(52, FPIOA.IIC3_SCL)
# gpio53 i2c3 sda
fpioa.set_function(53, FPIOA.IIC3_SDA)

#fpioa.help()

i2c3=I2C(3)
#print(i2c3.scan())

touch = TOUCH(1, i2c = i2c3, type = TOUCH.TYPE_CST328)

while True:
    os.exitpoint()

    point = touch.read(5)

    if len(point):
        print(point)
    time.sleep(0.1)
