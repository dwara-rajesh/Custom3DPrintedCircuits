'''
--------------------

Manufacturing Execution Software (MES) Python-Based Backend Scripting

    Scripting for the Control and Execution of the Flexible Manufacturing Cell
        at Boston University

    Developed by Jeffrey Costello, jdc0214@bu.edu

--------------------
'''

'''Python Built-In Libraries'''

'''Downloaded Libraries'''

'''User-Generated Libraries'''

'''
MES Backend

The backend script, built into a class-type object, looks into a sub-directory for "Process Files."
    A process file is a text file consisting of a sequence of "Tasks."
    Tasks are discrete system functions such as semaphore commands or running robot commands.
'''



import os
from collections import OrderedDict
import pprint
import time
import math
import datetime
import json
import sys
import paho.mqtt.client as mqtt
import schedule
import _mesScreen



class mesBackend:
    def __init__(self):
        '''Docstring: Initialize the MES Main Class Structure.'''
        # self.quit is only changed by self.systemStatusCallback
            # init self.quit as False
            # if self.quit changes to True, the script and screen will terminate
        self.quit = False
        self.debugOption = False

        # If debugging mode is enabled, copy sys.stdout content to .txt file in ./debug and pass argument to _mesProcess screens through debugOption boolean
        if len(sys.argv) > 1:
            if '-d' in sys.argv:
                print('DEBUG MODE ENABLED')
                self.debugOption = True
                debugFilename = './debug/backend.txt'
                sys.stdout = open(debugFilename, 'w')

        # clear the command line interface, just for clarity
        os.system('clear') 
        print('---MES Backend Script---\n')
        self.operationQueue = None

        # Dictionary for checking if all necessary startup screens have been created before proceeding in backend
        self.screenChecklist = {'CNCHandler': False,
                                'urHandler': False,
                                'PLCHandler': False,
                                'ResourceHandler': False,
                                'VisionHandler': False,
                                }
        # Establish connection to the MQTT broker
            # Callbacks are added and initialization messages are sent
        self.nextStartupPriority = 1
        self.initMQTT()
        schedule.every(1).seconds.do(self.checkProcessStatus)
        self.loopMain()

    def initMQTT(self):
        '''Invoked by MES backend __init__. Intializes the MQTT connection.'''
        self.mqttClient = mqtt.Client()
        
        # invoke self.onConnect when making connectiion to the MQTT broker
        self.mqttClient.on_connect = self.onConnect
        
        # invoke self.onDisconnect if the conenction to the MQTT broker
            # disconnects unexpectedly
        self.mqttClient.on_disconnect = self.onDisconnect

        self.mqttClient.message_callback_add(
            'system/status', self.systemStatusCallback)

        self.mqttClient.message_callback_add(
            'system/processQueue', self.queueCallback)

        self.mqttClient.message_callback_add(
            'backend/endProcess/#', self.endProcess)

        self.mqttClient.message_callback_add(
            'mesBackend/startup/#', self.startupCallback)

        self.mqttClient.message_callback_add(
            'screenStartup', self.screenStartupCallback)

        # Connect to the broker
            # successful connection invokes self.onConnect
        self.mqttClient.connect('localhost', 1883)

    def onConnect(self, client, userdata, flags, rc):
        print('Connected to MQTT client with result code ', rc)
        client.subscribe('system/#')  # multiple level wildcard
        client.subscribe('backend/#')  # multiple level wildcard
        client.subscribe('mesBackend/#')
        client.subscribe('screenStartup')

    def onDisconnect(self, client, userdata, rc):
        print('ERR: MES Backend has disconnected from the MQTT Broker Unexpectedly')

    def systemStatusCallback(self, client, userdata, msg):
        '''Invoked when an MQTT message with topic system/status is received'''
        # Expected Payloads are...
            # Starting_Real-Run
            # Starting_Full-Sim
            # Starting_Quick-Sim
            # Real-Run
            # Quick-Sim
            # Full-Sim
            # Stopped
        msg.payload = msg.payload.decode()

        # For debuigging purposes, the origin of the message is included in the payload
            # This split removes the origin so the status can be handled
        self.systemStatus = msg.payload.split('/')[0]

        print('statusCallback', self.systemStatus)

        if self.systemStatus == 'Starting_Real-Run':
            self.mqttClient.publish(
                'system/status', 'Real-Run/_mesBackend/systemStatusCallback', retain=True)
        elif self.systemStatus == 'Starting_Full-Simulation':
            self.mqttClient.publish(
                'system/status', 'Full-Simulation/_mesBackend/systemStatusCallback', retain=True)
        elif self.systemStatus == 'Starting_Quick-Simulation':
            self.mqttClient.publish(
                'system/status', 'Quick-Simulation/_mesBackend/systemStatusCallback', retain=True)
        elif self.systemStatus == 'Real-Run' or self.systemStatus == 'Full-Simulation' or self.systemStatus == 'Quick-Simulation':
            # If the system is already running, simulating, or quick simulating
                # don't do anything (pass)
            pass 
        elif self.systemStatus == 'Stopped':
            # Setting self.quit to true will stop the exection of this file
                # and close the screen session it is running in
            self.quit = True

    def queueCallback(self, client, userdata, msg):
        # In the web-based user interface, the user chooses to 
            # "Open the Process Queue"
            # Enter uinteger quantities for each process
            # Check their selection
            # The contents of that field become self.operationQueue
                # It is a JSON dictionary
        #SEE APPENDIX OF THIS CODE FOR AN EXAMPLE OF self.operationQueue
        if self.systemStatus == 'Starting_Real-Run' or self.systemStatus == 'Starting_Full-Simulation' or self.systemStatus == 'Starting_Quick-Simulation':
            self.operationQueue = json.loads(
                msg.payload, object_pairs_hook=OrderedDict)
            if self.operationQueue == OrderedDict() or self.operationQueue == None:
                # If the user tries to enter a running mode before queuing processes
                    # the backend will automatically exit the execution
                    # by sending a stop message to the rest of the system
                self.mqttClient.publish(
                    'system/status', 'Stopped/_mesBackend.py', retain=True)

    def checkProcessStatus(self):
        self.mqttClient.publish('debug/startup',self.nextStartupPriority)
        self.mqttClient.publish('debug/screensDictionary',
                                json.dumps(self.screenChecklist, indent=4), retain=True)
        '''Executes at the frequency defined by the schedule in the init function'''
        # The process queue is updated in real time
            # this information can be used for debugging
            # it appears on the fmc overview page as a JSON 
        #SEE APPENDIX OF THIS CODE FOR AN EXAMPLE OF self.operationQueue

        self.mqttClient.publish('system/processQueue',
            json.dumps(self.operationQueue, indent=4), retain=True)

        # self.mqttClient.publish('debug', str(self.operationQueue))
        
        # This try block iterates over all of the queued processes in self.operationQueue
            # The first complete:false child process for each parent process
                # is started and marked as running
            # When the child process is complete, the next child is executed
        try:
            if self.systemStatus == 'Real-Run' or \
                self.systemStatus == "Full-Simulation" or \
                self.systemStatus == "Quick-Simulation":

                # If this list isn't empty at the end of this try statement
                    # There are complete:Running or complete:false children
                    # the code will continue iterating until all child processes are complete 
                        # the "status of the queue" is an empty list
                statusQueue = [] #status of the queue

                #for processA.txt, processB.txt
                for process in self.operationQueue['Queued Processes']:
                    
                    #for processA_1of2, processB_1of2, processA_2of2, processB_2of2
                    for operation in self.operationQueue['Queued Processes'][process]:

                        #False, 'Running', or True
                        operationCompletionStatus = self.operationQueue[
                            'Queued Processes'][process][operation]['complete']

                        
                        #split the 'processA_1of2' into ['processA','1of2'] and collect 'processA'
                            #split '1of2' into ['1','2'] and collect the quantity '2'
                            #concatinate it back into the name of the operation that has priority
                        operationWithPriority = operation.split('_')[0] + '_1of' + operation.split('_')[1].split('of')[1] #string

                        #Only parts with value of '1' will have the fields
                            # 'StartupTasksComplete'
                            # 'Startup Priority'
                        if operation == operationWithPriority:
                            # print('\n\n\nFound operation with priority: ' + operation)
                            #True or False
                            operationStartupTasksComplete = \
                                self.operationQueue['Queued Processes'][process][operation]['StartupTasksComplete']
                            # print('StartupStatus:', operationStartupTasksComplete)
                            #A number assigned by the user
                            operationStartupPriority = \
                                self.operationQueue['Queued Processes'][process][operation]['Startup Priority']
                            # print('StartupPriority: ', operationStartupPriority)
                            # print('Next StartupPriority: ', self.nextStartupPriority)

                            if operationCompletionStatus == False and operationStartupPriority == self.nextStartupPriority:
                                #If false, the child process hasn't even been started
                                    # the process will be started in a new screen
                                    # the child process will be marked as "Running"
                                statusQueue.append(operation)
                                
                                # Create a completely unique name for the screen
                                    # comprised of the child process name and run ID
                                    # Ex. AconveyorRosieEdie_2of3~admin-20200803-112302-FullSim
                                    # The sessionName is so awfully complex to prevent
                                        # process reports from being overwritten
                                screenSessionName = operation+'~'+self.operationQueue['Run Identifier']
                                screenPythonFile = '_mesProcess.py'
                                _mesScreen.bashSession(
                                    self.debugOption, sessionName = screenSessionName, pythonFile = screenPythonFile)
                                
                                # Change the child process completion status to "Running"
                                self.operationQueue['Queued Processes'][process][operation]['complete'] = \
                                    'Running'

                                # Break the for loop at the first running child process
                                    # This stops multiple children from executing simultaneously                            
                                break #break the operation loop

                            elif operationCompletionStatus == 'Running':
                                # append to the list so the execution continues
                                statusQueue.append(operation)
                                # Break the for loop at the first running child process
                                    # This stops multiple children from executing simultaneously
                                if operationStartupTasksComplete == True:
                                    self.nextStartupPriority = self.operationQueue['Queued Processes'][process][operation]['Startup Priority'] + 1
                                break #break the operation loop

                            elif operationCompletionStatus == True:
                                # If the child is complete, skip it until the next 
                                # complete:running or complete:false child process is founnd
                                # or until all processes are complete
                                pass
                        
                        elif operation != operationWithPriority and \
                            self.operationQueue['Queued Processes'][process][operationWithPriority]['StartupTasksComplete']==True:
                            if operationCompletionStatus == False:
                                    #If false, the child process hasn't even been started
                                        # the process will be started in a new screen
                                        # the child process will be marked as "Running"
                                    statusQueue.append(operation)
                                    
                                    # Create a completely unique name for the screen
                                        # comprised of the child process name and run ID
                                        # Ex. AconveyorRosieEdie_2of3~admin-20200803-112302-FullSim
                                        # The sessionName is so awfully complex to prevent
                                            # process reports from being overwritten
                                    screenSessionName = operation+'~'+self.operationQueue['Run Identifier']
                                    screenPythonFile = '_mesProcess.py'
                                    _mesScreen.bashSession(
                                        self.debugOption, sessionName = screenSessionName, pythonFile = screenPythonFile)
                                    
                                    # Change the child process completion status to "Running"
                                    self.operationQueue['Queued Processes'][process][operation]['complete'] = \
                                        'Running'

                                    # Break the for loop at the first running child process
                                        # This stops multiple children from executing simultaneously                            
                                    break

                            elif operationCompletionStatus == 'Running':
                                # append to the list so the execution continues
                                statusQueue.append(operationCompletionStatus)
                                # Break the for loop at the first running child process
                                    # This stops multiple children from executing simultaneously
                                break

                            elif operationCompletionStatus == True:
                                # If the child is complete, skip it until the next 
                                # complete:running or complete:false child process is founnd
                                # or until all processes are complete
                                pass

                # If the "status of the queue" is empty, all child processes have completed execution
                if statusQueue == []:
                    self.mqttClient.publish(
                        'system/status', 'Stopped/_mesBackend', retain=True)
                    # At the end of execution, the process queue is cleared
                    self.mqttClient.publish(
                        'system/processQueue', json.dumps(None), retain=True)
        except Error as e:
            # faultMessage = 'Failed to execute self.checkProcessStatus. The encoded processes dict may be empty.'
            # print('\n', faultMessage, '\n')
            # print(sys.exc_info()[0])
            self.mqttClient.publish('system/fault/_mesBackend', json.dumps(e))
            self.mqttClient.publish('system/status', 'Stopped/_mesBackend', retain=True)

    # The backend doesn't control the end of the process
        # when a process is done, it sends a message to the backend
        # the backend processes that message in this callback function
    def endProcess(self, client, userdata, msg):
        msg = msg.topic.split('/')
        process = msg[-2:-1][0]+'.txt'
        operation = msg[-1:][0]
        operation = msg[-2:-1][0] + '_' + operation
        self.operationQueue['Queued Processes'][process][operation]['complete'] = \
            True
            
    def startupCallback(self, client, userdata, msg):
        print('StartupCallback')
        try:
            topic = msg.topic.split('/')
            # print(topic)
            operation = str(msg.payload.decode()) + "_" + topic[4]
            process = str(msg.payload.decode()) + ".txt"
            # print('process',process)
            # print('operation',operation)
            # print(json.dumps(self.operationQueue, indent=4))
            try:
                # self.operationQueue['Queued Processes'][process][operation]['StartupTasksComplete']
                self.operationQueue['Queued Processes'][process][operation]['StartupTasksComplete'] = True
                print('Successfuly set startup tasks to complete!')
            except:
                print('Failed to set startup tasks to complete!')
                pass #this is not a startup process
            self.mqttClient.publish('system/processQueue',
                                json.dumps(self.operationQueue, indent=4), retain=True)
            # print('Success')
        except Exception as e:
            print(e)
            # pass

    def screenStartupCallback(self, client, userdata, msg):
        # print('screenStartupCallback')
        msg = str(msg.payload.decode())
        # self.mqttClient.publish('debug/msgpayload', msg)
        try:
            self.screenChecklist[msg] = True
            print(self.screenChecklist)
        except Exception as e:
            print(e)

    def loopMain(self):
        while not self.quit:
        # while True:
            schedule.run_pending()
            self.mqttClient.loop(0.1)
        sys.exit(0)
        # while True: #not self.quit:
        #     schedule.run_pending()
        #     self.mqttClient.loop(0.1)

if __name__ == '__main__':
    backend = mesBackend()

# --------------
# // APPENDIX //
# --------------


# This is an example of self.operationQueue
    # Take note of the unique run indentifier
        # it contains the user, timestamp, and execution type
    # The "complete" key in these dictionaries can be...
         # false
         # "Running"
         # true
    # Notice, the dictionary is nested as...
        # Queued Processes >>> 
            # Parents Processes >>> 
                # Child Processes >>>
                    # Completion Status
'''
{
    "Run Identifier": "admin-20210201-171824",
    "Queued Processes": {
        "ACordganizerLid.txt": {
            "ACordganizerLid_1of2": {
                "Startup Priority": 1,
                "complete": false,
                "StartupTasksComplete": false,
                "operationNumber": 1
            },
            "ACordganizerLid_2of2": {
                "complete": false,
                "operationNumber": 2
            }
        },
        "BCordganizerBody.txt": {
            "BCordganizerBody_1of2": {
                "Startup Priority": 2,
                "complete": false,
                "StartupTasksComplete": false,
                "operationNumber": 1
            },
            "BCordganizerBody_2of2": {
                "complete": false,
                "operationNumber": 2
            }
        }
    }
}
'''