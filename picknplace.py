"""
Module containing the code to program and control the Pick-and-Place functionality
"""

import time
import math
import rtde_io
import rtde_receive
import rtde_control
import keyboard

# Import core module:
from coreModule import *

#-----------------------------------------------------------------------------------------------------------
# === # Pick-And-Place Code # === #

PRESSURE_THRESHOLD = 6.0 # If vacuum is on, and pressure reading is below this, an object has been picked up!

# Position data (In table coordinates) of the electronic component tray grids (Only XY coordinates)
COMPONENTS = {'battery': {'start': [91.87, 50.15],   # XY coords of the start of the grid (Bottom left corner)
                            'end': [142.33, 100.72], # XY coords of the end of the grid (Top right corner)
                           'grid': (3, 3),           # Grid dimensions (3x3)
                      'threshold': 6.5,              # Pressure threshold for pickup
                          'z_val': 0.0},             # Height offset for pick up (Active pressure feedback pickup starts at this height)
                  'led': {'start': [22.55, 66.63],
                            'end': [67.39, 106.07],
                           'grid': (4, 5),           # Grid dimensions (4x5)
                      'threshold': 9.5,
                          'z_val': 0.0},
               'switch': {'start': [29.7, 13.95],
                            'end': [60.45, 50.25],
                           'grid': (2, 4),           # Grid dimensions (2x4)
                      'threshold': 7.8,
                          'z_val': 1.0},
      'microcontroller': {'start': [101.84, 19.98],
                            'end': [139.93, 19.98],
                           'grid': (2, 1),           # Grid dimensions (2x1)
                      'threshold': 6.5,
                          'z_val': -1.0}}

# For now the target coordinates are hardcoded
batt_pos = [-143.82, 52.33, 35.47]
led_pos = [-123.52, 71.88, 35.04]
switch_pos = [-109.05, 53.76, 42.63]

# New coordinate package for the demo LED and Switch circuit:
# This data structure helps collect all info about the parts to be placed and allows
# expanding functionality via adding more paramters such as component height or rotation
#   TODO: This would be nicer if written as a class - and merged with ink printing trace data too
DEMO_CIRCUIT = {'bat': {'type': 'battery',
                         'pos': [-146.11, 46.17-0.5, 39.21]},
                'led': {'type': 'led',
                         'pos': [-109.58, 59.85, 39.82-2.4]},
                'swt': {'type': 'switch',
                         'pos': [-109.83, 33.15, 46.11-2.2]}}


def check_component_is_valid(component):
    """
    Raises an exception if the given component name is invalid
    Executes silently otherwise
    """
    if component not in COMPONENTS:
        raise Exception('Error - ComponentName: "' + str(component) + '" is not a valid component!')


def move_to_component(component, index, Z_target=2.0, speed=precise):
    """
    Moves nozzle avobe component #index for the given
    component type on the tray

    Component is given by string name, ex: 'battery'

    Component index is a number from 0 to num-1 starting
    at the bottom left corner and moving up a column and
    then over a row. For example, a 4x3 grid is indexed:
    2 5 8 11   ^
    1 4 7 10  Y|
    0 3 6 9    O-X->

    A Z offset can be specified to provide clearance above component
    Default is 2mm
    """

    # Check that given component is valid, and its index exists in the grid:
    check_component_is_valid(component)
    if index >= COMPONENTS[component]['grid'][0] * COMPONENTS[component]['grid'][1]:
        raise Exception('Error - ComponentGridIndex: index "' + str(index) + '" is outside the grid!')

    pos_data = COMPONENTS[component]

    # Calculate component spacing
    step_x = 0
    step_y = 0
    if pos_data['grid'][0] >= 2: # Prevent dividing by zero
        step_x = (pos_data['end'][0] - pos_data['start'][0]) / (pos_data['grid'][0] - 1)
    if pos_data['grid'][1] >= 2: # Prevent dividing by zero
        step_y = (pos_data['end'][1] - pos_data['start'][1]) / (pos_data['grid'][1] - 1)

    # Calculate component grid coordinates
    grid_x = index // pos_data['grid'][1]
    grid_y = index % pos_data['grid'][1]

    # Compute final position and move there
    target_pos = [step_x*grid_x + pos_data['start'][0],
                  step_y*grid_y + pos_data['start'][1],
                  Z_target]
    goto_pos(target_pos, speed=speed)


def sweep_component(component, delay=0.2, speed=precise):
    """
    Sweeps the nozzle through all components in the grid
    for the given component
    """

    # Check that given component is valid, and its index exists in the grid:
    check_component_is_valid(component)

    # Compute total number of components in the grid
    part_count = COMPONENTS[component]['grid'][0] * COMPONENTS[component]['grid'][1]

    # Sweep over all components
    for idx in range(part_count):
        move_to_component(component=component, index=idx, speed=speed)
        time.sleep(delay)


def sweep_all(delay=0.2, speed=slow):
    """
    Sweeps the nozzle over all tray components
    Useful for verifying correct calibration of component coordinates
    """

    print("Sweeping all tray components...")

    # Start sequence at standby pos, and go to table origin heaven
    rtde_control.moveL(standby, speed=fast)
    goto_pos([0,0,100])

    # Lower nozzle to sweep height
    goto_pos([0,0,2])

    # Perform full-tray sweep
    for component in COMPONENTS:
        sweep_component(component, delay, speed)

    # Return to safe standbu waypoint
    goto_pos([0,0,100])


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

    heaven = 54.0 # Z coordinate above part pick up location to move component to
    step = 0.01 # In mm

    #vertical_clearance = -1.0 # In mm - TO DECREASE PROCESS TIME SET VALUE TO -2mm IF USING STANDARD AMBER NOZZLE
    #if component == 'switch':
    #    vertical_clearance -= 2 # Pick up switches from lower height to save time

    max_wait = 15 # The nozzle wll retract anyway if the pressure does not drop below threshold in this time (s)

    PRESSURE_THRESHOLD = COMPONENTS[component]['threshold'] # Component-specific pressure threshold for pickup
    MAX_FORCE = 30 # Max force to be applied by the nozzle if no pressure drop is detected

    # Move nozzle above component and store position
    if skip_hover != True: # By default, nozzle moves to component location at heaven height, and then lowers onto it (This can be skipped)
        move_to_component(component=component, index=index, Z_target=heaven)
    move_to_component(component=component, index=index, Z_target=COMPONENTS[component]['z_val'])
    initial_pos = get_pos()
    target_pos = initial_pos.copy()

    # Slowly step downwards monitoring the vacuum pressure
    vacuum_on() # Turn vacuum on if it is not already
    elapsed = time.time()
    while get_pressure() > PRESSURE_THRESHOLD: # True when object not yet picked up
        nozzle_forces = rtde_receive.getActualTCPForce()
        if nozzle_forces[2] <= MAX_FORCE: # Check to ensure that if the vacuum fails, we still stop the nozzle safely!
            target_pos[2] -= step
            goto_pos(target_pos, speed=micrometric)
        else:
            if keyboard.is_pressed('ctrl'): # Ctrl key can be used to break out of loop if pickup fails
                break
            if print_warnings == True:
                print("Pick-and-Place nozzle WARNING: Max force exceeded!")
        # Check if max wait has been exceeded:
        if time.time() >= elapsed + max_wait:
            break

    # Assuming the pressure drop means the object was picked up, move the nozzle up to pick the component out of the tray
    heaven_pos = initial_pos.copy()
    heaven_pos[2] = heaven
    time.sleep(1) # Small delay to allow vacuum to set in before lifting component
    goto_pos(heaven_pos)


def return_component(component, index):
    """
    Returns currently held component back to indicated tray location
    """

    heaven = 50.0 # Z coordinate above part drop off location to move component to
    vertical_clearance = 1.0 # In mm

    if component == 'switch':
        vertical_clearance += 7 # Drop switches from high up to avoid collisions

    # Move nozzle above component tray location, lower it, and drop it off
    move_to_component(component=component, index=index, Z_target=heaven)
    move_to_component(component=component, index=index, Z_target=vertical_clearance)
    vacuum_off(delay=2)

    # Raise nozzle again
    move_to_component(component=component, index=index, Z_target=heaven)


def place_component(target_pos, heaven=100):
    """
    Places the currently held component at the target coordinates
    Travels at heaven height to avoid collisions

    Assumes that the nozzle vacuum is ON and currently holding a component!
    """

    actual_pos = get_pos()

    # Raise to heaven height
    actual_pos[2] = heaven
    goto_pos(actual_pos)

    # Travel to target coordinates
    goto_pos([target_pos[0], target_pos[1], heaven], speed=precise)
    goto_pos(target_pos, speed=precise)

    # Place component and return to heaven
    set_pressure(PLACE_PRESSURE) # Apply short burst of positive pressure to release component
    time.sleep(0.8)
    vacuum_off(delay=2)
    goto_pos([target_pos[0], target_pos[1], heaven], speed=slow)


def battery_shuffle_test(standalone=True):
    """
    Tests pick-and-place functionality by attempting shuffle arround some battery cells
    Can be configured to run on its own (grabbing and returning the nozzle) or as part of
    a larger program that already takes care of handling the nozzle
    """

    if standalone == True:
        grab_nozzle()
        goto_pos([0,0,100])
        goto_pos([0,0,5])

    pickup_component('battery', 0)
    return_component('battery', 6)

    pickup_component('battery', 2)
    return_component('battery', 0)

    pickup_component('battery', 8)
    return_component('battery', 2)

    pickup_component('battery', 6)
    return_component('battery', 8)

    if standalone == True:
        goto_pos([0,0,100])
        return_nozzle()


def pick_and_place_test():
    """
    Runs a demo sequence to pick and place a battery, LED, and switch onto an empty substrate
    """

    z_clearance = 1.0 # mm of extra clearance on the Z axis when placing components

    close_vice(0.1) # Close the assembly vice to fix substrate in place

    for coords in [batt_pos, led_pos, switch_pos]:
        coords[2] += z_clearance

    # Start sequence at standby pos, and go to table origin heaven
    rtde_control.moveL(standby, speed=fast)
    goto_pos([0,0,100])

    # Pick and place the battery
    pickup_component('battery', 0)
    place_component(batt_pos)

    # Pick and place the LED
    pickup_component('led', 0)
    place_component(led_pos)

    # Pick and place the switch
    pickup_component('switch', 0)
    place_component(switch_pos)

    # Return to standby
    rtde_control.moveL(standby, speed=fast)


def run_pick_and_place_experiment():
    """
    Runs the pick and place test endlessly, but requires the user to press
    the left SHITF key to start every run. Makes collecting data over multiple
    tests easier by allowing the operator time to reset the experiment and start
    it at their own pace rather than through fixed timing.

    Pressing CTRL will end the experiment!
    """

    # Equip nozzle from holder
    grab_nozzle()

    print("Running Experiment: - Demo circuit pick-and-place full assembly")
    print("Press SHIFT to begin experiment - CTRL to cancel and return the nozzle")

    while True:
        # If CTRL is pressed, break the loop
        if keyboard.is_pressed('ctrl'):
            break

        # Otherwise check for SHIFT and run experiment if it is pressed
        if keyboard.is_pressed('shift'):
            pick_and_place_test()

    # After the experiment is over, return the nozzle
    return_nozzle()


def component_yield_test(component_data, attempts):
    """
    Collects data on yield by picking and placing all available tray components of
    the specified type on substrate plate. The component to be tested must be specified
    in a tuple along with the target coordinates of the placement location.

    Ex: ('battery', [-143.94, 52.64, 35.47])

    Needs a human operator to continuously remove the placed components from the substrate!
    Assumes that the tray is fully stocked!

    The total number of trials to be run can be set via the attempts number
    """

    z_clearance = 1.0 # mm of extra clearance on the Z axis when placing components

    close_vice(0.1) # Close the assembly vice to fix substrate in place

    target_pos = list(component_data[1])
    part = component_data[0]

    target_pos[2] += z_clearance

    # Start sequence at standby pos, and go to table origin heaven
    rtde_control.moveL(standby, speed=fast)
    goto_pos([0,0,100])

    # Test component pick and place yield:
    part_count = COMPONENTS[part]['grid'][0]*COMPONENTS[part]['grid'][1]
    for idx in [x % part_count for x in range(attempts)]:
        pickup_component(part, idx)
        place_component(target_pos)


def run_yield_experiment(trials):
    """
    Runs the component yield test endlessly, but requires the user to press
    the left SHITF key to start every run. Makes collecting data over multiple
    tests easier by allowing the operator time to reset the experiment and start
    it at their own pace rather than through fixed timing.

    Tests for battery, LED, and switch yield. Cycle then repeats.

    Pressing CTRL will end the experiment!
    """

    experiment_set = [('battery',batt_pos), ('led',led_pos), ('switch',switch_pos)]
    experiment_set = [('led',led_pos)]
    exp_idx = 0

    # Equip nozzle from holder
    grab_nozzle()

    print("Running Experiment: - Full range pick-and-place yield - [" + str(trials) + " Trials]")
    print("Press SHIFT to begin experiment - CTRL to cancel and return the nozzle")

    while True:
        # If CTRL is pressed, break the loop
        if keyboard.is_pressed('ctrl'):
            break

        # Otherwise check for SHIFT and run experiment if it is pressed
        if keyboard.is_pressed('shift'):
            component_yield_test(component_data=experiment_set[exp_idx], attempts=trials)
            exp_idx += 1
            exp_idx %= len(experiment_set) # Prevent index overflow and wrap back to first experiment

    # After the experiment is over, return the nozzle
    return_nozzle()


def calibrate_demo_circuit_placement():
    """
    Runs a semi-automated sequence of component pickups and returns
    to streamline the process of capturing the placement coordinates
    of the components on the substrate.

    Deos this by picking up a component, moving it over the substrate,
    switching to manual control to allow the operator to perform point
    capture, and then returning the component back to the tray.

    Currently set up to do so for 1x battery, 1x LED, and 1x switch,
    as required by the demo circuit
    """

    # Set up process
    grab_nozzle()
    close_vice()

    print("Running Setup: - Component placement calibration sequence")

    # Iterate through desired components and execute calibration
    for part in ['battery', 'led', 'switch']:
        pickup_component(part, 0)
        goto_pos([-130.00, 50.00, 50.00]) # Rough location above substrate
        manual_control(inverted=True)
        return_component(part, 0)

    # Reset after sequence is over
    return_nozzle()


def tray_pickup_test(attempts=None):
    """
    Runs a sequence of pickup operations on a sample tray piece clamped in the vice
    Used to test if any changes made to tray geometry in the test pieces result in
    improvements to the pick yield of certain components

    Intended to be used with tray #1!
    """

    # Add a proxy component to the part library
    # In this case 4 switches in a 1x4 grid:
    COMPONENTS['testpart'] = {'start': [-102.7, 35.3], # XY coords of the start of the grid (Bottom left corner)
                                'end': [-102.7, 70.0], # XY coords of the end of the grid (Top right corner)
                               'grid': (1, 4),         # Grid dimensions (1x4)
                          'threshold': 7.8,            # Pressure threshold for pickup
                              'z_val': 43.0}           # Height offset for pick up (Active pressure feedback pickup starts at this height)

    drop_zone = [-137.75, 52.55, 45.8] # Use this to drop all components on the same location

    adaptive_drop = True # If this is set to True, it will drop all components at a consistent offset location from their pickup coordinates
    x_offset = -35.0 # X offset used with adaptive drop
    y_offset = 0.0 # Y offset used with adaptive drop

    # Close the vice to clamp the mini-tray
    close_vice()

    # Equip nozzle from holder
    grab_nozzle()

    print("Running Experiment: - Updated tray slot pickup yield")
    print("Press SHIFT to begin experiment - CTRL to cancel and return the nozzle")

    while True:
        # If CTRL is pressed, break the loop
        if keyboard.is_pressed('ctrl'):
            break

        # Otherwise check for SHIFT and run experiment if it is pressed
        if keyboard.is_pressed('shift'):
            # Test component pick yield:
            part_count = COMPONENTS['testpart']['grid'][0]*COMPONENTS['testpart']['grid'][1]
            if attempts is None: # If no number of attempts was specified, exhaust all components in provided grid
                attempts = part_count
            for idx in [x % part_count for x in range(attempts)]:
                pickup_component('testpart', idx)
                if adaptive_drop == True:
                    pickup_coords = get_pos()
                    relative_drop_zone = [pickup_coords[0] + x_offset, pickup_coords[1] + y_offset, drop_zone[2]]
                    place_component(target_pos=relative_drop_zone, heaven=54)
                else:
                    place_component(target_pos=drop_zone, heaven=54)

    # After the experiment is over, return the nozzle
    return_nozzle()


def tray_place_test(attempts=None):
    """
    Repeats the same pickup and placement operation on a sample tray
    Used to test if any changes made to tray geometry in the test pieces result in
    improvements to the placement yield of certain components

    Intended to be used with tray #2!
    """

    # Add a proxy component to the part library
    # In this case 4 switches in a 1x4 grid:
    COMPONENTS['testpart'] = {'start': [-102.7, 35.3], # XY coords of the start of the grid (Bottom left corner)
                                'end': [-102.7, 70.0], # XY coords of the end of the grid (Top right corner)
                               'grid': (1, 4),         # Grid dimensions (1x4)
                          'threshold': 7.8,            # Pressure threshold for pickup
                              'z_val': 43.0}           # Height offset for pick up (Active pressure feedback pickup starts at this height)
    # In this case 10 LEDs in a 2x5 grid:
    COMPONENTS['testpart'] = {'start': [-151.2, 35.1], # XY coords of the start of the grid (Bottom left corner)
                                'end': [-137.2, 71.5], # XY coords of the end of the grid (Top right corner)
                               'grid': (2, 5),         # Grid dimensions (1x4)
                          'threshold': 9.5,            # Pressure threshold for pickup
                              'z_val': 39.1}           # Height offset for pick up (Active pressure feedback pickup starts at this height)

    #drop_zone = [-142.90, 52.65, 43.5] # Use this to drop all components on the same location (Switch)
    drop_zone = [-142.90, 52.65, 38.0] # Use this to drop all components on the same location (Switch)

    adaptive_drop = True # If this is set to True, it will drop all components at a consistent offset location from their pickup coordinates
    #x_offset = -40.2 # X offset used with adaptive drop (Switch)
    #y_offset = 0.0 # Y offset used with adaptive drop (Switch)
    x_offset = 41.9 # X offset used with adaptive drop (LED)
    y_offset = 0.2 # Y offset used with adaptive drop (LED)

    # Close the vice to clamp the mini-tray\
    close_vice()

    # Equip nozzle from holder
    grab_nozzle()

    print("Running Experiment: - Updated tray slot placement yield")
    print("Press SHIFT to begin experiment - CTRL to cancel and return the nozzle")

    while True:
        # If CTRL is pressed, break the loop
        if keyboard.is_pressed('ctrl'):
            break

        # Otherwise check for SHIFT and run experiment if it is pressed
        if keyboard.is_pressed('shift'):
            # Test component pick yield:
            part_count = COMPONENTS['testpart']['grid'][0]*COMPONENTS['testpart']['grid'][1]
            if attempts is None: # If no number of attempts was specified, exhaust all components in provided grid
                attempts = part_count
            for idx in [x % part_count for x in range(attempts)]:
                pickup_component('testpart', idx)
                if adaptive_drop == True:
                    pickup_coords = get_pos()
                    relative_drop_zone = [pickup_coords[0] + x_offset, pickup_coords[1] + y_offset, drop_zone[2]]
                    place_component(target_pos=relative_drop_zone, heaven=54)
                else:
                    place_component(target_pos=drop_zone, heaven=54)

    # After the experiment is over, return the nozzle
    return_nozzle()


def circuit_pick_and_place(schematic, cycle_vice=False, print_log=False):
    """
    Performs Pick-and-Place assembly of all the components specified in the input schematic
    """

    if print_log == True:
        print("Pick-and-Place - Schematic assembly started...")

    # Placeholder for component stock index tracking (To account for depletion of tray components)
    index = 0

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
        if print_log == True:
            print("Pick-and-Place - Placing component " + str(part_num) + "/" + str(len(schematic)) + " [" + str(component) + "] - Coordinates: " + str(schematic[component]['pos']))
        pickup_component(schematic[component]['type'], index)
        place_component(schematic[component]['pos'])
        part_num += 1

    # Return to standby
    if print_log == True:
        print("Pick-and-Place - Assembly complete! Returning to standby...")
    rtde_control.moveL(standby, speed=fast)


def main():
    """
    Main script loop
    """

    #grab_nozzle()
    #point_capture()
    #return_nozzle()

    #run_pick_and_place_experiment()
    #run_yield_experiment(10)

    #calibrate_demo_circuit_placement()

    grab_nozzle()
    circuit_pick_and_place(DEMO_CIRCUIT, print_log=True)
    return_nozzle()


if __name__ == "__main__":
    main()
