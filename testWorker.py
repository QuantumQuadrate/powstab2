#!/usr/bin/env python
import random
import time
from origin.client import server
from origin import current_time, TIMESTAMP
import ConfigParser
import math


def makeTempMeasurement():
    return random.random()


def makeTestMeasurement():
    f = open("outputValue.txt", "r")
    output = float(f.readline())
    f.close()
    return math.exp(output) + random.random()


config = ConfigParser.ConfigParser()
config.read('origin-server.cfg')

serv = server(config)

connection = serv.registerStream(
    stream="toy",
    records={
        "toy1": "float",
        "toy2": "float",
        "testMeasurement1": "float",
        "testMeasurement2": "float",
        })

while True:
    t1, t2, t3, t4 = (makeTempMeasurement(), makeTempMeasurement(), makeTestMeasurement(), makeTestMeasurement())
    ts = current_time(config)
    data = {TIMESTAMP: ts, "toy1": t1, "toy2": t2, "testMeasurement1": t3, "testMeasurement2": t4}
    print data
    print "\n"
    connection.send(**data)
    time.sleep(.5)
