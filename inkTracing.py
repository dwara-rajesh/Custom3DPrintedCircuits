"""
Module containing the code to program and control the Ink Trace Printing functionality
"""

import time
import math
import rtde_io
import rtde_receive
import rtde_control
import keyboard
from math import pi
import json,os

# Import core module:
from coreModule import *

# Ink printing extrusion parameters
PRINT_SPEED = 0.1 # [m/s] Linear speed of the printer head when extruding ink - Original value: 0.15m/s
PRINT_SPEED_HALF = PRINT_SPEED / 2
PRINT_SPEED_SLOW = 0.02
PRINT_PRESSURE = 45 # [psi] Pressure of the pneumatic extrusion line - Original value: 70psi
PRIMER_DELAY = 0.360 # [s] Delay in seconds that the printer waits before starting to move to allow ink time to flow through the nozzle
PRINT_ACCEL = 0.8 # Printing uses reduced acceleration to avoid breaking the traces


# New coordinate package for the demo LED and Switch circuit:
# This data structure helps collect all info about the traces to be printed
# It is formatted as arrays of XYZ offsets from the same origin point
# This origin point is specified in the 'origin' entry (In this demo, it is at the center of the battery)
#   TODO: This would be nicer if written as a class - and merged with pick-and-place assembly data too
DEMO_PRINT = {'origin': [-145.04, 47.35, 36.85],
            'segments': {'bat-led-A': [[ 0.00,   0.00,  0.00],
                                       [ 0.00,   2.97,  0.00],
                                       [ 0.00,   7.85, -1.40],
                                       [ 0.00,  11.62, -1.40],
                                       [ 0.00,  15.80, -0.20],
                                       [ 0.00,  17.40, -0.20]],
                         'bat-led-B': [[ 0.00,  17.40, -0.20],
                                       [ 8.51,  17.40,  1.30],
                                       [13.20,  17.40,  1.30],
                                       [17.20,  13.40,  1.30],
                                       [31.13,  13.40,  1.30],
                                       [32.63,  13.40,  1.70]],
                           'bat-led': [[ 0.00,   0.00,  0.00],
                                       [ 0.00,   2.97,  0.00],
                                       [ 0.00,   7.85, -1.40],
                                       [ 0.00,  11.62, -1.40],
                                       [ 0.00,  15.80, -0.20],
                                       [ 0.00,  17.40, -0.20],
                                       [ 8.51,  17.40,  1.30],
                                       [13.20,  17.40,  1.30],
                                       [17.20,  13.40,  1.30],
                                       [31.13,  13.40,  1.30],
                                       [32.63,  13.40,  1.00]],
                           'led-swt': [[39.77,  13.40,  1.00],
                                       [41.27,  13.40,  1.30],
                                       [56.20,  13.40,  1.30],
                                       [56.20, -13.40,  1.30],
                                       [47.20, -13.40,  1.30],
                                       [47.20, -13.40,  0.30]],
                         'swt-bat-A': [[25.20, -13.40,  0.30],
                                       [25.20, -13.40,  1.30],
                                       [17.20, -13.40,  1.30],
                                       [13.20, -17.40,  1.30],
                                       [ 0.00, -17.40,  1.30]],
                         'swt-bat-B': [[ 0.00, -17.40,  1.30],
                                       [ 0.00, -11.40,  1.30],
                                       [ 0.00, -11.40,  2.80],
                                       [ 0.00,  -9.00,  2.80]],
                           'swt-bat': [[25.20, -13.40,  1.30],
                                       [17.20, -13.40,  1.30],
                                       [13.20, -17.40,  1.30],
                                       [ 0.00, -17.40,  1.30],
                                       [ 0.00, -11.40,  1.30],
                                       [ 0.00, -11.40,  2.80],
                                       [ 0.00,  -9.00,  2.80]],
                        'bat-anchor': [[ 0.00,   0.00,  0.00]],
                      'led-anchor-A': [[32.13,  13.40,  2.00],
                                       [29.63,  13.40,  2.00]],
                      'led-anchor-B': [[40.27,  13.40,  2.00],
                                       [42.77,  13.40,  2.00]],
                      'swt-anchor-A': [[47.20, -13.40,  1.50],
                                       [50.20, -13.40,  1.50]],
                      'swt-anchor-B': [[25.20, -13.40,  1.50],
                                       [22.20, -13.40,  1.50]]},
             'squares': {
                      'swt-square-A': [[44.75, -16.10], [50.15, -10.70], 1.70],
                      'swt-square-B': [[23.75, -16.10], [29.15, -10.70], 1.70],
                   'swt-reinforce-A': [[44.75, -20.10], [55.15, -06.70], 2.80],
                   'swt-reinforce-B': [[18.75, -20.10], [29.15, -06.70], 2.80]},
                'arcs': {  'bat-arc': [[-145.04, 46.82, 39.00], 10.15, [3*pi/4, pi/4]]}}

"""
DEMO CIRCUIT
Waypoint offsets from CAD model:
          X      Y      Z
BAT - LED
00 -     0.0    0.0    0.00
01 -     0.0   +2.97   0.00
02 -     0.0   +7.85  -1.40
03 -     0.0  +11.62  -1.40
04 -     0.0  +15.80  -0.20
05 -     0.0  +17.40  -0.20
06 -    +8.51 +17.40  +1.30
07 -   +17.20 +13.40  +1.30
08 -   +32.63 +13.40  +1.30

LED - SWT
00 -   +39.77 +13.40  +1.30
01 -   +56.20 +13.40  +1.30
02 -   +56.20 -13.40  +1.30
03 -   +47.20 -13.40  +1.30

SWT - BAT
00 -   +25.20 -13.40  +1.30
01 -   +17.20 -13.40  +1.30
02 -   +13.20 -17.40  +1.30
03 -     0.0  -17.40  +1.30
04 -     0.0  -11.40  +1.30
05 -     0.0  -11.40  +2.80
06 -     0.0    0.0   +2.80
"""


load_calibration_data()
z_origin_ink = CALIBRATION_DATA['ink'][2] + top_right_vise[2]
origin_in_m_ink = [top_right_vise[0],top_right_vise[1]-admlviceblock_yoff,z_origin_ink, 0, math.pi, 0] #top right corner of stock on vice in rosie station
origin_ink = [val * 1000 for val in origin_in_m_ink[:3]] + [0,math.pi,0] #origin in mm

#in inches
meander_square_size = {"battery":0.01,
                  "microcontroller":0.035,
                  "button":0.01,
                  "led":0.035}
wire_schematic = []
def clear_tip(delay=1.0):
    """
    Applies a vacuum to the ink nozzle for a short time to prevent leftover pressure
    from extruding more ink after the nozzle is pulled away (stringing)
    """
    set_pressure(0.1)
    time.sleep(0.5)
    ink_on()
    time.sleep(delay)
    ink_off()

def get_most_recent_saved_file(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    if not files:
        return None
    return max(files, key=os.path.getctime)

def get_traces():
    """
    Takes a schematic of print traces in offset format and calculates all the waypoints
    for the ink print head given the origin position.
    Returns a dictionary of traces for printing. (Preserving IDs)
    """
    # savefolderpath = os.path.join(os.getcwd(),"saves")
    # recentsavefilepath = get_most_recent_saved_file(savefolderpath)
    # recentsavefilepath = r"C:\git\ADML\Automated Circuit Printing and Assembly\finalSendToMill.json"
    recentsavefilepath = r"Automated Circuit Printing and Assembly/finalSendToMill.json"
    print(f"Save file path: {recentsavefilepath}")
    with open(recentsavefilepath, 'r') as f:
        data = json.load(f)

    wiring_schematic = []
    for wire in data['wiresdata']:
        nodes = []
        for node in wire['wireNodesdata']:
            if node['component'] is None:
                component = "empty"
            else:
                component = node['component']

            nodeX = (origin_ink[0] + (node['posX'] * 25.4)) / 1000
            nodeY = (origin_ink[1] + (node['posY'] * 25.4)) / 1000
            nodeZ = origin_ink[2] / 1000

            nodes.append({"pos":[nodeX,nodeY,nodeZ], "comp": component})
        wiring_schematic.append(nodes)

    return wiring_schematic

def printink(terminal_pos, terminal_component,print_pressure=PRINT_PRESSURE, primer_delay=PRIMER_DELAY,
                dry_print=True):
    if dry_print == True:
        set_pressure(ATMOSPHERE)
    else:
        set_pressure(print_pressure)

    ink_on()
    time.sleep(primer_delay)

    meander_terminal(terminal_pos,terminal_component)

def meander_terminal(centre, component, k=3):
    start_x = centre[0] - (meander_square_size[component]/39.37)
    start_y = centre[1] - (meander_square_size[component]/39.37)

    end_x = centre[0] + (meander_square_size[component]/39.37)
    end_y = centre[1] + (meander_square_size[component]/39.37)

    y_step = ((end_y - start_y) / k)

    startpos = [start_x,start_y,centre[2],centre[3],centre[4],centre[5]]
    rtde_control.moveL(startpos,speed=0.005)
    next_x = end_x
    next_y = start_y
    for i in range(k*2):
        endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]]
        rtde_control.moveL(endpos,speed=0.005)
        if i % 2 == 0:
            next_y = next_y + y_step
        else:
            if next_x == end_x:
                next_x = start_x
            else:
                next_x = end_x
    
    rtde_control.moveL(centre,speed=0.005)

def reinforce_connection():
    for wire in wire_schematic:
        for i,node in enumerate(wire):
            if i==0 or i==len(wire) - 1:
                nodepos = node['pos']+[0,pi,0]
                meander_terminal(nodepos, node['comp'])
def prime_ink():
    """
    Primes the ink extruder by extruding a short length of ink to ensure
    that the ink has flowed all throughout the nozzle
    """
    set_pressure(PRINT_PRESSURE)
    time.sleep(5)
    ink_on()
    time.sleep(3)
    ink_off()
    set_pressure(ATMOSPHERE)

def move_to_node(pos, comp, index, maxindex):
    if index == maxindex:
        rtde_control.moveL(pos, speed=0.005)
        printink(pos,comp)
    else:
        rtde_control.moveL(pos, speed=0.005)
#-----------------------------------------------------------------------------------------------------------
# === # Ink Trace Printing Code # === #


def main():
    """
    Main script loop
    """
    wire_schematic = get_traces()
    grab_inkprinter()
    # prime_ink()
    # clear_tip(delay=0.5)
    for wire in wire_schematic:
        for i,node in enumerate(wire):
            nodepos = node['pos']+[0,pi,0]
            if i==0:
                rtde_control.moveL(nodepos, speed=fast)
                printink(nodepos,node['comp'])
            else:
                move_to_node(nodepos,node['comp'],i,len(wire) - 1)

        ink_off()
        z_heaven = wire[len(wire) - 1]['pos'][2] + 50/1000 #mm to m
        node_heaven = [wire[len(wire) - 1]['pos'][0],wire[len(wire) - 1]['pos'][1],z_heaven] + [0,pi,0]
        rtde_control.moveL(node_heaven, speed=slow)

    # clear_tip(delay=0.5)
    return_inkprinter()

if __name__ == "__main__":
    main()