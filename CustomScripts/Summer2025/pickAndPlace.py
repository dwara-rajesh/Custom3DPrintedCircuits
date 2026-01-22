"""
Module containing the code to program and control the Pick-and-Place functionality
"""

import time,math,keyboard,os,json

# Import core module:
import coreModule

#-----------------------------------------------------------------------------------------------------------
# === # Pick-And-Place Code # === #

PRESSURE_THRESHOLD = 6.0 # If vacuum is on, and pressure reading is below this, an object has been picked up!

## Testing parameters - Uncomment only on module testing event
# filename = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\minimaltest.json"
# coreModule.get_stock_height_offset(filename)
# print(f"Stock height offset: {coreModule.STOCK_HEIGHT_OFFSET}")

coreModule.load_calibration_data() #obtain calibration data after calibration is complete
z_origin_vac = coreModule.CALIBRATION_DATA['vac'][2] + coreModule.top_right_vise[2] + coreModule.STOCK_HEIGHT_OFFSET #offset the origin by calibration data to avoid hitting the vise and stock height offset to avoid hitting stock
origin_in_m_vac = [coreModule.top_right_vise[0],coreModule.top_right_vise[1]-coreModule.admlviceblock_yoff,z_origin_vac, 0, math.pi, 0] #top right corner of stock on vice in rosie station in meters
origin_vac = [val * 1000 for val in origin_in_m_vac[:3]] + [0,math.pi,0] #origin in mm
tip_offset_from_gripper = 1.1705 * 25.4 #nozzle offset from center of gripper (convert in to mm)
#global variables for pickup status checking
pickupfailed = False
pickedup = False

# Placeholder for component stock index tracking (To account for depletion of tray components)
placed_components = {
    "battery": [],
    "microcontroller": [],
    "button": [],
    "led": []
    }
# Position data (In table coordinates) of the electronic component tray grids (Only XY coordinates)
COMPONENTS = {'battery': {'start': [91.87, 50.15],   # XY coords of the start of the grid (Bottom left corner)
                            'end': [142.33, 100.72], # XY coords of the end of the grid (Top right corner)
                           'grid': (3, 3),           # Grid dimensions (3x3)
                      'threshold': 9.7,              # Pressure threshold for pickup
                   'pocket_depth': 0.082,            # Max allowed depth into pocket in tray (in inches)
                          'z_val': 0.0},             # Height offset for pick up (Active pressure feedback pickup starts at this height)
                  'led': {'start': [22.55, 66.63],
                            'end': [67.39, 106.07],
                           'grid': (4, 5),           # Grid dimensions (4x5)
                      'threshold': 10.84,
                   'pocket_depth': 0.14,
                          'z_val': 0.0},
               'button': {'start': [29.7, 13.95],
                            'end': [60.45, 50.25],
                           'grid': (2, 4),           # Grid dimensions (2x4)
                      'threshold': 9.4,
                   'pocket_depth': 0.2,
                          'z_val': 1.0},
      'microcontroller': {'start': [101.84, 19.98],
                            'end': [139.93, 19.98],
                           'grid': (2, 1),           # Grid dimensions (2x1)
                      'threshold': 9.7,
                   'pocket_depth': 0.124,
                          'z_val': -1.0}}

#function allows for mapping component position and orientation to robot world coordinates for components
def determine_schematic(recentsavefilepath):
    with open(recentsavefilepath, 'r') as f:
        data = json.load(f)

    circuit_schematic = []
    for component in data['componentdata']: #go through all component information
        if component['modelName'] != "stock": #if its not stock
            name = os.path.splitext(os.path.basename(component['modelName']))[0].lower() #get component name
            #get position (x,y,z)
            position_x = origin_vac[0] + (component['posX'] * 25.4) #convert in to mm
            position_y = origin_vac[1] + (component['posY'] * 25.4)
            position_z = origin_vac[2] + coreModule.COMPONENT_HEIGHTS[name]
            position = [position_x,position_y,position_z]
            #get rotation and update position to align nozzle tip to position after rotation
            if component['rotZ'] == 270:
                component['rotZ'] = -90
                position = [position_x-tip_offset_from_gripper,position_y+tip_offset_from_gripper,position_z]
            elif component['rotZ'] == 90:
                position = [position_x-tip_offset_from_gripper,position_y-tip_offset_from_gripper,position_z]
            elif component['rotZ'] == 180:
                position = [position_x-2*tip_offset_from_gripper,position_y,position_z]
            rotation = math.radians(component['rotZ'])
            circuit_schematic.append({'type': name, 'pos': position, 'rot': rotation}) #populate in a set for later usage

    return circuit_schematic

def move_to_component(component, index, Z_target=2.0, speed=coreModule.precise):
    """
    Moves nozzle above component #index for the given
    component type on the tray

    Component is given by string name, ex: 'battery'

    Component index is a number from 0 to num-1 starting
    at the bottom left corner and moving up a column and
    then over a row. For example, a 3x4 grid is indexed:
    8 9 10 11   ^
    4 5 6 7  Y|
    0 1 2 3    O-X->

    A Z offset can be specified to provide clearance above component
    Default is 2mm
    """

    # Check that given component is valid, and its index exists in the grid:
    if component not in COMPONENTS:
        msg =  f"ComponentName ERROR, {component} is not a valid component!"
        return msg
    if index >= COMPONENTS[component]['grid'][0] * COMPONENTS[component]['grid'][1]:
        msg = f"ComponentGridIndex ERROR: index {index + 1} is outside the grid!"
        return msg

    pos_data = COMPONENTS[component]

    # Calculate component spacing
    step_x = 0
    step_y = 0
    if pos_data['grid'][0] >= 2: # Prevent dividing by zero
        step_x = (pos_data['end'][0] - pos_data['start'][0]) / (pos_data['grid'][0] - 1)
    if pos_data['grid'][1] >= 2: # Prevent dividing by zero
        step_y = (pos_data['end'][1] - pos_data['start'][1]) / (pos_data['grid'][1] - 1)

    # Calculate component grid coordinates
    column_num = index % pos_data['grid'][0]
    row_num = index // pos_data['grid'][0]

    # Compute final position and move there
    target_pos = [step_x*column_num + pos_data['start'][0],
                  step_y*row_num + pos_data['start'][1],
                  Z_target]
    coreModule.goto_pos(target_pos, speed=speed) #go to position
    return target_pos

def pickup_component(component, index, skip_hover=False, print_warnings=False,print_log=False):
    """
    Moves to, and picks up the specified component using the
    vacuum pick-and-place nozzle

    Achieves this by stepping towards the component until the
    nozzle pressure decreases dramatically (indicating contact and seal)

    The nozzle first moves to the target XY coords at heaven height, then lowers to
    the particular component's z-val height, and then begins the stepped active
    pressure monitoring pickup approach.
    """
    global pickupfailed
    global pickedup
    global placed_components
    heaven = 54.0 # Z coordinate above part pick up location
    step = 0.01 # In mm

    #vertical_clearance = -1.0 # In mm - TO DECREASE PROCESS TIME SET VALUE TO -2mm IF USING STANDARD AMBER NOZZLE
    #if component == 'switch':
    #    vertical_clearance -= 2 # Pick up switches from lower height to save time

    PRESSURE_THRESHOLD = COMPONENTS[component]['threshold'] # Component-specific pressure threshold for pickup
    MAX_FORCE = 100 # Max force to be applied by the nozzle if no pressure drop is detected

    # Move nozzle above component and store position
    if skip_hover != True: # By default, nozzle moves to component location at heaven height, and then lowers onto it (This can be skipped)
        move_to_component(component=component, index=index, Z_target=heaven)
    initial_pos = move_to_component(component=component, index=index, Z_target=COMPONENTS[component]['z_val'])

    initial_pos = coreModule.get_pos()
    target_pos = initial_pos.copy()

    # Slowly step downwards monitoring the vacuum pressure
    coreModule.vacuum_on() # Turn vacuum on if it is not already
    if print_log:
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Vacuum On\n")
        print("Vacuum On")

    depth_travelled_into_grid = abs(initial_pos[2] - target_pos[2]) #distance travelled into grid/tray of components (in mm)
    while coreModule.get_pressure() > PRESSURE_THRESHOLD and depth_travelled_into_grid < (COMPONENTS[component]['pocket_depth'] * 25.4): # True when object not yet picked up
        nozzle_forces = coreModule.rtde_receive.getActualTCPForce()
        if nozzle_forces[2] <= MAX_FORCE: # Check to ensure that if the vacuum fails, we still stop the nozzle safely!
            target_pos[2] -= step #step further into the tray/grid slot to try and pickup
            depth_travelled_into_grid = abs(initial_pos[2] - target_pos[2]) #update the depth travelled
            coreModule.goto_pos(target_pos, speed=coreModule.micrometric) #move to new position
        else:
            if keyboard.is_pressed('ctrl'): # Ctrl key can be used to break out of loop if pickup fails
                break
            if print_warnings == True:
                with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                    file.write("Pick-and-Place nozzle WARNING: Max force exceeded!\n")
                print("Pick-and-Place nozzle WARNING: Max force exceeded!")
    placed_components[component].append(index) #update placed_components list
    inventory_management('w') #write into inventory to update pickup or pickup fail to indicate component presence or absence in slot
    if depth_travelled_into_grid >= (COMPONENTS[component]['pocket_depth'] * 25.4) and print_warnings: #check and log if depth travelled is more than max allowed depth
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Pick-and-Place nozzle WARNING: Max depth inside grid pocket reached!\n")
        print("Pick-and-Place nozzle WARNING: Max depth inside grid pocket reached!")
    if coreModule.get_pressure() > PRESSURE_THRESHOLD: #if pressure is greater than threshold, failed pickup
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write(f"Pick N Place: Failed to pickup {component} in slot #{index + 1}, moving to next slot to attempt pickup\n")
        print(f"Pick N Place: Failed to pickup {component} in slot #{index + 1}, moving to next slot to attempt pickup")
        index += 1 #next slot number
        grid = COMPONENTS[component]['grid']
        maxindex = grid[0] * grid[1]
        if index >= maxindex: #check if next slot number is great than max slots
            pickupfailed = True #if yes, inventory empty
        else:
            coreModule.vacuum_off() #else switch off vacuum
            if print_log:
                with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                    file.write("Vacuum  Off\n")
                print("Vacuum  Off")
            target_pos = pickup_component(component=component, index=index) #move to the next slot
    else:
        pickedup = True #else pickup success
        if print_log:
            with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                file.write(f"Pick N Place: Picked up [{component}] from slot [{index + 1}]\n")
            print(f"Pick N Place: Picked up [{component}] from slot [{index + 1}]")

    if pickupfailed:
        index = maxindex
        pass
    else:
        # Assuming the pressure drop means the object was picked up, move the nozzle up to pick the component out of the tray
        if pickedup:
            pickedup = False
            heaven_pos = initial_pos.copy()
            heaven_pos[2] = heaven
            time.sleep(1) # Small delay to allow vacuum to set in before lifting component
            coreModule.goto_pos(heaven_pos)

    return pickupfailed

def place_component(target_pos,rot, heaven=0.4318552510405578,print_log=False):
    """
    Places the currently held component at the target coordinates
    Travels at heaven height to avoid collisions

    Assumes that the nozzle vacuum is ON and currently holding a component!
    """
    # Travel to target coordinates
    coreModule.rtde_control.moveL([target_pos[0], target_pos[1], heaven,0,math.pi,0], speed=coreModule.precise)

    jointangles = coreModule.rtde_receive.getActualQ() #get joint angles of robot

    #rotate the last joint/gripper to orient the component as per schematic/circuit diagram
    initialjoint = jointangles[5]
    jointangles[5] += rot
    coreModule.rtde_control.moveJ(jointangles)

    #get the current rotation after rotation
    currentrot = coreModule.get_robot_pos()[3:]
    #update destination position and move to position
    finaltarget = target_pos + currentrot
    coreModule.rtde_control.moveL(finaltarget, speed=coreModule.precise)

    # Place component and return to heaven
    coreModule.set_pressure(coreModule.PLACE_PRESSURE) # Apply short burst of positive pressure to release component
    time.sleep(0.8)
    coreModule.vacuum_off(delay=2)
    if print_log:
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Placed Component Successfully\n")
        print("Placed Component Successfully")

    #go to heaven position after dropping component
    target_heaven = [target_pos[0], target_pos[1], heaven] + currentrot
    coreModule.rtde_control.moveL(target_heaven, speed=coreModule.slow)

    #rotate the last joint/gripper to original orientation
    jointangles = coreModule.rtde_receive.getActualQ()
    jointangles[5] = initialjoint
    coreModule.rtde_control.moveJ(jointangles)


def circuit_pick_and_place(schematic, cycle_vice=False, print_log=False):
    """
    Performs Pick-and-Place assembly of all the components specified in the input schematic
    """
    global pickupfailed
    global placed_components
    if print_log == True:
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Pick-and-Place - Schematic assembly started...\nPick-and-Place - Closing and cycling vice...\n")
        print("Pick-and-Place - Schematic assembly started...")
        print("Pick-and-Place - Closing and cycling vice...")
    coreModule.close_vice() # Close the assembly vice to fix substrate in place
    if cycle_vice == True:
        coreModule.open_vice(0.5) # Cycle the vice to ensure substrate squareness
        coreModule.close_vice(0.5)

    # Start sequence at standby pos, and go to table origin heaven
    if print_log == True:
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Pick-and-Place - Moving to standby waypoint...\n")
        print("Pick-and-Place - Moving to standby waypoint...")
    coreModule.rtde_control.moveL(coreModule.standby, speed=coreModule.fast) #move to standby position
    coreModule.goto_pos([0,0,100]) #go to origin point of grid (the black crosshair on the bottom left of the components tray)

    # Pick and place all schematic components
    if print_log == True:
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Pick-and-Place - Starting component assembly sequence...\n")
        print("Pick-and-Place - Starting component assembly sequence...")
    part_num = 1 #counter for logging and debugging to see process progress
    for component in schematic: #go through each component in schematic
        index = 0 #start from first slot in components tray in the pickup section
        grid = COMPONENTS[component['type']]['grid']
        maxindex = grid[0] * grid[1]
        while index in placed_components[component['type']]: #check if slot has already been visited
            index += 1 #move to next slot
        if index >= maxindex: #if the slot number is more than last slot number, inventory empty
            if print_log:
                with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                    file.write(f"ComponentInventory ERROR: {component['type']} inventory is empty! Please refill\n")
                print(f"ComponentInventory ERROR: {component['type']} inventory is empty! Please refill")
            pickupfailed = True
        if pickupfailed:
            return False
        else: #if inventory not empty
            if print_log == True: #log pickup
                with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                    file.write(f"Pick-and-Place: {part_num}/{len(schematic)}\nPicking up {component['type']} #{index + 1} from {component['type']} inventory grid\n")
                print(f"Pick-and-Place: {part_num}/{len(schematic)}\nPicking up {component['type']} #{index + 1} from {component['type']} inventory grid")
            pickup_failure = pickup_component(component['type'], index,print_warnings=print_log,print_log=print_log) #pickup component
            if pickup_failure: #if failed, inventory empty
                if print_log:
                    with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                        file.write(f"ComponentInventory ERROR: {component['type']} inventory is empty! Please refill\n")
                    print(f"ComponentInventory ERROR: {component['type']} inventory is empty! Please refill")
                return False
            else: #if success
                if print_log: #log placing
                    with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
                        file.write(f"Placing component [{component['type']}] in Coordinates: {component['pos']}\n")
                    print(f"Placing component [{component['type']}] in Coordinates: {component['pos']}")
                tagretpos = [x/1000 for x in component['pos']] #convert position from mm to meters
                place_component(tagretpos, component['rot'],print_log=print_log) #call place_component function with position and rotation parameters respectively
                part_num += 1 #update counter for logging and debugging to see process progress

    # Return to standby
    if print_log == True:
        with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\rosie_pnp_log.txt", "a") as file:
            file.write("Pick-and-Place - Assembly complete! Returning to standby...\n")
        print("Pick-and-Place - Assembly complete! Returning to standby...")
    coreModule.rtde_control.moveL(coreModule.standby, speed=coreModule.fast)
    return True

def inventory_management(operation): #manage inventory (write or read a file for understanding component presence and absence)
    global placed_components
    inventory_file_path = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\inventory.json"

    if operation == 'r':
        with open(inventory_file_path, operation) as f: #read file
            data = json.load(f)
        for key, _ in data.items(): #update placed_components list with the information in inventory
            if key in placed_components:
                placed_components[key] = data[key]
    elif operation == 'w': #write into inventory file
        with open(inventory_file_path, operation) as f:
            data = json.dump(placed_components,f) #update the inventory with placed_components list

def PNP(file_path):
    """
    Main script loop
    """
    circuit_schematic = determine_schematic(file_path) #get component data
    inventory_management('r') #read inventory file
    coreModule.grab_nozzle() #grab nozzle
    coreModule.vacuum_on() #turn on vacuum
    result = circuit_pick_and_place(circuit_schematic, print_log=True) #execute pick and place
    coreModule.rtde_control.moveL(coreModule.standby, speed=coreModule.fast)
    coreModule.return_nozzle() #return nozzle
    return result #inform parent function (demoCircuit.py) that Pick N Place is complete or not

def PNP_Test(): #to test yield for new vacuum heads, ENSURE ALL SLOTS ARE FILLED
    coreModule.grab_nozzle() #grab nozzle
    coreModule.vacuum_on() #turn on vacuum
    comp_grid = {"button":5,"battery":6,"microcontroller":2,"led":16} #number of components present in each grid
    for key, value in comp_grid.items():
        for i in range(value):
            pickup_component(key,i) #pick component from slot
            pos = coreModule.rtde_receive.getActualTCPPose() #get current position
            pos[2] -= 54/1000 #offset z value for placing
            place_component(pos[:3],0) #place back into slot
    coreModule.return_nozzle() #return nozzle

## TESTING: Uncomment only on module testing event
# # Test Pick N Place Module
# PNP(filename)
# # YieldTest
# PNP_Test()
# # Flex Resin
# # Button: 8/8, Battery: 9/9, Microcontroller: 2/2, LED: 15/20 - New res all picked & Led 15/16
# # TPU
# # Button: 7/8, Battery: 6/9, Microcontroller: 2/2, LED: 12/20
# # HENCE FLEX RESIN BETTER