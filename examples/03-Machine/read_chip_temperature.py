import os
import time
import machine

while True:
    os.exitpoint()

    temp = machine.temperature()
    print(f"Temp: {temp}")

    time.sleep_ms(500)
