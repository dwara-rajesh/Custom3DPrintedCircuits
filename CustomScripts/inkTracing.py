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
PRINT_PRESSURE = 30 # [psi] Pressure of the pneumatic extrusion line - Original value: 70psi
PRIMER_DELAY = 0.360 # [s] Delay in seconds that the printer waits before starting to move to allow ink time to flow through the nozzle
PRINT_ACCEL = 0.8 # Printing uses reduced acceleration to avoid breaking the traces
DRY_RUN = True
angle = 0

load_calibration_data() #obtain calibration data after calibration is complete
z_origin_ink = CALIBRATION_DATA['ink'][2] + top_right_vise[2] #offset the origin by calibration data to avoid hitting the vise
origin_in_m_ink = [top_right_vise[0],top_right_vise[1]-admlviceblock_yoff,z_origin_ink, 0, math.pi, 0] #top right corner of stock on vice in rosie station in meters
origin_ink = [val * 1000 for val in origin_in_m_ink[:3]] + [0,math.pi,0] #origin in mm

#in inches - the size of solder/meander square
meander_square_size = {"battery":0.045,
                  "microcontroller":0.015,
                  "button":0.045,
                  "led":0.015}
#in inches - the size of reinforements
reinforcements = {
    "battery": [0.375,0.375], #(l = radius of battery, w = radius of battery)
    "button": [0.45,0.7], #(l = length of meander, w = width of meander)
}
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

def get_traces(recentsavefilepath,reinforce=False):
    """
    Takes a schematic of print traces in offset format and calculates all the waypoints
    for the ink print head given the origin position.
    Returns a dictionary of traces for printing. (Preserving IDs)
    """
    print(f"Save file path: {recentsavefilepath}")
    with open(recentsavefilepath, 'r') as f:
        data = json.load(f)

    wiring_schematic = []
    for wire in data['wiresdata']: #get all wire data
        nodes = []
        for node in wire['wireNodesdata']: #get all node data in each wire
            if node['component'] is None:
                component = "empty"
            else:
                component = node['component']

            if node['batteryneg'] is None:
                batteryneg = "empty"
            else:
                batteryneg = node['batteryneg']
            #get position (x,y,z) convert in to mm
            nodeX = (origin_ink[0] + (node['posX'] * 25.4)) / 1000
            nodeY = (origin_ink[1] + (node['posY'] * 25.4)) / 1000
            if not reinforce:
                nodeZ = origin_ink[2] / 1000
            else:
                nodeZ = origin_ink[2] / 1000 + 1/1000 #if reinforce offset z + a little offset

            if node['componentid'] is None:
                id = "empty"
            else:
                id = node['componentid']

            nodes.append({"pos":[nodeX,nodeY,nodeZ], "comp": component, "batteryneg": batteryneg, "comp_id": id}) #populate in a set for later usage

        if len(nodes) > 1 and not reinforce:
            first_node = nodes[0]
            last_node = nodes[-1]
            if first_node['batteryneg'] == "p":
                nodes.remove(first_node)
            elif last_node['batteryneg'] == "p":
                nodes.remove(last_node)

        wiring_schematic.append(nodes)

    return wiring_schematic

#function responsible for turning on extrusion
def printink(terminal_pos, terminal_component, terminal_polarity,print_pressure=PRINT_PRESSURE, primer_delay=PRIMER_DELAY):
    if DRY_RUN == True:
        set_pressure(ATMOSPHERE) #no ink is extruded
    else:
        set_pressure(print_pressure) #ink is extruded
    ink_on()
    time.sleep(primer_delay)

    if terminal_component != "battery" or terminal_polarity == "n": #if component is not battery or if the terminal component is battery and is a negative terminal
        meander_terminal(terminal_pos,terminal_component) #then meander

def meander_terminal(centre, component, k=3,speed=0.01, reinforce=False):
    global angle
    component = component.lower()
    if reinforce:
        speed = 0.005
        k = 10 #increase the layers from 3 to 10
        if component == "battery": #if battery, draw an arc to secure placement
            radius = reinforcements[component][0]/39.37
            #range is basically angle-120 -> angle + 120, so arc angle is 240 but 120 on either side of the middle
            rangemax = angle + 120
            rangemin = angle - 120
            for i in range(rangemin,rangemax+1,10): #go from rangemin to rangemax in intervals of 10 degrees
                rads = math.radians(i) #convert degrees to radians
                #get next position using pythagoras theorem
                next_x = radius * math.cos(rads) + centre[0] #get next_x
                next_y = radius * math.sin(rads) + centre[1] #get next_y
                endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]]
                rtde_control.moveL(endpos,speed=speed) #move to position
        else: #if any other component, meander with larger sizes
            start_x = centre[0] - (reinforcements[component][0]*0.5/39.37)
            start_y = centre[1] - (reinforcements[component][1]*0.5/39.37)

            end_x = centre[0] + (reinforcements[component][0]*0.5/39.37)
            end_y = centre[1] + (reinforcements[component][1]*0.5/39.37)

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
    else:
        '''
        Meander is a zig zag motion of sorts, if k = 3
                        end_x,end_y
            |-------------->|
            |<--------------|
            --------------->| y_step
        start_x,start_y
        '''
        #determine start_x,start_y
        start_x = centre[0] - (meander_square_size[component]*0.5/39.37)
        start_y = centre[1] - (meander_square_size[component]*0.5/39.37)

        #determine end_x,end_y
        end_x = centre[0] + (meander_square_size[component]*0.5/39.37)
        end_y = centre[1] + (meander_square_size[component]*0.5/39.37)

        #determine y_step
        y_step = ((end_y - start_y) / k)

        startpos = [start_x,start_y,centre[2],centre[3],centre[4],centre[5]]
        rtde_control.moveL(startpos,speed=speed) #move to start position
        #get next position
        next_x = end_x
        next_y = start_y
        #meander
        for i in range(k*2):
            endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]] #move to next position
            rtde_control.moveL(endpos,speed=speed)
            if i % 2 == 0:
                next_y = next_y + y_step #move to next layer
            else:
                if next_x == end_x: #move to other end
                    next_x = start_x
                else:
                    next_x = end_x
        #return to centre position of meander after meandering
        rtde_control.moveL(centre,speed=speed)

def reinforce_connection(reinforced_wire_schematic, dry_run = True):
    global angle
    global DRY_RUN
    global reinforcements
    DRY_RUN = dry_run
    grab_inkprinter()
    set_pressure(ATMOSPHERE)
    Terminal1button = {}
    Terminal2button = {}
    positive_battery_terminal_pos = {}
    positive_battery_neighbouring_node = {}
    for wire in reinforced_wire_schematic: #for each wire in schematic
        for i,node in enumerate(wire): #for each node in wire
            if node['comp'] == "battery" and node['batteryneg'] == "p":
                positive_battery_terminal_pos.update({node['comp_id']: node['pos']+[0,pi,0]}) #get positive terminals of all batteries present in circuit
                #Find neighbouring node of positive battery terminal node
                if i == 0:
                    positive_battery_neighbouring_node.update({node['comp_id']: wire[1]['pos']+[0,pi,0]})
                elif i == len(wire) - 1:
                    positive_battery_neighbouring_node.update({node['comp_id']: wire[i-1]['pos']+[0,pi,0]})

            if node['comp'] == "button": #get all terminals of all buttons in schematic
                key = node['comp_id']
                if key in Terminal1button:
                    if Terminal1button[key] == []:
                        Terminal1button.update({node['comp_id']: node['pos'][:2]})
                    else:
                        Terminal2button.update({node['comp_id']: node['pos'][:2]})
                else:
                    Terminal1button.update({node['comp_id']: node['pos'][:2]})

    for positiveterminals in positive_battery_terminal_pos:
        rtde_control.moveL(positive_battery_terminal_pos[positiveterminals], speed=slow) #go to position
        if not DRY_RUN:
            set_pressure(PRINT_PRESSURE)
            ink_on()
            time.sleep(PRIMER_DELAY)
        rtde_control.moveL(positive_battery_neighbouring_node[positiveterminals], speed=0.005) #go to position

        ink_off()
        node_position = positive_battery_neighbouring_node[positiveterminals]
        node_z_heaven = node_position[2] + 50/1000 #Move to heaven (mm to m)
        current_node_heaven = [node_position[0],node_position[1],node_z_heaven] + [0,pi,0]
        rtde_control.moveL(current_node_heaven, speed=slow)

    for wire in reinforced_wire_schematic: #for each wire in schematic
        for i,node in enumerate(wire): #for each node in wire
            if (i==0 or i==len(wire) - 1) and node['comp'] == "button": #if last or first node and component is button
                nodepos = node['pos']+[0,pi,0]
                rtde_control.moveL(nodepos, speed=slow) #go to position
                if not DRY_RUN:
                    set_pressure(PRINT_PRESSURE)
                    ink_on()
                    time.sleep(PRIMER_DELAY)

                if node['comp'] == "button": #if component is button
                    key = node['comp_id']
                    x_button_diff = Terminal1button[key][0] - Terminal2button[key][0] #determine oreintation of button
                    if x_button_diff != 0:
                        #adjust oreintation of meander or reinforcement rectangle
                        temp = reinforcements['button'][0]
                        reinforcements['button'][0] = reinforcements['button'][1]
                        reinforcements['button'][1] = temp

                    meander_terminal(nodepos, node['comp'],reinforce=True) #meander
                    ink_off() #switch off ink
                    #Reset change of oreintation in reinforcement rectangle
                    temp = reinforcements['button'][0]
                    reinforcements['button'][0] = reinforcements['button'][1]
                    reinforcements['button'][1] = temp

                node_z_heaven = nodepos[2] + 50/1000 #Move to heaven (mm to m)
                current_node_heaven = [nodepos[0],nodepos[1],node_z_heaven] + [0,pi,0]
                rtde_control.moveL(current_node_heaven, speed=slow)

            if node['comp'] == "battery" and node['batteryneg'] == "n": #if component is battery and terminal is negative
                nodepos = node['pos']+[0,pi,0] #get node position
                key = node['comp_id']
                #get positive and negative terminal of battery
                posterminal = positive_battery_terminal_pos[key][:2]
                negterminal = nodepos[:2]

                #determine x and y differences in terminal positions
                x_diff = posterminal[0] - negterminal[0]
                y_diff = posterminal[1] - negterminal[1]

                #determine angle
                if x_diff == 0:
                    if y_diff > 0:
                        angle = 90
                    else:
                        angle = 270
                else:
                    if x_diff > 0:
                        angle = 0
                    else:
                        angle = 180

                radius = reinforcements['battery'][0]/39.37
                minangle = angle - 120
                minangle = math.radians(minangle)
                #determine start_x,start_y, move to start_x,start_y
                start_x = (radius * math.cos(minangle)) + nodepos[0]
                start_y = (radius * math.sin(minangle)) + nodepos[1]
                startpos = [start_x,start_y,nodepos[2],nodepos[3],nodepos[4],nodepos[5]]
                rtde_control.moveL(startpos,speed=slow)

                if not DRY_RUN:
                    set_pressure(PRINT_PRESSURE)
                    ink_on()
                    time.sleep(PRIMER_DELAY)
                meander_terminal(nodepos, node['comp'],reinforce=True) #meander/reinforce battery
                ink_off()
                node_z_heaven = nodepos[2] + 50/1000 #Move to heaven (mm to m)
                current_node_heaven = [nodepos[0],nodepos[1],node_z_heaven] + [0,pi,0]
                rtde_control.moveL(current_node_heaven, speed=slow)
    if not DRY_RUN:
        clear_tip(delay=0.5)
    return_inkprinter()

def move_to_node(pos, comp, pole, index, maxindex,speed=0.005):
    if index == 0:
        speed = slow
    else:
        speed = 0.005
    if index == maxindex: #if this is the last node in the wire
        rtde_control.moveL(pos, speed=speed)
        printink(terminal_pos=pos,terminal_component=comp, terminal_polarity=pole) #call print_ink to meander
    else:
        rtde_control.moveL(pos, speed=speed) #else just move to the node
#-----------------------------------------------------------------------------------------------------------
# === # Ink Trace Printing Code # === #


def ink_trace(file_path,dry_run=True):
    """
    Main script loop
    """
    global DRY_RUN
    DRY_RUN = dry_run
    wire_schematic = get_traces(file_path) #get schematic
    grab_inkprinter() #grab ink printer

    for wire in wire_schematic: #for each wire in schematic
        for i,node in enumerate(wire): #for each node in wire
            nodepos = node['pos']+[0,pi,0] #get node position
            if i==0 and node['comp'] != "empty": #if first node of wire
                rtde_control.moveL(nodepos, speed=fast) #move to position
                printink(terminal_pos=nodepos,terminal_component=node['comp'], terminal_polarity=node['batteryneg']) #print ink
            else:
                move_to_node(pos=nodepos,comp=node['comp'],pole=node['batteryneg'],index=i,maxindex=len(wire) - 1) #else move to node

        ink_off() #after drawing wire, ink off
        z_heaven = wire[len(wire) - 1]['pos'][2] + 50/1000 #Move to heaven (mm to m)
        node_heaven = [wire[len(wire) - 1]['pos'][0],wire[len(wire) - 1]['pos'][1],z_heaven] + [0,pi,0]
        rtde_control.moveL(node_heaven, speed=slow)

    if not DRY_RUN:
        clear_tip(delay=0.5)
    return_inkprinter()

#Test InkTracing Module
# testing_run = True # False if extrusion, true if dry run
# filename = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\minimaltest.json"
# ink_trace(filename,dry_run=testing_run)
# reinforcement_schematic = get_traces(filename,reinforce=True)
# reinforce_connection(reinforcement_schematic,dry_run=testing_run)
