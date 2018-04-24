import logging


class Worker(object):
    type = ''

    def __init__(self, wname, config, logger=None):
        self.wname = wname
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def addToQueue(self, obj):
        # add some new message to the queue to send to the worker
        self.logger.info('Adding object to queue: `{}`'.format(obj))

    def start(self):
        # start a worker in a new process
        pass

    def update(self, input):
        # do the PID stuff
        pass
