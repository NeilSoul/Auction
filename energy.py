import smbus
import time
import threading

class Energy(object):

        def __init__(self, peer):
                self.peer = peer
                self.address = 0x48
                self.A0 = 0x40
                self.A1 = 0x41
                self.A2 = 0x42
                self.A3 = 0x43
                self.bus = smbus.SMBus(1)
                self.duration = 1.0

        def start(self):
                self.running = 1
                self.start_time = time.time()
                self.energy_cost = 0.0
                threading.Thread(target=self.loop).start()

        def loop(self):
                while self.running:
                        print(time.ctime())
                        # Read voltage,five multiple
                        self.bus.write_byte(self.address, self.A0)
                        # B : value = 5.0*bus.read_byte(self.address)/255
                        value = 5.0*5.0*self.bus.read_byte(self.address)/255 #A
                        print("voltage: %1.3f V" %value)

                        # Read current,using MAX471 (1V/A)
                        self.bus.write_byte(self.address, self.A1)
                        value2 = 1000.0*5.0*self.bus.read_byte(self.address)/255
                        print("current: %1.3f mA" %value2)

                        # Get the power
                        power = value*value2
                        print("power: %1.5f mW" %power)
                        print(">--------------------------------------------------<")
                        time.sleep(self.duration)
                        self.energy_cost += power * self.duration

        ''' @return energy_cost, duration '''
        def stop(self):
                self.running = 0
                return self.energy_cost, time.time() - self.start_time

def parse_args():
        parser = argparse.ArgumentParser(description='Energy')
        parser.add_argument('-p','--peer', required=False, default='Peer', help='name of peer')
        return args.peer

if __name__ == "__main__":
        peer = parse_args()
        energy  = Energy(peer)
        energy.start()
        try:
                while True:
                        command = raw_input().lower()
                        if not command or command == 'exit':
                                break
        except KeyboardInterrupt:
                pass
        cost, duration = energy.stop()
        print 'All = ', cost, 'duration = ', duration, 'power = ', cost/duration

