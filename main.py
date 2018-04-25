import os.path
import ConfigParser
import logging
import time
import RPi.GPIO as GPIO
import ads1256.ADS1256 as ads
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532


class RPiNE(object):

    def __init__(self, config_path='', logger=None):
        if logger is None:
            self.configure_logger()
        else:
            self.logger = logging.getLogger(__name__)
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.join(config_path, 'config.cfg'))
        self.configure()

    def configure(self):
        self.max_channels = self.config.getint('MAIN', 'MaxChannels')
        self.channels = [None]*self.max_channels
        self.set_points = [None]*self.max_channels
        self.configure_adc()
        self.configure_workers()
        self.configure_triggers()

    def configure_adc(self):
        pass

    def configure_triggers(self):
        GPIO.setmode(GPIO.BOARD)  # define the pin numbering (i think)
        trig_pin_list = []
        for ch in range(self.max_channels):
            # register trig pin for channel
            trig_pin = self.config.getint('CHANNEL{}'.format(ch), 'TrigPin')
            if trig_pin in trig_pin_list:
                msg = 'Duplicate trigger definition detected: `{}`.'
                self.logger.warning(msg.format(trig_pin))
            else:
                trig_pin_list.append(trig_pin)
                GPIO.setup(trig_pin, GPIO.IN)
                msg = 'Channel `{}` using trigger pin: `{}`.'
                self.logger.info(msg.format(ch, trig_pin))
            GPIO.add_event_detect(trig_pin, GPIO.RISING, callback=self.take_channel_reading(ch))

    def configure_workers(self):
        for ch in range(self.max_channels):
            self.channels[ch] = None  # in case this gets called twice
            # setup the correct worker type for each feedback channel
            fb_type = self.config.get('CHANNEL{}'.format(ch), 'FeedbackDevice')
            if fb_type == WK10CR1.type:
                self.channels[ch] = WK10CR1(ch, self.config)
            if fb_type == WDAC8532.type:
                self.channels[ch] = WDAC8532(ch, self.config)

            if self.channels[ch] is None:
                msg = 'No feedback device specified for channel `{}`.'
                self.logger.warning(msg.format(ch))
            else:
                msg = 'Channel `{}` using `{}`.'
                self.logger.info(msg.format(ch, fb_type))

    def configure_logger(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)  # change to info later
        formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.info('new logger initialized')

    def read_fixed_cycles(self, channel, log2_cycles):
        ref_time = time.time()
        try:
            result = ads.read_diff(channel, log2_cycles)
        except:
            self.logger.exception('Problem when trying to read analog input')
            result = None
        return {'time': ref_time, 'average': result}

    def read_fixed_time(self, channel, time_ms):
        ref_time = time.time()
        time_unit = 1000.0/float(ads.MAX_DATA_RATE)  # minimum sample time in ms
        log2_cycles = 0
        for i in range(15):
            time_unit *= 2
            if time_unit > time_ms:
                time_ms = time_unit/2
                log2_cycles = i
                break
        self.logger.debug("Using `{}` for `{}` ms.".format(log2_cycles, time_ms))
        return self.read_fixed_cycles(channel, log2_cycles)

    def start_workers(self):
        for ch in self.channels:
            if ch is not None:
                ch.start()

    def server_loop(self):
        # open a server interface
        try:
            while(True):
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('Shutting down server on request.')

    def take_channel_reading(self, chan):
        '''Return a function pointer to be used in a callback for reading an input channel
        and putting a message on the appropriate worker queue.'''
        # get the two channels to use as differential read channels
        adc_high_ch = self.config.getint('CHANNEL{}'.format(chan), 'ADCHigh')
        adc_low_ch = self.config.getint('CHANNEL{}'.format(chan), 'ADCLow')
        # read and average for a fixed time or a fixed number of cycles
        read_param = self.config.get('CHANNEL{}'.format(chan), 'ReadTime')
        read_method = self.read_fixed_time
        # if read time is 0 or negative use the
        if read_param <= 0:
            read_param = self.config.get('CHANNEL{}'.format(chan), 'ReadCycles')
            if read_param <= 0:
                msg = 'Channel `{}` has an unusable `ReadTime` and `ReadCycles` specified.  One must be >0'
                self.logger.error(msg.format(chan))
                read_param = 1
            read_method = self.read_fixed_cycles

        def read_callback(trig_chan):
            self.logger.debug('Trigger for channel `{}` detected.'.format(chan))
            result = read_method(chan, read_param)
            self.logger.debug('ADC read result `{}`.'.format(result))
            try:
                self.channels[chan].update(result)
            except:
                msg = 'Problem adding result: `{}` to worker queue for channel: `{}`'
                self.logger.exception(msg.format(result, chan))

        return read_callback


if __name__ == "__main__":
    rpine = RPiNE()
    # rpine.start_workers()
    rpine.server_loop()
