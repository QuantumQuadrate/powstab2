#!/usr/bin/python

from origin.client.origin_subscriber import Subscriber
from origin import TIMESTAMP
import time
import logging
import signal
import sys
import ConfigParser
import pid_poller
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532
import os

def sigterm_handler(_signo, _stack_frame):
    # from https://stackoverflow.com/a/24574672
    sys.exit(0)


def stream_callback(stream_id, data, log, calibration=1, field='', name='', channel=''):
    log.debug('Stream data for `{}` recieved.'.format(name))
    # send the necessary information so that the poller loop can sort the data to the
    # correct pid controller channel
    result = {
        'time': float(data[TIMESTAMP])/2**32,
        'measurement': calibration*data[field],
        'name': name,
        'channel': channel,
        'config': config,
    }
    log.debug('Origin result `{}`.'.format(result))
    return result


# I could open a subscriber object for each channel which would multi-process
# the actuators
if __name__ == '__main__':
    # setup a catch for SIGTERM so process can be killed gracefully in the background
    signal.signal(signal.SIGTERM, sigterm_handler)
    os.system('python ServerStuff/serverTest.py')
    # setup logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    fh = logging.FileHandler('pid.log')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.info('Started logging')

    # 12b 5V ADC calibration
    adc_word = 12
    v_ref = 5.0
    calib = v_ref/((2**adc_word)-1)

    # get the feedback config files
    config = ConfigParser.ConfigParser()
    config.read('config.cfg')
    # get all the activated channels from config file
    channels = []
    for section in config.sections():
        if 'CHANNEL' not in section:
            continue  # not a channel definition
        fb_type = config.get(section, 'FeedbackDevice')
        if fb_type in [WDAC8532.type, WK10CR1.type]:
            # get the channel number from the section title
            ch_num = int(section.rsplit('CHANNEL')[1])
            # callback has to be fully defined before Subscriber is initialized, since it starts
            # a new process and won't know about anything in the main process after it starts
            channels.append({
                'number': ch_num,
                'callback': stream_callback,
                'kwargs': {
                    'calibration': calib,
                    'field': config.get(section, 'FieldName'),
                    'name': section,
                    'channel': ch_num
                }
            })
    logger.info('Detected {} channel definitions from config file.'.format(len(channels)))

    # get the origin config file
    origin_config = ConfigParser.ConfigParser()
    origin_config.read('origin-server.cfg')

    # setup subcription object with special pid poller loop
    sub = Subscriber(origin_config, logger, loop=pid_poller.pid_poller_loop)
    # read channels from feedback config file
    for channel in channels:
        streamName = config.get('CHANNEL{}'.format(channel['number']), 'StreamName')
        sub.subscribe(
            streamName,
            callback=channel['callback'],
            **channel['kwargs']
        )

    sub.close()
    logger.info('closing')
