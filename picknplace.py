"""
Module containing the code to program and control the Pick-and-Place functionality
"""

import time,math,rtde_io,rtde_receive,rtde_control,keyboard,os,json

# Import core module:
from coreModule import *

#-----------------------------------------------------------------------------------------------------------
# === # Pick-And-Place Code # === #

PRESSURE_THRESHOLD = 6.0 # If vacuum is on, and pressure reading is below this, an object has been picked up!

load_calibration_data()
z_origin = CALIBRATION_DATA['vac'][2] + top_right_vise[2]
origin_in_m = [top_right_vise[0],top_right_vise[1]-admlviceblock_yoff,z_origin, 0, math.pi, 0] #top right corner of stock on vice in rosie station
origin = [val * 1000 for val in origin_in_m[:3]] + [0,math.pi,0] #origin in mm
tip_offset_from_gripper = 1.1705 * 25.4 #convert in to mm
pickupfailed = False
pickedup = False

# Placeholder for component stock index tracking (To account for depletion of tray components)
placed_components = {"battery": [],
                        "microcontroller": [],
                        "button": [],
                        "led": []}
# Position data (In table coordinates) of the electronic component tray grids (Only XY coordinates)
COMPONENTS = {'battery': {'start': [91.87, 50.15],   # XY coords of the start of the grid (Bottom left corner)
                            'end': [142.33, 100.72], # XY coords of the end of the grid (Top right corner)
                           'grid': (3, 3),           # Grid dimensions (3x3)
                      'threshold': 9.5,              # Pressure threshold for pickup
                   'pocket_depth': 0.082,            # Depth of pocket in tray (in inches)
                          'z_val': 0.0},             # Height offset for pick up (Active pressure feedback pickup starts at this height)
                  'led': {'start': [22.55, 66.63],
                            'end': [67.39, 106.07],
                           'grid': (4, 5),           # Grid dimensions (4x5)
                      'threshold': 10.8, #MESS AROUND WITH THIS
                   'pocket_depth': 0.1, #MESS AROUND WITH THIS
                          'z_val': 0.0},
               'button': {'start': [29.7, 13.95],
                            'end': [60.45, 50.25],
                           'grid': (2, 4),           # Grid dimensions (2x4)
                      'threshold': 9.7,
                   'pocket_depth': 0.2,
                          'z_val': 1.0},
      'microcontroller': {'start': [101.84, 19.98],
                            'end': [139.93, 19.98],
                           'grid': (2, 1),           # Grid dimensions (2x1)
                      'threshold': 9.5,
                   'pocket_depth': 0.124,
                          'z_val': -1.0}}

# get recent save data
def get_most_recent_saved_file(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    if not files:
        return None
    return max(files, key=os.path.getctime)

# get robot world coordinates for components
def determine_schematic():
    # savefolderpath = os.path.join(os.getcwd(),"saves")
    # recentsavefilepath = get_most_recent_saved_file(savefolderpath)
    recentsavefilepath = r"C:\git\ADML\Automated Circuit Printing and Assembly\finalSendToMill.json"
    print(f"Save file path: {recentsavefilepath}")

    with open(recentsavefilepath, 'r') as f:
        data = json.load(f)

    circuit_schematic = []
    for component in data['componentdata']:
        if component['modelName'] != "stock":
            name = os.path.splitext(os.path.basename(component['modelName']))[0].lower()
            position_x = origin[0] + (component['posX'] * 25.4) #convert in to mm
            position_y = origin[1] + (component['posY'] * 25.4)
            position_z = origin[2] + COMPONENT_HEIGHTS[name]
            position = [position_x,position_y,position_z]
            if component['rotZ'] == 270:
                component['rotZ'] = -90
                position = [position_x-tip_offset_from_gripper,position_y+tip_offset_from_gripper,position_z]
            elif component['rotZ'] == 90:
                position = [position_x-tip_offset_from_gripper,position_y-tip_offset_from_gripper,position_z]
            elif component['rotZ'] == 180:
                position = [position_x-tip_offset_from_gripper,position_y,position_z]
            rotation = math.radians(component['rotZ'])
            circuit_schematic.append({'type': name, 'pos': position, 'rot': rotation})

    return circuit_schematic

def move_to_component(component, index, Z_target=2.0, speed=precise):
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
        msg =  f"ComponentName Error, {component} is not a valid component!"
        return msg
    if index >= COMPONENTS[component]['grid'][0] * COMPONENTS[component]['grid'][1]:
        msg = f"ComponentGridIndex Error: index {index + 1} is outside the grid!"
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
    goto_pos(target_pos, speed=speed)
    return target_pos

def pickup_component(component, index, skip_hover=False, print_warnings=False):
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
    heaven = 54.0 # Z coordinate above part pick up location to move component to
    step = 0.01 # In mm

    #vertical_clearance = -1.0 # In mm - TO DECREASE PROCESS TIME SET VALUE TO -2mm IF USING STANDARD AMBER NOZZLE
    #if component == 'switch':
    #    vertical_clearance -= 2 # Pick up switches from lower height to save time

    PRESSURE_THRESHOLD = COMPONENTS[component]['threshold'] # Component-specific pressure threshold for pickup
    MAX_FORCE = 30 # Max force to be applied by the nozzle if no pressure drop is detected

    # Move nozzle above component and store position
    if skip_hover != True: # By default, nozzle moves to component location at heaven height, and then lowers onto it (This can be skipped)
        move_to_component(component=component, index=index, Z_target=heaven)
    initial_pos = move_to_component(component=component, index=index, Z_target=COMPONENTS[component]['z_val'])

    initial_pos = get_pos()
    target_pos = initial_pos.copy()

    # Slowly step downwards monitoring the vacuum pressure
    vacuum_on() # Turn vacuum on if it is not already
    print("Vacuum On")

    depth_travelled_into_grid = abs(initial_pos[2] - target_pos[2]) #in mm
    while get_pressure() > PRESSURE_THRESHOLD and depth_travelled_into_grid < (COMPONENTS[component]['pocket_depth'] * 25.4): # True when object not yet picked up
        nozzle_forces = rtde_receive.getActualTCPForce()
        if nozzle_forces[2] <= MAX_FORCE: # Check to ensure that if the vacuum fails, we still stop the nozzle safely!
            target_pos[2] -= step
            depth_travelled_into_grid = abs(initial_pos[2] - target_pos[2])
            goto_pos(target_pos, speed=micrometric)
        else:
            if keyboard.is_pressed('ctrl'): # Ctrl key can be used to break out of loop if pickup fails
                break
            if print_warnings == True:
                print("Pick-and-Place nozzle WARNING: Max force exceeded!")
    if depth_travelled_into_grid >= (COMPONENTS[component]['pocket_depth'] * 25.4):
        print("Pick-and-Place nozzle WARNING: Max depth inside grid pocket reached!")
    if get_pressure() > PRESSURE_THRESHOLD:
        print(f"Pick N Place: Failed to pickup {component} in slot #{index + 1}, moving to next slot to attempt pickup")
        index += 1
        grid = COMPONENTS[component]['grid']
        maxindex = grid[0] * grid[1]
        if index >= maxindex:
            pickupfailed = True
        else:
            vacuum_off()
            print("Vacuum  Off")
            placed_components[component].append(index)
            target_pos = pickup_component(component=component, index=index)
    else:
        pickedup = True
        print(f"Pick N Place: Picked up [{component}] from slot [{index + 1}]")

    if pickupfailed:
        index = maxindex
        pass
    else:
        # Assuming the pressure drop means the object was picked up, move the nozzle up to pick the component out of the tray
        if pickedup:
            placed_components[component].append(index)
            pickedup = False
            heaven_pos = initial_pos.copy()
            heaven_pos[2] = heaven
            time.sleep(1) # Small delay to allow vacuum to set in before lifting component
            goto_pos(heaven_pos)

    return pickupfailed

def place_component(target_pos,rot, heaven=0.4318552510405578):#100):
    """
    Places the currently held component at the target coordinates
    Travels at heaven height to avoid collisions

    Assumes that the nozzle vacuum is ON and currently holding a component!
    """
    # actual_pos = get_pos()

    # # Raise to heaven height
    # actual_pos[2] = heaven
    # print("GOTO ActualPos Heaven")
    # goto_pos(actual_pos)

    # Travel to target coordinates
    rtde_control.moveL([target_pos[0], target_pos[1], heaven,0,math.pi,0], speed=precise)

    jointangles = rtde_receive.getActualQ()

    initialjoint = jointangles[5]
    jointangles[5] += rot
    rtde_control.moveJ(jointangles)

    currentrot = get_robot_pos()[3:]
    finaltarget = target_pos + currentrot
    rtde_control.moveL(finaltarget, speed=precise)

    # Place component and return to heaven
    set_pressure(PLACE_PRESSURE) # Apply short burst of positive pressure to release component
    time.sleep(0.8)
    vacuum_off(delay=2)

    target_heaven = [target_pos[0], target_pos[1], heaven] + currentrot
    rtde_control.moveL(target_heaven, speed=slow)
    jointangles = rtde_receive.getActualQ()
    jointangles[5] = initialjoint
    rtde_control.moveJ(jointangles)


def circuit_pick_and_place(schematic, cycle_vice=False, print_log=False):
    """
    Performs Pick-and-Place assembly of all the components specified in the input schematic
    """
    global pickupfailed
    global placed_components
    if print_log == True:
        print("Pick-and-Place - Schematic assembly started...")

    if print_log == True:
        print("Pick-and-Place - Closing and cycling vice...")
    close_vice() # Close the assembly vice to fix substrate in place
    if cycle_vice == True:
        open_vice(0.5) # Cycle the vice to ensure substrate squareness
        close_vice(0.5)

    # Start sequence at standby pos, and go to table origin heaven
    if print_log == True:
        print("Pick-and-Place - Moving to standby waypoint...")
    rtde_control.moveL(standby, speed=fast)
    goto_pos([0,0,100])

    # Pick and place all schematic components
    if print_log == True:
        print("Pick-and-Place - Starting component assembly sequence...")
    part_num = 1
    for component in schematic:
        index = 0
        grid = COMPONENTS[component['type']]['grid']
        maxindex = grid[0] * grid[1]
        while index in placed_components[component['type']]:
            index += 1
        if index >= maxindex:
            print(f"ComponentInventory ERROR: {component['type']} inventory is empty! Please refill")
            pickupfailed = True
        if pickupfailed:
            break
        else:
            if print_log == True:
                print(f"Pick-and-Place: {part_num}/{len(schematic)}\nPicking up {component['type']} #{index + 1} from {component['type']} inventory grid")
            pickup = pickup_component(component['type'], index)
            if pickup:
                print(f"ComponentInventory ERROR: {component['type']} inventory is empty! Please refill")
            else:
                if print_log:
                    print(f"Placing component [{component['type']}] in Coordinates: {component['pos']}")
                tagretpos = [x/1000 for x in component['pos']]
                print(tagretpos)
                place_component(tagretpos, component['rot'])
                part_num += 1

    # Return to standby
    if print_log == True:
        print("Pick-and-Place - Assembly complete! Returning to standby...")
    rtde_control.moveL(standby, speed=fast)

def main():
    """
    Main script loop
    """
    circuit_schematic = determine_schematic()
    grab_nozzle()
    circuit_pick_and_place(circuit_schematic, print_log=False)
    return_nozzle()


if __name__ == "__main__":
    main()
