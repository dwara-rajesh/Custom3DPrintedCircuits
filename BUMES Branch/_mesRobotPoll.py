import time
import socket
import json
from helpers import error, warning, success

responses = {
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
	},
	'programState' : {
		'response' : {
			'STOPPED' : 'success',
			'PLAYING' : 'success',
			'PAUSED' : 'success'
		}
	}
}

def getStatus(host):
	robotStatus = {
		'running': 'no_data',
		'safety': 'no_data',
		'loaded': 'no_data',
		'programStatus': 'no_data'
	}
	currentRunningState, responseSuccess = dashboardCommand('running',host)
	currentSafteyModeState, responseSuccess = dashboardCommand('safetymode',host)
	currentLoadedProgram, responseSuccess = dashboardCommand('get loaded program',host)
	programStatus, responseSuccess = dashboardCommand('programState',host)

	robotStatus['running'] = currentRunningState
	robotStatus['safety'] = currentSafteyModeState
	robotStatus['loaded'] = currentLoadedProgram
	robotStatus['programStatus'] = programStatus

	return robotStatus



def dashboardCommand( command, robotAddress, argument = None):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.connect((robotAddress, 29999))
		connectionResponse = s.recv(2048).decode()
		# print(connectionResponse)
		originalCommand = command
		if command == 'load':
			command = command + ' ' + argument
		command = command + '\n'
		# print('Sending command: ' + originalCommand)
		s.send(command.encode())

		# print(s.recv(2048).decode())

		# Separates the response message
		response = s.recv(2048).decode()
		s.close()
		# print(response.split('\n')[0])
		try:
			responseTypes = responses[originalCommand]['response']
			for responseType in responseTypes:
				if responseType in response:
					try:
						responseStatus = responseTypes[responseType] # Should be either 'success' or 'fail'
						responseSuccess = True if responseStatus == 'success' else False
						if originalCommand == 'programState':
							finalResponse = response.split()[0]
							# print('Final response for programState is', finalResponse)
						else:
							response = response.split(responseType)
							finalResponse = response[1].split('\n')[0]
						return finalResponse, responseSuccess
					except:
						print('Error while splitting response. Verify that response type is included in dictionary.')
		except:
			print('Key Error! Verify the command and try again.')
			pass



def homeRobot(host, robotName):
	urpFile = '/programs/me345_admin/_adminRobotHome.urp'
	loadResponse, loadSuccess = dashboardCommand('load', host, urpFile)
	if not loadSuccess:
		response = {
			'title' : 'ERROR: ',
			'message' : 'Could not load file ' + urpFile + ' on ' + robotName,
			'type' : 'danger'
		}
		return response
	elif loadSuccess:
		playResponse, playSuccess = dashboardCommand('play', host)
		if not playSuccess:
			response = {
			'title' : 'ERROR: ',
			'message' : 'Failed to play ' + urpFile + ' on ' + robotName + '. Check robot position or perform homing sequence.',
			'type' : 'danger'
			}
			return response
		elif playSuccess:
			response = {
				'title' : 'SUCCESS: ',
				'message' : 'Performing homing sequence on ' + robotName,
				'type' : 'success'
			}
			return response

def stopRobot(host, robotName):
	stopResponse, stopSuccess = dashboardCommand('stop', host)
	if not stopSuccess:
		response = {
			'title' : 'ERROR: ',
			'message' : 'Failed to stop ' + robotName,
			'type' : 'danger'
		}
		return response
	elif stopSuccess:
		response = {
			'title' : 'SUCCESS: ',
			'message' : 'Stopped ' + robotName,
			'type' : 'success'
		}
		return response
