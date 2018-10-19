#!/usr/bin/python
import ServerStuff.server as server

a = [[0, 1], [1, 0]]
dataStream = 'toy'
outputStream = "BGTest"
inputs = ['toy1', 'toy2']
outputs = ['output1', 'output2']


myServer = server.MatrixTransformServer()
myServer.setup(a, dataStream, inputs, outputs, outputStream)
myServer.runServer()
