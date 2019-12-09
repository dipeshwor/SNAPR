# SNAPR - Snap, Narrate, Auto Post and Reflect
# December 19, 2019 
# Tufts University 
# Tufts Center for Engineering Education and Outreach

# Keywords
# Canvas, Flask
# Hardware - Raspberry Pi Zero W, RPi Camera

# Code for Video streaming modified from 
# https://github.com/miguelgrinberg/flask-video-streaming

# Import necessary libraries   
from flask import Flask, render_template, request, Response, send_file
app = Flask(__name__)
from datetime import datetime
import time, io, threading
import requests, os, picamera

# Part 1: Canvas 
# Canvas API URL
base_url = "https://canvas.tufts.edu/api/v1"
# Canvas API key
# Default API Key (RPi OS environment variable) 
API_KEY = os.environ.get('API_D')
authorization = ''

# Set Canvas course number 
courseNumber='18705'
#courses or groups depending on where you want to create the page
groups='/courses/'
#groups='/groups/'

# Set up a session
session = requests.Session()

# Define variables
message1 = 'Dipeshwor M. Shrestha'
message2 = '1'
message3 = 'dipeshwor-m-shrestha'
message4 = ''

# Folder where the code resides 
rootFolder='/home/pi/Desktop/SNAPR/'
filename=rootFolder+'files/documentationSetup.PNG'

# Set flags 
flag=0
stopFlag=0
delay=1

#Create file on Canvas (Test on Canvas Live API to see how it works)
def createFile(filePath, folderName):
	global apiKey, authorization
	# Step 1 - tell Canvas you want to upload a file
	#file attributes
	attributes = {}
	attributes['parent_folder_path'] = '/'+folderName
	
	#Post command. Tested in Canvas API Live 
	API_URL=base_url+groups+courseNumber+"/files"
	r = session.post(API_URL, data=attributes)
	r.raise_for_status()
	r = r.json()	
	print('Upload URL:'+r['upload_url'])
	message=r['progress']

	# Step 2 - upload file in the provided upload_url from Step 1 post request 
	attributes = {"file": open(filePath, 'rb')}
	r = requests.post(r['upload_url'], files=attributes)
	r.raise_for_status()
	r = r.json()
	print(r)
	print('Location:'+r['location'])
	message=r['filename']

	#Step 3: Confirm upload success status
	r = requests.post(r['location'], headers=authorization)
	r.raise_for_status()
	r = r.json()
	print('Upload Status:'+r['upload_status'])
	message="File upload: "+r['upload_status']
	fileID=r['id']
	return message, fileID

#Create a page on Canvas (Test on Canvas Live API to see how it works)
def createPage(url, title, body):
	global apiKey, authorization
	#folder attributes
	attributes = {}
	attributes['wiki_page[title]'] = title
	attributes['wiki_page[body]'] = body
	attributes['wiki_page[published]'] = True
	
	#Post command. Tested in Canvas API Live 
	API_URL=base_url+groups+courseNumber+"/pages/"+url
	#put not post
	r = session.put(API_URL, data=attributes, headers=authorization)
	r.raise_for_status()
	r = r.json()
	return r['url']

#Update page on Canvas (Test on Canvas Live API to see how it works)
def showPage(url):
	global apiKey, authorization
	attributes = {}
	#Get command. Tested in Canvas API Live 
	API_URL=base_url+groups+courseNumber+"/pages/"+url
	r = session.get(API_URL, data=attributes, headers=authorization)
	r.raise_for_status()
	r = r.json()
	url=r['url']
	title=r['title']
	body=r['body']
	return url, title, body

# Get user details based on individual access token
def userDetails():
	#Post command. Tested in Canvas API Live 
	API_URL=base_url+"/users/self"
	attributes = {}
	r = session.get(API_URL, data=attributes, headers=authorization)
	try:
		r = r.json()
		r = r['name']
	except Exception as error:
		r = 'Error: Authorization failed. Enter access token again.'
	return r

# Parse the folder name for standard page creation 
def getFolderName():
	name=userDetails()
	name=name.lower()
	name=name.replace(".", "")
	name=name.replace(" ", "-")
	return name

# Part 2: Flask
# Main page  
@app.route('/')
def index():
	#Messages
	global message1, message2, message3, message4, flag, stopFlag

	templateData = {
		'msg1'  : message1,
		'msg2'  : message2, 
		'msg3': message3,
		'msg4': message4,
		'flag': flag
	}
	return render_template('index.html', **templateData)

# Video streaming 
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask 
def gen(camera):
	"""Video streaming generator function."""
	global flag
	while True:
		frame = camera.get_frame()
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

class Camera(object):
	thread = None  # background thread that reads frames from camera
	frame = None  # current frame is stored here by background thread
	last_access = 0  # time of last client access to the camera

	def initialize(self):
		if Camera.thread is None:
			# start background frame thread
			Camera.thread = threading.Thread(target=self._thread)
			Camera.thread.start()
			# wait until frames start to be available
			while self.frame is None:
				time.sleep(0)

	def get_frame(self):
		Camera.last_access = time.time()
		self.initialize()
		return self.frame

	@classmethod
	def _thread(cls):
		while True:
			global flag, delay, message1, stopFlag, filename
			with picamera.PiCamera() as camera:
				# camera setup
				#camera.resolution = (1080, 720)
				camera.resolution = (640, 480)
				camera.hflip = True
				camera.vflip = True
				camera.rotation=270

				stream = io.BytesIO()
				for foo in camera.capture_continuous(stream, 'jpeg', use_video_port=True):
					# store frame
					stream.seek(0)
					cls.frame = stream.read()

					# reset stream for next frame
					stream.seek(0)
					stream.truncate()
					#When flag is raised start capturing and uploading files to Canvas 
					if flag==1:
						urlOld=getFolderName()
						for filename in camera.capture_continuous(rootFolder+'files/img{timestamp:%Y%m%d_%H%M%S}.jpg'):
							print('Captured %s' % filename)
							filePath=filename
							shortFileName=filePath.split('/')
							shortFileName=shortFileName[-1]
							folderName=userDetails()
							#Save the file on Canvas on the corresponding folder 
							#I created folders for each individual students on Canvas beforehand 
							message, fileID=createFile(filePath, folderName)
							print(message)
							url, title, body = showPage(urlOld)
							#Update the Canvas page 
							body="""<p>Filename: """+shortFileName+"""</p><p><img src="https://canvas.tufts.edu"""+groups+courseNumber+"""/files/"""+str(fileID)+"""/preview" width="320" height="240" /></p>"""+body
							url=createPage(url, title, body)
							time.sleep(delay)
							#When Stop Flag is raised, stop capturing 
							if stopFlag == 1:
								flag=0
								message1="Complete"
								break
							
					# if there hasn't been any clients asking for frames in
					# the last 120 seconds stop the thread
					if time.time() - cls.last_access > 120:
						break

			cls.thread = None

#Start page 
#User can enter the time delay between each snapshots 
@app.route('/start', methods = ['POST', 'GET'])
def start():
	global message1, message2, message3, flag, delay, stopFlag
	flag=1
	stopFlag=0
	if request.method == 'POST':
		delay=int(request.form['delay'])
	
	message2=str(delay)
	templateData = {
		'msg1'  : message1,
		'msg2'  : message2, 
		'msg3': message3,
		'msg4': message4,
		'flag': flag
	}

	return render_template('start.html', **templateData)

# Home page 
@app.route('/home', methods = ['POST', 'GET'])
def home():
	global message1, message2, message3, message4, flag, stopFlag
	flag=0
	stopFlag=1
	templateData = {
		'msg1'  : message1,
		'msg2'  : message2, 
		'msg3': message3,
		'msg4': message4,
		'flag': flag
	}
	return render_template('index.html', **templateData)

#Enter 
#Capture page 
@app.route('/enter', methods = ['POST', 'GET'])
def enter():
	global message1, message2, message3, message4, flag, filename
	global apiKey, authorization	
	flag=0
	if request.method == 'POST':
		apiKey=request.form['apiKey']
		message1="In Progress"	

	# Canvas API key
	if apiKey=='default':
		API_KEY=os.environ.get('API_D')
	else:
		#Update API key with the one the user has entered 
		API_KEY=apiKey	
	authorization = {'Authorization': 'Bearer %s' % API_KEY}
	session.headers = authorization
	message1=userDetails()
	message3=getFolderName()

	templateData = {
		'msg1'  : message1,
		'msg2'  : message2, 
		'msg3': message3,
		'msg4': message4,
		'flag': flag
	}
	return render_template('enter.html', **templateData)

#Stop page 
@app.route('/stop', methods = ['POST', 'GET'])
def stop():
	global message1, message2, message3, message4, flag, stopFlag
	flag=0
	stopFlag=1
	templateData = {
		'msg1'  : message1,
		'msg2'  : message2, 
		'msg3': message3,
		'msg4': message4,
		'flag': flag
	}
	return render_template('enter.html', **templateData)

#Download page
#Has the latest captured image 
#You can use a GET from another app to get the latest captured image 
@app.route('/download')
def download():
	global filename
	try:
		return send_file(filename, attachment_filename='image.jpg')
	except Exception as e:
		return str(e)

#Video feed path 
@app.route('/video_feed')
def video_feed():
	"""Video streaming route. Put this in the src attribute of an img tag."""
	return Response(gen(Camera()),
		mimetype='multipart/x-mixed-replace; boundary=frame')

# Flash server on port 80
# Open up a browser and enter the RPi IP 
if __name__ == '__main__':
	app.run(host='0.0.0.0', port =80, debug=True, threaded=True)