#!/usr/bin/python
import ServerStuff.server as server
cal = 5.0/2**12
a = [
        [cal, cal, 0, 0],
        [cal, -cal, 0, 0],
        [0, 0, cal, cal],
        [0, 0, cal, -cal]
    ]
dataStream = 'FNODE_ADCS'
outputStream = "FNODE_POWMON"
# MZ780, MXY780, MZ852, MXY852
inputs = ['c1', 'c2', 'c3', 'c4']
outputs = ['T780', 'D780', 'T852', 'D852']


myServer = server.MatrixTransformServer()
myServer.setup(a, dataStream, inputs, outputs, outputStream)
myServer.runServer(debug=False)
