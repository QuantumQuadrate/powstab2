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
import subprocess
import ServerStuff.serverTest as server
import configManager


def sigterm_handler(_signo, _stack_frame):
    # from https://stackoverflow.com/a/24574672
    sys.exit(0)


# I could open a subscriber object for each channel which would multi-process
# the actuators
if __name__ == '__main__':
    # setup a catch for SIGTERM so process can be killed gracefully in the background
    signal.signal(signal.SIGTERM, sigterm_handler)

    time.sleep(1)
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



    # get the feedback config files
    configFiles = os.listdir('configs/')
    paths = [os.path.join(path, basename) for basename in files]
    latestConfig = max(paths, key=os.path.getctime)
    print latestConfig
    conMan = configManager.configManager(latestConfig)
    channels = conMan.getChannels()
    conMan.updateConfig(1, "StreamName", "toy")
    # get the origin config file
    origin_config = ConfigParser.ConfigParser()
    origin_config.read('origin-server.cfg')

    # setup subcription object with special pid poller loop
    sub = Subscriber(origin_config, logger, loop=pid_poller.pid_poller_loop)
    # read channels from feedback config file
    streamName = ''
    for channel in channels:
        streamName = conMan.config.get('CHANNEL{}'.format(channel['number']), 'StreamName')
        sub.subscribe(
            streamName,
            callback=channel['callback'],
            **channel['kwargs']
        )

    server.runServer(sub, streamName)

    sub.close()
    logger.info('closing')
