"""
Script executed with BUMES command: --- "functionalPrinting()" ---
"""

import os

def runPythonScript(filename,schematic):
    """
    Finds and executes the python script with given filename
    """

    command = f'python.exe "{filename}" "{schematic}"' #passes the project file as an argument to demoCircuit.py
    print(command)
    os.system(command)

schematic_file = globals().get("file_to_process") #reads the global variable to get the project file
runPythonScript(r"C:\git\ADML\Automated Circuit Printing And Assembly\Summer2025\demoCircuit.py",schematic_file) #passes the project file to function
