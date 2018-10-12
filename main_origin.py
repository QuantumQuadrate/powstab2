#!/usr/bin/python

from origin.client.origin_subscriber import Subscriber
import time
import logging
import signal
import sys
import pid_poller
import ServerStuff.serverTest as server
import configManager
import ConfigParser


def sigterm_handler(_signo, _stack_frame):
    # from https://stackoverflow.com/a/24574672
    sys.exit(0)


if __name__ == '__main__':
    f = open("outputValue.txt", "w+")
    f.write('0.0')
    f.close()
    dataTracker = open("ServerStuff/static/data.txt", "w+")
    dataTracker.close()
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
    conMan = configManager.configManager()
    channels = conMan.getChannels()

    # get the origin config file
    origin_config = ConfigParser.ConfigParser()
    origin_config.read('origin-server.cfg')

    # setup subcription object with special pid poller loop
    sub = Subscriber(origin_config, logger, loop=pid_poller.pid_poller_loop)
    # read channels from feedback config file
    streamName = ''
    print channels
    for channel in channels:
        if channel['number'] == 2:
            print "made one"
            streamName = conMan.config.get('CHANNEL{}'.format(channel['number']), 'StreamName')
            sub.subscribe(
                streamName,
                callback=channel['callback'],
                **channel['kwargs']
            )

    server.runServer(sub, streamName, conMan)

    sub.close()
    logger.info('closing')
