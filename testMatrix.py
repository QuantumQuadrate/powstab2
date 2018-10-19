#!/usr/bin/python
import ServerStuff.server as server
import numpy as np
import time

a = [[0, 1],[1, 0]]
dataStream = 'toy'
outputStream = "BGTest"
inputs = ['toy1', 'toy2']
outputs = ['output1', 'output2']


myServer = server.MatrixTransformServer()
myServer.setup(a, dataStream, inputs, outputs, outputStream)
while True:
    time.sleep(1)
sub.close()
