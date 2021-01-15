from worker import Worker
import threading
from PDR1.pdr1 import PDR1


class WPDR1(Worker):
    type = 'PDR1'

    def setup(self):
        # setup motor
        self.ser_num = self.config.get('CHANNEL{}'.format(self.channel), 'Address')
        self.motchan = self.config.get('CHANNEL{}'.format(self.channel), 'Motor_channel')
        self.motor = PDR1(self.ser_num,self.motchan)
        # setup thread for actuator since moving rotator can take some time
        self.restart = threading.Event()  # make an event for unpausing execution thread
        self.thread = threading.Thread(target=self.loop, name=self.wname)
        self.thread.daemon = True  # stop thread on exit of main program
        self.thread.start()

    def update_output(self):
        # wake up thread (which will push the new output to the rotator)
        self.restart.set()
        self.restart.clear()

    def loop(self):
        while True:
            self.restart.wait()  # wait for event from main thread
            msg = '{}: Pushing new output to rotator: {}'
            self.logger.debug(msg.format(self.wname, self.ser_num))
            self.motor.moverel(self.delta)
            self.ready = True  # let the controller know it can accept new inputs
