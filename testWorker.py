#!/usr/bin/env python
import random
import time
from origin.client import server
from origin import current_time, TIMESTAMP
import ConfigParser
import math


class testWorker(object):
    """docstring for ."""

    def __init__(self):
        self.worker = ''

    def startServer(self):
        # first find ourself
        self.config = ConfigParser.ConfigParser()
        self.config.read('origin-server.cfg')

        serv = server(self.config)

        self.connection = serv.registerStream(
            stream="toy",
            records={
                "toy1": "float",
                "toy2": "float",
                "testMeasurement1": "float",
                "testMeasurement2": "float",
                })

    def makeTempMeasurement(self):
        return random.random()

    def makeTestMeasurement(self):
        f = open("outputValue.txt", "r")
        output = float(f.read())
        return math.exp(output)

    def streamData(self):
        while True:
            t1, t2, t3, t4 = (self.makeTempMeasurement(), self.makeTempMeasurement(), self.makeTestMeasurement(), self.makeTestMeasurement())
            ts = current_time(self.config)
            data = {TIMESTAMP: ts, "toy1": t1, "toy2": t2, "testMeasurement1": t3, "testMeasurement2": t4}
            self.connection.send(**data)
            
