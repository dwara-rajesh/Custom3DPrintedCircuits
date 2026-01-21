"""
Module containing the code to fully assemble and print the demo LED + Switch circuit
"""
import sys
import os
import json

# Import core module:
import coreModule

TEST_RUN = False #if True, no ink extrusion (dry run), else ink extrusion (wet run)
workdir = os.getcwd()
circuitprintingdir = os.path.join(workdir,"Automated Circuit Printing and Assembly")
projectfilefolder = os.path.join(circuitprintingdir,"Summer2025") #points to C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025

# def get_most_recent_saved_file(folder):
#     files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and f.endswith(".json")]
#     if not files:
#         return None
#     return max(files, key=os.path.getctime)

def main():
    """
    Main script loop - RUNS PROCESS TO ASSEMBLE DEMO CIRCUIT
    """
    # test_BUMES_comms() #to check if BUMES can communicate efficiently with the custom script ensure software stack communication
    if len(sys.argv) > 1:
        assemble(sys.argv[1]) #tracing and assembly
        # test_BUMES_argument_transfer(sys.argv[1]) #to check if BUMES can transfer/pass arguments/parameters to custom scripts
    else:
        print("Project file not submitted, ensure dynamicfunctionalPrinting() has a parameter passed in BUMES")

def assemble(projfile):
    global TEST_RUN # Prevents python from being stupid >:(
    coreModule.close_vice()
    # file_path = get_most_recent_saved_file(savefolder)
    file_path = os.path.join(projectfilefolder,projfile)

    #get stock height offset
    coreModule.get_stock_height_offset(file_path)

    # Import modular code from Pick-and-Place file
    import pickAndPlace
    # Import modular code from Ink Tracing file
    import inkTracing
    #Trace Wire -> Place Components -> Reinforce Connection (Workflow)
    inkTracing.ink_trace(file_path,TEST_RUN)
    pnpcomplete = pickAndPlace.PNP(file_path)
    if pnpcomplete:
        reinforcement_schematic = inkTracing.get_traces(file_path,reinforce=True)
        inkTracing.reinforce_connection(reinforcement_schematic,TEST_RUN)

    coreModule.open_vice()

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
    coreModule.close_grabber()
    coreModule.open_grabber()


if __name__ == "__main__":
    main()
    coreModule.rtde_control.stopScript()