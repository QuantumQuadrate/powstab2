import matplotlib.pyplot as plt
import urllib2

data = urllib2.urlopen("http://192.168.137.2:5000/static/data.txt").read(20000) # read only 20 000 chars
data = data.split("\n")

plt.plot(data)

plt.show()
