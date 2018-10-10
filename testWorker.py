#!/usr/bin/env python
import sys
import os
import random
import time
from origin.client import server
from origin import current_time, TIMESTAMP
import ConfigParser
import math


class testWorker(object):
    """docstring for ."""

    def __init__(self):
        startServer()

    def startServer(self):
        # first find ourself
        fullBinPath = os.path.abspath(os.getcwd() + "/" + sys.argv[0])
        fullBasePath = os.path.dirname(os.path.dirname(fullBinPath))
        fullLibPath = os.path.join(fullBasePath, "lib")
        fullCfgPath = os.path.join(fullBasePath, "config")
        sys.path.append(fullLibPath)

        if len(sys.argv) > 1:
            if sys.argv[1] == 'test':
                configfile = os.path.join(fullCfgPath, "origin-server-test.cfg")
            else:
                configfile = os.path.join(fullCfgPath, sys.argv[1])
        else:
            configfile = os.path.join(fullCfgPath, "origin-server.cfg")

        self.config = ConfigParser.ConfigParser()
        self.config.read(configfile)

        serv = server(self.config)

        self.connection = serv.registerStream(
            stream="toy",
            records={
                "toy1": "float",
                "toy2": "float",
                "testMeasurement1": "float",
                "testMeasurement2": "float",
                })

    def makeTempMeasurement():
        return random.random()

    def makeTestMeasurement(self, output):
        return math.exp(output)

    def streamData(self):
        while True:
            t1, t2, t3, t4 = (makeTempMeasurement(), makeTempMeasurement(), makeTestMeasurement(self.worker.output), makeTestMeasurement(self.worker.output))
            ts = current_time(self.config)
            data = {TIMESTAMP: ts, "toy1": t1, "toy2": t2, "testMeasurement1": t3, "testMeasurement2": t4}
            self.connection.send(**data)
            time.sleep(1)
