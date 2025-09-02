"""
Script executed with BUMES command: --- "dynamicMachining("cnc_program_number")" ---
"""
import sys
import os
import subprocess

def runPythonScript(filename,cnc_program_num):
    """
    Finds and executes the python script with given filename
    """

    # command = f'python.exe "{filename}" "{cnc_program_num}"' #passes the cnc program number as an argument to MaryDynamicCNCProgLoad.py
    command = ["python.exe",filename,cnc_program_num]
    print(command)
    subprocess.run(command) #runs the MaryDynamicCNCProgLoad.py script in another terminal
    # os.system(command)

if len(sys.argv) > 1:
    program_num = sys.argv[1] #reads the global variable to get the project file
    runPythonScript(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\MaryDynamicCNCProgLoad.py",program_num) #passes the CNC program number to function
else:
    print("Error: No Argument Passed")