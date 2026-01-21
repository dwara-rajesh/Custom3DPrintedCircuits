"""
Contains the code for configuring and running the nozzle calibration sequence
"""

import time
from math import degrees
import array as arr
import rtde_io
import rtde_receive
import rtde_control
import csv
import keyboard

# In order to run this from visual studio code you must install python into Windows
rtde_io = rtde_io.RTDEIOInterface("10.241.34.45")
rtde_receive = rtde_receive.RTDEReceiveInterface("10.241.34.45")
rtde_control = rtde_control.RTDEControlInterface("10.241.34.45")

### List of updated waypoints: ###

# Griper positions next to and at pickup locations for nozzles
near_vac = [-0.3267, -0.2950, 0.2227, 0, 3.1415, 0]
at_vac = [-0.4944, -0.2950, 0.2227, 0, 3.1415, 0]
lift_vac = [-0.4944, -0.2950, 0.3664, 0, 3.1415, 0]
near_ext = [-0.3267, -0.3967, 0.2227, 0, -3.1415, 0]
at_ext = [-0.4939, -0.3967, 0.2227, 0, -3.1415, 0]
lift_ext = [-0.4939, -0.3967, 0.3664, 0, -3.1415, 0]
standby = [0.1385114178390316, -0.3392137805606495, 0.3050825568665961, 0.0004118402665590182, -3.141424612295421, -0.0004761644469756241]

# Fine tuning offsets for all 3 calibration axis (Allows trimming the nozzles to get closer to the sensor and thus waste less time stepping towards it)
# These have been reset to zero as they are no longer needed (The waypoints have been updated directly)
# They are still here for tinkering or tweaking if desired, and the original values are recorded next to them
X_offset_vac = 0.0000 # 1.2mm (-X)
Y_offset_vac = 0.0000 # 0.8mm (+Y)
Z_offset_vac = 0.0000 # 2mm (-Z)
X_offset_ext = 0.0000 # 1mm (-X)
Y_offset_ext = 0.0000 # 0.8mm (+Y)
Z_offset_ext = 0.0000 # 1.2mm (-Z)
height_offset_vac = -0.0000 # (1.2mm) Used to trim the height at which the vacuum nozzle sits inside the sensor channel
height_offset_ext = +0.0000 # (0.5mm) Used to trim the height at which the extrusion nozzle sits inside the sensor channel

SAFEMODE = 0 # Disabled
if SAFEMODE == True: # Gives all calibration axis 1mm of extra clearance to ensure nozzle does not start calibrating already inside the sensor beam (or beyond it!)
    X_offset_vac -= 0.001
    Y_offset_vac -= 0.001
    Z_offset_vac -= 0.002
    X_offset_ext -= 0.001
    Y_offset_ext -= 0.001
    Z_offset_ext -= 0.002

# Griper positions right above (at) and inside the sensor channels (start of the calibration sweep)
#For 10ml Syringe
# channel_pos = {'vac':{'at_x':[0.37107-X_offset_vac, -0.28984, 0.15000, 0.0, -3.1415, 0.0],
#                       'in_x':[0.37107-X_offset_vac, -0.28984, 0.09848+height_offset_vac, 0.0, -3.1415, 0.0],
#                       'at_y':[0.40120, -0.29703+Y_offset_vac, 0.15000, 0.0, -3.1415, 0.0],
#                       'in_y':[0.40120, -0.29703+Y_offset_vac, 0.09848+height_offset_vac, 0.0, -3.1415, 0.0]},
#                'ink':{'at_x':[0.37217-X_offset_ext, -0.29010, 0.15000, 0.0, -3.1415, 0.0],
#                       'in_x':[0.37217-X_offset_ext, -0.29010, 0.10015+height_offset_ext, 0.0, -3.1415, 0.0],
#                       'at_y':[0.40234, -0.29753+Y_offset_ext, 0.15000, 0.0, -3.1415, 0.0],
#                       'in_y':[0.40234, -0.29753+Y_offset_ext, 0.09935+height_offset_ext, 0.0, -3.1415, 0.0]}}

#For 5ml Syringe for ink and 10ml for Vacuum
channel_pos = {'vac':{'at_x':[0.3735-X_offset_vac, -0.2897, 0.15000, 0.0, -3.1415, 0.0],
                      'in_x':[0.3735-X_offset_vac, -0.2897, 0.0986+height_offset_vac, 0.0, -3.1415, 0.0],
                      'at_y':[0.4007, -0.2987+Y_offset_vac, 0.15000, 0.0, -3.1415, 0.0],
                      'in_y':[0.4007, -0.2987+Y_offset_vac, 0.0989+height_offset_vac, 0.0, -3.1415, 0.0]},
               'ink':{'at_x':[0.3735-X_offset_ext, -0.2889, 0.15000, 0.0, -3.1415, 0.0],
                      'in_x':[0.3735-X_offset_ext, -0.2889, 0.0763+height_offset_ext, 0.0, -3.1415, 0.0],  
                      'at_y':[0.4023, -0.2987+Y_offset_ext, 0.15000, 0.0, -3.1415, 0.0],
                      'in_y':[0.4023, -0.2987+Y_offset_ext, 0.0768+height_offset_ext, 0.0, -3.1415, 0.0]}}


slow = 0.1 # Move speed for slow motions
fast = 3.0 # Move speed for fast motions
wait_time = 0.4 # Buffer time in seconds (s) that the arm waits for the grabber to physically open and close after being toggled

# Tray component data location and memory [CWD is "C:\git\ADML"]
COMPONENT_TRAY_FILEPATH = "tray_data.txt"


def read_tray_indexes():
    """
    Reads the tray indexes from the tray data file and returns the
    tray data in the form of a dictionary mapping component types
    to the current index value for those components
    """

    tray_data = {}

    with open(COMPONENT_TRAY_FILEPATH, 'r') as f:
        lines = f.readlines()
        for line in lines:
            part, idx = line.replace("\n", "").split('-')
            tray_data[part] = int(idx)
    
    f.close()
    return tray_data


def write_tray_indexes(tray_data):
    """
    Writes indexes from the tray data to the tray data file for storage
    """
    
    with open(COMPONENT_TRAY_FILEPATH, 'w') as f:
        for part in tray_data:
            f.write(part + '-' + str(tray_data[part]) + '\n')
    f.close()


def reset_tray_indexes():
    """
    Resets all tray-data indexes to zero
    """
    
    tray_data = read_tray_indexes()
    for part in tray_data:
        tray_data[part] = 0
    write_tray_indexes(tray_data)
    print("Tray-Data indexes reset to zero!")


def Ink_Pickup():
    """
    Move robot to pick up the ink extrusion head. 
    Grabber must be free. Throws exception if robot grabber is already holding something
    """

    # Check if grabber is NOT already closed, throw exception otherwise
    alicat_state = rtde_receive.getDigitalOutState(0)
    if alicat_state:
        raise Exception("I'm already holding something!")
    
    # Move robot onto ink extrusion head
    rtde_control.moveL(near_ext, speed=fast)
    rtde_control.moveL(at_ext, speed=slow)
    
    # Grab head (Close grabber)
    time.sleep(wait_time)
    rtde_io.setStandardDigitalOut(0, True)
    time.sleep(wait_time)
    
    # Lift head out of holder and retract arm
    rtde_control.moveL(lift_ext, speed=slow)
    rtde_control.moveL(standby, speed=fast)

def Ink_Place():
    """
    Return the ink extrusion head to its holder
    """

    # Move ink extrusion head back onto its holder
    rtde_control.moveL(standby, speed=fast)
    rtde_control.moveL(lift_ext, speed=fast)
    rtde_control.moveL(at_ext, speed=slow)
    
    # Release head from grabber and retract arm
    time.sleep(wait_time)
    rtde_io.setStandardDigitalOut(0, False)
    time.sleep(wait_time)
    rtde_control.moveL(near_ext, speed=fast)


def Vacuum_Pickup():
    """
    Move robot to pick up the vacuum head. 
    Grabber must be free. Throws exception if robot grabber is already holding something
    """

    # Check if grabber is NOT already closed, throw exception otherwise
    alicat_state = rtde_receive.getDigitalOutState(0)
    if alicat_state:
        raise Exception("I'm already holding something!")
    
    # Move robot onto vacuum head
    rtde_control.moveL(near_vac, speed=fast)
    rtde_control.moveL(at_vac, speed=slow)
    
    # Grab head (Close grabber)
    time.sleep(wait_time)
    rtde_io.setStandardDigitalOut(0, True)
    time.sleep(wait_time)
    
    # Lift head out of holder and retract arm
    rtde_control.moveL(lift_vac, speed=slow)
    rtde_control.moveL(standby, speed=fast)

def Vacuum_Place():
    """
    Return the vacuum head to its holder
    """

    # Move vacuum head back onto its holder
    rtde_control.moveL(standby, speed=fast)
    rtde_control.moveL(lift_vac, speed=fast)
    rtde_control.moveL(at_vac, speed=slow)
    
    # Release head from grabber and retract arm
    time.sleep(wait_time)
    rtde_io.setStandardDigitalOut(0, False)
    time.sleep(wait_time)
    rtde_control.moveL(near_vac, speed=fast)


#### Calibration #### ==================================================================================

def get_X(nozzle):
    """
    Calibrates the X coordinate of the nozzle tip.
    Achieves this by stepping the nozzle through the sensor beam.
    The sensor beam breaking gives the position of the leading edge of the nozzle,
        and the sensor beam reappearing indicates the trailing edge position
    Final X coordinate at the center of the nozzle is the midpoint between both edges.

    NOTE: nozzle can be 'vac' or 'ink' for vacuum and ink respectively
    """
    
    # Position head inside sensor channel
    rtde_control.moveL(channel_pos[nozzle]['at_x'], speed=fast) # Move head above sensor channel location
    rtde_control.moveL(channel_pos[nozzle]['in_x'], speed=slow) # Lower head into sensor channel
    
    step = 0.00001
    
    # Calibrate leading nozzle edge by moving it into the sensor until the sensor beam breaks
    X_upper = channel_pos[nozzle]['in_x'][0]
    while not rtde_receive.getDigitalInState(2):
        X_upper = X_upper - step
        step_pos = channel_pos[nozzle]['in_x'].copy()
        step_pos[0] = X_upper
        rtde_control.moveL(step_pos, speed=slow)
    X_upper_actual = rtde_receive.getActualTCPPose()[0]

    # Calibrate trailing nozzle edge by moving it out of the sensor until the sensor beam is no longer broken
    X_lower = X_upper
    while rtde_receive.getDigitalInState(2):
        X_lower = X_lower - step
        step_pos = channel_pos[nozzle]['in_x'].copy()
        step_pos[0] = X_lower
        rtde_control.moveL(step_pos, speed=slow)
    X_lower_actual = rtde_receive.getActualTCPPose()[0]

    # Retract nozzle from channel and return midpoint X position
    rtde_control.moveL(channel_pos[nozzle]['at_x'], speed=fast)
    return (X_lower+X_upper)/2.0


def get_Y_Z(nozzle):
    """
    Calibrates the Y and Z coordinates of the nozzle tip.
    Achieves this by first stepping the nozzle through the sensor beam (Y coord).
    The sensor beam breaking gives the position of the leading edge of the nozzle,
        and the sensor beam reappearing indicates the trailing edge position
    Final Y coordinate at the center of the nozzle is the midpoint between both edges.

    The Z coordinate is then calibrated by lifting the nozzle on top of the sensor beam,
        (beam position given by the Y coordinate) and slowly lowering it onto the sensor
        until the beam breaks.

    NOTE: nozzle can be 'vac' or 'ink' for vacuum and ink respectively
    """

    # NOTE: rtde_receive.getDigitalInState(3) returns True if the light is blocked, False if the light is not blocked

    # Position head inside sensor channel
    rtde_control.moveL(channel_pos[nozzle]['at_y'], speed=fast) # Move head above sensor channel location
    rtde_control.moveL(channel_pos[nozzle]['in_y'], speed=slow) # Lower head into sensor channel

    step = 0.00001 # 0.01 mm

    # Calibrate leading nozzle edge by moving it into the sensor until the sensor beam breaks
    Y_upper = channel_pos[nozzle]['in_y'][1]
    while not rtde_receive.getDigitalInState(3):
        Y_upper = Y_upper + step
        step_pos = channel_pos[nozzle]['in_y'].copy()
        step_pos[1] = Y_upper
        rtde_control.moveL(step_pos, speed=slow)
    Y_upper_actual = rtde_receive.getActualTCPPose()[1]

    # Calibrate trailing nozzle edge by moving it out of the sensor until the sensor beam is no longer broken
    Y_lower = Y_upper
    while rtde_receive.getDigitalInState(3):
        Y_lower = Y_lower + step
        step_pos = channel_pos[nozzle]['in_y'].copy()
        step_pos[1] = Y_lower
        rtde_control.moveL(step_pos, speed=slow)
    Y_lower_actual = rtde_receive.getActualTCPPose()[1]
    
    # Compute nozzle center Y coordinate
    Y_coord = (Y_lower+Y_upper)/2.0

    # initialize Z start location and move there
    z_initial = channel_pos[nozzle]['in_y'].copy()
    z_initial[1] = Y_coord
    Z_offset = Z_offset_ext # Select correct Z offset value
    if nozzle == 'vac':
        Z_offset = Z_offset_vac
    z_initial[2] = z_initial[2] + 0.003 - Z_offset # +3mm in +Z axis
    rtde_control.moveL(z_initial, speed=slow)
    
    # Calibrate nozzle Z height by lowering it onto the sensor beam at y=Y_coord
    Z_coord = z_initial[2]
    while not rtde_receive.getDigitalInState(3):
        Z_coord = Z_coord - step
        updated = z_initial.copy()
        updated[2] = Z_coord
        rtde_control.moveL(updated, speed=slow)

    rtde_control.moveL(channel_pos[nozzle]['at_y'], speed=slow)
    return Y_coord, Z_coord


def test_toolswap():
    """
    Tests the pickup and place sequence for both the vacuum head
    and for the extrusion head
    """
    Vacuum_Pickup()
    Vacuum_Place()
    Ink_Pickup()
    Ink_Place()


def run_calibration(n=1, save=True, reset_tray=True, output=True):
    """
    Runs the calibration procedure a total of n times and stores the result
    in calibration.csv, as well as returns it

    Result is the average of all runs for each datapoint
    """

    data = {'vac': [0.0, 0.0, 0.0],
            'ink': [0.0, 0.0, 0.0]}

    # Run calibration procedure (n trials)
    for idx in range(n):
        if output == True:
            print('Running calibration step ' + str(idx+1) + '/' + str(n))
        
        # Collect calibration data for vacuum head
        Vacuum_Pickup()
        if output == True:
            print('Calibrating X for vacuum head')
        vacuum_x = get_X('vac')
        if output == True:
            print(vacuum_x)
            print('Calibrating Y and Z for vacuum head')
        vacuum_y, vacuum_z = get_Y_Z('vac')
        if output == True:
            print([vacuum_y,vacuum_z])
        Vacuum_Place()
        
        # Write data to sum
        data['vac'][0] += vacuum_x
        data['vac'][1] += vacuum_y
        data['vac'][2] += vacuum_z

        # Collect calibration data for ink extrusion head
        Ink_Pickup()
        if output == True:
            print('Calibrating X for extrusion head')
        extrude_x = get_X('ink')
        if output == True:
            print(extrude_x)
            print('Calibrating Y and Z for extrusion head')
        extrude_y, extrude_z = get_Y_Z('ink')
        if output == True:
            print([extrude_y, extrude_z])
        Ink_Place()
        
        # Write data to sum
        data['ink'][0] += extrude_x
        data['ink'][1] += extrude_y
        data['ink'][2] += extrude_z
    
    # Take average of data sum
    calibrated_average = [data['vac'][0]/n, data['vac'][1]/n, data['vac'][2]/n,
                          data['ink'][0]/n, data['ink'][1]/n, data['ink'][2]/n]
    
    # Save calibration data to calibration.csv
    if save == True:
        with open('C:\git\ADML\Functional Printing Calibration\calibration.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(calibrated_average)
    
    if reset_tray == True:
        if output == True:
            print("Calibration sequence - Tray index data reset to 0")
        reset_tray_indexes()
    
    return calibrated_average


def run_sample_test():
    """
    Runs the calibration sqeuence once and prints the result.
    Does not save data to file. Used for testing.
    """
    result = run_calibration(save=False)
    print('--------------------------------------------------------------------------------------------------------')
    print('Result: ' + str(result))
    print('--------------------------------------------------------------------------------------------------------')


def collect_data(n, filename='data'):
    """
    Executes the calibration program n times and records all results
    in a CSV file (default=data.csv) for analysis
    """
    print('\n\n\n')
    print('========================================================================================================')
    print('Running experiment: [' + str(n) + ' trials]')

    filepath = 'C:\\git\\ADML\\Functional Printing Calibration\\' + str(filename) + '.csv'
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')

        print('--------------------------------------------------------------------------------------------------------')
        for k in range(n):
            result = run_calibration()
            print('[' + str(k+1) + '] Result: ' + str(result))
            writer.writerow(result)
        print('--------------------------------------------------------------------------------------------------------')


def get_robot_pos():
    """
    Returns the coordinate array of the position that the robot TCP is currently in.
    """

    return rtde_receive.getActualTCPPose()


def manual_control(inverted=False, show_forces=False):
    """
    Activates manual control. This mode allows moving the robot tool in the X and Y plane using
    the keyboard arrow keys. Hold shift for precise movement, and press ENTER to exit manual control.
    Holding Ctrl allows the up and down keys to jog the Z axis

    Prints out the current nozzle coordinates (in mm) when space is pressed
    """

    speed = 0.100 # m/s
    accel = 0.400 # m/s^2

    # Print robot position when space is pressed
    if show_forces == True:
        keyboard.add_hotkey('space', lambda: print([round(x,2) for x in rtde_receive.getActualTCPForce()]))
    else:
        keyboard.add_hotkey('space', lambda: print([round(x,6) for x in get_robot_pos()]))

    print('Manual control enabled!')
    if show_forces == True:
        print("Running in force-mode")
    while True:
        # If ENTER is pressed, break the loop
        if keyboard.is_pressed('enter'):
            break

        command = [0,0]
        Z = 0

        # Check arrow keys and construct command
        if keyboard.is_pressed('left'): # -X
            command[0] -= speed
        if keyboard.is_pressed('right'): # +X
            command[0] += speed
        if keyboard.is_pressed('down'): # -Y
            if keyboard.is_pressed('ctrl'): # -Z
                Z -= 0.005
            else:
                command[1] -= speed
        if keyboard.is_pressed('up'): # +Y
            if keyboard.is_pressed('ctrl'): # +Z
                Z += 0.005
            else:
                command[1] += speed

        # Apply command (Scaled if shift is pressed)
        if keyboard.is_pressed('shift'): # Slow down motion by a factor of 10
            command = [x/10 for x in command]
        speeds = [command[0], command[1], 0, 0, 0, 0]
        if inverted == True:
            speeds = [-x for x in speeds]
        speeds[2] = Z
        rtde_control.speedL(xd=speeds, acceleration=accel, time=0.002)

    rtde_control.speedStop(a=accel)
    print("Manual control disabled.")


def nozzle_setup_aid(nozzle):
    """
    Runs a short sequence of positioning and manual control stages to help streamline
    capturing the waypoint coordinates of the calibration sensor channels
    """
    
    # Position head inside X sensor channel
    rtde_control.moveL(channel_pos[nozzle]['at_x'], speed=fast) # Move head above sensor channel location
    rtde_control.moveL(channel_pos[nozzle]['in_x'], speed=slow) # Lower head into sensor channel

    # Enable manual drive to allow capturing X and Y coordinates for the start waypoint
    manual_control(inverted=True)

    # Pull out of the channel
    rtde_control.moveL(channel_pos[nozzle]['at_x'], speed=fast)

    # Position head inside YZ sensor channel
    rtde_control.moveL(channel_pos[nozzle]['at_y'], speed=fast) # Move head above sensor channel location
    rtde_control.moveL(channel_pos[nozzle]['in_y'], speed=slow) # Lower head into sensor channel

    # Enable manual drive to allow capturing X and Y coordinates for the start waypoint
    manual_control(inverted=True)

    # Pull out of the channel
    rtde_control.moveL(channel_pos[nozzle]['at_y'], speed=fast)


def set_up_calibration():
    """
    Streamlined method of adjusting the calibration procedure if needed
    Utilizes keyboard control and predefined travel to quickly capture
    the waypoint coordinates of the calibration channels
    """

    Vacuum_Pickup()
    nozzle_setup_aid('vac')
    Vacuum_Place()

    Ink_Pickup()
    nozzle_setup_aid('ink')
    Ink_Place()


def nozzle_runout_test(nozzle='vac'):
    """
    Runs an xperiment to collect data on the runout error between different nozzles of
    the same type and the total accumulated error when swapping one nozzle for another

    Each trial is triggered by the SHIFT key and the experiment ends when CTRL is pressed
    Writes all data to "data.csv" when the experiment ends
    """

    # Check that nozzle identifier is valid:
    if nozzle not in ['vac', 'ink']:
        raise Exception('Error - NozzleID: "' + str(nozzle) + '" is not a valid nozzle!')

    # Equip nozzle from holder
    if nozzle == 'ink':
        Ink_Pickup()
    else:
        Vacuum_Pickup()
    
    print("Running Experiment: - Nozzle Runout Error Test")
    print("Press SHIFT to begin experiment - CTRL to cancel and return the nozzle")

    data = []

    while True:
        # If CTRL is pressed, break the loop
        if keyboard.is_pressed('ctrl'):
            break

        # Otherwise check for SHIFT and run experiment if it is pressed
        if keyboard.is_pressed('shift'):
            X = get_X(nozzle)
            Y, Z = get_Y_Z(nozzle)
            data.append([X, Y, Z])
    
    # If any data was collected, write it to "data.csv"
    if data != []:
        with open('C:\git\ADML\Functional Printing Calibration\data.csv', 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            for point in data:
                writer.writerow(point)
        f.close()
        print('Data saved to "Functional Printing Calibration\data.csv"')

    # After the experiment is over, return the nozzle
    if nozzle == 'ink':
        Ink_Place()
    else:
        Vacuum_Place()


#### Execute Procedure #### =================================================================================

if __name__ == "__main__":
    #collect_data(5, 'data_lab_group_99')
    run_calibration()

    # ----------========== Code below this is for lab setup only: ==========----------
    #run_calibration(reset_tray=False) # Uncomment this line to calibrate robot WITHOUT reseting tray_data.txt
