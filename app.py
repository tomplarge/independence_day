from __future__ import print_function
import requests
import numpy as np
from flask import Flask, request
from flask_restful import Resource, Api
import os, sys, logging
from pixels import pixels
# import RPi.GPIO as GPIO
import time
# from sample import *
# --------------- Initialize GPIO Pins -----------------
# GPIO.setmode(GPIO.BCM)
# GPIO.setwarnings(False)

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """
    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to the Makerspace Navigator. Ask where a tool is, or how to use a tool, and I can help you."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Ask me where a tool is, and I can help you find it."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    session_attributes = {}
    card_title = "Session Ended"
    speech_output = "I hope you found what you needed! Make away!"
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def levenshtein_distance(string1, string2, deletion_cost, insertion_cost, substitution_cost):
	"""
	Computes levenshtein distance between string1 and string2 given costs.
	Returns the last entry in the distance matrix, d, representing the distance
	"""
	d = np.zeros((len(string1) + 1, len(string2) + 1))

	# initialize matrix
	for i in range(d.shape[0]):
		d[i,0] = i * deletion_cost
	for j in range(d.shape[1]):
		d[0,j] = j * insertion_cost

	for j in range(1, d.shape[1]): # counter for string2
		for i in range(1, d.shape[0]): # counter for string1
			if string2[j-1] == string1[i-1]:
				# no operation cost, letters match
				d[i,j] = d[i-1,j-1]
			else:
				d[i,j] = min(d[i-1,j] + deletion_cost,
							d[i,j-1] + insertion_cost,
							d[i-1,j-1] + substitution_cost)

	return d[i,j]


def determine_tool(word):
    # compute levenshtein distance for word.
    # choose lowest distance for set of tools
    tools = get_tools()
    substitution_cost = 1
    deletion_cost = 1
    insertion_cost = 1
    errors = [levenshtein_distance(word, tools[i]["name"], deletion_cost, insertion_cost, substitution_cost) for i in range(len(tools))]
    return tools[np.argmin(errors)]


def get_tools():
    tools = [{
                "name": "3d printer",
                "endpoint": "https://3dprinter.ngrok.io/LED",
                "location": "right side",
                "safety": "Don't touch while hot",
                "info": "The 3D printer works by using a plastic filament to construct the design. " +
                    "The plastic filament is melted, and the arm of the printer moves back and forth, " +
                    "slowly building up the object. Once it is finished, it will be cool and dry. " +
                    "3D printing can take anywhere from 1 hour to several days, depending on the size of the object. " +
                    "Let me know if you need any more assistance or guidance. Happy making!"
            },
            {
                "name": "laser cutter",
                "endpoint": "https://lasercutter.ngrok.io/LED",
                "location": "front",
                "safety": "Don't look directly at the laser while it is cutting. This can damage your eyes.",
                "info": "Place a piece of wood on the cutting surface, flush with the top left edge. Close the lid, and choose your design. " +
                    "Be sure to check your settings for power and speed, as this will affect the outcome of your design. " +
                    "Let me know if you need any more assistance or guidance. Happy making!"
            }]

    return tools


# def get_tool_location(tool_name):
#     tools = {
#         "laser cutter": "front left quadrant.",
#         "Lisa cutter": "front left quadrant.",
#         "laser color": "front left quadrant.",
#         "lisa cutter": "front left quadrant.",
#         "3d printer": "back left quadrant.",
#         "3dprinter": "back left quadrant.",
#         "3 d printer": "back left quadrant.",
#         "3 printer": "back left quadrant.",
#         "3D printer": "back left quadrant."
#     }
#
#     endpoints = {
#         "3D printer": "https://3dprinter.ngrok.io/LED",
#         "3d printer": "https://3dprinter.ngrok.io/LED",
#         "3dprinter": "https://3dprinter.ngrok.io/LED",
#         "3 d printer": "https://3dprinter.ngrok.io/LED",
#         "3 printer": "https://3dprinter.ngrok.io/LED",
#         "laser cutter": "https://lasercutter.ngrok.io/LED",
#         "Lisa cutter": "https://lasercutter.ngrok.io/LED",
#         "lisa cutter": "https://lasercutter.ngrok.io/LED",
#         "laser color": "https://lasercutter.ngrok.io/LED"
#     }
#     try:
#         endpoint = endpoints[tool_name]
#     except:
#         endpoint = None
#     try:
#         tool_location = tools[tool_name]
#     except:
#         tool_location = None
#
#     return tool_location, endpoint
#

def find_tool_in_session(intent, session):
    """ Finds the tool in the session and prepares the speech to reply to the
    user.
    """
    card_title = intent['name']
    session_attributes = {}
    reprompt_text = None

    if 'Tool' in intent['slots'] and 'value' in intent['slots']['Tool']:
        spoken_tool = intent['slots']['Tool']['value']
        tool = determine_tool(spoken_tool)
        speech_output = "The " + tool["name"] + " is located in the " + tool["location"] + ". Happy making."
        should_end_session = True
    else:
        speech_output = "I didn't catch that. Try again."
        should_end_session = False

    # fork, respond to alexa in parent, and send LED request as child
    pid = os.fork()
    if pid == 0:
        # child sends request to correct pi to light up
        r = requests.get(tool["endpoint"])
        os._exit(1)
    else:
        # parent returns to response to flask
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, reprompt_text, should_end_session))


def get_tool_info_in_session(intent, session):
    """ Gets tool info in session and prepares speech to reply to user """
    card_title = intent['name']
    session_attributes = {}
    reprompt_text = None

    if 'Tool' in intent['slots'] and 'value' in intent['slots']['Tool']:
        spoken_tool = intent['slots']['Tool']['value']
        tool = determine_tool(spoken)
        speech_output = tool["info"]
        should_end_session = True
    else:
        speech_output = "I didn't catch that. Try again."
        should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "FindTool":
        return find_tool_in_session(intent, session)
    elif intent_name == "ToolInfo":
        return get_tool_info_in_session(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def main_handler(event, context):
    """
    Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

# -------- Flask Setup and Run ---------

# initialize flask app
flask_app = Flask(__name__)
flask_api = Api(flask_app)

class Navigator(Resource):
    def post(self):
        response = main_handler(request.get_json(), {})
        return response

class LED(Resource):
    def get(self):
        start = time.time()
        pixels.power.on()
        while time.time() - start < 3:
            pixels.show([255] * 48)
            time.sleep(0.3)
            pixels.show([255,0,0] * 16)
            time.sleep(0.3)
        pixels.power.off()
        return "Success"

# define endpoints
navigator_endpoint = "/navigator"
LED_endpoint = "/LED"

# add endpoints to flask
flask_api.add_resource(Navigator, navigator_endpoint)
flask_api.add_resource(LED, LED_endpoint)

if __name__ == '__main__':
    # run on open host on port 5000
    flask_app.run(host = "0.0.0.0", port = 5000)
