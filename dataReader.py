import matplotlib.pyplot as plt


dataTracker = open("data.txt", "w+")
data = dataTracker.read().split('\n')
dataTracker.close()
plt.plot(data)

plt.show()
