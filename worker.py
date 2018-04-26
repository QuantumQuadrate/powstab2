import logging
from ivPID import PID


class Worker(object):
    type = ''

    def __init__(self, channel, config, logger=None):
        self.channel = channel
        self.wname = 'NE_CH{}_{}'.format(channel, self.type)
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.setup_pid()
        self.ready = True
        self.output = 0  # TODO: initialize with reasonable start value from config
        # could also read current state from device
        self.delta = 0  # in case an actuator needs a differential output
        self.address = self.config.getint('CHANNEL{}'.format(channel), 'Address')
        self.setup()

    def setup(self):
        "override for actuator specific initilization"
        pass

    def setup_pid(self):
        section = 'CHANNEL{}'.format(self.channel)
        kp = self.config.getfloat(section, 'Kp')
        ki = self.config.getfloat(section, 'Ki')
        kd = self.config.getfloat(section, 'Kd')
        tau_s = self.config.getfloat(section, 'TauS')
        self.invert = self.config.getboolean(section, 'Invert')
        set_point = self.config.getfloat(section, 'SetPointV')
        self.pid = PID(P=kp, I=ki, D=kd)
        self.update_setpoint(set_point)
        self.pid.setFiniteFilter(tau_s)

    def start(self):
        "override to start a worker in a new process if feedback device takes a while."
        pass

    def update(self, input_obj):
        # do the PID stuff
        # TODO: use actual timestamp from data
        input = input_obj['measurement']
        if self.ready:
            self.ready = False
            self.pid.update(input)
            out = self.pid.output
            if self.invert:
                out *= -1.0
            self.delta = out
            self.output += out
            self.logger.debug('output: `{}`'.format(self.output))
            # when done updating output set self.ready to True
            self.update_output()
        else:
            self.logger.warning('Recieved new input while busy updating the setpoint.')

    def update_setpoint(self, sp):
        self.pid.SetPoint = sp
        self.pid.clear()

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
