import os
import subprocess
import time
import pprint

'''For more information about using screen,
visit https://www.gnu.org/software/screen/manual/screen.html'''


def createSession(sessionName):
    # '-dm' to run background job
    # '-S' to name the session
    os.system('screen -dmS ' + sessionName)


def bashSession(debugOption, sessionName, pythonFile):
    '''Docstring.'''
    operatingDirectory = os.getcwd() + '/_mesBashFiles/'
    try:
        os.mkdir(operatingDirectory)
    except:
        # if the directory already exists
        pass
    sessionBashFile = operatingDirectory + sessionName + '.sh'
    # sessionProcessName = sessionName.split('_')[0]
    with open(sessionBashFile, 'w') as bashFile:
        bashFileEcho = 'echo "Starting ' + sessionName + '";\n'
        bashFile.write(bashFileEcho)
        # screen -dms urHandler bash -c python3 _mesUrHandler.py
        if debugOption == False:
            bashFileExecute  = "screen -dmS " + sessionName + \
                " bash -c "+"'python3 " + pythonFile + "';"
        else:
            bashFileExecute = "screen -dmS " + sessionName + \
                " bash -c "+"'python3 " + pythonFile + " -d';"
        bashFile.write(bashFileExecute)
    os.system('bash ' + sessionBashFile)
    os.system('screen -ls')
    print('Created bash session: ' + bashFileExecute)


def getSessions():
    '''Docstring: Takes no arguments.
        Returns dictionary with format {screenID:{'sessionName':sessionName}.'''
    # get system output for 'screen -ls'
    # returns bytes, decodes into a string for manipulation
    screenList = subprocess.check_output(['screen', '-ls']).decode('utf-8')
    # manipulate string to get session ID numbers and session Names
    # names are assigned by the user when creating a instance of screen
    screenList = screenList.split('\r\n\t')
    screenList = screenList[1].split('\n\t')
    sessions = {}
    # create a dictionary containing all screens on the system
    # dict key is screen session ID because they are unique identifiers
    # names can be shared by multiple sessions, hence we do not use them as identifiers
    for session in screenList:
        sessionID = session.split('.')[0]
        sessionName = session.split('.')[1]
        sessionName = sessionName.split('\t')[0]
        sessions[sessionID] = {'sessionName': sessionName}
    return sessions


def killSession(sessionName):
    '''Doctstring: Takes string argument containing the common name of a screen session.'''
    sessions = getSessions()
    # iterate over the entire list of sessions to ensure all screens sharing sessionName are killed
    for sessionID in sessions:
        if sessions[sessionID]['sessionName'] == sessionName:
            # executes a kill command by sessionID number
            os.system('echo _mesScreen.py is attempting to kill any \
                hung-up GNU Screen sessions.')
            os.system('kill ' + sessionID)


def killallSessions():
    os.system('killall screen')


def rmOldBashFiles():
    operatingDirectory = os.getcwd() + '/_mesBashFiles'
    print('\n\n_mesScreen.py is attempting to remove old bash files from the _mesOperatingFiles directory.')
    command = 'rm -r ' + operatingDirectory + '/*'
    print('\nExecuting the following command:',command)
    os.system(command)
    print('\n')

def unpackSTY():
    # $STY gets the socket name of the current screen session
        # example: 167.processA-Body_1of2~admin-20200427-085948-RealRun

    # get the socket name and remove the job number    
    screenSession = os.environ['STY'].split('.')[1]  # processA-Body_1of2~admin-20200427-085948-RealRun
    
    runID = screenSession.split('~')[1]  # admin-20200427-085948-RealRun
    user = runID.split('-')[0] # admin
    runType = runID.split('-')[3] # RealRun
    childProcessName = screenSession.split('~')[0]  # processA-Body_1of2

    return runID, user, runType, childProcessName

if __name__ == '__main__':
    #    os.system('clear')
    #    bashSession('processA-Body_2of7','process')
    bashSession('resourceHandler', 'resourceHandler')
