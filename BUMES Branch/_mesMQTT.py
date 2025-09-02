def statusStopped(mqttClient, origin, comment=None):
    message = 'Stopped/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusStartingRealRun(mqttClient, origin, comment=None):
    message = 'Starting_Real-Run/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusStartingFullSimulation(mqttClient, origin, comment=None):
    message = 'Starting_Full-Simulation/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusStartingQuickSimulation(mqttClient, origin, comment=None):
    message = 'Starting_Quick-Simulation/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusRunning(mqttClient, origin, comment=None):
    message = 'Real-Run/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusQuickSim(mqttClient, origin, comment=None):
    message = 'Quick-Simulation/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusFullSim(mqttClient, origin, comment=None):
    message = 'Full-Simulation/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def statusFaulted(mqttClient, origin, comment=None):
    message = 'Faulted/'+origin+'/'+comment
    mqttClient.publish('system/status', message, retain=True)


def user(mqttClient, user, origin, comment=None):
    message = user+'/'+origin+'/'+comment
    mqttClient.publish('system/user', message, retain=True)
