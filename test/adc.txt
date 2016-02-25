import smbus
import time

address = 0x48
A0 = 0x40
A1 = 0x41
A2 = 0x42
A3 = 0x43
bus = smbus.SMBus(1)

while True:
        print(time.ctime())
        # Read voltage,five multiple
        bus.write_byte(address, A0)
        value = 5.0*5.0*bus.read_byte(address)/255
        print("voltage: %1.3f V" %value)

        # Read current,using MAX471 (1V/A)
        bus.write_byte(address, A1)
        value2 = 1000.0*5.0*bus.read_byte(address)/255
        print("current: %1.3f mA" %value2)

        # Get the power
        power = value*value2
        print("power: %1.5f mW" %power)
        print(">--------------------------------------------------<")
        time.sleep(0.5)

