import time
import sys
s = 0
for a in range(200):
    s = s+1
    time.sleep(1)
    print(s)
    if s == 100:
        sys.path.insert(1, '/home/pi/Desktop/BOOT')
        import prgrm

