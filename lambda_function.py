"""
SubTracker, an Alexa skill

"""
import requests
import xmltodict
import json
from bs4 import BeautifulSoup

resp = requests.get('http://web.mta.info/status/serviceStatus.txt')
status = xmltodict.parse(resp.text.encode('punycode').replace(resp.text.encode('punycode').split('</service>')[1],''), encoding = 'ascii')

def lambda_handler(event, context):


	build_status_dict()

	if (event["session"]["application"]["applicationId"] !=
			"amzn1.ask.skill.d249dc27-e167-4718-8b09-6a7388ea3c1e"):
		raise ValueError("Invalid Application ID")

	if event["session"]["new"]:
		on_session_started({"requestId": event["request"]["requestId"]}, event["session"])

	if event["request"]["type"] == "LaunchRequest":
		return on_launch(event["request"], event["session"])
	elif event["request"]["type"] == "IntentRequest":
		return on_intent(event["request"], event["session"])
	elif event["request"]["type"] == "SessionEndedRequest":
		return on_session_ended(event["request"], event["session"])

def build_status_dict():
	#build a dict
	global alllines
	alllines = {}
	for trunk in status['service']['subway']['line']:
		trunkDict = {}
		if trunk['status'] == 'GOOD SERVICE':
			trunkDict['status'] = 'normal service.'
			alllines[trunk['name']] = trunkDict
			continue

		workAlerts = BeautifulSoup(trunk['text'].replace('<br/>','\n')).findAll('a',{'class':'plannedWorkDetailLink'})
		trunkDict['workIssues'] = [BeautifulSoup(str(alert)).get_text() for alert in workAlerts]

		delayAlerts = BeautifulSoup(trunk['text'].encode('punycode').replace('<br/>','\n')).findAll('p')
		delayIssues = [BeautifulSoup(str(alert)).get_text() for alert in delayAlerts]
		trunkDict['delayIssues'] = ' '.join(delayIssues)
		if len(trunkDict['workIssues']) > 0:
			if len(trunkDict['delayIssues']) > 0:
				trunkDict['status'] = 'planned work and delays or service changes. '
			else:
				trunkDict['status'] = 'planned work. '
		else:
			trunkDict['status'] = 'some delays or service changes. '
		alllines[trunk['name']] = trunkDict
	alllines.pop('SIR',0)
	alllines['NQRW'] = alllines.pop('NQR',{'status':'normal service.'})
	return


def on_intent(intent_request, session):
	intent = intent_request["intent"]
	intent_name = intent_request["intent"]["name"]

	if intent_name == "AllTrainsIntent":
		return subway_status()
	elif intent_name == "LineStatusIntent":
		return single_line_status(intent)
	elif intent_name == "CommuteStatusIntent":
		return get_commute(intent)
	elif intent_name == "AMAZON.HelpIntent":
		return subtracker_help()
	elif intent_name == "AMAZON.CancelIntent":
		return get_welcome_response()
	elif intent_name == "AMAZON.StopIntent":
		return handle_session_end_request()
	else:
		raise ValueError("Invalid intent")

def subtracker_help():
	session_attributes = {}
	card_title = "SubTracker"
	speech_output = "You can ask for the status of all subway lines, " \
					"or for a specific line. For instance, you can ask, " \
					"'are there any delays on the Q?'"
	should_end_session = False
	return

def subway_status():
	session_attributes = {}
	card_title = "SubTracker: full subway status"
	speech_output = ''
	reprompt_text = ''
	should_end_session = False
	# Add 'SIR' later for Staten Islanders
	orderedlines = [u'123', u'456', u'7', u'ACE', u'G', u'BDFM', u'JZ', u'L', u'NQRW', u'S']

	lineissues = [x for x in [line_status(line, alllines[line],False)  for line in orderedlines] if x != None]

	speech_output = ' '.join(lineissues)
	if len(lineissues) < 10:
		speech_output += " All other lines are running normally. "

	return build_response(\
			session_attributes,\
			build_speechlet_response(\
				card_title, speech_output, reprompt_text, should_end_session\
				))

def line_status(trunk, values, isSingle):
	outputspeech = ''
	trunkmod = trunk
	# Fun with grammar and mechanics!
	if len(trunk) == 1:
		if trunk == 'S':
			trunkmod = " Shuttles "
			trunkpl = " are reporting "
		else:
			trunkmod = trunk
			trunkpl = " is reporting "
	elif trunk == 'SIR':
		trunkmod = " Staten Island Railroad "
		trunkpl = " is reporting "
	else:
		trunkmod = ' '.join(trunk)
		trunkpl = " lines are reporting "
	status_speech = ("The "+ trunkmod+ trunkpl+ values['status'])

	try:
		if len(values['workIssues']) > 1:
			work_header = "There are " + str(len(values['workIssues'])) + " planned work alerts: "
		elif len(values['workIssues']) == 1:
			work_header = "There is one planned work alert: "
		else:
			work_header = None
		if work_header != None:
			work_body = ''
			for idx, issue in enumerate(values['workIssues']):
				work_body += ("Alert " + str(idx+1) + ": "+ issue + ". ")
		else:
			work_body = None

		work_speech = work_header + work_body
	except:
		work_speech = None

	try:
		if values['delayIssues'].count('Due to') > 1:
			delay_header = " There are currently multiple service issues. "
		else:
			delay_header = " There is currently a service issue. "
		if values['delayIssues'] == '':
			delay_body = ' After an earlier incident, service has resumed with some delays. '
		else:
			delay_body = values['delayIssues']
		delay_speech = delay_header + delay_body
	except:
		delay_speech = ''
	if not isSingle:
		if values['status'] == 'normal service.':
			output_speech = ''
		else:
			output_speech = status_speech
		output_speech += ' You can ask for the status of a specific line, or say stop to exit.'
	else:
		output_speech = ''
		for part in [status_speech, work_speech, delay_speech]:
			if part != None:
				output_speech += part
		output_speech += ' You can ask for the status of another line, of all lines, or say stop to exit.'
	return output_speech

def single_line_status(intent):
	session_attributes = {}
	card_title = "SubTracker: line status"
	line = intent['slots']['Line']["value"][0]

	for k,v in alllines.iteritems():
		if line.upper() in k:
			trunk = k
		else:
			continue
	if trunk:
		speech_output = line_status(trunk, alllines[trunk],True)
	reprompt_text = "Sorry, I'm not sure which line you're looking for. Please repeat your requst. "

	should_end_session = False

	return build_response(\
			session_attributes,\
			build_speechlet_response(\
				card_title, speech_output, reprompt_text, should_end_session\
				))

def get_commute(intent):
	session_attributes = {}
	card_title = "SubTracker: my commute"
	commuter = intent['slots']['Commuter']["value"]
	speech_output = 'This feature is coming soon.  Until then, ask about your line, or about all train service.'
	should_end_session = False

	return build_response(\
			session_attributes,\
			build_speechlet_response(\
				card_title, speech_output, reprompt_text, should_end_session\
				))

def on_session_started(session_started_request, session):
	print "Starting new session."

def on_launch(launch_request, session):
	return get_welcome_response()

def get_welcome_response():
	session_attributes = {}
	card_title = "SubTracker"
	speech_output = "Welcome to SubTracker. " \
					"You can ask for the status of all subway lines, " \
					"or for a specific line. "
	reprompt_text = "Please ask me for the status of a specific line, " \
					"or for all train lines. "
	should_end_session = False
	return build_response(\
			session_attributes,\
			build_speechlet_response(\
				card_title, speech_output, reprompt_text, should_end_session\
				))

def handle_session_end_request():
	session_attributes = {}
	card_title = "SubTracker: end session"
	speech_output = "Thank you for using the SubTracker on Alexa. Safe travels!"
	should_end_session = True
	return build_response(\
			session_attributes,\
			build_speechlet_response(\
				card_title, speech_output, None, should_end_session\
				))

def build_speechlet_response(title, output, reprompt_text, should_end_session):
	return {
		"outputSpeech": {
			"type": "PlainText",
			"text": output
		},
		"card": {
			"type": "Simple",
			"title": title,
			"content": output
		},
		"reprompt": {
			"outputSpeech": {
				"type": "PlainText",
				"text": reprompt_text
			}
		},
		"shouldEndSession": should_end_session
	}

def build_response(session_attributes, speechlet_response):
	return {
		"version": "1.0",
		"sessionAttributes": session_attributes,
		"response": speechlet_response
	}

