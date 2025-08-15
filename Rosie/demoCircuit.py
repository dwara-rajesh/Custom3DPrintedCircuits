"""
Module containing the code to fully assemble and print the demo LED + Switch circuit
"""
import sys
import os
import json

# Import core module:
from coreModule import *
# Import modular code from Pick-and-Place file
from pickAndPlace import *
# Import modular code from Ink Tracing file
from inkTracing import *

TEST_RUN = True #if True, no ink extrusion (dry run), else ink extrusion (wet run)
workdir = os.getcwd()
circuitprintingdir = os.path.join(workdir,"Automated Circuit Printing and Assembly")
projectfilefolder = os.path.join(circuitprintingdir,"Summer2025")

# def get_most_recent_saved_file(folder):
#     files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".json")]
#     if not files:
#         return None
#     return max(files, key=os.path.getctime)

def main():
    """
    Main script loop - RUNS PROCESS TO ASSEMBLE DEMO CIRCUIT
    """
    # test_BUMES_comms()
    if len(sys.argv) > 1:
        assemble(sys.argv[1]) #task status fails to update - stuck at running and waiting to execute
        # test_BUMES_argument_transfer(sys.argv[1]) #task status updates when this function is run
    else:
        print("Project file not submitted, ensure functionalPrinting() has a parameter passed in BUMES")

def assemble(projfile):
    global TEST_RUN # Prevents python from being stupid >:(
    close_vice()
    # file_path = get_most_recent_saved_file(savefolder)
    file_path = os.path.join(projectfilefolder,projfile)
    #Trace Wire -> Place Components -> Reinforce Connection
    ink_trace(file_path,TEST_RUN)
    pnpcomplete = PNP(file_path)
    if pnpcomplete:
        reinforcement_schematic = get_traces(file_path,reinforce=True)
        reinforce_connection(reinforcement_schematic)

    open_vice()

def test_BUMES_comms(): #Test to ensure that BUMES can communicate with script
    with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\testComm.json", "r") as f:
        data = json.load(f)
    
    for key,_ in data.items():
        data[key].append("hellofromBUMES")
        break
    with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\testComm.json", "w") as f:
        json.dump(data,f)

def test_BUMES_argument_transfer(argument): #Test to ensure that the parameter/argument is passed correctly
    with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\testArgumentPass.json", "r") as f:
        data = json.load(f)
    data["file"].append(os.path.join(projectfilefolder,argument))
    with open(r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\testArgumentPass.json", "w") as f:
        json.dump(data,f)

def runBUMES():
    """
    Proxy debug function used because BUMES hates windows python >:(
    Do not worry about it. It does nothing and serves no purpose.
    """
    close_grabber()
    open_grabber()


if __name__ == "__main__":
    main()
    rtde_control.stopScript()