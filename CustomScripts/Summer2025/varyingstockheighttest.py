#Test Varying Height Stock
#PLEASE READ IF PERFORMING TEST
#1) set Rosie to linearindex5
#2) run calibration.py
#3) manually open progfile, under componentdata -> modelName = "stock"... find dimZ for stock. Adjust dimZ value to height of stock being tested 
#4) uncomment line 20 or line 21 depending on extruder or vacuum test, run code
#5) navigate to I/O tab in Rosie teach pendant, grab the ink extruder manually, place in Rosie gripper manually, set digital output 0 to active
#6) place the stock being test in vice, ensure good clearance, i.e ensure the tip of extruder/vacuum does not touch vice or stock OR ensure tip is not too far away from vice or stock
import coreModule

#this variable loads the circuit you developed with circuit information
projfile = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\minimaltest.json" 

#get stock height offset
coreModule.get_stock_height_offset(projfile)

import pickAndPlace 
import inkTracing 

#IMPORTANT: only uncomment one of the below lines at once.
# coreModule.rtde_control.moveL(inkTracing.origin_in_m_ink,speed=coreModule.fast) #uncomment to start varying height test for ink tracing/extruder
# coreModule.rtde_control.moveL(pickAndPlace.origin_in_m_vac,speed=coreModule.fast) #uncomment to start varying height test for pick and place/vacuum