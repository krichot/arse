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
#app.config['HOST']='0.0.0.0'

#Payload.max_decode_packets = 50
#socketio = SocketIO(app, async_mode='eventlet', ping_timeout=5000, ping_interval=25000)
#async_mode = None
#socketio = SocketIO(app, async_mode=async_mode)
#socketio = SocketIO(app)
#socketio.init_app(app, cors_allowed_origins="*")
#disconnected=None
app.host = '0.0.0.0'
app.debug = True

xls_data = []

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

@app.route("/")
def home():
	return render_template("index.html", template_folder = "templates", config=configs)

@app.route('/uploader', methods=['POST'])
def upload_file():
	f = request.files['file']
	df = pd.read_excel(f)

	session['username'] = request.form.get("login")
	session['password'] = request.form.get("password")

	#fName = session['username'] + '-' + f.filename
	#session['filename'] = fName

	#f.save(secure_filename(fName))
	#parse_calendar(fName, session['username'], session['password'])

	# Open Firefox and start login to SFDC
	#browser = webdriver.Firefox()

	# Use Selenuim container from defined host
	browser = webdriver.Remote(
	   command_executor=str(configs['worker']) ,
	   desired_capabilities={'browserName': 'firefox'})

	wait = WebDriverWait(browser, 30)
	browser.get('https://vmware.my.salesforce.com')

	ssoButton = browser.find_element_by_xpath("//div[@id='idp_section_buttons']/button[2]")
	ssoButton.click()

	# Sign in using username/password to Workspace ONE
	wait.until(EC.presence_of_element_located((By.ID, "username")))

	usernameField = browser.find_element_by_id("username")
	usernameField.send_keys(session['username'])
	passwordField = browser.find_element_by_id("password")
	passwordField.send_keys(session['password'])

	signInButton = browser.find_element_by_id("signIn")
	signInButton.click()

	lightningNotificationDismissed = False

	# Wait for SFDC to load
	wait.until(sfdc_is_loaded_class())

	# Check for SFDC Lightning
	matches = re.match(r".*lightning.*", browser.current_url)
	if matches:
		print("Lightning detected - Switching to SFDC Classic")

		browser.implicitly_wait(10)

		profileIcon = browser.find_element_by_xpath("/html/body/div[4]/div[1]/section/header/div[2]/span/div[2]/ul/li[8]/span/button/div/span[1]/div")
		profileIcon.click()

		switchToClassicLink = browser.find_element_by_xpath("/html/body/div[4]/div[2]/div[2]/div[1]/div[1]/div/div[5]/a")
		switchToClassicLink.click()

		# wait.until(EC.presence_of_element_located((By.ID, "lightningFeedbackPage:feedbackForm")))

		lightningNotificationDismissed = True

	# Wait classic SFDC to load
	wait.until(EC.title_is("Salesforce - Unlimited Edition"))

	for index, row in df.iterrows():

		print("Processing task [" + str(index + 1) + "/" + str(len(df)) + "]")

		if row.activity == "EMEA SE Activity":

			# Go to "non-lightning" new task creation form
			browser.get('https://vmware.my.salesforce.com/00T/e?retURL=%2Fapex%2FSFA_SEActivitiesTab&RecordType=01234000000QF7y&ent=Task')

			# Dismiss the SFDC switch to Lighning notification. The dialog popup blocks screen and automatic select does not work.
			if lightningNotificationDismissed is False:

				wait.until(EC.presence_of_element_located((By.ID, "lexNoThanks")))

				lightningNotificationQuestionButton = browser.find_element_by_id("lexNoThanks")
				lightningNotificationQuestionButton.click()

				wait.until(EC.presence_of_element_located((By.ID, "lexSubmit")))

				lightningNotificationCloseButton = browser.find_element_by_id("lexSubmit")
				lightningNotificationCloseButton.click()

				lightningNotificationDismissed = True

			# Fill the form
			subjectField = browser.find_element_by_id("tsk5")
			subjectField.send_keys(row.subject)

			dateField = browser.find_element_by_id("tsk4")
			dateField.send_keys(row.date.strftime(str(configs['date_format'])))

			relatedObjectSelect = Select(browser.find_element_by_id('tsk3_mlktp'))
			relatedObjectSelect.select_by_visible_text(row.related_object)

			relatedToField = browser.find_element_by_id("tsk3")
			relatedToField.send_keys(row.related_to)

			activityTypeSelect = Select(browser.find_element_by_id('00N80000004k1L2'))
			activityTypeSelect.select_by_value(row.type)

			statusSelect = Select(browser.find_element_by_id('tsk12'))
			statusSelect.select_by_value(row.status)

			workHoursField = browser.find_element_by_id("00N80000004k1Mo")
			workHoursField.send_keys(str(row.hours).replace(".", str(configs['decimal_separator'])))

			# Submit
			submitButton = browser.find_element_by_xpath("/html/body/div[1]/div[3]/table/tbody/tr/td[2]/form/div/div[3]/table/tbody/tr/td[2]/input[1]")
			submitButton.click()

			# Wait for the form to be fully submited (TODO: Create some condition and remove the explicit wait)
			browser.implicitly_wait(10) # seconds

		elif row.activity == "SE Internal Activity":

			# Go to "non-lightning" new task creation form
			browser.get('https://vmware.my.salesforce.com/00T/e?retURL=%2Fapex%2FSFA_SEActivitiesTab&RecordType=01280000000BY0b&ent=Task')

			# Dismiss the SFDC switch to Lighning notification. The dialog popup blocks screen and automatic select does not work.
			if lightningNotificationDismissed is False:

				wait.until(EC.presence_of_element_located((By.ID, "lexNoThanks")))

				lightningNotificationQuestionButton = browser.find_element_by_id("lexNoThanks")
				lightningNotificationQuestionButton.click()

				wait.until(EC.presence_of_element_located((By.ID, "lexSubmit")))

				lightningNotificationCloseButton = browser.find_element_by_id("lexSubmit")
				lightningNotificationCloseButton.click()

				lightningNotificationDismissed = True

			# Fill the form
			subjectField = browser.find_element_by_id("tsk5")
			subjectField.send_keys(row.subject)

			dateField = browser.find_element_by_id("tsk4")
			dateField.send_keys(row.date.strftime(str(configs['date_format'])))

			activityTypeSelect = Select(browser.find_element_by_id('00N80000004k1L2'))
			activityTypeSelect.select_by_value(row.type)

			workHoursField = browser.find_element_by_id("00N80000004k1Mo")
			workHoursField.send_keys(str(row.hours).replace(".", str(configs['decimal_separator'])))

			statusSelect = Select(browser.find_element_by_id('tsk12'))
			statusSelect.select_by_value(row.status)

			# Submit
			submitButton = browser.find_element_by_xpath("/html/body/div[1]/div[3]/table/tbody/tr/td[2]/form/div/div[3]/table/tbody/tr/td[2]/input[1]")
			submitButton.click()

			# Wait for the form to be fully submited (TODO: Create some condition and remove the explicit wait)
			browser.implicitly_wait(10) # seconds

		else:
			print("Item cannot be logged due to invalid value of field 'activity'")

	return df.to_html()

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
	#print (app.host)
	# run flask
	app.run (host="0.0.0.0")
	#socketio.run(app)
