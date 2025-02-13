## channel.py - a simple message channel
##


from flask import Flask, request, render_template, jsonify
import json
import requests
from werkzeug.wrappers import response
from better_profanity import profanity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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
CHANNEL_NAME = "Tell Tale Chain"
CHANNEL_ENDPOINT = (
    "http://localhost:5001"  # don't forget to adjust in the bottom of the file
)
CHANNEL_FILE = "messages.json"
CHANNEL_TYPE_OF_SERVICE = "aiweb24:chat"

MAX_MESSAGES = 4  # maximum number set to 10 only to not consume too many resources

WELCOME_MESSAGE = {
    "content": "Welcome Tell Tale Chain Channel, continue the story!",
    "sender": "System",
}


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


# msg filter
def filter_message(message):
    censored_message = profanity.censor(message)

    return censored_message


# response generator
def generate_response():
    messages = read_messages()
    if not messages:
        return WELCOME_MESSAGE

    latest_msg = messages[-1]
    response = {
        "content": f"Story similarity score: {latest_msg.get('similarity', 1.0):.2f}",
        "sender": "System",
        "timestamp": latest_msg["timestamp"],
        "extra": None,
    }

    return response


# approach in coherence check by checking similarity, not best apprach but "lightweight"
# check similarity value of new message with TfidfVectorizer
def calc_similarity(new_message):
    messages = read_messages()

    # get only user messages exclude system msgs
    # user_messages = [msg for msg in messages if msg["sender"] != "System"]

    # filter user content directly
    user_content = [
        msg["content"] for msg in messages if msg["sender"].lower() != "system"
    ]

    print(user_content)
    # return 100% for first message
    if not user_content:
        return 100

    # last_message = user_content[-1]
    # print(last_message)

    updated_convo = user_content + [new_message]
    print(updated_convo)
    # transform messages
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(updated_convo)

    # calculate cosine similarity, to have an approach of coherence
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    # return a percentage value
    similarity_percentage = similarity * 100

    return similarity_percentage


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

    # filter the message content before saving
    filtered_msg = filter_message(message["content"])

    # check coherence by checking similarity
    similarity = calc_similarity(filtered_msg)

    # add message to messages
    messages = read_messages()
    messages.append(
        {
            "content": filtered_msg,
            "sender": message["sender"],
            "timestamp": message["timestamp"],
            #            "coherence factor": similarity,
        }
    )

    system_response = generate_response()
    messages.append(
        {
            "content": system_response["content"],
            "sender": system_response["sender"],
            "timestamp": message["timestamp"],  # Using same timestamp for simplicity
            "similarity": similarity,  # System messages don't need similarity check
            # "extra": system_response.get("extra"),
        }
    )
    save_messages(messages)
    return jsonify(system_response, 200)


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

    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]

    with open(CHANNEL_FILE, "w") as f:
        json.dump(messages, f)


# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == "__main__":
    app.run(port=5001, debug=True)
