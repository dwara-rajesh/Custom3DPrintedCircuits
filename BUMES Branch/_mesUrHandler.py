import paho.mqtt.client as mqtt
import time
import socket
import schedule
import json
from collections import OrderedDict
from helpers import error, warning, success
import sys
from mysql.connector import connect, Error

class urHandler:
    def __init__(self):
        print('URHANDLER IS ALIVE')

        # Used to parse command responses and determine response success status
        self.responses = {
            'safetymode' : {
                'response' : {
                    'Safetymode: ' : 'success'
                },
                'NORMAL' : 'normal',
                'REDUCED' : '',
                'PROTECTIVE_STOP' : 'protective',
                'RECOVERY' : '',
                'SAFEGUARD_STOP' : '',
                'SYSTEM_EMERGENCY_STOP' : 'emergency',
                'ROBOT_EMERGENCY_STOP' : '',
                'VIOLATION' : '',
                'FAULT' : ''
            },
            'unlock protective stop' : {
                'response' : {
                    'Protective stop releasing' : 'success',
                    'Cannot unlock protective stop until 5s after occurrence. Always inspect cause of protective stop before unlocking' : 'fail'
                }
            },
            'play' : {
                'response' : {
                    'Starting program' : 'success',
                    'Failed to execute: ' : 'fail'
                }
            },
            'stop' : {
                'response' : {
                    'Stopped' : 'success',
                    'Failed to execute: ' : 'fail'
                }
            },
            'load' : {
                'response' : {
                    'Loading program: ' : 'success',
                    'File not found: ' : 'fail',
                    'Error while loading program: ' : 'fail'
                }
            },
            'get loaded program' : {
                'response' : {
                    'Loaded program: ' : 'success',
                    'No program loaded' : 'fail'
                }
            },
            'running' : {
                'response' : {
                    'Program running: ' : 'success'
                }
            }
        }

        self.quit = False
        self.debugMode = False
        self.retainedValues = {}
        self.initMQTT()

        # Connect to the database
        self.db_connect()

        # Arg parsing for debugging mode:
        # If debugging mode is enabled, copy sys.stdout content to .txt file in ./debug
        if len(sys.argv) > 1:
            if '-d' in sys.argv:
                debugFilename = './debug/UrHandler.txt'
                self.debugMode = True
                sys.stdout = open(debugFilename, 'w')

        # self.mqttClient.publish('screenStartup', "urHandler", retain=True)
        schedule.every(1).seconds.do(self.checkIfRunning)

        update_screens_table_query = "UPDATE screens SET active = True WHERE name = 'urHandler'"
        self.cursor.execute(update_screens_table_query)
        self.connection.commit()
    
        # schedule.every(1).seconds.do(self.mqttClient.publish('screenStartup', 'urHandler', retain=True))
        self.loop()

    def initMQTT(self):
        self.mqttClient = mqtt.Client()
        self.mqttClient.on_connect = self.onConnect
        self.mqttClient.message_callback_add(
            'system/status', self.systemStatusCallback)
        self.mqttClient.message_callback_add(
            'system/resources', self.getResources)
        self.mqttClient.message_callback_add(
            'urHandler/request/#', self.dashboardRequest)
        self.mqttClient.message_callback_add('fault/resolution/urHandler/+',self.faultCallback)
        self.mqttClient.connect('localhost', 1883)

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
                
        # Why three cursors 0,0
        self.cursor = self.connection.cursor()
        print("Database connection successful")
        # self.cursor1 = self.connection.cursor(buffered = True)
        # self.cursor2 = self.connection.cursor()
        # self.cursor.execute(select_process_query)
        # result = self.cursor.fetchall()
        # for row in result:
        #     self.mqttClient.publish('debug', str(row))

    def getResources(self, client, userdata, msg):
        # print('GET RESOURCES CALLBACK')
        self.resources = json.loads(msg.payload.decode(),object_pairs_hook=OrderedDict)
        for resource in self.resources:
            if self.resources[resource]['type'] == 'Robot':
                self.retainedValues[resource] = self.resources[resource] #keep the contents of resource config if the resource is a robot
                self.retainedValues[resource]['isRunning'] = False #add an additional key 
                self.retainedValues[resource]['safetyMode'] = '' #default safety mode is 'NORMAL'
                self.retainedValues[resource]['programStarted'] = False #add an additioanl key
                self.retainedValues[resource]['mqttTopic'] = ''
                self.retainedValues[resource]['requestID'] = 0
                self.retainedValues[resource]['taskID'] = 0
        # print(self.retainedValues)

    def onConnect(self, client, userdate, flags, rc):
        self.mqttClient.subscribe('system/#')
        self.mqttClient.subscribe('urHandler/#')
        self.mqttClient.subscribe('fault/resolution/urHandler/+')

    def systemStatusCallback(self, client, userdata, msg):
        # print(msg.payload.decode())
        msg.payload = msg.payload.decode()
        if msg.payload.split('/')[0] == 'Stopped':
            self.quit = True

        if msg.payload.split('/')[0] == 'KillAll':
            for robot in self.retainedValues:
                self.dashboardCommand('stop', self.retainedValues[robot]['identifier'])
            self.quit = True


    #  Returns final parsed response (str) and response success status (bool)
    def dashboardCommand(self, command, robotAddress, argument = None):
        # print('Dashboard Command',command,robotAddress,argument)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.connect((robotAddress, 29999))
            connectionResponse = s.recv(2048).decode() # Connected Response
            # print(connectionResponse)
            originalCommand = command
            if command == 'load':
                command = command + ' ' + argument
            command = command + '\n'
            # print('Sending command: ' + originalCommand) # For debugging
            s.send(command.encode())

            # print(s.recv(2048).decode())

            # Separates the response message
            response = s.recv(2048).decode()
            s.close()
            print(response.split('\n')[0])
            try:
                responseTypes = self.responses[originalCommand]['response']
                for responseType in responseTypes:
                    if responseType in response:
                        try:
                            responseStatus = responseTypes[responseType] # Should be either 'success' or 'fail'
                            responseSuccess = True if responseStatus == 'success' else False
                            response = response.split(responseType)
                            finalResponse = response[1].split('\n')[0]
                            return finalResponse, responseSuccess
                            pass
                        except:
                            print('Error while splitting response. Verify that response type is included in dictionary.')
            except:
                print('Key Error! Verify the command and try again.')
                pass
    
    # Here we define the different fault resolution methods for robots
    def faultCallback(self, client, userdata, msg):
        print(msg.topic)
        msg.payload = msg.payload.decode()
        robot = msg.topic.split('/')[-1]
        print('ROBOT',robot)
        if msg.payload == 'manual':
            print('\nPROGRAM COMPLETED MANUALLY AFTER FAULT - Robot ' + robot + '\n')
            self.retainedValues[robot]['isRunning'] = False
            self.retainedValues[robot]['requestID'] = ''

            update_task_complete_process_query = "UPDATE process_handler SET task_complete = True, end_time = " + \
                str(time.time()) + " WHERE id = " + str(self.retainedValues[robot]['taskID'])
            self.cursor.execute(update_task_complete_process_query)
            self.connection.commit()

            if self.debugMode == False:
                delete_record_handler_query = "DELETE FROM handler_requests WHERE handler = 'urHandler' AND id = " + str(self.retainedValues[robot]['requestID'])
                self.cursor.execute(delete_record_handler_query)
                self.connection.commit()

            print('Request set to finished (MANUAL FAULT RESOLUTION) for robot mqtt topic: ' + self.retainedValues[robot]['mqttTopic'])

        # if msg.payload == 'automatic':
        #     # SEND CONTINUE RUNNING HERE

        # self.retainedValues[robot]['isRunning'] = True


#DO NOT DELETE
    # def checkSafetyMode(robot):
    #     safetymode = dashboardCommand('safetymode', robot['ip'])
    #     if safetymode == 'PROTECTIVE_STOP':
    #         print('Robot is in PROTECTIVE STOP')
    #         handleProtectiveStop(robot)
    #     if safetymode == 'NORMAL':
    #         print('Safety mode is normal')

    def checkIfRunning(self):
        for robot in self.retainedValues:
            #We expect the 'running\n' command to return 'true' when the program is running.
            #However, on startup, the first 'running\n' command sometimes returns 'False'. 
            #Because 'running\n' is 'false,' we cannot be sure if the program has yet to start -or- if the program has finished execution
            #To make sure the program has started, we wait for the first 'running\n' is 'true'.
            #After receiving 'running\n' is 'true' the first time, we set 'programStarted' to True 
            #   because we are confident the program has _actually_ started.
            if self.retainedValues[robot]['isRunning'] == True:
                print('CHECK IF RUNNING',time.time(),robot,self.retainedValues[robot]['identifier'],self.retainedValues[robot]['isRunning'])
                currentRunningState, responseSuccess = self.dashboardCommand('running',self.retainedValues[robot]['identifier'])
                currentSafteyModeState, responseSuccess = self.dashboardCommand('safetymode',self.retainedValues[robot]['identifier'])
                if currentSafteyModeState == 'NORMAL':
                    if currentRunningState == 'true':
                        self.retainedValues[robot]['isRunning'] = True
                        self.retainedValues[robot]['programStarted'] = True

                        update_task_executing_handler_query = "UPDATE handler_requests SET task_executing = True WHERE id = " + str(self.retainedValues[robot]['requestID'])
                        self.cursor.execute(update_task_executing_handler_query)
                        self.connection.commit()

                    elif currentRunningState=='false' and self.retainedValues[robot]['programStarted'] == True:
                        print('\nPROGRAM COMPLETE - Robot ' + robot + '\n')
                        # time.sleep(2)
                        self.retainedValues[robot]['isRunning'] = False
                        self.retainedValues[robot]['requestID'] = ''

                        update_task_complete_process_query = "UPDATE process_handler SET task_complete = True, end_time = " + \
                            str(time.time()) + " WHERE id = " + str(self.retainedValues[robot]['taskID'])
                        self.cursor.execute(update_task_complete_process_query)
                        self.connection.commit()

                        if self.debugMode == False:
                            delete_record_handler_query = "DELETE FROM handler_requests WHERE handler = 'urHandler' AND id = " + str(self.retainedValues[robot]['requestID'])
                            self.cursor.execute(delete_record_handler_query)
                            self.connection.commit()

                        # self.mqttClient.publish(self.retainedValues[robot]['mqttTopic'],'SUCCESS')
                        print('Sent SUCCESS message to topic: ' + self.retainedValues[robot]['mqttTopic'])
                elif currentSafteyModeState != 'NORMAL':

                    self.retainedValues[robot]['isRunning'] = 'fault'
                    self.mqttClient.publish('fault/message/urHandler/'+robot, currentSafteyModeState) #fault/resolution

            # self.retainedValues[robot]['safetyMode'] = \
            #     'fault' if self.dashboardCommand('safetymode',self.retainedValues[robot]['identifier']) != 'NORMAL' else 'normal'
            # print('SAFETYMODE',robot,self.retainedValues[robot]['safetyMode'])

    def dashboardRequest(self, client, userdate, msg):
        print(self.retainedValues)
        # msg.payload = msg.payload.decode().split('~')
        # print(msg.topic, msg.payload)
        # robot = msg.payload[0]
        # urpFile = msg.payload[1]

        select_data_handler_query = "SELECT * FROM handler_requests WHERE handler = 'urHandler' AND received = False"
        self.cursor.execute(select_data_handler_query)
        result = self.cursor.fetchall()

        print(result)
        for row in result:
            if len(result) == 1:
                result = result[0]
            robot = result[5]
            urpFile = result[6]
            self.retainedValues[robot]['requestID'] = result[0]
            self.retainedValues[robot]['taskID'] = result[9]

            update_received_handler_query = "UPDATE handler_requests SET received = True WHERE id = " + str(self.retainedValues[robot]['requestID'])
            self.cursor.execute(update_received_handler_query)
            self.connection.commit()

            print('Received request. ROBOT: ' + robot + '; FILE: ' + urpFile)
        # print('Topic Received was ' + msg.topic)

            # Try loading
            loadResponse, loadSuccess = self.dashboardCommand('load',self.retainedValues[robot]['identifier'],urpFile)
            if not loadSuccess:
                safetyMsg = 'SAFETY STOP - Couldn\'t load file!\nRobot file \'' + urpFile + '\'\nOn robot: ' + robot.upper() + '\nCheck process file for URP filename syntax errors'
                # CRASH THE SYSTEM HERE - Couldn't load file
                print(safetyMsg)
                self.mqttClient.publish('system/status', 'Stopped/urHandler', retain=True)
                self.mqttClient.publish('system/processQueue', safetyMsg, retain=True)
                
            elif loadSuccess:
                # Try playing
                playResponse, playSuccess = self.dashboardCommand('play',self.retainedValues[robot]['identifier'])
                if not playSuccess:
                    safetyMsg = 'SAFETY STOP - Failed to play!\nRobot file \'' + urpFile + '\'\nOn robot: ' + robot.upper() + '\nCheck robot position or perform homing sequence'
                    # CRASH THE SYSTEM HERE - Failed to play
                    print(safetyMsg)
                    self.mqttClient.publish('system/status', 'Stopped/urHandler', retain=True)
                    self.mqttClient.publish('system/processQueue', safetyMsg, retain=True)
                elif playSuccess:
                    self.retainedValues[robot]['mqttTopic'] = msg.topic.replace('request','outcome')
                    print('Setting this outcome topic to ' + self.retainedValues[robot]['mqttTopic'])
                    self.retainedValues[robot]['isRunning'] = True
                    self.retainedValues[robot]['programStarted'] = False

    def loop(self):
        while self.quit != True:
        # while True:
            # self.mqttClient.publish('screenStartup', "urHandler", retain=True)
            schedule.run_pending()
            self.mqttClient.loop(0.1)
        sys.exit(0)
            
        sys.exit(0)

urHandler = urHandler()
