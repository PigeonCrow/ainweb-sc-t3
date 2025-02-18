## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
from werkzeug.wrappers import response
import time
import random


# Class-based application configuration
class ConfigClass(object):
    """Flask application config"""

    # Flask settings
    SECRET_KEY = "This is an INSECURE secret!! DO NOT use this in production!!"


# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + ".ConfigClass")  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = "http://localhost:5555"
HUB_AUTHKEY = "1234567890"
CHANNEL_AUTHKEY = "0987654321"
CHANNEL_NAME = "Group14-tbd"  # TODO: come up with a propper name
CHANNEL_ENDPOINT = (
    "http://localhost:5001"  # don't forget to adjust in the bottom of the file
)
CHANNEL_FILE = "messages.json"
CHANNEL_TYPE_OF_SERVICE = "aiweb24:chat"

MAX_MESSAGES = (
    100  # maximum number of messages to keep, TODO: mby a date/time would be better?
)
WELCOME_MESSAGE = {  # TODO: define a proper message
    "content": "Welcome to Groups 14 Channel the topic needs still to be defined properly",
    "sender": "System",
}

story = []
submissions = [] #stores sentences for the current round
votes = {}
current_phase = "submission" #or "voting"
sentence_limit = 5
vote_time_limit = 30 #seconds
submission_time_limit = 60 #seconds
last_phase_change = time.time()

@app.cli.command("register")
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(
        HUB_URL + "/channels",
        headers={"Authorization": "authkey " + HUB_AUTHKEY},
        data=json.dumps(
            {
                "name": CHANNEL_NAME,
                "endpoint": CHANNEL_ENDPOINT,
                "authkey": CHANNEL_AUTHKEY,
                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
            }
        ),
    )

    if response.status_code != 200:
        print("Error creating channel: " + str(response.status_code))
        print(response.text)
        return


def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if "Authorization" not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers["Authorization"] != "authkey " + CHANNEL_AUTHKEY:
        return False
    return True


# TODO: msg filter
def filter_message(message):
    # TODO
    return message


# TODO: response generator
def generate_response():
    # TODO
    return response


def save_game_state():
    with open(CHANNEL_FILE, "w") as f:
        json.dump({"story": story, "submissions": submissions, "votes": votes})


def load_game_state():
    global story, submissions, votes
    try:
        with open(CHANNEL_FILE, "r") as f:
            data = json.load(f)
            story = data.get("story", [])
            submissions = data.get("submissions", [])
            votes = data.get("votes", {})
    except FileNotFoundError:
        save_game_state()


@app.route("/health", methods=["GET"])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({"name": CHANNEL_NAME}), 200


# GET: Return list of messages
@app.route("/", methods=["GET"])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    return jsonify(read_messages())


# POST: Send a message
@app.route("/", methods=["POST"])
def send_message():
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not "content" in message:
        return "No content", 400
    if not "sender" in message:
        return "No sender", 400
    if not "timestamp" in message:
        return "No timestamp", 400
    if not "extra" in message:
        extra = None
    else:
        extra = message["extra"]
    # add message to messages
    messages = read_messages()
    messages.append(
        {
            "content": message["content"],
            "sender": message["sender"],
            "timestamp": message["timestamp"],
            "extra": extra,
        }
    )
    save_messages(messages)
    return "OK", 200


def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, "r")
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages


def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, "w") as f:
        json.dump(messages, f)


@app.route("/story", methods=["GET"])
def get_game_state():
    #return the current game state
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({
        "story": story,
        "current_phase": current_phase,
        "submissions": submissions,
        "votes" : votes
    })


@app.route("/submit", methods=["POST"])
def submit_sentence():
    global current_phase, last_phase_change, submissions
    if not check_authorization(request):
        return "Invalid authorization", 400
    if current_phase != "submission":
        return "Submission phase is over. Voting is in progess.", 400
    data = request.json
    if not data or "content" not in data or "sender" not in data:
        return "Invalid request", 400
    sentence = data["content"]
    sender = data["sender"]
    #add sentences
    submissions.append({"sentence": sentence, "sender": sender})
    #check for submission limit
    if len(submissions) >= sentence_limit:
        current_phase = "voting"
        votes.clear()
        last_phase_change = time.time()
    save_game_state()
    return "Sentence submitted!", 200


@app.route("/vote", methods=["POST"])
def vote():
    global current_phase, last_phase_change, story, submissions, votes
    if not check_authorization(request):
        return "Invalid authorization", 400
    if current_phase != "voting":
        return "Voting is closed.", 400
    data = request.json
    if not data or "content" not in data:
        return "Invalid request", 400
    sentence = data["content"]
    #counting the votes
    if sentence in votes:
        votes[sentence] += 1
    else:
        votes[sentence] = 1
    #stop if all users voted or time limit reached:
    if len(votes) >= len(submissions) or (time.time() - last_phase_change > vote_time_limit):
        winning_sentence = max(votes, key=votes.get, default=None) #if there are several max -> randomly choose? / another voting?
        if winning_sentence:
            #add sentence to the story
            story.append(winning_sentence)
            #prepare and clear everything for the next round
            submissions = [] 
            votes = {}
            current_phase = "submission"
            last_phase_change = time.time()
    save_game_state()
    return "Thanks for voting!", 200
    

# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == "__main__":
    load_game_state()
    app.run(port=5001, debug=True)
