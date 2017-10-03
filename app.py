from flask import Flask, request
from flask_restful import Resource, Api
import os, sys, logging

# initialize flask app
flask_app = Flask(__name__)
flask_api = Api(flask_app)

class Navigator(Resource):
    def get(self):
        return "success"

# define endpoint
navigator_endpoint = "/navigator"

# add endpoint to flask
flask_api.add_resource(Navigator, navigator_endpoint)

if __name__ == '__main__':
    # run on open host on port 5000
    flask_app.run(host = "0.0.0.0", port = 5000)
