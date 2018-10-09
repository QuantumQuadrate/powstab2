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
from datetime import datetime

config = ''
def __init__(configFile):

    self.config = ConfigParser.ConfigParser()
    self.config.read(configFile)
    # get all the activated channels from config file
def getChannels():
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
    return channels

def getChannelConfigInfo():
    return config



def updateConfig(channels):
    newfile = "config"+str(datetime.now())+".cfg"
    with open(sub_file, 'w') as f:
        f.write("""[MAIN]
        MaxChannels: 4 ;
        ErrorPin: 36 ;"""

        for channel in channels:
            f.write('[CHANNEL'+channel['number']+']')
            for values channel.keys()
            f.close()



def setConfig(configFile):
        self.config = ConfigParser.ConfigParser()
        self.config.read(configFile)
