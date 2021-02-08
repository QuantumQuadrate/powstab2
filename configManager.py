from origin import TIMESTAMP
import ConfigParser
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532
from datetime import datetime
import os


def stream_callback(stream_id, data, log, calibration=1, field='', name='', channel=''):
    log.debug('Stream data for `{}` recieved.'.format(name))
    # send the necessary information so that the poller loop can sort the data to the
    # correct pid controller channel
    result = {
        'time': float(data[TIMESTAMP])/2**32,
        'measurement': float(calibration)*float(data[field]),
        'name': name,
        'channel': channel
    }
    log.debug('Origin result `{}`.'.format(result))
    return result


class configManager():
    config = ''
    
    def __init__(self):
        configPath = 'configs/'
        configFiles = os.listdir(configPath)
        paths = [os.path.join(configPath, basename) for basename in configFiles]
        latestConfig = max(paths, key=os.path.getctime)
        self.configFile = latestConfig
        self.config = ConfigParser.ConfigParser()
        self.config.read(latestConfig)
        # get all the activated channels from config file

    def getChannels(self):
        channels = []
        for section in self.config.sections():
            if 'CHANNEL' not in section:
                continue  # not a channel definition
            fb_type = self.config.get(section, 'FeedbackDevice')
            if fb_type in [WDAC8532.type, WK10CR1.type]:
                # get the channel number from the section title
                ch_num = int(section.rsplit('CHANNEL')[1])
                # callback has to be fully defined before Subscriber is initialized, since it starts
                # a new process and won't know about anything in the main process after it starts
                channels.append({
                    'number': ch_num,
                    'callback': stream_callback,
                    'kwargs': {
                        'calibration': 1.0,
                        'field': self.config.get(section, 'FieldName'),
                        'name': section,
                        'channel': ch_num
                    }
                })
        return channels

    def updateConfig(self):
        fileName = "configs/config"+str(datetime.now())+".cfg"
        f = open(fileName, "w+")
        with f as configfile:
            self.config.write(configfile)
        f.close()
        return ''

    def getConfigFilePath(self):
        return self.configFile

    def getConfig(self):
        return self.config

    def setConfig(self, configFile):
            self.config = ConfigParser.ConfigParser()
            self.config.read(configFile)
