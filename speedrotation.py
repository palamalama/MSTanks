import numpy as np
speed = np.loadtxt(r'C:\Users\CDT\Desktop\GUTS\MSTanks\speed.csv', delimiter=',')
speed2 = np.loadtxt(r'C:\Users\CDT\Desktop\GUTS\MSTanks\speed2.csv', delimiter=',')
rotation = np.loadtxt(r'C:\Users\CDT\Desktop\GUTS\MSTanks\rotation.csv', delimiter=',')
d = np.sqrt(((speed[16,0] - speed[0,0])**2) + ((speed[16,1]-speed[0,1])**2))
d2 = np.sqrt(((speed2[16,0] - speed2[0,0])**2) + ((speed2[16,1]-speed2[0,1])**2))
timebetweenpol = 0.358853
v = d / (16* timebetweenpol)
v2 = d2 / (16* timebetweenpol)
avv = (v2 + v)/2

avpolltime = np.mean(rotation[:,2])
avrotperpoll = rotation[:,3]

for i in range(len(avrotperpoll)):
    if avrotperpoll[i] < 0:
        avrotperpoll[i] = avrotperpoll[i] + 360
        print(avrotperpoll[i])

degreepersecond = np.mean(avrotperpoll /0.358853)


