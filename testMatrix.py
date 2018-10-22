#!/usr/bin/python
import ServerStuff.server as server

a = [[1, -1], [1, 1]]
dataStream = 'toy'
outputStream = "BGTest"
inputs = ['toy1', 'toy2']
outputs = ['diff', 'sum']


myServer = server.MatrixTransformServer()
myServer.setup(a, dataStream, inputs, outputs, outputStream)
myServer.runServer()
