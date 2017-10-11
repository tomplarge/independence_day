from __future__ import print_function
import requests
from flask import Flask, request
from flask_restful import Resource, Api
import os, sys, logging
from pixels import pixels
import subprocess
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


def get_tool_location(tool_name):
    tools = {
        "laser cutter": "front left quadrant.",
        "Lisa cutter": "front left quadrant.",
        "laser color": "front left quadrant.",
        "lisa cutter": "front left quadrant.",
        "3d printer": "back left quadrant.",
        "3dprinter": "back left quadrant.",
        "3 d printer": "back left quadrant.",
        "3 printer": "back left quadrant.",
        "3D printer": "back left quadrant."
    }

    endpoints = {
        "3D printer": "https://3dprinter.ngrok.io/LED",
        "3d printer": "https://3dprinter.ngrok.io/LED",
        "3dprinter": "https//3dprinter.ngrok.io/LED",
        "3 d printer": "https://3dprinter.ngrok.io/LED",
        "3 printer": "https://3dprinter.ngrok.io/LED",
        "laser cutter": "https://lasercutter.ngrok.io/LED",
        "Lisa cutter": "https://lasercutter.ngrok.io/LED",
        "lisa cutter": "https://lasercutter.ngrok.io/LED",
        "laser color": "https://lasercutter.ngrok.io/LED"
    }
    try:
        endpoint = endpoints[tool_name]
    except:
        endpoint = None
    try:
        tool_location = tools[tool_name]
    except:
        tool_location = None

    return tool_location, endpoint


def find_tool_in_session(intent, session):
    """ Finds the tool in the session and prepares the speech to reply to the
    user.
    """
    card_title = intent['name']
    session_attributes = {}
    reprompt_text = None

    if 'Tool' in intent['slots']:
        tool_to_find = intent['slots']['Tool']['value']
        print(tool_to_find + "\n")
        tool_location, tool_endpoint = get_tool_location(tool_to_find)
        if tool_location is not None and tool_endpoint is not None:
            speech_output = "The " + tool_to_find + " is located in the " + tool_location + ". Happy making."
        else:
            speech_output = "I'm sorry. I couldn't find the requested tool. Goodbye."
        should_end_session = True
    else:
        speech_output = "I didn't catch that. Try again."
        should_end_session = False
    
    if tool_endpoint is not None:
        pid = os.fork()
        if pid == 0:
            # child sends request to correct pi to light up
            #subprocess.call(['python','pixels.py'])
            r = requests.get(tool_endpoint)
            os._exit(1)
        else:
            # parent returns to response to flask
            return build_response(session_attributes, build_speechlet_response(
                card_title, speech_output, reprompt_text, should_end_session))
    else:
            return build_response(session_attributes, build_speechlet_response(
                card_title, speech_output, reprompt_text, should_end_session))

def get_tool_info_in_session(intent, session):
    """ Gets tool info in session and prepares speech to reply to user """
    card_title = intent['name']
    session_attributes = {}
    reprompt_text = None

    if 'Tool' in intent['slots']:
        tool_for_info = intent['slots']['Tool']['value']
        speech_output = "The " + tool_for_info + " can be used with your brain, you fuh king idiot. Happy making."
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