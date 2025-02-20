import os
import time
import machine

while True:
    os.exitpoint()
    
    chipid = machine.chipid()
    print(f"chipid {chipid}")

    time.sleep_ms(500)
