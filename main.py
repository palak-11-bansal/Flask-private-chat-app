from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, emit
import requests

app = Flask(__name__)
app.config["SECRET_KEY"] = "some_secret_value"
socketio = SocketIO(app, cors_allowed_origins="*")

# the url to which we make a POST request so that message gets saved in the database
ADD_MESSAGE_TO_DB_URL = (
    "https://www.elixarsystems.com/back/devplatform/store_message/"
)

# make a global users dict of user_profile_id vs users_session_id (from flask)
users_and_session_id = {}


@socketio.on("user_profile_id", namespace="/chat")
def receive_user_profile_id(user_profile_id):
    """
    This function adds the user's profile id to
    the global user_and_session_id dict. This is the first
    event to be triggered in the chat app.

    Args:
        user_profile_id (str): The profile id of the person in the database
    """
    users_and_session_id[user_profile_id] = request.sid
    print("User profile id added")
    print(users_and_session_id)


@socketio.on("private_message", namespace="/chat")
def private_message(payload):

    """
    Sends a private message

    Args:
        payload (dict): dict of recipient_profile_id, message, jwt_token of user
    """
    # the profile id of the sender whom is sending the message
    # needed to send message to sender to(using session id)
    sender_profile_id = payload["sender_profile_id"]
    # the profile id of the user to whom the message should be sent
    recipient_profile_id = payload["recipient_profile_id"]
    # message to be sent
    message = payload["message"]
    # jwt token of sender
    jwt_token_of_sender = payload["jwt_token"]
    sender_username = payload["sender_username"]
    # get the session id of the recipient
    recipient_session_id = users_and_session_id.get(recipient_profile_id)
    sender_session_id = users_and_session_id.get(sender_profile_id)

    if recipient_session_id:
        if add_message_to_db(
            jwt_token_of_sender, recipient_profile_id, message
        ):
            data_to_send = {"message": message, "username": sender_username}
            # data_to_sender = {"message" : message , "username" : sender_username }
            # data_to_recipient = {"message" : message , "username" : sender_username}
            emit(
                "new_private_message", data_to_send, room=recipient_session_id
            )
            emit("new_private_message", data_to_send, room=sender_session_id)
            print("Message sent successfully")
        else:
            print("there was error in adding data to db")
    else:
        print("User is offline")



def add_message_to_db(jwt_token_of_sender, recipient_profile_id, message):
    """
    Adds the message to the Django database by making a POST request to django backend.

    Args:
        jwt_token_of_sender (string): JWT token of the sender of message
        recipient_profile_id (string): The Profile ID of the recipient
        message (string): The text message that has been sent

    Returns:
        Boolean: True if the request to Django backend was successful
        and data got saved. False otherwise
    """
    auth_token = "Bearer {}".format(jwt_token_of_sender)
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_token,
    }
    body = {
        "receiver_profile_id": str(recipient_profile_id),
        "content": str(message),
        "receiver_online": "true",  # true for all requests now as user online / offline feature not implemented yet
    }
    # verify=False set due to ssl error
    r = requests.post(
        ADD_MESSAGE_TO_DB_URL, headers=headers, json=body, verify=False
    )
    if r.status_code == 200:
        return True
    return False


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    print("started")
