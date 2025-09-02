import pysftp
import json

def getRobotFiles(hostname, username, password):
	cnopts = pysftp.CnOpts()
	cnopts.hostkeys = None
	sftp = pysftp.Connection(hostname, username=username, password=password, cnopts=cnopts)

	directories = ['/programs']
	outputList = []

	while len(directories) != 0:
		with sftp.cd():
			for directory in directories:
				directories.remove(directory)
				sftp.chdir(directory)
				subList=sftp.listdir()
				for sub in subList:
					if sftp.isdir(sub):
						directories.append(directory+'/'+sub)
					else:
						outputList.append(directory+'/'+sub)
	sftp.close()
	urpOnly = []
	for file in outputList:
		if file.find('.urp') != -1:
			urpOnly.append(file.replace('/programs/',''))
	urpOnly.sort()
	# urpOnly = json.dumps(urpOnly)
#	print(urpOnly)
	return urpOnly
