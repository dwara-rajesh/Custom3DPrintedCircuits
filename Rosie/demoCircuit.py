"""
Module containing the code to fully assemble and print the demo LED + Switch circuit
"""
import sys
import time
import math
import rtde_io
import rtde_receive
import rtde_control
import keyboard

# Import core module:
from coreModule import *
# Import modular code from Pick-and-Place file
from pickAndPlace import *
# Import modular code from Ink Tracing file
from inkTracing import *

TEST_RUN = True #if True, no ink extrusion (dry run), else ink extrusion (wet run)
# savefolder = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025"
# def get_most_recent_saved_file(folder):
#     files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".json")]
#     if not files:
#         return None
#     return max(files, key=os.path.getctime)

def main(projfile):
    """
    Main script loop - RUNS PROCESS TO ASSEMBLE DEMO CIRCUIT
    """

    global TEST_RUN # Prevents python from being stupid >:(
    close_vice()
    # file_path = get_most_recent_saved_file(savefolder)
    file_path = projfile
    #Trace Wire -> Place Components -> Reinforce Connection
    ink_trace(file_path,TEST_RUN)
    pnpcomplete = PNP(file_path)
    if pnpcomplete:
        reinforcement_schematic = get_traces(file_path)
        reinforce_connection(reinforcement_schematic)

    open_vice()


def runBUMES():
    """
    Proxy debug function used because BUMES hates windows python >:(
    Do not worry about it. It does nothing and serves no purpose.
    """
    close_grabber()
    open_grabber()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1]) #loads any project file given
    else:
        print("Enter absolute project file path")
    rtde_control.stopScript()