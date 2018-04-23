import os.path
import ConfigParser
import logging
import time
import RPi.GPIO as GPIO
import ADS1256
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532


class RPiNE(object):

    def __init__(self, config_path='', logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = ConfigParser(os.path.join(config_path, 'config.cfg'))
        self.configure()

    def configure(self):
        self.max_channels = self.config.getint('MAIN', 'MaxChannels')
        self.channels = [None]*self.max_channels
        self.set_points = [None]*self.max_channels
        self.configure_logger()
        self.configure_adc()
        self.configure_workers()
        self.configure_triggers()

    def configure_adc(self):
        self.adc = ADS1256.ADS1256()

    def configure_triggers(self):
        trig_pin_list = []
        for ch in range(self.max_channels):
            # register trig pin for channel
            trig_pin = self.config.get('CHANNEL{}'.format(ch), 'TrigPin')
            if trig_pin in trig_pin_list:
                msg = 'Duplicate trigger definition detected: `{}`.'
                self.logger.warning(msg.format(trig_pin))
            else:
                trig_pin_list.append(trig_pin)
                msg = 'Channel `{}` using trigger pin: `{}`.'
                self.logger.info(msg.format(ch, trig_pin))
            GPIO.add_event_detect(trig_pin, GPIO.RISING, callback=self.take_channel_reading(ch))

    def configure_workers(self):
        for ch in range(self.max_channels):
            self.channels[ch] = None  # in case this gets called twice
            # setup the correct worker type for each feedback channel
            fb_type = self.config.get('CHANNEL{}'.format(ch), 'FeedbackDevice')
            if fb_type == WK10CR1.type:
                self.channels[ch] = WK10CR1(self.config)
            if fb_type == WDAC8532.type:
                self.channels[ch] = WDAC8532(self.config)

            if self.channels[ch] is None:
                msg = 'No feedback device specified for channel `{}`.'
                self.logger.warning(msg.format(ch))
            else:
                msg = 'Channel `{}` using `{}`.'
                self.logger.info(msg.format(ch, fb_type))

    def configure_logging(self):
        pass

    def prepare_adc(self, chan, h_chan, l_chan):
        # set up the mux to read the correct channels
        self.adc.SetInputMux(h_chan, l_chan)
        # wait for the mux to settle if necessary
        time.sleep(self.config.getfloat('MAIN'.format(chan), 'MuxSettleTimeSec'))

    def read_fixed_cycles(self, cycles):
        ref_time = time.time()
        datalist = []
        # dummy read to clear any accumulated charge
        self.adc.ReadADC()
        try:
            for i in xrange(cycles):
                datalist.append(self.adc.ReadADC())
            result = float(sum(datalist))/float(cycles)
        except:
            self.logger.exception('Problem when trying to read analog input')
            result = None
        return {'time': ref_time, 'average': result}

    def read_fixed_time(self, time_ms):
        ref_time = time.time()
        try:
            result = self.adc.ReadADCc(float(time_ms)/1000.0)
        except:
            self.logger.exception('Problem when trying to read analog input')
            result = None
        return {'time': ref_time, 'average': result}

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

        def read_callback():
            self.prepare_adc(chan, adc_high_ch, adc_low_ch)
            result = read_method(read_param)
            try:
                self.channels[chan].addToQueue(result)
            except:
                msg = 'Problem adding result: `{}` to worker queue for channel: `{}`'
                self.logger.exception(msg.format(result, chan))


if __name__ == "__main__":
    rpine = RPiNE()
    # rpine.start_workers()
    rpine.server_loop()
