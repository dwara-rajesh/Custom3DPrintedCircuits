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

SUBSTRATE = {'start': [-155.8, 31.64], # X and Y Coordinates for the start and end points of the printable area of the substrate (with margins)
               'end': [-87.64, 72.74],
             'level': 38.5} # Height level just above substrate surface

load_calibration_data()
z_origin_ink = CALIBRATION_DATA['ink'][2] + top_right_vise[2]
origin_in_m_ink = [top_right_vise[0],top_right_vise[1]-admlviceblock_yoff,z_origin_ink, 0, math.pi, 0] #top right corner of stock on vice in rosie station
origin_ink = [val * 1000 for val in origin_in_m_ink[:3]] + [0,math.pi,0] #origin in mm

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
            nodeX = (origin_ink[0] + (node['posX'] * 25.4)) / 1000
            nodeY = (origin_ink[1] + (node['posY'] * 25.4)) / 1000
            nodeZ = origin_ink[2] / 1000

            nodes.append([nodeX,nodeY,nodeZ])
        wiring_schematic.append(nodes)

    return wiring_schematic



def print_trace(trace, print_speed=PRINT_SPEED, print_pressure=PRINT_PRESSURE, primer_delay=PRIMER_DELAY,
                dry_print=False, skip_hover=False):
    """
    Prints a single multi-point conductive trace using the printing head

    Traces are arrays of 3D table coordinates, and the printing process
    simply moves from the beggining to the end coordinate in order, while
    extruding ink at constant rate. Hence a single trace can have complex
    3-dimensional shapes, but must be continuous.

    If dry_print is set to TRUE, no ink will be extruded but the line path
    will still be traced normally. This is useful for testing that a path
    is correct before commiting to printing actual ink.
    """

    heaven = 15.0 # Z coordinate above trace height to enter and exit the trace at
    vertical_clearance = 0.2 # In mm (Can be used to adjust the vertical offset when printing)

    # Set printing pressure:
    if dry_print == True:
        set_pressure(ATMOSPHERE)
    else:
        set_pressure(print_pressure)

    # Go to trace start coordinates and begin printing
    if skip_hover != True: # By default, nozzle moves to trace location at heaven height, and then lowers onto it (This can be skipped)
        goto_pos(trace[0][:2] + [trace[0][2]+heaven]) # Compact way of just adding heaven value onto last coordinate without altering original coord array
    goto_pos(trace[0])
    ink_on() # Begin printing

    time.sleep(primer_delay)
    for coord in trace[1::]: # Skip the first coord since we are already there
        goto_pos(coord[:2] + [coord[2]+vertical_clearance], speed=print_speed, accel=PRINT_ACCEL)

    # One the trace is finished, stop printing and return to heaven height
    ink_off()
    clear_tip(delay=0.5) # Prevent stringing
    goto_pos(trace[-1][:2] + [trace[-1][2]+heaven])

def print_quality_test(type='pressure', dry_run=False):
    """
    Prints several horizontal lines in a substrate part at varying speeds or pressures to
    visually determine which printing pressure works best with the current ink
    """

    pressure_range = [45,80] # Pressure range used when testing pressure
    speed_range = [0.03,0.20] # Speed range used when testing speed
    delay_range = [0.040,0.600] # Primer delay range used when testing primer delay

    lines = 8 # Number of different lines to print (In other words, number of different pressures to test)

    line_start = SUBSTRATE['start'][0]
    line_end = SUBSTRATE['end'][0]

    dy = (SUBSTRATE['end'][1] - SUBSTRATE['start'][1]) / (lines - 1)

    trace_data = [[line_start, SUBSTRATE['start'][1], SUBSTRATE['level']],
                  [line_end, SUBSTRATE['start'][1], SUBSTRATE['level']]]
    for idx in range(lines):
        # Print trace with correct speed and pressure paramters
        if type == 'pressure': # Lines will have varying pressure values and default speed:
            pressure = idx * ((pressure_range[1]-pressure_range[0]) / (lines - 1)) + pressure_range[0]
            print("Printing test trace #[" + str(idx+1) + "] - Pressure: " + str(round(pressure)) + "psi")
            print_trace(trace=trace_data, print_pressure=pressure, dry_print=dry_run)
        if type == 'speed': # Lines will have verying speed values and default pressure
            speed = idx * ((speed_range[1]-speed_range[0]) / (lines - 1)) + speed_range[0]
            print("Printing test trace #[" + str(idx+1) + "] - Speed: " + str(round(speed, 2)) + "m/s")
            print_trace(trace=trace_data, print_speed=speed, dry_print=dry_run)
        if type == 'delay':
            delay = idx * ((delay_range[1]-delay_range[0]) / (lines - 1)) + delay_range[0]
            print("Printing test trace #[" + str(idx+1) + "] - Primer delay: " + str(round(delay*1000)) + "ms")
            print_trace(trace=trace_data, primer_delay=delay, dry_print=dry_run)

        # Update trace coordinates for next line:
        trace_data[0][1] += dy
        trace_data[1][1] += dy


def print_meander(k=10, dry_run=False):
    """
    Prints a test meander trace on an empty flat substrate piece
    Uses default speed and pressure

    'k' is the pitch of the meander (How many S-turns the meander will have)
    """

    dx = (SUBSTRATE['end'][0] - SUBSTRATE['start'][0]) / (k - 1)

    # Construct trace from substrate parameters
    meander = []
    direction = 0 # Flag variable to keep track of direction
    for idx in range(k):
        if direction == 0: # Bottom to top
            meander.append([SUBSTRATE['start'][0]+(dx*idx), SUBSTRATE['start'][1], SUBSTRATE['level']])
            meander.append([SUBSTRATE['start'][0]+(dx*idx), SUBSTRATE['end'][1], SUBSTRATE['level']])
            direction = 1
        elif direction == 1: # Top to bottom
            meander.append([SUBSTRATE['start'][0]+(dx*idx), SUBSTRATE['end'][1], SUBSTRATE['level']])
            meander.append([SUBSTRATE['start'][0]+(dx*idx), SUBSTRATE['start'][1], SUBSTRATE['level']])
            direction = 0

    # Print the constructed trace
    print_trace(meander, dry_print=dry_run)


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

def move_to_node(pos, index, maxindex):
    nodepos = pos + [0,pi,0]
    if index == 0:
        rtde_control.moveL(nodepos, speed=0.005)
        #extrude ink
        #draw ball for firm connection
    elif index == maxindex:
        #extrude ink
        rtde_control.moveL(nodepos, speed=0.005)
        #draw ball for firm connection
    else:
       #extrude ink
        rtde_control.moveL(nodepos, speed=0.005)
#-----------------------------------------------------------------------------------------------------------
# === # Ink Trace Printing Code # === #


def main():
    """
    Main script loop
    """
    wire_schematic = get_traces()
    grab_inkprinter()
    for wire in wire_schematic:
        for i,node in enumerate(wire):
            move_to_node(node,i,len(wire) - 1)
    
    return_inkprinter()


if __name__ == "__main__":
    main()