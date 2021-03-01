from flask import Flask, session, render_template, request, redirect, url_for, abort
from flask_socketio import SocketIO, emit
#import eventlet
#from engineio.payload import Payload

#from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage

#
# Automated Reporting for System Engineers (A.R.S.E)
# by Michal Minarik (mminarik@vmware.com)
# version 1.1
#

import logging
logging.basicConfig(level='DEBUG')

import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import xml.etree.ElementTree as et
import pandas as pd
import getpass
import argparse
import re
import json

import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/uploads'
app.config['UPLOAD_EXTENSIONS'] = ['.xlsx']
app.config['SECRET_KEY'] = 'd2e82988-d9e7-40a1-89d0-1a9577be6ba6'
app.config['DEBUG']=True
app.config['HOST']='0.0.0.0'

#Payload.max_decode_packets = 50
#socketio = SocketIO(app, async_mode='eventlet', ping_timeout=5000, ping_interval=25000)
#async_mode = None
#socketio = SocketIO(app, async_mode=async_mode)
#socketio.init_app(app, cors_allowed_origins="*")
#disconnected=None
#app.host = '0.0.0.0'
#app.debug = True


# Class for checking if SDFC was loaded (either Lighning or Classic)
class sfdc_is_loaded_class(object):
	def __call__(self, driver):
		element = driver.find_element_by_xpath("/html/body")
		classes = element.get_attribute("class")
		if classes != '':
			if "desktop" in classes:
				return element
			elif "sfdcBody" in classes:
				return element
			else:
				return False

def parse_calendar (fileName):
    if fileName != None:

		xtree = et.parse(fileName)
		xroot = xtree.getroot()

		data = []

		for node in xroot.iter('appointment'):

			activity = ''
			activityType = ''
			related_object = ''
			related_to = ''

			try:
				summary = node.find('OPFCalendarEventCopySummary').text.strip()
			except AttributeError:
				summary = ''

			start = pd.to_datetime(node.find('OPFCalendarEventCopyStartTime').text)
			end = pd.to_datetime(node.find('OPFCalendarEventCopyEndTime').text)

			try:
				description = node.find('OPFCalendarEventCopyDescriptionPlain').text
			except AttributeError:
				description = ''

			# Calculate the duration and round to half hours
			duration = round(((end - start).total_seconds() / 3600) * 2) / 2

			if description:
				# Sanitize input for RegEx
				description = description.replace("\u2028", "")

				matches = re.match(r"^#(e|i):(\w+):(Account|Opportunity):(.+)#$", description, re.MULTILINE)
				if matches:
					if matches.groups()[0] == "e":
						activity = "EMEA SE Activity"
					elif matches.groups()[0] == "i":
						activity = "SE Internal Activity"
					activityType = matches.groups()[1]
					related_object = matches.groups()[2]
					related_to = matches.groups()[3]

			# Skip items before selected date
			if args.limit_start:
				limitStart = pd.to_datetime(args.limit_start)
				if (start <= limitStart):
					continue

			# Skip items after selected date
			if args.limit_end:
				limitEnd = pd.to_datetime(args.limit_end)
				if (start >= limitEnd):
					continue

			data.append([start, activity, activityType, summary, duration, related_object, related_to, 'Completed'])

		df = pd.DataFrame(data, columns = ['date', 'activity', 'type', 'subject', 'hours', 'related_object', 'related_to', 'status'])

		df.to_excel(session['username'] + '-input.xlsx', index=False)

@app.route("/")
def home():
	return render_template("index.html", template_folder = "templates", config=configs)

@app.route('/uploader', methods=['POST'])
def upload_file():
	f = request.files['file']
	session['username'] = request.form.get("login")
	session['password'] = request.form.get("password")

	fName = session['username'] + '-' + f.filename
	session['filename'] = fName

	f.save(secure_filename(fName))
	parse_calendar(fName)

	return 'file ' + fName + ' uploaded successfully for user ' + request.form.get("login")

@app.route("/settings")
def help():
	return render_template("settings.html", template_folder = "templates", config=configs)

@app.route("/test")
def page():
	return render_template("socket.html", template_folder = "templates", async_mode=socketio.async_mode)

if __name__ == "__main__":
	# Read configuration JSON
	with open('../config.json', 'r') as configFile:
	    data = configFile.read()
	# Parse JSON file
	configs = json.loads(data)
	print (app.host)
	# run flask
	app.run ()
