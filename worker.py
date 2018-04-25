import logging
from ivPID import PID


class Worker(object):
    type = ''

    def __init__(self, channel, config, logger=None):
        self.channel = channel
        self.wname = 'NE_CH{}_{}'.format(channel, self.type)
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.pid = PID()  # TODO: initilize with PID values from config
        self.pid.setWindup(0)  # cancels build up of integral error on large SP changes to prevent overshoots
        self.ready = True
        self.output = 0  # TODO: initialize with reasonable start value from config
        # could also read current state from device
        self.delta = 0  # in case an actuator needs a differential output
        self.address = self.config.getint('CHANNEL{}'.format(channel), 'Address')
        self.setup()

    def setup(self):
        "override for actuator specific initilization"
        pass

    def start(self):
        "override to start a worker in a new process if feedback device takes a while."
        pass

    def update(self, input_obj):
        # do the PID stuff
        input = input_obj['average']
        if self.ready:
            self.ready = False
            self.delta = self.pid.update(input)
            self.output += self.delta
            # when done updating output set self.ready to True
            self.update_output()
        else:
            self.logger.warning('Recieved new input while busy updating the setpoint.')

    def update_setpoint(self, sp):
        self.pid.SetPoint = sp

    def update_pid(self, p=None, i=None, d=None):
        if p is not None:
            self.pid.setKp(p)
        if i is not None:
            self.pid.setKi(i)
        if d is not None:
            self.pid.setKd(d)
        self.pid.clear()

    def update_output(self):
        "Override in child class.  Set self.ready to True when complete."
        raise NotImplementedError
