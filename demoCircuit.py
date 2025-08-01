"""
Module containing the code to fully assemble and print the demo LED + Switch circuit
"""

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

# Set this to true to execute in test mode (no ink will be printed)
TEST_RUN = False


def main():
    """
    Main script loop - RUNS PROCESS TO ASSEMBLE DEMO CIRCUIT
    """

    global TEST_RUN # Prevents python from being stupid >:(

    TYPE = 1 # Assembly method selection (-1 for debug)

    # Prepare trace data
    traces = assemble_traces(DEMO_PRINT)
    squares = assemble_squares(DEMO_PRINT)
    
    if TYPE == -1: # Just the traces in order, no coponents are placed (For testing and validation)
        TEST_RUN = True # Forces dry run mode!
        grab_inkprinter()
        print_trace(traces['bat-led'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        for traceID in ['led-swt', 'swt-bat-A']:
            print_trace(traces[traceID], print_speed=PRINT_SPEED_SLOW, dry_print=TEST_RUN)
        print_trace(traces['led-anchor-A'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['led-anchor-B'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['swt-anchor-A'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['swt-anchor-B'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['swt-bat-B'], print_speed=PRINT_SPEED_SLOW, dry_print=TEST_RUN)
        print_square(squares['swt-square-A'][0], squares['swt-square-A'][1], squares['swt-square-A'][2], dx=0.9, dry_run=TEST_RUN)
        print_square(squares['swt-square-B'][0], squares['swt-square-B'][1], squares['swt-square-B'][2], dx=0.9, dry_run=TEST_RUN)
        print_square(squares['swt-reinforce-A'][0], squares['swt-reinforce-A'][1], squares['swt-reinforce-A'][2], dx=0.9, dry_run=TEST_RUN)
        print_square(squares['swt-reinforce-B'][0], squares['swt-reinforce-B'][1], squares['swt-reinforce-B'][2], dx=0.9, dry_run=TEST_RUN)
        print_arc(DEMO_PRINT['arcs']['bat-arc'][0], DEMO_PRINT['arcs']['bat-arc'][1], DEMO_PRINT['arcs']['bat-arc'][2], dry_run=TEST_RUN)
        return_inkprinter()

    if TYPE == 0: # Components first, then traces - OUTDATED! Do not use!
        # ----- Step 1 - Print trace under battery -----------------------    
        # Equip printer and close vice
        grab_inkprinter()
        close_vice()
        # Print trace under battery
        print_trace(traces['bat-led-A'], print_speed=PRINT_SPEED_HALF, dry_print=TEST_RUN)
        # Swap tools
        return_inkprinter()

        # ----- Step 2 - Pick-and-Place all components -------------------
        # Equip vacuum nozzle
        grab_nozzle()
        # Assemble components
        circuit = determine_schematic() #me
        # circuit_pick_and_place(DEMO_CIRCUIT) #Juan
        circuit_pick_and_place(circuit) #me
        # Swap tools again
        return_nozzle()

        # ----- Step 3 - Print remaining traces --------------------------
        # Equip printer again
        grab_inkprinter()
        # Print remaining traces
        for traceID in ['bat-led-B', 'led-swt', 'swt-bat']:
            print_trace(traces[traceID], print_speed=PRINT_SPEED_HALF, dry_print=TEST_RUN)
        # Return printer and end fabrication sequence
        return_inkprinter()
    
    if TYPE == 1: # Traces first, then components
        grab_inkprinter()
        close_vice()
        # Print all traces except trace that goes over battery
        print_trace(traces['bat-led'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        #print_trace(traces['bat-anchor'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.2, dry_print=TEST_RUN)
        for traceID in ['led-swt', 'swt-bat-A']:
            print_trace(traces[traceID], print_speed=PRINT_SPEED_SLOW, dry_print=TEST_RUN)
        # Swap tools
        return_inkprinter()
        grab_nozzle()
        # Assemble components
        circuit = determine_schematic() #me
        # circuit_pick_and_place(DEMO_CIRCUIT) #Juan
        circuit_pick_and_place(circuit) #me
        # Swap tools again
        return_nozzle()
        grab_inkprinter()
        # Print remaining traces and mechanical support anchors
        print_trace(traces['led-anchor-A'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['led-anchor-B'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['swt-anchor-A'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['swt-anchor-B'], print_speed=PRINT_SPEED_SLOW, primer_delay=1.0, dry_print=TEST_RUN)
        print_trace(traces['swt-bat-B'], print_speed=PRINT_SPEED_SLOW, dry_print=TEST_RUN)
        print_square(squares['swt-square-A'][0], squares['swt-square-A'][1], squares['swt-square-A'][2], dx=0.9, dry_run=TEST_RUN)
        print_square(squares['swt-square-B'][0], squares['swt-square-B'][1], squares['swt-square-B'][2], dx=0.9, dry_run=TEST_RUN)
        print_square(squares['swt-reinforce-A'][0], squares['swt-reinforce-A'][1], squares['swt-reinforce-A'][2], dx=0.9, dry_run=TEST_RUN)
        print_square(squares['swt-reinforce-B'][0], squares['swt-reinforce-B'][1], squares['swt-reinforce-B'][2], dx=0.9, dry_run=TEST_RUN)
        print_arc(DEMO_PRINT['arcs']['bat-arc'][0], DEMO_PRINT['arcs']['bat-arc'][1], DEMO_PRINT['arcs']['bat-arc'][2], dry_run=TEST_RUN)
        # Return printer and end fabrication sequence
        return_inkprinter()
        open_vice()


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
