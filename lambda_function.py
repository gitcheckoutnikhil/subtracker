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
	            trunkDict['status'] = 'planned work and delays or service changes.'
	        else:
	            trunkDict['status'] = 'planned work.'
	    else:
	        trunkDict['status'] = 'some delays or service changes.'
	    if trunkDict['delayIssues'] == '':
	        trunkDict['delayIssues'] = 'After an earlier incident, service has resumed with some delays.'
	    alllines[trunk['name']] = trunkDict
	return

def subway_status():
	# Add 'SIR' later for Staten Islanders
	orderedlines = [u'123', u'7',  u'456', u'ACE', u'G', u'BDFM', u'JZ', u'L', u'NQR', u'S']

	lineissues = [linestatus(line, alllines[line],False) for line in orderedlines]
	if len(lineissues) >= 5:
		output = "Yikes! The trains are a mess today!"
	output += ' '.join(lineissues)
	return output

def line_status(trunk, values, isSingle):
    outputspeech = ''
    trunkmod = trunk
    # Fun with grammar and mechanics!
    if len(trunk) == 1:
        if trunk == 'S':
            trunkmod = " Shuttles "
            trunkpl = " are reporting "
        else:
            trunkpl = " is reporting "
    elif trunk == 'SIR':
        trunkmod = " Staten Island Railroad "
        trunkpl = " is reporting "
    else:
        trunkmod = ' '.join(trunkmod)
        trunkpl = " lines are reporting "
    outputspeech += ("The "+ trunkmod+ trunkpl+ values['status'])
    if values['status'] == ' normal service. ':
    	# If we're getting all lines, skip the ones that are okay.
        if isSingle == True:
            return outputspeech
        else:
            return ''
    try:
    	# Parse planned work alerts.
        if len(values['workIssues']) > 0:
            if len(values['workIssues']) > 1:
                outputspeech += ("There are ",len(values['workIssues']), " planned work alerts: ")
            else:
                outputspeech += "There is one planned work alert: "
            for idx, issue in enumerate(values['workIssues']):
                outputspeech += ("Alert", idx+1, issue)
    except:
        pass
    try:
    	# Parse current service issues
        if len(values['delayIssues']) > 0:
            if (values['delayIssues'].count('Due to')) > 1:
                outputspeech += "There are multiple service issues, including: "
            outputspeech += values['delayIssues']
    except:
        pass
    return outputspeech

def single_line_status():


def get_commute():
	# Find out who's asking, and then do some commute calc stuff
	return


def on_session_started(session_started_request, session):
    print "Starting new session."

def on_launch(launch_request, session):
    return get_welcome_response()

def on_intent(intent_request, session):
    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if intent_name == "AllTrainsIntent":
        return subway_status(intent)
    elif intent_name == "LineStatusIntent":
        return single_line_status(intent)
    elif intent_name == "CommuteStatusIntent":
        return get_commute(intent)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")

def get_welcome_response():
    session_attributes = {}
    card_title = "BART"
    speech_output = "Welcome to the Alexa BART times skill. " \
                    "You can ask me for train times from any station, or " \
                    "ask me for system status or elevator status reports."
    reprompt_text = "Please ask me for trains times from a station, " \
                    "for example Fremont."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def handle_session_end_request():
    card_title = "BART - Thanks"
    speech_output = "Thank you for using the BART skill.  See you next time!"
    should_end_session = True

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
