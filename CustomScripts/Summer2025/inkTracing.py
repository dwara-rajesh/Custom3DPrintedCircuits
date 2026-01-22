"""
Module containing the code to program and control the Ink Trace Printing functionality
"""

import time
from math import pi,sqrt,radians,sin,cos
import json

# Import core module:
import coreModule

# Ink printing extrusion parameters
PRINT_PRESSURE = 40 #reduce if too much extrusion of ink is too much # [psi] Pressure of the pneumatic extrusion line - Original value: 70psi
PRINT_SPEED = 0.005

#Adjust PRIMER_DELAY if ink extrusion is slow
PRIMER_DELAY = 1.0 # [s] Delay in seconds that the printer waits before starting to move to allow ink time to flow through the nozzle
PRINT_ACCEL = 0.8 # Printing uses reduced acceleration to avoid breaking the traces
pressure_stabilization = 1.0 # in seconds to wait for pressure stabilization in setup
pressure_set = False
DRY_RUN = True
angle = 0

# Testing parameters - Uncomment only on module testing event
# filename = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\DEMO2.json" #circuit being tested
# coreModule.get_stock_height_offset(filename)
# print(f"Stock height offset: {coreModule.STOCK_HEIGHT_OFFSET}")

coreModule.load_calibration_data() #obtain calibration data after calibration is complete
z_origin_ink = coreModule.CALIBRATION_DATA['ink'][2] + coreModule.top_right_vise[2] + coreModule.STOCK_HEIGHT_OFFSET - 1.0 / 1000#offset the origin by calibration data to avoid hitting the vise and stock height offset to avoid hitting stock
origin_in_m_ink = [coreModule.top_right_vise[0],coreModule.top_right_vise[1]-coreModule.admlviceblock_yoff,z_origin_ink, 0, pi, 0] #top right corner of stock on vice in rosie station in meters
origin_ink = [val * 1000 for val in origin_in_m_ink[:3]] + [0,pi,0] #origin in mm

#in inches - the size of solder/meander square
meander_square_size = {"battery":0.025,
                  "microcontroller":0.005,
                  "button":0.01,
                  "led":0.005}
#in inches - the size of reinforements
reinforcements = {
    "battery": [0.375,0.375], #(l = radius of battery, w = radius of battery)
    "button": [0.20,0.50], #(l = length of meander, w = width of meander)
}
wire_schematic = []

#Keeps track of meandered and reinforced terminals to ensure it does not repeat
meandered_terminals = []
reinforced_terminals = []

slant_line_height_inches = 0.059 #in inches
slant_line_height = slant_line_height_inches / 39.37 #convert inches to m
"""
|<     node1 to node2     >|
|< node1 to midpoint|
---------------------------- _
                     \       | slant_line_height
                  ____\____  _
"""

trapezium_long_base_offset_inches = 0.063 #in inches. For negative terminal of battery -> neighbour node: trapezium long length - distance of negative terminal of battery -> neighbour node
trapezium_height_inches = 0.047 #in inches. Height of trapezium
trapezium_long_base_offset = trapezium_long_base_offset_inches / 39.37 #convert inches to m
trapezium_height = trapezium_height_inches / 39.37 #convert inches to m
"""
|<trapezium_long_base_offset>|< trapezium long length>| _
4----------------------------3------------------------0 ^
                              \                      /  | trapezium_height
                              2\____________________/1  _
|<dist of negative battery terminal to neighbour node>|
"""

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
            #get position (x,y,z) convert in to m
            nodeX = (origin_ink[0] + (node['posX'] * 25.4)) / 1000
            nodeY = (origin_ink[1] + (node['posY'] * 25.4)) / 1000
            if not reinforce:
                nodeZ = origin_ink[2] / 1000
            else:
                nodeZ = origin_ink[2] / 1000 + 0.5/1000 #if reinforce offset z + a little offset

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
    global pressure_stabilization
    global pressure_set

    if not pressure_set:
        pressure_set = True
        if DRY_RUN == True:
            coreModule.set_pressure(coreModule.ATMOSPHERE) #no ink is extruded
        else:
            coreModule.set_pressure(print_pressure) #ink is extruded
        time.sleep(pressure_stabilization)
        coreModule.ink_on()
        time.sleep(primer_delay)
    else:
        coreModule.ink_on()

    if terminal_component != "battery" or terminal_polarity == "n": #if component is not battery or if the terminal component is battery and is a negative terminal
        meander_terminal(terminal_pos,terminal_component) #then meander

def meander_terminal(centre, component, k=3,speed=coreModule.precise, reinforce=False):
    global angle
    global meandered_terminals
    global reinforced_terminals
    component = component.lower()
    if reinforce:
        speed = PRINT_SPEED
        k = 10 #increase the layers from 3 to 10
        if component == "battery": #if battery, draw an arc to secure placement
            radius = reinforcements[component][0]/39.37
            #range is basically angle-120 -> angle + 120, so arc angle is 240 but 120 on either side of the middle
            rangemax = angle + 120
            rangemin = angle - 120
            for i in range(rangemin,rangemax+1,10): #go from rangemin to rangemax in intervals of 10 degrees
                rads = radians(i) #convert degrees to radians
                #get next position using pythagoras theorem
                next_x = radius * cos(rads) + centre[0] #get next_x
                next_y = radius * sin(rads) + centre[1] #get next_y
                endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]]
                coreModule.rtde_control.moveL(endpos,speed=speed) #move to position
        else: #if any other component, meander with larger sizes
            start_x = centre[0] - (reinforcements[component][0]*0.5/39.37)
            start_y = centre[1] - (reinforcements[component][1]*0.5/39.37)

            end_x = centre[0] + (reinforcements[component][0]*0.5/39.37)
            end_y = centre[1] + (reinforcements[component][1]*0.5/39.37)

            y_step = ((end_y - start_y) / k)

            startpos = [start_x,start_y,centre[2],centre[3],centre[4],centre[5]]
            coreModule.rtde_control.moveL(startpos,speed=speed)
            next_x = end_x
            next_y = start_y
            for i in range(k*2):
                endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]]
                coreModule.rtde_control.moveL(endpos,speed=speed)
                if i % 2 == 0:
                    next_y = next_y + y_step
                else:
                    if next_x == end_x:
                        next_x = start_x
                    else:
                        next_x = end_x

            coreModule.rtde_control.moveL(centre,speed=speed)
        reinforced_terminals.append({centre,component})
    else:
        '''
        Meander is a zig zag motion of sorts, if k = 3
                        end_x,end_y
            |-------------->|
            |<--------------|
            --------------->| y_step
        start_x,start_y
        '''
        if {centre,component} in meandered_terminals:
            pass
        else:
            if component == "battery":
                speed = PRINT_SPEED
            #determine start_x,start_y
            start_x = centre[0] - (meander_square_size[component]*0.5/39.37)
            start_y = centre[1] - (meander_square_size[component]*0.5/39.37)

            #determine end_x,end_y
            end_x = centre[0] + (meander_square_size[component]*0.5/39.37)
            end_y = centre[1] + (meander_square_size[component]*0.5/39.37)

            #determine y_step
            y_step = ((end_y - start_y) / k)

            startpos = [start_x,start_y,centre[2],centre[3],centre[4],centre[5]]
            coreModule.rtde_control.moveL(startpos,speed=speed) #move to start position
            #get next position
            next_x = end_x
            next_y = start_y
            #meander
            for i in range(k*2):
                endpos = [next_x,next_y,centre[2],centre[3],centre[4],centre[5]] #move to next position
                coreModule.rtde_control.moveL(endpos,speed=speed)
                if i % 2 == 0:
                    next_y = next_y + y_step #move to next layer
                else:
                    if next_x == end_x: #move to other end
                        next_x = start_x
                    else:
                        next_x = end_x
            #return to centre position of meander after meandering
            coreModule.rtde_control.moveL(centre,speed=speed)

            meandered_terminals.append({centre,component})

def reinforce_connection(reinforced_wire_schematic, dry_run = True):
    global angle
    global DRY_RUN
    global reinforcements
    global pressure_stabilization
    global pressure_set
    global reinforced_terminals
    pressure_set = False
    DRY_RUN = dry_run
    coreModule.grab_inkprinter()
    coreModule.set_pressure(coreModule.ATMOSPHERE)
    time.sleep(pressure_stabilization)
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
        coreModule.rtde_control.moveL(positive_battery_terminal_pos[positiveterminals], speed=coreModule.slow) #go to position
        if not pressure_set:
            pressure_set = True
            if DRY_RUN == True:
                coreModule.set_pressure(coreModule.ATMOSPHERE) #no ink is extruded
            else:
                coreModule.set_pressure(PRINT_PRESSURE) #ink is extruded
            time.sleep(pressure_stabilization)
            coreModule.ink_on()
            time.sleep(PRIMER_DELAY)
        else:
            coreModule.ink_on()
        coreModule.rtde_control.moveL(positive_battery_neighbouring_node[positiveterminals], speed=PRINT_SPEED) #go to position

        coreModule.ink_off()
        node_position = positive_battery_neighbouring_node[positiveterminals]
        node_z_heaven = node_position[2] + 50/1000 #Move to heaven (mm to m)
        current_node_heaven = [node_position[0],node_position[1],node_z_heaven] + [0,pi,0]
        time.sleep(0.1)
        coreModule.rtde_control.moveL(current_node_heaven, speed=coreModule.fast)

    for wire in reinforced_wire_schematic: #for each wire in schematic
        for i,node in enumerate(wire): #for each node in wire
            if node['comp'] == "button": #if component is button
                nodepos = node['pos']+[0,pi,0]
                key = node['comp_id']
                x_button_diff = Terminal1button[key][0] - Terminal2button[key][0] #determine oreintation of button
                if x_button_diff == 0:
                    if (nodepos[:2] == Terminal1button[key]):
                        if (Terminal1button[key][1] > Terminal2button[key][1]):
                            nodepos[1] = nodepos[1] + 0.09 / 39.37
                        else:
                            nodepos[1] = nodepos[1] - 0.09 / 39.37
                    else:
                        if (Terminal1button[key][1] > Terminal2button[key][1]):
                            nodepos[1] = nodepos[1] - 0.09 / 39.37
                        else:
                            nodepos[1] = nodepos[1] + 0.09 / 39.37
                    #adjust oreintation of meander or reinforcement rectangle
                    temp = reinforcements['button'][0]
                    reinforcements['button'][0] = reinforcements['button'][1]
                    reinforcements['button'][1] = temp
                else:
                    if (nodepos[:2] == Terminal1button[key]):
                        if (Terminal1button[key][0] > Terminal2button[key][0]):
                            nodepos[0] = nodepos[0] + 0.09 / 39.37
                        else:
                            nodepos[0] = nodepos[0] - 0.09 / 39.37
                    else:
                        if (Terminal1button[key][0] > Terminal2button[key][0]):
                            nodepos[0] = nodepos[0] - 0.09 / 39.37
                        else:
                            nodepos[0] = nodepos[0] + 0.09 / 39.37

                if {nodepos, node['comp']} in reinforced_terminals:
                    pass
                else:
                    coreModule.rtde_control.moveL(nodepos, speed=coreModule.slow) #go to position
                    coreModule.ink_on()
                    time.sleep(PRIMER_DELAY)
                    meander_terminal(nodepos, node['comp'],reinforce=True) #meander
                    coreModule.ink_off() #switch off ink
                    #Reset change of oreintation in reinforcement rectangle
                    if x_button_diff == 0:
                        temp = reinforcements['button'][0]
                        reinforcements['button'][0] = reinforcements['button'][1]
                        reinforcements['button'][1] = temp

                    node_z_heaven = nodepos[2] + 50/1000 #Move to heaven (mm to m)
                    current_node_heaven = [nodepos[0],nodepos[1],node_z_heaven] + [0,pi,0]
                    time.sleep(0.1)
                    coreModule.rtde_control.moveL(current_node_heaven, speed=coreModule.fast)

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
                minangle = radians(minangle)
                #determine start_x,start_y, move to start_x,start_y
                start_x = (radius * cos(minangle)) + nodepos[0]
                start_y = (radius * sin(minangle)) + nodepos[1]
                startpos = [start_x,start_y,nodepos[2],nodepos[3],nodepos[4],nodepos[5]]

                if {nodepos, node['comp']} in reinforced_terminals:
                    pass
                else:
                    coreModule.rtde_control.moveL(startpos,speed=coreModule.slow)
                    coreModule.ink_on()
                    time.sleep(PRIMER_DELAY)
                    meander_terminal(nodepos, node['comp'],reinforce=True) #meander/reinforce battery
                    coreModule.ink_off()
                    node_z_heaven = nodepos[2] + 50/1000 #Move to heaven (mm to m)
                    current_node_heaven = [nodepos[0],nodepos[1],node_z_heaven] + [0,pi,0]
                    time.sleep(0.1)
                    coreModule.rtde_control.moveL(current_node_heaven, speed=coreModule.fast)

    coreModule.return_inkprinter()

def move_to_node(pos, comp, pole, index, maxindex,speed=PRINT_SPEED):
    global pressure_set
    if index == 0:
        speed = coreModule.fast
        coreModule.rtde_control.moveL(pos, speed=speed) #else just move to the node
        if not pressure_set:
            pressure_set = True
            if DRY_RUN == True:
                coreModule.set_pressure(coreModule.ATMOSPHERE) #no ink is extruded
            else:
                coreModule.set_pressure(PRINT_PRESSURE) #ink is extruded
            time.sleep(pressure_stabilization)
            coreModule.ink_on()
            time.sleep(PRIMER_DELAY)
        else:
            coreModule.ink_on()

    if index == maxindex and comp != "empty": #if this is the last node in the wire
        coreModule.rtde_control.moveL(pos, speed=speed)
        printink(terminal_pos=pos,terminal_component=comp, terminal_polarity=pole) #call print_ink to meander
    else:
        coreModule.rtde_control.moveL(pos, speed=speed)

#-----------------------------------------------------------------------------------------------------------
# === # Ink Trace Printing Code # === #


def ink_trace(file_path,dry_run=True):
    """
    Main script loop
    """
    global DRY_RUN
    DRY_RUN = dry_run
    wire_schematic = get_traces(file_path) #get schematic
    coreModule.grab_inkprinter() #grab ink printer

    battery_wire_indices = {}
    for j, wire in enumerate(wire_schematic):
        for i,node in enumerate(wire):
            if node['comp'] == "battery":
                battery_wire_indices[j] = i
                break

    for j, wire in enumerate(wire_schematic): #for each wire in schematic
        if j in battery_wire_indices:
            #Print negative battery terminal properly
            i = battery_wire_indices[j]
            if i == 0:
                battery_terminal_x = wire[i]['pos'][0]
                battery_terminal_y = wire[i]['pos'][1]
                neighbour_node_x = wire[i+1]['pos'][0]
                neighbour_node_y = wire[i+1]['pos'][1]
                slant_neighbour_node_x = wire[i+2]['pos'][0]
                slant_neighbour_node_y = wire[i+2]['pos'][1]
                other_terminal = wire[i+3]
            else:
                battery_terminal_x = wire[i]['pos'][0]
                battery_terminal_y = wire[i]['pos'][1]
                neighbour_node_x = wire[i-1]['pos'][0]
                neighbour_node_y = wire[i-1]['pos'][1]
                slant_neighbour_node_x = wire[i-2]['pos'][0]
                slant_neighbour_node_y = wire[i-2]['pos'][1]
                other_terminal = wire[i-3]

            #trapezium
            dist_neg_battery_to_neighbour = sqrt(((neighbour_node_x - battery_terminal_x)**2) + ((neighbour_node_y - battery_terminal_y)**2))
            #get point 1, point 2, point 3 of trapezium. PS: point 0 = battery negative terminal and point 4 = neighbour node
            #point 1
            x1 = ((dist_neg_battery_to_neighbour * (neighbour_node_x + (3 * battery_terminal_x))) + (trapezium_long_base_offset * (battery_terminal_x - neighbour_node_x))) / (4 * dist_neg_battery_to_neighbour)
            y1 = ((dist_neg_battery_to_neighbour * (neighbour_node_y + (3 * battery_terminal_y))) + (trapezium_long_base_offset * (battery_terminal_y - neighbour_node_y))) / (4 * dist_neg_battery_to_neighbour)
            z1 = wire[i]['pos'][2] - (trapezium_height + slant_line_height)
            point_1_pos = [x1, y1, z1, 0, pi, 0]
            #point 2
            x2 = ((dist_neg_battery_to_neighbour * ((3 * neighbour_node_x) + battery_terminal_x)) + ((3 * trapezium_long_base_offset)*(battery_terminal_x - neighbour_node_x))) / (4 * dist_neg_battery_to_neighbour)
            y2 = ((dist_neg_battery_to_neighbour * ((3 * neighbour_node_y) + battery_terminal_y)) + ((3 * trapezium_long_base_offset)*(battery_terminal_y - neighbour_node_y))) / (4 * dist_neg_battery_to_neighbour)
            z2 = wire[i]['pos'][2] - (trapezium_height + slant_line_height)
            point_2_pos = [x2, y2, z2, 0, pi, 0]
            #point 3
            x3 = ((dist_neg_battery_to_neighbour * neighbour_node_x) + (trapezium_long_base_offset * (battery_terminal_x - neighbour_node_x))) / dist_neg_battery_to_neighbour
            y3 = ((dist_neg_battery_to_neighbour * neighbour_node_y) + (trapezium_long_base_offset * (battery_terminal_y - neighbour_node_y))) / dist_neg_battery_to_neighbour
            z3 = wire[i]['pos'][2] - slant_line_height
            point_3_pos = [x3, y3, z3, 0, pi, 0]

            #slant
            #slant_midpoint
            slant_mid_x = (slant_neighbour_node_x + neighbour_node_x) / 2
            slant_mid_y = (slant_neighbour_node_y + neighbour_node_y) / 2

            slant_mid_pos = [slant_mid_x,slant_mid_y,wire[i]['pos'][2],0,pi,0]

            if i == 0: #if battery negative terminal first : battery neg -> point 1 -> point 2 -> point 3 -> neighbour node(point 4) -> slant mid point -> slant neighbour node -> other terminal
                nodepos_battery = wire[i]['pos'] + [0,pi,0]
                coreModule.rtde_control.moveL(nodepos_battery, speed=coreModule.fast) #move to battery negative terminal
                printink(terminal_pos=nodepos_battery,terminal_component=wire[i]['comp'], terminal_polarity=wire[i]['batteryneg']) #print ink
                coreModule.rtde_control.moveL(point_1_pos, speed=PRINT_SPEED) #move to point 1 trapezium
                coreModule.rtde_control.moveL(point_2_pos, speed=PRINT_SPEED) #move to point 2 trapezium
                coreModule.rtde_control.moveL(point_3_pos, speed=PRINT_SPEED) #move to point 3 trapezium
                nodepos_neighbour = [neighbour_node_x,neighbour_node_y,z3,0,pi,0]
                coreModule.rtde_control.moveL(nodepos_neighbour, speed=PRINT_SPEED) #move to neighbour node (point 4)
                coreModule.rtde_control.moveL(slant_mid_pos, speed=PRINT_SPEED) #move to slant midpoint
                nodepos_slant_neighbour = [slant_neighbour_node_x,slant_neighbour_node_y,slant_mid_pos[2],0,pi,0]
                coreModule.rtde_control.moveL(nodepos_slant_neighbour, speed=PRINT_SPEED) #move to slant neighbour
                nodepos_other_terminal = other_terminal['pos'] + [0,pi,0]
                coreModule.rtde_control.moveL(nodepos_other_terminal, speed=PRINT_SPEED) #move to other terminal to finish wire connection
                printink(terminal_pos=nodepos_other_terminal,terminal_component=other_terminal['comp'], terminal_polarity=other_terminal['batteryneg']) #print ink
                z_heaven = other_terminal['pos'][2] + 50/1000 #Move to heaven (mm to m)
                node_heaven = [other_terminal['pos'][0],other_terminal['pos'][1],z_heaven] + [0,pi,0]
            else: #order in reverse
                nodepos_other_terminal = other_terminal['pos'] + [0,pi,0]
                coreModule.rtde_control.moveL(nodepos_other_terminal, speed=coreModule.fast) #move to component
                printink(terminal_pos=nodepos_other_terminal,terminal_component=other_terminal['comp'], terminal_polarity=other_terminal['batteryneg']) #print ink
                nodepos_slant_neighbour = [slant_neighbour_node_x,slant_neighbour_node_y,slant_mid_pos[2],0,pi,0]
                coreModule.rtde_control.moveL(nodepos_slant_neighbour, speed=PRINT_SPEED) #move to slant neighbour
                coreModule.rtde_control.moveL(slant_mid_pos, speed=PRINT_SPEED) #move to slant midpoint
                nodepos_neighbour = [neighbour_node_x,neighbour_node_y,z3,0,pi,0]
                coreModule.rtde_control.moveL(nodepos_neighbour, speed=PRINT_SPEED) #move to neighbour node (point 4)
                coreModule.rtde_control.moveL(point_3_pos, speed=PRINT_SPEED) #move to point 3 trapezium
                coreModule.rtde_control.moveL(point_2_pos, speed=PRINT_SPEED) #move to point 2 trapezium
                coreModule.rtde_control.moveL(point_1_pos, speed=PRINT_SPEED) #move to point 1 trapezium
                nodepos_battery = wire[i]['pos'] + [0,pi,0]
                coreModule.rtde_control.moveL(nodepos_battery, speed=PRINT_SPEED) #move to battery negative terminal
                printink(terminal_pos=nodepos_battery,terminal_component=wire[i]['comp'], terminal_polarity=wire[i]['batteryneg']) #print ink
                z_heaven = wire[i]['pos'][2] + 50/1000 #Move to heaven (mm to m)
                node_heaven = [wire[i]['pos'][0],wire[i]['pos'][1],z_heaven] + [0,pi,0]

            coreModule.ink_off()
            time.sleep(0.1)
            coreModule.rtde_control.moveL(node_heaven, speed=coreModule.fast)
        else:
            for i,node in enumerate(wire): #for each node in wire
                nodepos = node['pos']+[0,pi,0] #get node position
                if i==0 and node['comp'] != "empty": #if first node of wire
                    coreModule.rtde_control.moveL(nodepos, speed=coreModule.fast) #move to position
                    printink(terminal_pos=nodepos,terminal_component=node['comp'], terminal_polarity=node['batteryneg']) #print ink
                else:
                    move_to_node(pos=nodepos,comp=node['comp'],pole=node['batteryneg'],index=i,maxindex=len(wire) - 1) #else move to node

            coreModule.ink_off() #after drawing wire, ink off
            z_heaven = wire[len(wire) - 1]['pos'][2] + 50/1000 #Move to heaven (mm to m)
            node_heaven = [wire[len(wire) - 1]['pos'][0],wire[len(wire) - 1]['pos'][1],z_heaven] + [0,pi,0]
            time.sleep(0.1)
            coreModule.rtde_control.moveL(node_heaven, speed=coreModule.fast)

    coreModule.return_inkprinter()

## TESTING: Uncomment only on module testing event
# # Testing parameters
# testing_run = False # False if extrusion, true if dry run

# # Test InkTracing Module
# ink_trace(filename,dry_run=testing_run) #IMPORTANT: This will NOT draw the positive wire of battery

# # Reinforcement - run AFTER ink_trace and pick and place
# # IMPORTANT: This draws positive wire of battery and reinforce the connections
# reinforcement_schematic = get_traces(filename,reinforce=True)
# reinforce_connection(reinforcement_schematic,dry_run=testing_run)