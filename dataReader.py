import matplotlib.pyplot as plt
import urllib2
import numpy as np
import matplotlib.animation as animation
import time
flag = True
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
while True:
    data = urllib2.urlopen("http://192.168.137.2:5000/static/data.txt").read(20000) # read only 20 000 chars
    data = data.split("\n")[:-1]

    x = np.array(data)
    y = x.astype(np.float)
    ax1.clear()
    ax1.plot(y)
    time.sleep(.5)
    if flag:
        plt.show()
        flag = False
