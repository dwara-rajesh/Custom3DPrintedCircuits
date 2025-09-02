import paho.mqtt.client as mqtt
import time
import schedule
import json
from collections import OrderedDict
# import serial
import socket
from mysql.connector import connect, Error
import sys
import datetime

class plcHandler:
    def __init__(self):
        print('PLCHANDLER IS ALIVE')
        self.quit = False
        self.initMQTT()

        self.plcIP = '10.241.34.62'
        self.plcPort = 4001

        # Arg parsing for debugging mode:
        # If debugging mode is enabled, copy sys.stdout content to .txt file in ./debug
        if len(sys.argv) > 1:
            if '-d' in sys.argv:
                debugFilename = './debug/PLCHandler.txt'
                sys.stdout = open(debugFilename, 'w')
                print('Now printing to file!')

        self.db_connect()
        schedule.every(1).seconds.do(self.checkIfRunning)

        update_screens_table_query = "UPDATE screens SET active = True WHERE name = 'plcHandler'"
        self.cursor.execute(update_screens_table_query)
        self.connection.commit()

        self.loop()

    def initMQTT(self):
        self.mqttClient = mqtt.Client()
        self.mqttClient.on_connect = self.onConnect
        self.mqttClient.message_callback_add(
            'system/resources', self.getResources)
        self.mqttClient.message_callback_add(
            'system/status', self.systemStatusCallback)
        self.mqttClient.message_callback_add(
            'plcHandler/request/#', self.plcRequest)
        self.mqttClient.message_callback_add('plcHandler/release/#',self.plcRelease)
        self.mqttClient.connect('localhost', 1883)

    def db_connect(self):

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
        print('Connected to DB')

    def onConnect(self, client, userdate, flags, rc):
        self.mqttClient.subscribe('system/#')
        self.mqttClient.subscribe('plcHandler/#') #might need to move this into the get resources function to prevent callback before resources are received
        print('Connected to MQTT')

    def systemStatusCallback(self, client, userdata, msg):
        print(msg.payload.decode())
        msg.payload = msg.payload.decode()
        if msg.payload.split('/')[0] == 'Stopped':
            self.quit = True

    def checkIfRunning(self):

        print('\n\n\n', datetime.datetime.now(), 'CheckIfRunning')

        for station in self.stationDict:
            print(datetime.datetime.now(), 'Station: ' + station)
            command = station + ',' + self.stationDict[station]['AGV']+'\r'
            
            response = self.plcSend(self.plcIP, self.plcPort, command) # Returns response from PLC "convStn1,agv1=T_convStn2,agv-1=F_convStn3,agv-1=F_convStn4,agv-1=F"

            if self.stationDict[station]['AGV'] != 'agv-1':
                commandState = station + ',' + self.stationDict[station]['AGV'] + '=T'

                if commandState in response and self.stationDict[station]['messageSent']==False: #the cart has arrived
                    print('***The cart has arrived!***')
                    taskID = self.stationDict[station]['taskID']

                    update_task_complete_process_query = "UPDATE process_handler SET task_complete = True, end_time = " + \
                        str(time.time()) + " WHERE id = " + str(taskID)
                    self.cursor.execute(update_task_complete_process_query)
                    self.connection.commit()
                    self.stationDict[station]['messageSent'] = True
                    self.stationDict[station]['taskID'] = None
            # print(station,'\nPLC Status:\n',response)

    'convStn1agv-1convStn2agv3,convStn3'
    def getResources(self, client, userdata, msg):
        self.resources = json.loads(msg.payload.decode(),object_pairs_hook=OrderedDict)
        # print('RESOURCE CALLBACK\n',self.resources)
        self.stationDict = OrderedDict()
        for resource in self.resources:
            if self.resources[resource]['type'] == "Conveyor Station":
                self.stationDict[resource] = OrderedDict()
                self.stationDict[resource]['AGV'] = 'agv-1'
                # self.stationDict[resource]['status'] = False
                self.stationDict[resource]['messageSent'] = True
                self.stationDict[resource]['sendbackMessage'] = ''
                self.stationDict[resource]['taskID'] = None
        print(json.dumps(self.stationDict, indent=4),'\n\n\n')
        time.sleep(1)

    def plcRequest(self, client, userdate, msg):
        # print('MADE IT')
        sendbackMessage = msg.payload.decode()
        msg = msg.topic.split('/') # Ex. plcHandler/request/station/agv/taskID
        station = msg[2] # Ex. convStn3
        agv = msg[3] # Ex. agvB
        agvID = self.resources[agv]['identifier']
        taskID = msg[4] # Ex. 8571

        self.stationDict[station]['AGV'] = agvID
        self.stationDict[station]['messageSent'] = False
        self.stationDict[station]['sendbackMessage'] = sendbackMessage
        self.stationDict[station]['taskID'] = taskID
        print('\n\n\n', datetime.datetime.now(), 'Received request. STATION: ' + station + ' AGV: ' + agv + ' TASK: ' + taskID)

    def plcRelease(self, client, userdata, msg):
        sendbackMessage = msg.payload.decode()
        msg = msg.topic.split('/')
        station = msg[-1:][0] # Ex. convStn3
        self.stationDict[station]['AGV'] = 'agv-1'
        self.stationDict[station]['messageSent'] = True
        self.stationDict[station]['sendbackMessage'] = ''
        self.stationDict[station]['taskID'] = None
        self.mqttClient.publish(sendbackMessage)

    def plcSend(self, ip, port, command):
        plcSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        plcSocket.connect((ip, port))
        plcSocket.sendall(command.encode())
        received = (plcSocket.recv(2048).decode()).replace('\r','')
        plcSocket.close()

        print(datetime.datetime.now(), 'Sent command: ' + command)
        print(datetime.datetime.now(), 'Received response: ' + received)
        return received

    def loop(self):
        while True:
        # while self.quit != True:
            # self.mqttClient.publish('screenStartup', "PLCHandler", retain=True)
            self.mqttClient.loop(0.1)
            schedule.run_pending()
        self.connection.disconnect()
        sys.exit(0)
        # plcRelease('convStn1')
        # plcRelease('convStn2')
        # plcRelease('convStn3')
        # plcRelease('convStn4')
        # self.checkIfRunning()


plcHandler = plcHandler()
