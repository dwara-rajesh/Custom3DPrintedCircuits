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
DRY_RUN = True


            #  'squares': {
            #           'swt-square-A': [[44.75, -16.10], [50.15, -10.70], 1.70],
            #           'swt-square-B': [[23.75, -16.10], [29.15, -10.70], 1.70],
            #        'swt-reinforce-A': [[44.75, -20.10], [55.15, -06.70], 2.80],
            #        'swt-reinforce-B': [[18.75, -20.10], [29.15, -06.70], 2.80]},
            #     'arcs': {  'bat-arc': [[-145.04, 46.82, 39.00], 10.15, [3*pi/4, pi/4]]}}


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

def get_traces(recentsavefilepath):
    """
    Takes a schematic of print traces in offset format and calculates all the waypoints
    for the ink print head given the origin position.
    Returns a dictionary of traces for printing. (Preserving IDs)
    """
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
                dry_print=DRY_RUN):
    if dry_print == True:
        set_pressure(ATMOSPHERE)
    else:
        set_pressure(print_pressure)

    ink_on()
    time.sleep(primer_delay)

    meander_terminal(terminal_pos,terminal_component)

def meander_terminal(centre, component, k=3,speed=0.005):
    start_x = centre[0] - (meander_square_size[component]/39.37)
    start_y = centre[1] - (meander_square_size[component]/39.37)

    end_x = centre[0] + (meander_square_size[component]/39.37)
    end_y = centre[1] + (meander_square_size[component]/39.37)

    y_step = ((end_y - start_y) / k)

    startpos = [start_x,start_y,centre[2],centre[3],centre[4],centre[5]]
    rtde_control.moveL(startpos,speed=speed)
    next_x = end_x
    next_y = start_y
    for i in range(k*2):
        endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]]
        rtde_control.moveL(endpos,speed=speed)
        if i % 2 == 0:
            next_y = next_y + y_step
        else:
            if next_x == end_x:
                next_x = start_x
            else:
                next_x = end_x

    rtde_control.moveL(centre,speed=speed)

def reinforce_connection(reinforced_wire_schematic):
    grab_inkprinter()

    for wire in reinforced_wire_schematic:
        for i,node in enumerate(wire):
            if i==0 or i==len(wire) - 1:
                nodepos = node['pos']+[0,pi,0]
                rtde_control.moveL(nodepos, speed=slow)
                ink_on()
                time.sleep(PRIMER_DELAY)
                meander_terminal(nodepos, node['comp'])
                ink_off()
                node_z_heaven = nodepos[2] + 50/1000 #mm to m
                current_node_heaven = [nodepos[0],nodepos[1],node_z_heaven] + [0,pi,0]
                rtde_control.moveL(current_node_heaven, speed=slow)
    
    if not DRY_RUN:
        clear_tip(delay=0.5)
    return_inkprinter()

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

def move_to_node(pos, comp, index, maxindex,speed=0.005):
    if index == maxindex:
        rtde_control.moveL(pos, speed=speed)
        printink(terminal_pos=pos,terminal_component=comp)
    else:
        rtde_control.moveL(pos, speed=speed)
#-----------------------------------------------------------------------------------------------------------
# === # Ink Trace Printing Code # === #


def ink_trace(file_path,dry_run=True):
    """
    Main script loop
    """
    global DRY_RUN
    DRY_RUN = dry_run
    wire_schematic = get_traces(file_path)
    grab_inkprinter()

    for wire in wire_schematic:
        for i,node in enumerate(wire):
            nodepos = node['pos']+[0,pi,0]
            if i==0:
                rtde_control.moveL(nodepos, speed=fast)
                printink(terminal_pos=nodepos,terminal_component=node['comp'])
            else:
                move_to_node(pos=nodepos,comp=node['comp'],index=i,maxindex=len(wire) - 1)

        ink_off()
        z_heaven = wire[len(wire) - 1]['pos'][2] + 50/1000 #mm to m
        node_heaven = [wire[len(wire) - 1]['pos'][0],wire[len(wire) - 1]['pos'][1],z_heaven] + [0,pi,0]
        rtde_control.moveL(node_heaven, speed=slow)

    if not DRY_RUN:
        clear_tip(delay=0.5)
    return_inkprinter()

#Test InkTracing Module
# ink_trace(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\finalSendToMill.json")