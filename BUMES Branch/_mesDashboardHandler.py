import paho.mqtt.client as mqtt
import time
import json
import schedule
import re
from collections import OrderedDict
from helpers import error, warning, success, blue
from mysql.connector import connect, Error
import sys

# ----- MES Dashboard Handler ------ #
# Manages FrontEnd Data Visualizations


class dashboardHandler:
    def __init__(self):
        print('DASHBOARD HANDLER HAS JOINED THE TEAM')

        self.quit = False
        self.retainedProcessQueue = {}
        self.retainedTasks = {}
        self.internalProcessQueue = {
            'operationsQty' : {
                'doneOperations' : {},
                'runningOperations' : {},
                'queuedOperations' : {}
            },
            'processesQty' : {
                'doneProcesses' : {},
                'runningProcesses' : {},
                'queuedProcesses' : {}
            },
            'processes' : {

            }
        } # Used only within processQueueUpdate() to calculate values
        self.internalTasks = {
            'tasksQty' : {
                'doneTasks' : {},
                'runningTasks' : {},
                'queuedTasks' : {}
            },
            'processes' : {

            }
        } # Used only within processQueueUpdate() to calculate values
        self.count = 0 # Process Queue Updated Count during run
        self.countReceived = 0 # Process Queue Received Count during run

        # Connect to the database
        self.db_connect()

        self.initMQTT()

        # Arg parsing for debugging mode:
        # If debugging mode is enabled, copy sys.stdout content to .txt file in ./debug
        if len(sys.argv) > 1:
            if '-d' in sys.argv:
                debugFilename = './debug/dashboardHandler.txt'
                sys.stdout = open(debugFilename, 'w')

        self.connection.commit()
        update_screens_table_query = "UPDATE screens SET active = True WHERE name = 'dashboardHandler'"
        self.cursor.execute(update_screens_table_query)
        self.connection.commit()

        self.loop()

    # Connects to Database
    def db_connect(self):
        select_process_query = 'SELECT * FROM process_handler'

        '''
        IMPORTANT:
        You may need to run a SQL command in order to connect to the mySQL database from a detached screen. The command is:

        ALTER USER 'yourusername'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yourpassword';

        Source: https://stackoverflow.com/questions/49194719/authentication-plugin-caching-sha2-password-cannot-be-loaded
        '''

        # Move this to a config file
        self.connection = connect(
            host="localhost",
            user='root',
            password='buADML@2021',
            database="bumes",
        )
                
        self.cursor = self.connection.cursor()
        self.cursor1 = self.connection.cursor()

        success('CONNECTED TO OUR DATABASE')

    # ----- LOCAL MQTT ------ #
    def initMQTT(self):
        self.mqttClient = mqtt.Client()
        self.mqttClient.on_connect = self.onConnect

        # Functions to be executed go here
        # self.mqttClient.message_callback_add('topic', self.functionName)
        self.mqttClient.message_callback_add('system/status', self.systemStatusCallback)
        self.mqttClient.message_callback_add('system/processQueue', self.getProcessQueue)
        # self.mqttClient.message_callback_add('tasks/#', self.getTasks)
        self.mqttClient.message_callback_add('dashboardHandler/updateTasks', self.getTasks) # This is the MQTT flag

        try:
            self.mqttClient.connect('localhost', 1883)
        except Exception as e:
            error('Failed to connect to MQTT Server')
            error(e)
            sys.exit(0)

    def onConnect(self, client, userdata, flags, rc):
        self.mqttClient.subscribe('system/#')
        # self.mqttClient.subscribe('tasks/#')
        self.mqttClient.subscribe('dashboardHandler/updateTasks')
        success('CONNECTED TO OUR VERY OWN MQTT SERVER')

    def systemStatusCallback(self, client, userdata, msg):
        msg.payload = msg.payload.decode()
        if msg.payload.split('/')[0] == 'Stopped':
            self.quit = True

    def getProcessQueue(self, client, userdata, msg):
        processQueue = json.loads(msg.payload.decode())
        self.countReceived += 1
        # print('RECEIVED ' + str(self.countReceived) + ' times')
        if processQueue == None:
            # print('Received NONE')
            self.count = 0
            self.countReceived = 0
            self.retainedProcessQueue = {}
            # self.retainedTasks = {} # May be the cause of not finishing everything
        elif self.retainedProcessQueue != processQueue:
            if self.retainedProcessQueue == {}:
                firstTime = True
            elif processQueue['Run Identifier'] != self.retainedProcessQueue['Run Identifier']:
                self.count = 0
                self.countReceived = 0
                firstTime = True
                # print('Process Queue Changed')
            else:
                firstTime = False
            
            self.retainedProcessQueue = processQueue
            self.count += 1
            # print('UPDATED ' + str(self.count) + ' times')
            #print(self.retainedProcessQueue)
            self.processQueueUpdate() # Update the Internal Process Queue
            if firstTime:
                self.initDashboard()
                self.createTasks() # Create Tasks if first time
                self.tasksUpdate()
            self.publishData() # Publish Data ( Runs every time Process Queue is updated )
        else:
            pass
            # print('Process Queue was the same!')
        # Get process queue
        # Runs when process queue is published to its topic from backend
        # Compare it with the last one received (if not first)
        # Update process queue dots data only if necessary to reduce dots usage
        # Store the process queue for next checking

    # Runs on flag from _mesProcess
    def getTasks(self, client, userdata, msg):
        # warning('TASKS: Got Flag')
        getTasksQuery = 'SELECT * FROM process_handler'
        self.cursor.execute(getTasksQuery)
        result = self.cursor.fetchall()

        # Empty received operations tasks from self.internalTasks
        # Other operations' tasks are kept from createTasks
        for process in self.retainedProcessQueue['Queued Processes']:
            thisProcessName = process.split('.txt')[0]
            for operation in self.retainedProcessQueue['Queued Processes'][process]:
                if operation in [row[2] for row in result]: # Checks if the operation exists in the list of different operations
                    self.retainedTasks[thisProcessName][operation] = {}

        for row in result:
            # print(str(row))
            processName = row[1]
            operationName = row[2]
            taskName = row[3]
            taskComplete = row[4]
            taskExecuting = row[7]
            taskStarttime = row[8]
            taskEndtime = row[9]
            taskCommand = row[10]

            thisTaskStuff = {
                'command': taskCommand,
                'complete': taskComplete,
                'executing': taskExecuting,
                'startTime': taskStarttime,
                'endTime': taskEndtime
            }

            self.retainedTasks[processName][operationName][taskName] = thisTaskStuff

        # print(json.dumps(self.retainedTasks, indent=4))
        self.connection.commit()
        # success('End this getTasks, passing to tasksUpdate')
        self.tasksUpdate() # Update the Internal Tasks

        # Get tasks
        # Runs when tasks is published from its topic from process handler
        # Compare them with the last one received
        # Verify if they have changed
        # Update dots only if necesarry
        # Store tasks for next checking

    # This runs when a process queue is received for the first time
    def createTasks(self):
        user = self.retainedProcessQueue['Run Identifier'].split('-')[0]
        queuedProcesses = self.retainedProcessQueue['Queued Processes']
        for process in queuedProcesses:
            thisProcessName = process.split('.txt')[0] # Gets process name without .txt
            self.retainedTasks[thisProcessName] = {}
            processFileLocation = '_mesProcessFiles/' + user + '/' + process
            with open(processFileLocation, 'r') as processFile:
                theseTasks = {}  # Empty dictionary
                taskNumber = 1 #starting 
                for task in processFile:
                    task = task.strip() #remove leading and trailing whitespace
                    if task == '\n' or task =='':
                        # warning('Passing task because of empty line')
                        continue # exclude empty lines, move to the next iteration
                    elif task.startswith('//'):
                        # warning('Passing task because of full comment')
                        continue # exclude comments, next loop iteration
                    else:
                        try:
                            task = task.split('//')[0] # remove inline comments
                        except: 
                            pass # no inline comments, do nothing
                        task = task.strip() # remove leading or trailing whitespace left by the comment

                    # print(task)

                    # ----- TO DO ----- #
                    # Add functionality for creating ready for assembly task
                    if task.find('readyForAssembly') != -1:
                        assemblyArguments = re.split('\(|\)',task)[-2]
                        assemblyArguments = assemblyArguments.replace("'",'').split(',')
                        theseTasks = self.readyForAssembly(taskNumber, assemblyArguments, theseTasks)
                    else:
                        theseTasks['task_'+str(taskNumber)] = OrderedDict()
                        theseTasks['task_'+str(taskNumber)]['command'] = [task.replace('\n', '')][0]
                        theseTasks['task_'+str(taskNumber)]['complete'] = False
                        theseTasks['task_'+str(taskNumber)]['executing'] = False
                        theseTasks['task_'+str(taskNumber)]['startTime'] = None
                        theseTasks['task_'+str(taskNumber)]['endTime'] = None
                    taskNumber += 1
                theseTasks['task_'+str(taskNumber)] = OrderedDict()
                theseTasks['task_'+str(taskNumber)]['command'] = "endProcess()"
                theseTasks['task_'+str(taskNumber)]['complete'] = False
                theseTasks['task_'+str(taskNumber)]['executing'] = False
                theseTasks['task_'+str(taskNumber)]['startTime'] = None
                theseTasks['task_'+str(taskNumber)]['endTime'] = None
            processFile.close()

            queuedOperations = self.retainedProcessQueue['Queued Processes'][process]
            for operation in queuedOperations:
                thisOperationName = operation.split('_')[1] # Gets '1of1'
                self.retainedTasks[thisProcessName][thisOperationName] = {}
                self.retainedTasks[thisProcessName][thisOperationName] = theseTasks
            
            
        # success('CREATED TASKS')
        # print(json.dumps(self.retainedTasks, indent=4))
            
        # Creates tasks dictionary when process queue is received
        # Executed even before process queue sends tasks, since it does when the process actually starts (could be mid-run)
        # Gets user from run identifier in process queue
        # "Run Identifier": "public-20201014-092638-FullSim"
        # Uses same method as process handler to create tasks dictionaries


    def readyForAssembly(self, taskNumber, assemblyArguments, operationTasklist):
        primaryProcess = assemblyArguments[0]
        secondaryProcess = assemblyArguments[1]
        assemblyStep = assemblyArguments[2]
        if assemblyStep == 'initializeAssembly':
            operationTasklist['task_'+str(taskNumber)] = OrderedDict()
            operationTasklist['task_'+str(taskNumber)]['notes'] = 'readyForAssemblyMacro-initializeAssembly'
            operationTasklist['task_'+str(taskNumber)]['command'] = "resourceSeize('" + primaryProcess + "')"
            operationTasklist['task_'+str(taskNumber)]['executing'] = False
            operationTasklist['task_'+str(taskNumber)]['complete'] = False
            operationTasklist['task_'+str(taskNumber)]['startTime'] = None
            operationTasklist['task_'+str(taskNumber)]['endTime'] = None
        elif assemblyStep == 'startAssembly':
            operationTasklist['task_'+str(taskNumber)+'.1'] = OrderedDict()
            operationTasklist['task_'+str(taskNumber)+'.1']['notes'] = 'readyForAssemblyMacro-startAssembly'
            operationTasklist['task_'+str(taskNumber)+'.1']['command'] = "resourceRelease('" + primaryProcess + "')"
            operationTasklist['task_'+str(taskNumber)+'.1']['executing'] = False
            operationTasklist['task_'+str(taskNumber)+'.1']['complete'] = False
            operationTasklist['task_'+str(taskNumber)+'.1']['startTime'] = None
            operationTasklist['task_'+str(taskNumber)+'.1']['endTime'] = None

            operationTasklist['task_'+str(taskNumber)+'.2'] = OrderedDict()
            operationTasklist['task_'+str(taskNumber)+'.2']['notes'] = 'readyForAssemblyMacro-startAssembly'
            operationTasklist['task_'+str(taskNumber)+'.2']['command'] = "resourceSeize('" + secondaryProcess + "')"
            operationTasklist['task_'+str(taskNumber)+'.2']['executing'] = False
            operationTasklist['task_'+str(taskNumber)+'.2']['complete'] = False
            operationTasklist['task_'+str(taskNumber)+'.2']['startTime'] = None
            operationTasklist['task_'+str(taskNumber)+'.2']['endTime'] = None

        elif assemblyStep == 'finishAssembly':
            operationTasklist['task_'+str(taskNumber)+'.1'] = OrderedDict()
            operationTasklist['task_'+str(taskNumber)+'.1']['notes'] = 'readyForAssemblyMacro-finishAssembly'
            operationTasklist['task_'+str(taskNumber)+'.1']['command'] = "resourceRelease('" + secondaryProcess + "')"
            operationTasklist['task_'+str(taskNumber)+'.1']['executing'] = False
            operationTasklist['task_'+str(taskNumber)+'.1']['complete'] = False
            operationTasklist['task_'+str(taskNumber)+'.1']['startTime'] = None
            operationTasklist['task_'+str(taskNumber)+'.1']['endTime'] = None

            operationTasklist['task_'+str(taskNumber)+'.2'] = OrderedDict()
            operationTasklist['task_'+str(taskNumber)+'.2']['notes'] = 'readyForAssemblyMacro-finishAssembly'
            operationTasklist['task_'+str(taskNumber)+'.2']['command'] = "resourceSeize('" + primaryProcess + "')"
            operationTasklist['task_'+str(taskNumber)+'.2']['executing'] = False
            operationTasklist['task_'+str(taskNumber)+'.2']['complete'] = False
            operationTasklist['task_'+str(taskNumber)+'.2']['startTime'] = None
            operationTasklist['task_'+str(taskNumber)+'.2']['endTime'] = None

            operationTasklist['task_'+str(taskNumber)+'.3'] = OrderedDict()
            operationTasklist['task_'+str(taskNumber)+'.3']['notes'] = 'readyForAssemblyMacro-finishAssembly'
            operationTasklist['task_'+str(taskNumber)+'.3']['command'] = "resourceRelease('" + primaryProcess + "')"
            operationTasklist['task_'+str(taskNumber)+'.3']['executing'] = False
            operationTasklist['task_'+str(taskNumber)+'.3']['complete'] = False
            operationTasklist['task_'+str(taskNumber)+'.3']['startTime'] = None
            operationTasklist['task_'+str(taskNumber)+'.3']['endTime'] = None
        
        return operationTasklist

    # This updates the internalProcessQueue dictionary with data from external process queue
    # Does not know anything about tasks, only about processes and operations
    # This data is then used in publishData function
    def processQueueUpdate(self):

        self.internalProcessQueue = {
            'operationsQty' : {
                'doneOperations' : {},
                'runningOperations' : {},
                'queuedOperations' : {}
            },
            'processesQty' : {
                'doneProcesses' : {},
                'runningProcesses' : {},
                'queuedProcesses' : {}
            },
            'processes' : {

            }
        }

        queuedProcesses = self.retainedProcessQueue['Queued Processes']

        
        for process in queuedProcesses:
            #print('Entered process loop')
            operations = queuedProcesses[process]

            self.internalProcessQueue['processes'][process] = {}
            self.internalProcessQueue['processes'][process]['doneOperations'] = {}
            self.internalProcessQueue['processes'][process]['runningOperations'] = {}
            self.internalProcessQueue['processes'][process]['queuedOperations'] = {}

            for operation in operations:
                operationStatus = operations[operation]['complete']

                if operationStatus == True:
                    self.internalProcessQueue['operationsQty']['doneOperations'][operation] = operations[operation]
                    self.internalProcessQueue['processes'][process]['doneOperations'][operation] = operations[operation]
                elif operationStatus == 'Running':
                    self.internalProcessQueue['operationsQty']['runningOperations'][operation] = operations[operation]
                    self.internalProcessQueue['processes'][process]['runningOperations'][operation] = operations[operation]
                else:
                    self.internalProcessQueue['operationsQty']['queuedOperations'][operation] = operations[operation]
                    self.internalProcessQueue['processes'][process]['queuedOperations'][operation] = operations[operation]

            processDoneOperations = len(self.internalProcessQueue['processes'][process]['doneOperations'])
            processRunningOperations = len(self.internalProcessQueue['processes'][process]['runningOperations'])
            processQueuedOperations = len(self.internalProcessQueue['processes'][process]['queuedOperations'])

            if (processRunningOperations + processQueuedOperations) == 0:
                self.internalProcessQueue['processesQty']['doneProcesses'][process] = queuedProcesses[process]
            elif processRunningOperations != 0:
                self.internalProcessQueue['processesQty']['runningProcesses'][process] = queuedProcesses[process]
            else:
                self.internalProcessQueue['processesQty']['queuedProcesses'][process] = queuedProcesses[process]

    # This populates the internalTasks dictionary with all the tasks received from the Database
    # Runs when an update flag is sent, commonly from _mesProcess when they update something in DB
    def tasksUpdate(self):
        # print('Updating tasks')
        self.internalTasks = {
            'tasksQty' : {
                'doneTasks' : {},
                'runningTasks' : {},
                'queuedTasks' : {}
            },
            'processes' : {

            }
        }

        queuedTasksByProcess = self.retainedTasks

        for process in queuedTasksByProcess:
            queuedTasksByOperations = self.retainedTasks[process]

            self.internalTasks['processes'][process] = {}

            for operation in queuedTasksByOperations:
                tasks = self.retainedTasks[process][operation]

                self.internalTasks['processes'][process][operation] = {
                    'doneTasks' : {},
                    'runningTasks' : {},
                    'queuedTasks' : {}
                }
                # self.internalTasks['processes'][process][operation]['doneTasks'] = {}
                # self.internalTasks['processes'][process][operation]['runningTasks'] = {}
                # self.internalTasks['processes'][process][operation]['queuedTasks'] = {}

                for task in tasks:
                    # taskStatus = tasks[task]['complete']
                    taskExecuting = tasks[task]['executing']
                    taskComplete = tasks[task]['complete']
                    uniqueTaskName = process + '/' + operation + '/' + task

                    if taskComplete == True: # Done
                        self.internalTasks['tasksQty']['doneTasks'][uniqueTaskName] = tasks[task]
                        self.internalTasks['processes'][process][operation]['doneTasks'][task] = tasks[task]
                    elif taskExecuting == True and taskComplete == False: # In Process
                        self.internalTasks['tasksQty']['runningTasks'][uniqueTaskName] = tasks[task]
                        self.internalTasks['processes'][process][operation]['runningTasks'][task] = tasks[task]
                    else: # Queued
                        self.internalTasks['tasksQty']['queuedTasks'][uniqueTaskName] = tasks[task]
                        self.internalTasks['processes'][process][operation]['queuedTasks'][task] = tasks[task]
                    # check if finished and add to internal tasks

        doneTasks = len(self.internalTasks['tasksQty']['doneTasks'])
        runningTasks = len(self.internalTasks['tasksQty']['runningTasks'])
        queuedTasks = len(self.internalTasks['tasksQty']['queuedTasks'])
        
        totalTasks = doneTasks + runningTasks + queuedTasks
        message = 'There are ' + str(doneTasks) + ' out of ' + str(totalTasks) + ' tasks done'
        # blue(message)
        # print(json.dumps(self.internalTasks, indent=4))
        self.publishData()

    def publishData(self):

        runIdentifier = self.retainedProcessQueue['Run Identifier']
        runIdentifier = runIdentifier.split('-')
        user = runIdentifier[0]
        try:
            mode = runIdentifier[3]
        except:
            mode = 'null'

        
        runDoneProcesses = len(self.internalProcessQueue['processesQty']['doneProcesses'])
        runRunningProcesses = len(self.internalProcessQueue['processesQty']['runningProcesses'])
        runQueuedProcesses = len(self.internalProcessQueue['processesQty']['queuedProcesses'])

        runDoneOperations = len(self.internalProcessQueue['operationsQty']['doneOperations'])
        runRunningOperations = len(self.internalProcessQueue['operationsQty']['runningOperations'])
        runQueuedOperations = len(self.internalProcessQueue['operationsQty']['queuedOperations'])

        runDoneTasks = len(self.internalTasks['tasksQty']['doneTasks'])
        runRunningTasks = len(self.internalTasks['tasksQty']['runningTasks'])
        runQueuedTasks = len(self.internalTasks['tasksQty']['queuedTasks'])

        runTotalProcesses = runDoneProcesses + runRunningProcesses + runQueuedProcesses
        runTotalOperations = runDoneOperations + runRunningOperations + runQueuedOperations
        runTotalTasks = runDoneTasks + runRunningTasks + runQueuedTasks

        #print(self.internalProcessQueue)

        #print('RunDoneOps', runDoneOperations)
        #print('RunDoneProc', runDoneProcesses)

        runStatus = int((runDoneTasks / runTotalTasks) * 100)
        processStatus = (runDoneProcesses / runTotalProcesses) * 100
        operationsStatus = (runDoneOperations / runTotalOperations) * 100

        # Last tasks aren't updated since the processes end before the tasks could be published again
        if operationsStatus == 100 and processStatus == 100:
            runStatus = 100
            runDoneTasks = runTotalTasks
            runRunningTasks = 0
            runQueuedTasks = 0

        payload = {
            'run-status' : {
                'value' : runStatus,
                'context' : {
                    'user' : user,
                    'mode' : mode
                }
            },
            'process-status' : {
                'value' : processStatus,
                'context' : {
                    'total-done' : runDoneProcesses,
                    'total-running' : runRunningProcesses,
                    'total-queued' : runQueuedProcesses,
                    'total-total' : runTotalProcesses
                }
            },
            'operations-status' : {
                'value' : operationsStatus,
                'context' : {
                    'total-done' : runDoneOperations,
                    'total-running' : runRunningOperations,
                    'total-queued' : runQueuedOperations,
                    'total-total' : runTotalOperations
                }
            },
            'tasks-status' : {
                'value' : runStatus,
                'context' : {
                    'total-done' : runDoneTasks,
                    'total-running' : runRunningTasks,
                    'total-queued' : runQueuedTasks,
                    'total-total' : runTotalTasks
                }
            }
        }

        payload = json.dumps(payload)

        #print(payload)

        self.mqttClient.publish('dashboardHandler/runStatus', runStatus)
        runStatusMsg = 'Run Status: ' + str(runStatus) + '%'
        taskStatusMsg = 'There are ' + str(runDoneTasks) + ' out of ' + str(runTotalTasks) + ' tasks done'
        print()
        success(runStatusMsg)
        blue(taskStatusMsg)
        # success('Published Data')

        # IDEA: Add Seized Resources/Inv Information

        # Percent done of every task / total of tasks
        # ** Preferably will use simulation time to better reflect the percent
        # i.e. cncRun will contribute the same to the runStatus being a single command, but it contributes a considerably
        # longer time, so it should be calculated with time weights eventually

    def updateImage(self, client, userdata, msg):
        # imageUrl = 'https://adml.azurewebsites.net/inspection-images/body.bmp'
        response = json.loads(msg.payload.decode())
        variableName = response['variable']
        variableValue = response['value']
        imageUrl = response['imageurl']
        imageDescription = variableName + '=' + variableValue
        payload = json.dumps({'inspection-image' : {'value' : 0, 'context' : {'imageurl' : imageUrl, 'imagedescription' : imageDescription}}})
        self.mqttUbiClient.publish(self.topic, payload)

    def initDashboard(self):
        pass
        # warning('Setting all data to ZERO or NULL!')
    #     # Set all data to zero or null
    #     # Executed before every run


    def loop(self):
        try:
            while self.quit != True:
                self.mqttClient.loop(0.1)
            print('DASHBOARD HANDLER OUT, MAY THE FORCE BE WITH YOU')
            sys.exit(0)
        except Exception as e:
            print(e)
            sys.exit(0)

        
dashboardHandler = dashboardHandler()


# Process Queue Example

# {
#     "Run Identifier": "public-20201014-092638-FullSim",
#     "Queued Processes": {
#         "axelWasHere.txt": {
#             "axelWasHere_1of6": {
#                 "complete": true
#             },
#             "axelWasHere_2of6": {
#                 "complete": true
#             },
#             "axelWasHere_3of6": {
#                 "complete": true
#             },
#             "axelWasHere_4of6": {
#                 "complete": true
#             },
#             "axelWasHere_5of6": {
#                 "complete": true
#             },
#             "axelWasHere_6of6": {
#                 "complete": true
#             }
#         }
#     }
# }
