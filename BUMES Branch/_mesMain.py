'''
--------------------

Manufacturing Execution Software (MES)

    Scripting for the Control and Execution of the Flexible Manufacturing Cell
        at Boston University

    Primary Developer (Python, HTML, Javascript, Rockwell Ladder, Universal Robotics, Hass CNC)
        Jeffrey Costello, jdc0214@bu.edu
    Supporting Developer (Python, HTML, Javascript, Teledyne Dalsa System, Universal Robotics)
        Axel S. Toro Vega, axelt@bu.edu

--------------------

MES Main

The main script is primarly a Flask web application built into a class-type object.
Use -d to run Flask in debug mode
'''

# // Python Built-In Libraries //
import os
import glob
import json
from collections import OrderedDict
import pprint
import datetime
import time
import re #regular expressions
import sys # For arguments
import shutil # For zipping
import csv
import signal # For capturing exits
import traceback # For printing stack frames

# // Downloaded Libraries //
import flask  # import the Flask library
import paho.mqtt.client as mqtt
from mysql.connector import connect, Error

# // User-Generated Libraries //
import _mesScreen
import _mesSFTP
import _mesMQTT
from helpers import warning, success, error, txtToCsv
import _mesRobotPoll

class mesWebApp:
    def __init__(self):

        self.debugFolder = 'debug/'
        if not os.path.exists(self.debugFolder):
            os.makedirs(self.debugFolder)

        # Set prevStatus variable to Stopped in order to prevent logging before anything has run
        self.prevStatus = 'Stopped'

        # initialize some attributes that will be retained by the system
        self.activeUser = 'public'  # always start with the "public" user

        # in a future step, this list will be populated with the contents of _mesConfigFiles/user.txt
        self.userList = []

        # initialize a variable to store operation startup priorities
        self.startupPriority = 0

        # self.processDirectory defaults to public but is modified ever time there is a self.userCallback callback
        self.processDirectory = '_mesProcessFiles/public'

        # self.reportsDirectory contains all the process reports for the system
        self.reportsDirectory = 'Logs'

        # self.tempReportsDirectory is a temporary directory to store zipped process reports for download
        self.tempReportsDirectory = self.reportsDirectory + '/temp'

        # intialize some empty fields for the "editor" HTML template (templates/editor.html)
        self.editor_textArea = ''
        self.editor_selection = ''

        self.cncDirectory = 'admlNC/public'

        # intialize some empty fields for the "cnc" HTML template (templates/editor.html)
        self.cnc_textArea = self.getCNCTemplate()
        self.cnc_selection = ''

        # intializae some empty fields for the "robot" HTML template (templates/robot.html)
        self.robot_robotURPFiles = ''
        self.robot_robotSelection = ''

        # In case there was a dirty exit on a previous exection
        # Remove extranous bash files (the files used to start screen jobs in the background)
        # Make sure all background processes are dead
        _mesScreen.rmOldBashFiles()  # remove old bash files
        _mesScreen.killallSessions()  # kill any hung-up screen sessions
        os.system('clear')  # clear the terminal window

        # Initlize the Flask application
        # create a website in variable self.app
        self.app = flask.Flask(__name__)

        # Connect to the database
        self.db_connect()

        # clear process_table at system start
        delete_process_table_query = "DELETE FROM process_handler"
        self.cursor.execute(delete_process_table_query)
        self.connection.commit()

        # Reset resource table at system start
        update_isSeized_usedBy_resource_query = "UPDATE resource_handler SET isSeized = False, usedBy = ''"
        self.cursor.execute(update_isSeized_usedBy_resource_query)
        self.connection.commit()

        # Captures when ctrl-c is pressed, terminating _mesMain process (We want to capture this so we can close the db connection)
        signal.signal(signal.SIGINT, self.handler)
        
        # Initialize the MQTT connection to the server, publish some messages, add callbacks
        self.initMQTT()

        signal.signal(signal.SIGINT, self.handler)

        # self.mqttClient.publish('debug', 'DIE DIE DIE DIE')

        # Define global Flask variables here
        self.app.context_processor(self.setGlobal)
        

        # add rules to the web app
        # https://kite.com/python/docs/flask.Flask.add_url_rule
        self.app.add_url_rule(
            rule='/', 
            view_func=self.render_index, 
            methods=None)

        self.app.add_url_rule(
            rule='/test', 
            view_func=self.render_test, 
            methods=None)

        # Making this universal
        self.app.add_url_rule(
            rule='/changeUser', 
            view_func=self.index_changeUser, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/encodeProcesses', 
            view_func=self.index_encode, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/config', 
            view_func=self.render_config, 
            methods=None)

        self.app.add_url_rule(
            rule='/config/saveFile', 
            view_func=self.config_saveFile, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/editor', 
            view_func=self.render_editor, 
            methods=['GET'])

        self.app.add_url_rule(
            rule='/editor/loadFile', 
            view_func=self.editor_loadFile, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/editor/deleteFile', 
            view_func=self.editor_deleteFile, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/editor/saveFile',
            view_func=self.editor_saveFile, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/reports', 
            view_func=self.render_reports, 
            methods=None)

        self.app.add_url_rule(
            rule='/reports/download/<path:directory>', 
            view_func=self.reports_download, 
            methods=None)

        self.app.add_url_rule(
            rule='/cnc', 
            view_func=self.render_cnc, 
            methods=None)

        self.app.add_url_rule(
            rule='/cnc/loadFile', 
            view_func=self.cnc_loadFile, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/cnc/deleteFile', 
            view_func=self.cnc_deleteFile, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/cnc/saveFile',
            view_func=self.cnc_saveFile, 
            methods=['POST'])
        
        self.app.add_url_rule(
            rule='/cnc/template',
            view_func=self.cnc_template, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/robot', 
            view_func=self.render_robot, 
            methods=None)

        self.app.add_url_rule(
            rule='/robots/<robotName>', 
            view_func=self.render_individual_robot, 
            methods=None)

        self.app.add_url_rule(
            rule='/robots/status/<robotName>', 
            view_func=self.getRobotStatus, 
            methods=None)

        self.app.add_url_rule(
            rule='/robots/home/<robotName>', 
            view_func=self.robotHome, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/robots/stop/<robotName>', 
            view_func=self.robotStop, 
            methods=['POST'])

        self.app.add_url_rule(
            rule='/robots/get/<robotName>', 
            view_func=self.robot_getURP, 
            methods=None)

        self.app.add_url_rule(
            rule='/docs', 
            view_func=self.render_docs, 
            methods=None)

    # Handler for capturing ctrl-c keypress and closing db connection
    def handler(self, signal, frame):
        print('')
        print('SYSTEM STOPPING')
#         traceback.print_stack(frame)
        self.connection.disconnect()

        files = glob.glob('./debug/*.txt', recursive=True)
        for f in files:
            try:
                os.remove(f)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))

        files = glob.glob('./Logs/temp/*', recursive=True)
        for f in files:
            try:
                os.remove(f)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))

        sys.exit(0)

    def setGlobal(self):
        self.getUsers
        return {'userList': self.userList,'robotSelection' : self.robot_robotSelection}
    
    def robotSelection(self):
        return 

    def initMQTT(self):
        # init attribute self.mqttClient as paho.mqtt.client.Client()
        self.mqttClient = mqtt.Client()
        self.mqttClient.on_connect = self.onConnect
        self.mqttClient.on_disconnect = self.onDisconnect

        try:
            self.mqttClient.connect('localhost', 1883)
            self.mqttClient.loop_start()
        except Exception as e:
            error('Failed to connect to MQTT Server')
            error(e)
            sys.exit()

    def db_connect(self):
        select_process_query = 'SELECT * FROM process_handler'

        '''
        IMPORTANT:
        You may need to run a SQL command in order to connect to the mySQL database from a detached screen. The command is:

        ALTER USER 'yourusername'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yourpassword';

        Source: https://stackoverflow.com/questions/49194719/authentication-plugin-caching-sha2-password-cannot-be-loaded
        '''

        self.connection = connect(
            host="localhost",
            user='root',
            password='buADML@2021',
            database="bumes",
        )
                
        self.cursor = self.connection.cursor()
        self.cursor2 = self.connection.cursor()

    def onConnect(self, client, userdata, flags, rc):
        _mesMQTT.statusStopped(self.mqttClient, '_mesMain', 'onConnect')
        _mesMQTT.user(self.mqttClient, self.activeUser,
                      '_mesMain', 'onConnect')
        self.processQueue = None

        self.mqttClient.publish(
            'system/processQueue',
            json.dumps(self.processQueue), retain=True)

        self.mqttClient.publish(
            'system/resources',
            json.dumps(self.getResources()), retain=True)

        self.mqttClient.subscribe(
            'system/#')

        self.mqttClient.message_callback_add(
            'system/status', self.systemStatusCallback)

        self.mqttClient.message_callback_add(
            'system/user', self.userCallback)

    def onDisconnect(self, client, userdata, rc):
        # Use this print statement to debug lost connections to the MQTT server
        print('\n\nThe MQTT Client has disconnected from the server.\n\n')

    def activeScreens(self):
        # Counts number of active screens
        select_active_screens_query = "SELECT COUNT(active = 1 or null) FROM screens"
        self.cursor.execute(select_active_screens_query)
        result = self.cursor.fetchall()
        self.connection.commit()
        return result[0][0]

    def systemStatusCallback(self, client, userdata, msg):
        status = (msg.payload.decode()).split('/')[0]
        if status == 'Starting_Real-Run' or \
            status == 'Starting_Quick-Simulation' or \
            status == 'Starting_Full-Simulation':
            self.prevStatus = status
            try:
                if status == 'Starting_Real-Run':
                    self.processQueue['Run Identifier'] = \
                        self.processQueue['Run Identifier']+'-RealRun'
                    _mesScreen.rmOldBashFiles()  # remove old bash files
                    _mesScreen.killallSessions()  # kill all hung-up screen sessions
                    _mesScreen.bashSession(
                        debugOption, sessionName='urHandler', pythonFile='_mesUrHandler.py')
                    _mesScreen.bashSession(
                        debugOption, sessionName='cncHandler', pythonFile='_mesCNCHandler.py')
                    _mesScreen.bashSession(
                        debugOption, sessionName='plcHandler', pythonFile='_mesPLCHandler.py')
                    _mesScreen.bashSession(
                        debugOption, sessionName='visionHandler', pythonFile='_mesVisionHandler.py')
                    _mesScreen.bashSession(
                        debugOption, sessionName='dashboardHandler', pythonFile='_mesDashboardHandler.py')
                    '''
                    WARNING: If screens are added or removed, you must reflect this in the screens table
                    of the database AND change the hardcoded number of screens to check in the conditional below
                    '''
                    counter = 0
                    #Resposible for ensuring that the PC is able to establish a connection with all Handlers
                    #Only after all handlers are active the script would run
                    while self.activeScreens() != 5: #and counter != 20:
                        # counter += 1
                        # if counter == 10:
                        #     print('One or more screens were unable to start successfully.')
                        #     raise RuntimeError('One or more screens were unable to start successfully.')
                        time.sleep(.5)
                elif status == 'Starting_Quick-Simulation':
                    self.processQueue['Run Identifier'] = \
                        self.processQueue['Run Identifier']+'-QuickSim'
                elif status == 'Starting_Full-Simulation':
                    self.processQueue['Run Identifier'] = \
                        self.processQueue['Run Identifier']+'-FullSim'
                self.mqttClient.publish(
                    'system/processQueue', json.dumps(self.processQueue, indent=4), retain=True)
                self.connection.commit()
                
                _mesScreen.bashSession(
                    debugOption, sessionName='backend', pythonFile='_mesBackend.py')

                # Clear process_handler table at beginning of run
                delete_process_table_query = "DELETE FROM process_handler"
                self.cursor.execute(delete_process_table_query)
                self.connection.commit()

                # Reset resource table at beginning of run
                update_isSeized_usedBy_resource_query = "UPDATE resource_handler SET isSeized = False, usedBy = ''"
                self.cursor.execute(update_isSeized_usedBy_resource_query)
                self.connection.commit()

                # Clear handler_requests table at beginning of run
                delete_handler_requests_query = "DELETE FROM handler_requests"
                self.cursor.execute(delete_handler_requests_query)
                self.connection.commit()

            except:
                _mesMQTT.statusStopped(
                    self.mqttClient, '_mesMain', 'systemStatusCallback')
        elif status == "Stopped":
            # Clear the process queue
            self.processQueue = None
    
            # Save contents of process table to CSV before clearing
            if self.prevStatus != status:
                select_process_table_query = "SELECT DISTINCT(process_name) FROM process_handler"
                self.cursor.execute(select_process_table_query)
                processes = self.cursor.fetchall()

                if self.activeUser in self.runID:
                    self.newRunID = self.runID.split(self.activeUser)
                    self.newRunID = self.activeUser + '-' + self.newRunID[1]

                if os.path.isdir('./Logs/' + self.newRunID + '-' + self.prevStatus + '/') != True:
                    os.mkdir('./Logs/' + self.newRunID + '-' + self.prevStatus + '/')
                file_path = './Logs/' + self.newRunID + '-' + self.prevStatus + '/'

                for process in processes:
                    process = process[0]
                    select_process_table_query = "SELECT * FROM process_handler WHERE process_name = '" + \
                        process + "'"
                    self.cursor.execute(select_process_table_query)
                    tasks = self.cursor.fetchall()

                    if tasks:
                        currentOperation = ''
                        result = list()
                        columns_names = list()
                        for i in self.cursor.description:
                            columns_names.append(i[0])

                        result.append(columns_names)
                        for task in tasks:
                            if currentOperation == '':
                                prevOp = task[2]
                            else:
                                prevOp = currentOperation
                            currentOperation = task[2]
                            if prevOp == currentOperation:
                                result.append(task)
                            else:
                                csv_file_path = file_path + process + '_' + prevOp + '_Report.csv'
                                with open(csv_file_path, 'w', newline='') as csvfile:
                                    csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                                    for row in result:
                                        csvwriter.writerow(row)
                                result = list()

                        csv_file_path = file_path + process + '_' + prevOp + '_Report.csv'
                        with open(csv_file_path, 'w', newline='') as csvfile:
                            csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                            for row in result:
                                csvwriter.writerow(row)
                        result = list()

                    else:
                        print('No rows found for query: {}'.format(select_process_table_query))

            delete_process_table_query = "DELETE FROM process_handler"
            update_isSeized_usedBy_resource_query = "UPDATE resource_handler SET isSeized = False, usedBy = ''"

            # Clear process table at end of run
            self.cursor.execute(delete_process_table_query)
            self.connection.commit()

            # Reset resource table at end of run
            self.cursor.execute(update_isSeized_usedBy_resource_query)
            self.connection.commit()

            # Clear handler_requests table at end of run
            delete_handler_requests_query = "DELETE FROM handler_requests"
            self.cursor.execute(delete_handler_requests_query)
            self.connection.commit()

            # Reset screens table at end of run
            update_screens_table_query = "UPDATE screens SET active = False"
            self.cursor.execute(update_screens_table_query)
            self.connection.commit()

            _mesScreen.rmOldBashFiles()  # remove old bash files
            _mesScreen.killallSessions()  # kill any hung-up screen sessions
#            print('Stop Request Recieved from',messageOrigin)

            self.prevStatus = status

    def userCallback(self, client, userdata, msg):
        self.activeUser = (msg.payload.decode()).split('/')[0]
        self.processDirectory = '_mesProcessFiles/'+self.activeUser
        self.cncDirectory = 'admlNC/'+self.activeUser
        try:
            os.mkdir(self.processDirectory)
        except:
            pass #directory already exists
        try:
            os.mkdir(self.cncDirectory)
        except:
            pass #directory already exists

   # Get the parent process files from the subdirectory and return them as a list

    def getProcesses(self):
        processList = os.listdir(self.processDirectory)
        processList = [processName.split('.txt')[0]
                       for processName in processList]
        processList = sorted(processList, key=str.lower)
        return processList

    def getGCode(self):
        gCodeList = os.listdir(self.cncDirectory)
        return gCodeList

    # Get the resources file from the subdirectory and return the resources as a dictonary
    def getResources(self):
        with open('_mesConfigFiles/resourceConfig.txt', 'r') as resourceFile:
            resourceList = resourceFile.read()
            resourceList = json.loads(
                resourceList, object_pairs_hook=OrderedDict)
        return resourceList

    # Get the CNC GCode template file
    def getCNCTemplate(self):
        with open('_mesConfigFiles/millTemplate.txt', 'r') as cncFile:
            cncTemplate = cncFile.read()
        return cncTemplate

    def robot_getURP(self, robotName):
        resourceList = self.getResources()
        hostname = resourceList[robotName]['identifier']
        username = resourceList[robotName]['username']
        password = resourceList[robotName]['password']
        try:
            robotFiles = _mesSFTP.getRobotFiles(
                hostname, username, password)
        except:
            robotFiles = ['Unable to connect to remote robot SFTP server.','Check robot power.','Check FMC Configuration.','Check Network Cables.']
        return flask.jsonify(robotFiles)

    def getRobotNames(self):
        self.robotNames = []
        resourceList = self.getResources()
        for resource in resourceList:
            if resourceList[resource]['type'] == 'Robot':
                self.robotNames.append(resource)

    def getUsers(self):
        self.userList = []
        with open('_mesConfigFiles/users.txt') as userFile:
            for user in userFile:
                user = user.replace('\n', '')
                self.userList.append(user)
        for user in self.userList:
            try:
                os.mkdir('_mesProcessFiles/'+user)
            except:
                pass  # directory already exists

    def getReports(self):
        reportList = os.listdir(self.reportsDirectory)
        reportsDict = {}
        for report in reportList:
            if report != 'temp':
                subFiles = os.listdir(self.reportsDirectory + '/' + report)
                if report != []:
                    reportsDict[report] = subFiles
        # print(reportsDict)
        return reportsDict

    def getRobotStatus(self, robotName):
        resourceList = self.getResources()
        hostname = resourceList[robotName]['identifier']
        robotStatus = _mesRobotPoll.getStatus(hostname)
        return flask.jsonify(robotStatus)

    def robotHome(self, robotName):
        resourceList = self.getResources()
        hostname = resourceList[robotName]['identifier']
        response = _mesRobotPoll.homeRobot(hostname, robotName)
        return flask.jsonify(response)
    
    def robotStop(self, robotName):
        resourceList = self.getResources()
        hostname = resourceList[robotName]['identifier']
        response = _mesRobotPoll.stopRobot(hostname, robotName)
        return flask.jsonify(response)
    
    def alphanumeric(self,string):
        regex = re.compile('[^a-zA-Z0-9]')
        #First parameter is the replacement, second parameter is your input string
        #Example: regex.sub('', 'ab3d*E'); Out: 'abdE'
        return regex.sub('',string)

    # For index.html, generate a dictonary of processes with empty "Quantity" fields
    def index_processQuantities(self):
        processFiles = self.getProcesses()  # get the list of processes
        processQuantityDict = OrderedDict()  # empty ordered dictonary
        # form the list of process files, create a dictionary with OrderedDict([Quantity:None])
        for processFile in processFiles:
            processQuantityDict[processFile] = OrderedDict()
            processQuantityDict[processFile]['Quantity'] = None
        return json.dumps(processQuantityDict)

    # Process encoding, in this context, is taking a parent process such as processA-Body.txt...
        # ...and breaking it into operation such as processA-Body_2of7
    def index_encode(self):
        # get the form values containing the quantity input by the user
        # request the contents of the form and convert from immuatble multidict to regular dict
        # Dict with format {process:desiredQuantity}
        form = list(flask.request.form.items())
        print(form)
        self.processQueue = OrderedDict()
        self.runID = str(datetime.datetime.now())[0:19].replace(':', '')
        self.runID = self.runID.replace('-', '')
        self.runID = self.runID.replace(' ', '-')
        self.runID = self.activeUser + self.runID
        self.processQueue['Run Identifier'] = str(datetime.datetime.now())[
            0:19].replace(':', '')
        self.processQueue['Run Identifier'] = self.processQueue['Run Identifier'].replace(
            '-', '')
        self.processQueue['Run Identifier'] = self.processQueue['Run Identifier'].replace(
            ' ', '-')
        self.processQueue['Run Identifier'] = self.activeUser + '-' + \
            self.processQueue['Run Identifier']
        self.processQueue['Queued Processes'] = OrderedDict()
        i = 3
        for process, desiredQuantity in form:
            if 'StartupPriority' not in process:
                if desiredQuantity == '0' or desiredQuantity == '':
                    pass  # ignore a parent process if the user has entered 0 or not made a selection
                else:
                    try:
                        # if the conversion to type INT tosses an error, it goes to the except statement
                        desiredQuantity = int(desiredQuantity)
                        # Store this value in another variable for use in the startup priority else statement
                        prevDesiredQuantity = desiredQuantity
                        self.processQueue['Queued Processes'][process +
                                                            '.txt'] = OrderedDict()
                        for part in range(1, desiredQuantity+1):
                            subprocess = process+'_' + \
                                str(part)+'of'+str(desiredQuantity)

                            if part == 1:
                                self.processQueue['Queued Processes'][process +
                                                                '.txt'][subprocess] = {'Startup Priority': i,
                                                                                        'complete': False,
                                                                                        'StartupTasksComplete': False,
                                                                                        'part': part}
                                i += 1
                            else:
                                self.processQueue['Queued Processes'][process +
                                                                '.txt'][subprocess] = {'complete': False,
                                                                                        'part': part}
                    except:
                        pass  # pass any non-integer selections
            # If this conditional is triggered, then we are looking at the startup priority
            # portion of the form, and the enumerated variable 'desiredQuantity' is actually
            # storing the operation's startup priority
            else:
                if desiredQuantity == '':
                    pass
                else:
                    process = process[:len(process) - 15]
                    self.startupPriority = int(desiredQuantity)
                    try:
                        subprocess = process+'_' + '1of' + str(prevDesiredQuantity)
                        self.processQueue['Queued Processes'][process + '.txt'][subprocess]['Startup Priority'] = self.startupPriority
                        # print(self.processQueue)
                    except:
                        print('Passed')
                        pass

        print(pprint.pformat(self.processQueue))
        self.mqttClient.publish('system/processQueue',
                                json.dumps(self.processQueue, indent=4), retain=True)
        return flask.redirect('/')

    # Make this changeuser universal for all routes since it will go in the header
    # Problem is the user list is not passed to header because it is loaded with javaScript
    def index_changeUser(self):
        self.editor_textArea = ''
        self.editor_selection = ''
        self.cnc_textArea = self.getCNCTemplate()
        self.cnc_selection = ''
        self.robot_robotURPFiles = ''
        self.robot_robotSelection = ''
        self.processQueue = None
        self.mqttClient.publish('system/processQueue',
                                json.dumps(self.processQueue), retain=True)
        try:
            self.activeUser = flask.request.form['userList']
            self.mqttClient.publish(
                'system/user', self.activeUser, retain=True)
        except:
            print('No User Selection')
        # For universal form
        return flask.redirect(flask.request.referrer)
        # return flask.redirect('/')

     # callback for web app route '/'
    def render_index(self):
        self.getUsers()
        self.getRobotNames()
        return flask.render_template('index.html',
                                     userList=self.userList,
                                     processQuantity=self.index_processQuantities(),
                                     robotNames=self.robotNames)  # ,processQueue=json.dumps(self.processQueue, indent=4))

    # callback for web app route '/test'
    def render_test(self):
        return flask.render_template('test.html')

    # callbback for web app route '/config'
    def render_config(self):
        resources = self.getResources()  # get ordered dictionary of resources
        return flask.render_template('config.html',
                                     resourceList=json.dumps(resources))

    def config_saveFile(self):
        filename = '_mesConfigFiles/resourceConfig.txt'
        fileContents = flask.request.form['config_hiddenContent']
        try:
            json.loads(fileContents, object_pairs_hook=OrderedDict)
            with open(filename, 'w') as configFile:
                configFile.write(fileContents)
            self.mqttClient.publish(
                'system/resources', json.dumps(self.getResources()), retain=True)
        except:
            print('Bad formatting from the config file!')

        return flask.redirect('/config')

    def render_reports(self):
        reportHistory = self.getReports()
        return flask.render_template('reports.html', reportList=reportHistory)

    # Directory is runID // admin-20210309-111822-RealRun
    def reports_download(self, directory):
        try:
            if not (os.path.isdir('./Logs/temp')):
                os.mkdir('./Logs/temp')
            shutil.rmtree(self.tempReportsDirectory) # Delete temp reports directory
            os.mkdir('./Logs/temp')
            
        except Exception as e:
            error('While zipping reports: '+ str(e))

        runID = directory
        reportDirectory = self.reportsDirectory + '/' + runID # Logs/admin-20210309-111822-RealRun
        tempDir = self.tempReportsDirectory # Logs/temp
        tempRunDir = tempDir + '/' + runID # Logs/temp/admin-20210309-111822-RealRun

        zipName = runID + '_zipped' # admin-20210309-111822-RealRun_zipped
        zipPath = zipName + '.zip' # admin-20210309-111822-RealRun_zipped.zip
        shutil.make_archive(zipName, 'zip', reportDirectory) # Zip run directory

        try:
            shutil.move(zipPath, tempDir) # Move zipped file to temp directory
        except Exception as e:
            error('While zipping reports: '+ str(e))

        # Send file
        return flask.send_file(tempDir + '/' + zipPath, as_attachment=True)

    def render_cnc(self):
        gCodeFiles = self.getGCode()
        self.cncOption = [file.replace('.txt','') for file in gCodeFiles]
        gCodeFiles = [self.activeUser + '/' + file for file in gCodeFiles]
        return flask.render_template('cnc.html',
                                     cnc_content=self.cnc_textArea,
                                     cnc_retainedFilename=self.cnc_selection,
                                     optionList=self.cncOption,
                                     gCodeFiles=gCodeFiles)

    def cnc_loadFile(self):
        try:
            self.cnc_selection = flask.request.form['cnc_selection']
            print(self.cnc_selection)
            with open(self.cncDirectory + '/' + self.cnc_selection + '.txt', 'r') as cncFile:
                self.cnc_textArea = cncFile.read()
        except:
            print('no selection was made')
        return flask.redirect('/cnc')

    def cnc_deleteFile(self):
        try:
            self.cnc_selection = flask.request.form['cnc_selection']
            os.system('rm ' + self.cncDirectory +
                      '/'+self.cnc_selection + '.txt')
            self.cnc_textArea = ''
            self.cnc_selection = ''
        except:
            print('Failed to delete the specificed file')
        return flask.redirect('/cnc')

    def cnc_saveFile(self):
        shortFilename = flask.request.form['cnc_processSaveFilename']
        shortFilename = self.alphanumeric(shortFilename)
        filename = self.cncDirectory + '/' + shortFilename + '.txt'
        fileContents = flask.request.form['cnc_hiddenContent']
        with open(filename, 'w') as myFile:
            myFile.write(fileContents)
        self.cnc_textArea = fileContents
        self.cnc_selection = shortFilename
        return flask.redirect('/cnc')

    def cnc_template(self):
        self.cnc_selection = ''
        self.cnc_textArea = self.getCNCTemplate()
        return flask.redirect('/cnc')

    def render_robot(self,):
        self.getRobotNames()
        main = flask.request.args.get('main')
        if main == 'true' or self.robot_robotSelection == '':
            self.robot_robotSelection = ''
            return flask.render_template('robot.html',
                                        textarea=self.robot_robotURPFiles,
                                        optionList=self.robotNames,
                                        robotSelection=self.robot_robotSelection,
                                        file=self.robot_robotSelection + '_Files')
        elif self.robot_robotSelection != '':
            return flask.redirect('/robots/' + self.robot_robotSelection)

    def render_individual_robot(self, robotName):
        self.robot_robotSelection = robotName
        return flask.render_template('robots.html', robotName=robotName)

    def render_docs(self):
        with open('README.md', 'r') as readmeFile:
            readme = readmeFile.read()
            readme = json.dumps(readme, indent=4)
        return flask.render_template('docs.html',
                                     readme=readme)

    def render_editor(self):
        self.editorOption = self.getProcesses()
        resources = self.getResources()
        return flask.render_template('editor.html',
                                     editor_content=self.editor_textArea,
                                     editor_retainedFilename=self.editor_selection,
                                     optionList=self.editorOption,
                                     resourceList=json.dumps(resources))

    def editor_loadFile(self):
        try:
            self.editor_selection = flask.request.form['editor_selection']
            with open(self.processDirectory + '/' + self.editor_selection+'.txt', 'r') as processFile:
                self.editor_textArea = processFile.read()
        except:
            print('no selection was made')
        return flask.redirect('/editor')

    def editor_deleteFile(self):
        try:
            self.editor_selection = flask.request.form['editor_selection']
            os.system('rm ' + self.processDirectory +
                      '/'+self.editor_selection+'.txt')
            self.editor_textArea = ''
            self.editor_selection = ''
        except:
            print('Failed to delete the specificed file')
        return flask.redirect('/editor')

    def editor_saveFile(self):
        shortFilename = flask.request.form['editor_processSaveFilename']
        shortFilename = self.alphanumeric(shortFilename)
        filename = self.processDirectory + '/' + shortFilename + '.txt'
#        print('\n\nfilename:',filename)
        fileContents = flask.request.form['editor_hiddenContent']
#        print('filecontent:',fileContents)
        with open(filename, 'w') as myFile:
            myFile.write(fileContents)
        self.editor_textArea = fileContents
        self.editor_selection = shortFilename
        return flask.redirect('/editor')


# If the script is run directly...
if __name__ == '__main__':
    try:
        # ...start the application.
        mes = mesWebApp()

        debugOption = False
        hostOption = 'localhost'

        if len(sys.argv) > 1:
            if '-d' in sys.argv:
                print('----- Starting in DEBUG mode -----')
                debugOption = True
            if '-h' in sys.argv:
                warning('----- HOST OPEN TO LOCAL NETWORK -----')
                hostOption = '0.0.0.0'

        mes.app.run(debug=False, host=hostOption)  # localhost:5000
    except KeyboardInterrupt as m:
        print('SYSTEM STOPPING')
        try:
            sys.exit(m)
        except SystemExit:
            os._exit(m)

# Other hosts and ports for running the web application
#    mes.app.run(host='0.0.0.0')
#    mes.app.run(host='localhost', port='5005')
