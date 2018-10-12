import matplotlib.pyplot as plt


dataTracker = open("http://192.168.137.2:5000/static/data.txt", "w+")
data = dataTracker.read().split('\n')
dataTracker.close()
plt.plot(data)

plt.show()
