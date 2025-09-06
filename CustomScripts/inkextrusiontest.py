from coreModule import *

time.sleep(5) #hold for 5 seconds
set_pressure(45) #set pressure to 45 PSI
ink_on() #turn on ink solenoid
time.sleep(10) #wait for 10s 
ink_off() #switch off ink

#Fresh ink works at 45 PSI
#One day later - Capped and stored doesn't work at 85 PSI, and 100 PSI