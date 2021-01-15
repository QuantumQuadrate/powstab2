import logging
import time
from ivPID import PID
import ConfigParser
import os
import filecmp
from origin.client import server
from origin import current_time, TIMESTAMP
import ConfigParser


class Worker(object):
    type = ''

    def __init__(self, channel, config, logger=None):
        self.channel = channel
        self.wname = 'NE_CH{}_{}'.format(channel, self.type)
        self.config = config
        configPath = 'configs/'
        configFiles = os.listdir(configPath)
        paths = [os.path.join(configPath, basename) for basename in configFiles]
        latestConfig = max(paths, key=os.path.getctime)
        self.currentConfig = latestConfig
        self.logger = logger or logging.getLogger(__name__)
        self.setup_pid()
        self.ready = True
        self.output = 0  # TODO: initialize with reasonable start value from config
        # could also read current state from device
        self.delta = 0  # in case an actuator needs a differential output
        tmpaddress = str(self.config.getint('CHANNEL{}'.format(channel), 'Address'))
        if(len(tmpaddress) == 9):
            self.address = int(tmpaddress[0:8])
            self.motchan = int(tmpaddress[8])
        else:
            self.address = int(tmpaddress)
        # self.address = self.config.getint('CHANNEL{}'.format(channel), 'Address')
        # self.motchan = self.config.getint('CHANNEL{}'.format(channel), 'Motor_channel')
        self.setup()
        self.last_update = time.time()
        self.last_pos_log = time.time()
        self.connection = ''
        self.origin_config = ''

    def setup(self):
        "override for actuator specific initilization"
        pass

    def updateConfig(self):
        configPath = 'configs/'
        configFiles = os.listdir(configPath)
        paths = [os.path.join(configPath, basename) for basename in configFiles]
        latestConfig = max(paths, key=os.path.getctime)
        if latestConfig != self.currentConfig:
            self.config = ConfigParser.ConfigParser()
            self.config.read(latestConfig)
            self.setup_pid()
            self.currentConfig = latestConfig
        
        return ''

    def setup_pid(self):
        section = 'CHANNEL{}'.format(self.channel)
        kp = self.config.getfloat(section, 'Kp')
        ki = self.config.getfloat(section, 'Ki')
        kd = self.config.getfloat(section, 'Kd')
        tau_s = self.config.getfloat(section, 'TauS')
        self.invert = self.config.getboolean(section, 'Invert')
        set_point = self.config.getfloat(section, 'SetPointV')
        self.max_error = self.config.getfloat(section, 'MaxErrorV')
        self.pid = PID(P=kp, I=ki, D=kd)
        self.update_setpoint(set_point)
        self.pid.setFiniteFilter(tau_s)
        self.error_sig = False

    def start(self):
        "override to start a worker in a new process if feedback device takes a while."
        pass

    def update(self, input_obj):
        # do the PID stuff
        # TODO: use actual timestamp from data
        input = input_obj['measurement']
        # if we end up in a wierd state where the ready pin does get set back then just continue
        if self.ready or (time.time()-self.last_update) > 10:
            self.ready = False
            self.last_update = time.time()
            out = self.pid.update(input)
            if self.invert:
                out *= -1.0
            self.delta = out
            self.output += out
            if time.time() - self.last_pos_log > 15:
                self.logger.info('[{}] input: `{:.3f}`, error: `{:.3f}`, output: `{:.3f}`'.format(
                    self.wname,
                    input,
                    self.pid.last_error,
                    self.output
                ))
                self.last_pos_log = time.time()
            else:
                self.logger.debug('[{}] output: `{:.3f}`'.format(self.wname, self.output))
            # when done updating output set self.ready to True
            self.update_output()
            self.logger.debug('[{}] error {:05.3f}, max error {:05.3f}'.format(self.wname, self.pid.last_error, self.max_error))
        else:
            self.logger.warning('[{}] Recieved new input while busy updating the setpoint.'.format(self.wname))
        if abs(input - self.pid.SetPoint) > self.max_error:
            self.error_sig = True
        else:
            self.error_sig = False
        return self.error_sig

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
        "Override in child class. Set self.ready to True when complete."
        raise NotImplementedError

    def sendOutput(self):
        ts = current_time(self.origin_config)
        data = {TIMESTAMP: ts, "Output": self.output}
        self.connection.send(**data)

    def startClient(self):
        config_file = 'origin-client.cfg'
        self.origin_config = ConfigParser.ConfigParser()
        self.origin_config.read(config_file)

        serv = server(self.origin_config)

        self.connection = serv.registerStream(
            stream="PIDworker",
            records={
                "Output": "float",
                "Output": "float"
                })
