"""
Script executed with BUMES command: --- "dynamicfunctionalPrinting("schematic_filename")" ---
"""
import sys
import os
import subprocess

def runPythonScript(filename,schematic_file):
    """
    Finds and executes the python script with given filename
    """

    # command = f'python.exe "{filename}" "{schematic_file}"' #passes the project file as an argument to demoCircuit.py
    command = ["python.exe",filename,schematic_file]
    print(command)
    subprocess.run(command) #runs the demoCircuit.py script in another terminal
    # os.system(command)

if len(sys.argv) > 1:
    schematic_file = sys.argv[1] #reads the global variable to get the project file
    runPythonScript(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\demoCircuit.py",schematic_file) #passes the schematic to function
else:
    print("Error: No Argument Passed")