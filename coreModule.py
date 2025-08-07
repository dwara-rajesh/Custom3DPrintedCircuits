"""
Contains all of the core functionality and code modules that support the pick and place and ink printing features
"""

import time
import math
import rtde_io
import rtde_receive
import rtde_control
import csv
import struct
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import keyboard


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Setup code to initialize robot control and pressure regulator control # === #

# In order to run this from visual studio code you must install python into Windows
rtde_io = rtde_io.RTDEIOInterface("10.241.34.45")
rtde_receive = rtde_receive.RTDEReceiveInterface("10.241.34.45")
rtde_control = rtde_control.RTDEControlInterface("10.241.34.45")

# Alicat pressure regulator
client = ModbusTcpClient("10.241.34.56")
client.connect()


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Program initialization and global definitions # === # --------------------------------------------------------------------------------------------\

# Basic waypoints and speeds
micrometric = 0.1
precise = 0.1
slow = 1.0
fast = 3.0
ACCELERATION = 1.2
pHome = [0.10916398083657383, -0.4869139234884672, 0.4318552510405578, 0.00012300640813111974, -3.1415831259486633, -5.7967739237283965e-05]
wait_time = 0.4

# Central, above table waypoint - Circuit assembly rest position
standby = [0.2683069106214198, -0.3272583283863385, 0.23585134091291987, -1.1211011736148604e-05, -3.1415181771835474, -3.8546943176232075e-05]

z_origin_offset_from_sensor = 1.747 / 39.37 #z distance from calibration sensor to top of vise + clearnace (convert in to m)
top_right_vise = [0.27591455175868757,-0.3373095135474149, z_origin_offset_from_sensor] #obtained manually using precision tip and moving robot around
admlviceblock_yoff = 0.486 / 39.37 #convert in to m

# Calibration data location and memory [CWD is "C:\git\ADML"]
CALIBRATION_FILEPATH = "Functional Printing Calibration/calibration.csv"
CALIBRATION_DATA = {'vac': None,
                    'ink': None}

# Tray component data location and memory [CWD is "C:\git\ADML"]
COMPONENT_TRAY_FILEPATH = "tray_data.txt"

COMPONENT_HEIGHTS = { #in mm
    'battery': 1.6,
    'button': 8.6,
    'microcontroller': 5.55,
    'led': 2.55
}
# Basic constants and definitions:
vac_IO = 5 # IO pin for the vacuum solenoid
ink_IO = 4 # IO pin for the ink extrusion solenoid

ATMOSPHERE = 14.8 # Atmospheric pressure (psi) - Used to "reset" the pressure regulator [Real value is 14.696psi]
PLACE_PRESSURE = 20 # Positive pressure (psi) applied briefly when placing components to release them from the vacuum
DEFAULT_PRINT_PRESSURE = 85 # Default regulator pressure when extruding ink (in psi) - A custom pressure can be passed to ink_on() as a parameter!


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Code for general robot control # === #

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


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Code for general robot control # === #

def load_calibration_data():
    """
    Loads the calibration data from the CSV into local program memory.
    Accessed via CALIBRATION_DATA dictionary above ^
    """

    data = None

    # Open the CSV file in read mode
    with open(CALIBRATION_FILEPATH, 'r') as f:
        # Create a reader object
        reader = csv.reader(f)

        # Iterate through the rows in the CSV file
        for row in reader:
            # Access each element in the row
            data = row



    # Check that data appears valid, and load it:
    if data is not None:
        if len(data) != 6:
            raise Exception("Calibration data malformed. - Please re-run calibration sequence.")
        num_data = [float(x) for x in data] # Data is read as string so convert into float first
        # Vacuum nozzle data is first, Ink nozzle data last:
        CALIBRATION_DATA['vac'] = num_data[0:3]
        CALIBRATION_DATA['ink'] = num_data[3:6]
    else:
        raise Exception("Calibration data empty! - Please run calibration sequence first.")


def get_robot_pos():
    """
    Returns the coordinate array of the position that the robot TCP is currently in.
    """

    return rtde_receive.getActualTCPPose()


def print_robot_pos():
    """
    Prints the current robot position in the console output
    """

    print("\n\n\n\n\n\n\n\n\n\n\n")
    print("===============================================================================================================================================")
    print(get_robot_pos())
    print("===============================================================================================================================================")


def open_grabber(wait=1.0):
    """
    Opens the robot grabber, with a buffer time delay before and after opening
    """

    time.sleep(wait)
    rtde_io.setStandardDigitalOut(0, False)
    time.sleep(wait)


def close_grabber(wait=1.0):
    """
    Closes the robot grabber, with a buffer time delay before and after closing
    """

    time.sleep(wait)
    rtde_io.setStandardDigitalOut(0, True)
    time.sleep(wait)


def toggle_grabber(wait=0.01):
    """
    Closes the grabber if it is open, and vice-versa
    """
    if rtde_receive.getDigitalOutState(0) == True:
        open_grabber(wait=wait)
    else:
        close_grabber(wait=wait)


def open_vice(wait=1.0):
    """
    Opens the assembly vice, with a buffer time delay before and after opening
    """

    time.sleep(wait)
    rtde_io.setStandardDigitalOut(1, False)
    time.sleep(wait)


def close_vice(wait=1.0):
    """
    Closes the assembly vice, with a buffer time delay before and after closing
    """

    time.sleep(wait)
    rtde_io.setStandardDigitalOut(1, True)
    time.sleep(wait)


def set_pressure(pressure):
    """
    Configures the Alicat regulator to the requested pressure
    """

    hex_string = hex(struct.unpack('<I', struct.pack('<f', pressure))[0])
    while len(hex_string) < 2+8: #The hexcode should be length 2+8 ex: 0x00000000. Padd with zeroes as needed
        hex_string += '0'
    part1 = hex_string[2:6]
    part2 = hex_string[6:10]
    #client.write_registers(1009, [int(part1, 16),int(part2, 16)])
    client.write_registers(1009, [int(part1, 16),int(part2, 16)])


def get_pressure():
    """
    Reads the current pressure from the Alicat regulator
    """

    try:
        rr = client.read_input_registers(1202, 2, unit=1) #this used to say unit=1 instead of slave =1.  Changed do to error message: TypeError: ModbusClientMixin.read_input_registers() got an unexpected keyword argument 'unit'
    except ModbusException as exc:
        return -1
    return struct.unpack('>f', bytes.fromhex(f"{rr.registers[0]:0>4x}" + f"{rr.registers[1]:0>4x}"))[0]


def vacuum_on(delay=0.5, log=False):
    """
    Turns on the vacuum suction on the pick-and-place nozzle
    """
    set_pressure(0.1)
    while get_pressure() >= 12.0:
        set_pressure(0.1)
        time.sleep(0.1)
    rtde_io.setStandardDigitalOut(vac_IO, True)

    # If log is set to True, print status message
    if log == True:
        print("Vacuum nozzle: - Active")

    time.sleep(delay) # Delay to allow the pressure to change


def vacuum_off(delay=0.5, log=False):
    """
    Turns off the vacuum suction on the pick-and-place nozzle
    """
    set_pressure(ATMOSPHERE)
    rtde_io.setStandardDigitalOut(vac_IO, False)

    # If log is set to True, print status message
    if log == True:
        print("Vacuum nozzle: - Disabled")

    time.sleep(delay) # Delay to allow the pressure to change


def toggle_vacuum():
    """
    Toggles the vacuum on if it is off, and vice-versa
    """
    if rtde_receive.getDigitalOutState(vac_IO) == True:
        vacuum_off(log=True)
    else:
        vacuum_on(log=True)


def prime_ink(pressure=DEFAULT_PRINT_PRESSURE, delay=1.0):
    """
    Primes the air line to the ink printer and pressurizes it
    at the specified pressure. Default is 85psi!
    """
    set_pressure(pressure=pressure)
    time.sleep(delay) # Delay to let the pressure stabilize inside the physical line


def ink_on():
    """
    Starts extruding ink with the syringe
    """
    rtde_io.setStandardDigitalOut(ink_IO, True)


def ink_off():
    """
    Stops extruding ink with the syringe
    """
    rtde_io.setStandardDigitalOut(ink_IO, False)


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Functions to control the robot in table coordinates # === #

# Array with table coordinate offsets (Used to move robot in table relative coordinates)
table_offsets = [-9.52, -125.93, 1+3.45] # All units in millimeters! NOT meters! (Z=0 at 1mm above table for safety)


def goto_pos(pos,rot=[0.0, 3.1415, 0.0], speed=precise, accel=ACCELERATION):
    """
    Moves nozzle tip to indicated [X,Y,Z] TABLE coordinates accounting
    for calibration data, at given speed. Uses precise speed by default.
    Assumes real position is valid and safe!

    POSITION COORDINATES ARE GIVEN IN MILIMITERS!
    This is different from usual UR coordinates which are in meters!
    """

    # If the calibration data is not loaded, load it!
    if CALIBRATION_DATA['vac'] is None:
        load_calibration_data()

    # Adjust pos with table offsets
    table_pos = [pos[x] + table_offsets[x] for x in range(3)]

    # Adjust pos with calibration data
    real_pos = [table_pos[x]/1000.0 + CALIBRATION_DATA['vac'][x] for x in range(3)]

    # Add rotation coordinates to final position vector
    real_pos = real_pos + rot
    # Move there!
    rtde_control.moveL(real_pos, speed=speed, acceleration=accel)


def get_pos():
    """
    Returns the current nozzle position in table coordinates
    Returns the coordinates in millimeters!
    """

    # If the calibration data is not loaded, load it!
    if CALIBRATION_DATA['vac'] is None:
        load_calibration_data()

    # Extract real XYZ coordinates
    real_pos = [x for x in get_robot_pos()][0:3]

    # Adjust pos with calibration data and convert to millimeters
    calibrated_pos = [(real_pos[x] - CALIBRATION_DATA['vac'][x])*1000 for x in range(3)]

    # Adjust pos with table offsets
    table_pos = [calibrated_pos[x] - table_offsets[x] for x in range(3)]

    return table_pos


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Functions to command the robot to grab or return the Vacuum Nozzle and Ink Printer tools# === #

# Waypoints related to grabbing and dropping the vacuum nozzle
nearNozzle = [-0.3267296578454656, -0.2950769202750008, 0.22283614652490163, -1.9680334423059386e-05, -3.1415525711296683, 3.735069317041807e-05]
atNozzle = [-0.49432230938109256, -0.29513193360988554, 0.22281989498894283, -0.00013456905793184112, 3.141581819587058, 2.2074167787736784e-05]
liftNozzle = [-0.4942928705734949, -0.29509246141832063, 0.3664258589362551, 0.00017239352196365805, -3.1415747862339565, -5.75287498767879e-06]

# Waypoints related to grabbing and dropping the ink printer
nearPrinter = [-0.3267296578454656, -0.39684457188849165, 0.22283614652490163, -1.9680334423059386e-05, -3.1415525711296683, 3.735069317041807e-05]
atPrinter = [-0.49432230938109256, -0.39679106537367614, 0.22281989498894283, -0.00013456905793184112, 3.141581819587058, 2.2074167787736784e-05]
liftPrinter = [-0.4942928705734949, -0.3967658909572524, 0.3664258589362551, 0.00017239352196365805, -3.1415747862339565, -5.75287498767879e-06]


def grab_nozzle():
    """
    Controls the robot to grab the vacuum nozzle and move to standby position
    Assumes gripper is not already holding something!! If it is, the robot will
    drop it!
    """

    # Move to nozzle location
    rtde_control.moveL(nearNozzle, speed=fast)

    # If grabber is closed, open it to avoid crashing!
    if rtde_receive.getDigitalOutState(0) == True:
        open_grabber(0.1)

    # Move to tool pickup waypoint
    rtde_control.moveL(atNozzle, speed=slow)

    # Grab nozzle (Close grabber)
    close_grabber(wait=wait_time)

    # Lift nozzle out of rack and move to standby
    rtde_control.moveL(liftNozzle, speed=precise)
    rtde_control.moveL(standby, speed=fast)


def return_nozzle(skip_standby=False):
    """
    Controls the robot to return the vacuum nozzle to its rack
    Assumes gripper is already holding the nozzle.
    Can be instructed to skip the final move to standby to optimize
    pathing and speed when swapping from one tool to another.
    """

    # Turn off vacuum if it is not already
    vacuum_off()

    # Move to rack location and lower nozzle into place
    rtde_control.moveL(liftNozzle, speed=fast)
    rtde_control.moveL(atNozzle, speed=precise)

    # Release nozzle (Open grabber)
    open_grabber(wait=wait_time)

    # Lift nozzle out of rack and move to standby (unless otherwise specified)
    rtde_control.moveL(nearNozzle, speed=slow)
    if skip_standby != True:
        rtde_control.moveL(standby, speed=fast)


def grab_inkprinter():
    """
    Controls the robot to grab the vacuum nozzle and move to standby position
    Assumes gripper is not already holding something!! If it is, the robot will
    drop it!
    """

    # Move to nozzle location
    rtde_control.moveL(nearPrinter, speed=fast)

    # If grabber is closed, open it to avoid crashing!
    if rtde_receive.getDigitalOutState(0) == True:
        open_grabber(0.1)

    # Move to tool pickup waypoint
    rtde_control.moveL(atPrinter, speed=slow)

    # Grab nozzle (Close grabber)
    close_grabber(wait=wait_time)

    # Lift nozzle out of rack and move to standby
    rtde_control.moveL(liftPrinter, speed=precise)
    rtde_control.moveL(standby, speed=fast)

    # Once the ink printer tool is ready, prime the air line and pressurize it
    prime_ink()


def return_inkprinter(skip_standby=False):
    """
    Controls the robot to return the vacuum nozzle to its rack
    Assumes gripper is already holding the nozzle.
    Can be instructed to skip the final move to standby to optimize
    pathing and speed when swapping from one tool to another.
    """

    # Reset the air line back to atmospheric pressure if it is not already and stop all printing
    ink_off()
    set_pressure(ATMOSPHERE)

    # Move to rack location and lower nozzle into place
    rtde_control.moveL(liftPrinter, speed=fast)
    rtde_control.moveL(atPrinter, speed=precise)

    # Release nozzle (Open grabber)
    open_grabber(wait=wait_time)

    # Lift nozzle out of rack and move to standby
    rtde_control.moveL(nearPrinter, speed=slow)
    if skip_standby != True:
        rtde_control.moveL(standby, speed=fast)


def test_toolswap():
    """
    Picks up nozzle, goes to standby, and returns nozzle to rack
    Then does the same with the ink printing head and finally returns to standby
    Intended to test that tool pickup and return works as intended
    """

    grab_nozzle()
    time.sleep(1)
    return_nozzle(skip_standby=True)

    grab_inkprinter()
    time.sleep(1)
    return_inkprinter()


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Functions and aids for developing/debugging, programming the robot, and running experiments # === #


def freedrive_mode():
    """
    Activates freedrive mode on the robot along the X and Y axis while
    keeping the Z axis and tool rotation locked. Very useful for calibrating
    waypoints on the table. Be sure to move the robot to an appropriate Z
    height before turning freedrive on!

    Currently set up to stay in freedrive until the X calibration sensor is triggered
    Triggering the Y calibration sensor causes the robot's current position to be
    printed out to the console (In table coordinates [mm])

    ONLY WORKS ON ROBOTS WITH FIRMWARE VERSION 5.10 OR GREATER
    """

    # Enable freedrive
    print("X-Y Freedrive Enabled!")
    rtde_control.freedriveMode()#free_axes=[1,1,0,0,0,0]#

    # Monitor sensors
    printed = False
    while rtde_receive.getDigitalInState(2) == False:
        if rtde_receive.getDigitalInState(3) == True:
            if printed == False:
                print("Current table coordinates: ", get_pos())
                printed = True # Used to print only on the falling edge of the sensor
        else:
            printed = False
        time.sleep(0.1)


    # End freedrive
    rtde_control.endFreedriveMode()
    print("X-Y Freedrive Disabled!")


def fake_freedrive(height=100, apply_raw_force=False):
    """
    Attempts to mimick the behaviour of freedrive_mode(), but using force feedback.
    It measures the force on the TCP, and applies external forces as motion commands
    to the X and Y axis, while maintaining the Z axis and rotational axes locked.

    To prevent oscillations and nosie, forces under the threhold are not applied, and
    when no forces are applied externally, the robot locks and maintains position.
    """

    print("Force-based freedrive mode enabled!")
    force_threshold = 15 # Any force detected above this value (N) will be considered intentional by the operator
    task_frame = [0,0,0,0,0,0] # Force frame equal to base frame (relative frame)
    selection_vector = [1,1,0,0,0,0] # Compliant only in X and Y axis
    force_type = 2 # Does not transform force vector (maintains base frame)
    limits = [2, 2, 0.2, 0.5, 0.5, 0.5] # Speed limits at TCP that will not be exceeded

    rtde_control.forceModeSetDamping(0.1)
    rtde_control.forceModeSetGainScaling(0.9)

    # Monitor sensors
    printed = False
    while rtde_receive.getDigitalInState(2) == False:
        if rtde_receive.getDigitalInState(3) == True:
            if printed == False:
                print("Current table coordinates: ", get_pos())
                printed = True # Used to print only on the falling edge of the sensor
        else:
            printed = False

        # Measure applied forces and compute force command
        command = [0,0]
        F = rtde_receive.getActualTCPForce()
        #print(F)
        if math.fabs(F[0]) > force_threshold: # Apply force in X
            command[0] =+ F[0]
        if math.fabs(F[1]) > force_threshold: # Apply force in Y
            command[1] =+ F[1]

        # Apply force command using force mode
        if command == [0,0]:
            location = get_pos() # Get current X Y coordinates
            location[2] = height
            rtde_control.forceModeStop() # Lock position when no forces are being applied
            goto_pos(location)
        wrench = [command[0], command[1], F[2], 0, 0, 0]
        if apply_raw_force == True:
            wrench = F
        rtde_control.forceMode(task_frame, selection_vector, wrench, force_type, limits)
        time.sleep(0.002) # ~500Hz loop (not timed)

    # End force mode and return robot to normal operation
    rtde_control.forceModeStop()
    print("Force-based freedrive mode disabled.")


def linear_freedrive(precision_mode=False, print_output=False):
    """
    Attempts to mimick the behaviour of freedrive_mode(), but using force feedback.
    It measures the force on the TCP, and translates them into linear speed commands
    along the X and Y axis, while maintaining the Z axis and rotational axes locked.

    To prevent oscillations and nosie, forces under the thrsehold are not applied.
    Take care not to force the robot beyond its max speeds, or a protective stop will trigger

    Precision mode is capped at 30mm/s! Standard mode is capped at 150mm/s
    """

    # Zero force seor while robot is locked in place
    time.sleep(1)
    rtde_control.zeroFtSensor()
    time.sleep(1)

    print("Force-based linear freedrive mode enabled!")
    force_threshold = 24 # Any force detected above this value (N) will be considered intentional by the operator
    max_accel = 0.350 # [m/s^2] Acceleration of the robot while in linear speed mode
    if precision_mode == True:
        print(" > Running precision mode")
        max_speed = 0.030 # [m/s] (30mm/s) Max speed cap. Any speeds above this are reduced to max
        gain = 0.010
    else:
        print(" > Running standard mode")
        max_speed = 0.150 # [m/s] (15cm/s) Max speed cap. Any speeds above this are reduced to max
        gain = 0.012

    # Monitor sensors
    printed = False
    while rtde_receive.getDigitalInState(2) == False:
        if rtde_receive.getDigitalInState(3) == True:
            if printed == False:
                print("Current table coordinates: ", get_pos())
                printed = True # Used to print only on the falling edge of the sensor
        else:
            printed = False

        # Measure applied forces and compute linear speed command
        command = [0,0]
        F = rtde_receive.getActualTCPForce()
        #print(F)
        if math.fabs(F[0]) > force_threshold: # Apply force in X (within threshold and corrected for zero point)
            command[0] =+ [(F[0]-force_threshold) if F[0] >= 0 else (F[0]+force_threshold) for x in [0]][0] * gain
        if math.fabs(F[1]) > force_threshold: # Apply force in Y (within threshold and corrected for zero point)
            command[1] =+ [(F[1]-force_threshold) if F[0] >= 0 else (F[1]+force_threshold) for x in [0]][0] * gain

        # Apply max speed threshold
        command = [x if x <= max_speed else max_speed for x in command]
        command = [x if x >= -max_speed else -max_speed for x in command]

        # Apply command using linear speed function
        speeds = [command[0], command[1], 0, 0, 0, 0]
        if print_output == True:
            print("F, C, S: ", [round(x,3) for x in F[0:3]], command, speeds)
        rtde_control.speedL(xd=speeds, acceleration=max_accel, time=0.002) # ~500kHz loop (not timed)

    # End force mode and return robot to normal operation
    rtde_control.speedStop(a=max_accel)
    print("Force-based linear freedrive mode disabled.")


def manual_control(inverted=False, show_forces=False):
    """
    Activates manual control. This mode allows moving the robot tool in the X and Y plane using
    the keyboard arrow keys. Hold shift for precise movement, and press ENTER to exit manual control.
    Holding Ctrl allows the up and down keys to jog the Z axis

    Prints out the current nozzle coordinates (in mm) when space is pressed

    The ALT key can be used to toggle vacuum on and off

    CAPS LOCK can be used to toggle the gripper
    """

    speed = 0.100 # m/s
    accel = 0.400 # m/s^2

    # Print robot position when space is pressed
    if show_forces == True:
        keyboard.add_hotkey('space', lambda: print([round(x,2) for x in rtde_receive.getActualTCPForce()]))
    else:
        keyboard.add_hotkey('space', lambda: print([round(x,2) for x in get_pos()]))

    # Toggle vacuum when ALT is pressed
    keyboard.add_hotkey('alt', toggle_vacuum)

    # Toggle vacuum when ALT is pressed
    keyboard.add_hotkey('capslock', toggle_grabber)

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
        else:
            Z *= 20
        speeds = [command[0], command[1], 0, 0, 0, 0]
        if inverted == True:
            speeds = [-x for x in speeds]
        speeds[2] = Z
        rtde_control.speedL(xd=speeds, acceleration=accel, time=0.002)

    rtde_control.speedStop(a=accel)
    print("Manual control disabled.")


def point_capture():
    """
    Wrapper function to simplify setting up manual control
    for point capture

    Intended to be performed from the POV inside the conveyor belt
    If performing point capture from the table POV, set the inverted
    parameter to False in manual_control()
    """

    goto_pos([0,0,100], speed=fast)
    goto_pos([0,0,30], speed=precise)
    goto_pos([0,0,1], speed=micrometric)
    manual_control(inverted=True) # Set inverted=False if running from the table POV
    goto_pos([0,0,100], speed=fast)


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# === # Main program loop # === #


def main():
    """
    Main script loop - In the core module, this is mainly used for debugging / setting things up
    Other test programs should be run directly from the Pick-and-Place or the Ink Printing scripts
    """

    #test_toolswap()
    manual_control(inverted=True)

    #reset_tray_indexes()

    """
    tray = read_tray_indexes()
    print(tray)
    for item in tray:
        tray[item] += 12345
    write_tray_indexes(tray)
    print('Done!')
    """


if __name__ == "__main__":
    main()



