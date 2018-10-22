#!/usr/bin/python
import ServerStuff.server as server

a = [[1, -1], [1, 1], [0, 0]]
dataStream = 'toy'
outputStream = "BGTest"
inputs = ['toy1', 'toy2']
outputs = ['diff', 'sum', 'zero']


myServer = server.MatrixTransformServer()
myServer.setup(a, dataStream, inputs, outputs, outputStream)
myServer.runServer()
