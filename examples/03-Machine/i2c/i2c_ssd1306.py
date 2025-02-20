from machine import FPIOA, I2C
import time

HARD_I2C = True

# use hardware i2c
if HARD_I2C:
    fpioa = FPIOA()
    fpioa.set_function(11, FPIOA.IIC2_SCL)
    fpioa.set_function(12, FPIOA.IIC2_SDA)
    i2c=I2C(2, freq = 400 * 1000)
    print(i2c.scan())
else:
    # use soft i2c
    i2c=I2C(5, scl = 11, sda = 12, freq = 400 * 1000)
    print(i2c.scan())

# SSD1306 I2C address (common values: 0x3C or 0x3D)
OLED_I2C_ADDR = 0x3C

# Function to send a command to the SSD1306
def send_command(command):
    # 0x00 indicates we're sending a command (as opposed to data)
    i2c.writeto(OLED_I2C_ADDR, bytearray([0x00, command]))

# Function to send data (for pixel values) to the SSD1306
def send_data(data):
    # 0x40 indicates we're sending data (as opposed to a command)
    i2c.writeto(OLED_I2C_ADDR, bytearray([0x40] + data))

# SSD1306 Initialization sequence (based on datasheet)
def oled_init():
    send_command(0xAE)  # Display OFF
    send_command(0xA8)  # Set MUX Ratio
    send_command(0x3F)  # 64MUX
    send_command(0xD3)  # Set display offset
    send_command(0x00)  # Offset = 0
    send_command(0x40)  # Set display start line to 0
    send_command(0xA1)  # Set segment re-map (A1 for reverse, A0 for normal)
    send_command(0xC8)  # Set COM output scan direction (C8 for reverse, C0 for normal)
    send_command(0xDA)  # Set COM pins hardware configuration
    send_command(0x12)  # Alternative COM pin config, disable left/right remap
    send_command(0x81)  # Set contrast control
    send_command(0x7F)  # Max contrast
    send_command(0xA4)  # Entire display ON, resume to RAM content display
    send_command(0xA6)  # Set Normal display (A6 for normal, A7 for inverse)
    send_command(0xD5)  # Set oscillator frequency
    send_command(0x80)  # Frequency
    send_command(0x8D)  # Enable charge pump regulator
    send_command(0x14)  # Enable charge pump
    send_command(0xAF)  # Display ON

# Function to clear the display (turn off all pixels)
def oled_clear():
    for page in range(0, 8):  # 8 pages in 64px tall screen
        send_command(0xB0 + page)  # Set page start address (0xB0 to 0xB7)
        send_command(0x00)  # Set low column address
        send_command(0x10)  # Set high column address
        send_data([0xFF] * 128)  # Clear 128 columns (1 byte per column)

# Initialize the OLED display
oled_init()
oled_clear()
