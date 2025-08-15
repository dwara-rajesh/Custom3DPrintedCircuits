"""
Script executed with BUMES command: --- "functionalPrinting()" ---
"""
import os
import subprocess

def runPythonScript(filename,cnc_program_num):
    """
    Finds and executes the python script with given filename
    """

    # command = f'python.exe "{filename}" "{schematic}"' #passes the project file as an argument to demoCircuit.py
    command = ["python.exe",filename,cnc_program_num]
    print(command)
    subprocess.run(command)
    # os.system(command)

program_num = globals().get("cnc_prog_number") #reads the global variable to get the project file
runPythonScript(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\MaryDynamicCNCProgLoad.py",program_num) #passes the CNC program number to function
