import datetime
import json
import os
import time

import firebase_admin
from firebase_admin import credentials, auth, exceptions, db
import flask
from flask import Flask, render_template, make_response, request, redirect, flash, url_for, Markup
import pyrebase

app = Flask(__name__)

# Required for things like flash
SECRET_KEY = "webeb1king@llday3verydayalri6ht"
app.secret_key = SECRET_KEY


# Default to Roosevelt Island Citi Bike station
FIRST_STATION = "Motorgate"
SECOND_STATION = "Roosevelt Island Tramway"
THIRD_STATION = "Southpoint Park"


LOCAL = os.environ.get("LOCAL", "local")
if LOCAL == "local":
    admin_cred_filepath = "./server/config/firebase_admin_config.json"
    other_cred_filepath = "./server/config/firebase_config.json"

else:
    admin_cred_filepath = "./config/firebase_admin_config.json"
    other_cred_filepath = "./config/firebase_config.json"

cred = credentials.Certificate(admin_cred_filepath)
firebase_admin.initialize_app(
    cred,
    {'databaseURL': 'https://cytybyke-c917e-default-rtdb.firebaseio.com/'}
)

other_cred = json.load(open(other_cred_filepath))
other_cred["serviceAccount"] = admin_cred_filepath
other_cred["databaseURL"] = ""
pb = pyrebase.initialize_app(other_cred)
pb_auth = pb.auth()

def format_server_time():
  server_time = time.localtime()
  return time.strftime("%I:%M:%S %p", server_time)

@app.route("/")
def index():
    context = { 'server_time': format_server_time() }
    # A good example of how to use the cache. This is great because it will let us cache information and not
    # rerun code for every page load
    # The Citi Bike API should only be updating every 5 minutes (ish) so we can limit our page to store in the cache
    # every 5 minutes!
    template = render_template("index.html", context=context)
    response = make_response(template)
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=600"
    return response

@app.route("/sign-in")
def sign_in():
    return render_template("sign-in.html")

@app.route("/sign-up")
def sign_up():
    return render_template("sign-up.html")

@app.route("/dashboard")
def dashboard():
    session_cookie = flask.request.cookies.get("__session")
    print("Hello from dashboard")

    if not session_cookie:
        # Session cookie is unavailable. Force user to login.
        print("No session cookie")
        return redirect(url_for("sign_in"))

    try:
        # decoded_claims will have the info specific to that user and their cookie
        decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
        user_uid = decoded_claims.get("uid", None)
        user_db_data = _get_user_stations(user_uid)
        context = {
            "name": user_db_data.get("name", "You"),
            "first_station": user_db_data.get("first_station", FIRST_STATION),
            "second_station": user_db_data.get("second_station", SECOND_STATION),
            "third_station": user_db_data.get("third_station", THIRD_STATION),
        }

        return render_template("dashboard.html", context=context)

    except auth.InvalidSessionCookieError as e:
        # Session cookie is invalid, expired or revoked. Force user to login.
        print("ERROR")
        print(e)
        print("Invalid session cookie")
        response = {"error": e}
        return response
        # return redirect(url_for("sign_in"))

def _get_user_stations(user_uid: str):
    user_ref = db.reference(f'/users/{user_uid}')
    user_db_data = user_ref.get()
    return user_db_data

# TODO: Repeated code to check session cookie can be updated using common function or decorator
@app.route("/settings")
def settings():
    session_cookie = flask.request.cookies.get("__session")

    if not session_cookie:
        # Session cookie is unavailable. Force user to login.
        print("No session cookie")
        return redirect(url_for("sign_in"))

    try:
        # decoded_claims will have the info specific to that user and their cookie
        decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
        return render_template("settings.html")

    except auth.InvalidSessionCookieError as e:
        print("ERROR")
        print(e)
        print("Invalid session cookie")
        # Session cookie is invalid, expired or revoked. Force user to login.
        return redirect(url_for("sign_in"))

@app.route("/sessionLogin", methods=["POST"])
def session_login():
    if request.method=="POST":
        # TODO: REMOVE PRINT
        # print(request.json)

        id_token = request.json["idToken"]
        expires_in = datetime.timedelta(days=5)

        try:
            session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
            # response = redirect(url_for("dashboard"))
            response = make_response({"status": "success"})
            expires = datetime.datetime.now() + expires_in
            # If secure=True, then you won't see it when you Inspect in the browser
            # IMPORTANT: CAN ONLY BE NAMED __session because of Firebase shtuff
            response.set_cookie(
                "__session", session_cookie, expires=expires, httponly=True#, secure=True
            )

            return response

        except exceptions.FirebaseError:
            return flask.abort(401, 'Failed to create a session cookie')

@app.route("/sessionLogout", methods=["POST"])
def session_logout():
    if request.method=="POST":
        response = redirect(url_for("sign_in"))
        response.set_cookie("__session", expires=0)
        return response

@app.route("/userDbCreation", methods=["POST"])
def user_db_creation():
    if request.method=="POST":
        user_uid = request.json["uid"]
        user_name = request.json["name"]
        first_station = request.json["first_station"]

        if not user_name:
            user_name = "You"

        if not first_station:
            first_station = FIRST_STATION

        users_ref = db.reference('/users')

        # Similar to a dict, use .set() or .update()
        users_ref.update({
            user_uid: {
                "name": user_name,
                "first_station": first_station,
                "second_station": SECOND_STATION,
                "third_station": THIRD_STATION,
            }
        })

        return {"status": "successful db creation!"}

@app.route("/updateUserDb", methods=["POST"])
def update_user_db():
    station_and_name_strings = ["first_station", "second_station", "third_station", "name"]

    if request.method=="POST":
        session_cookie = flask.request.cookies.get("__session")

        if not session_cookie:
            return redirect(url_for("settings"))

        decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
        user_uid = decoded_claims.get("uid", None)

        user_inputs = request.json

        updates = {
            station_or_name: user_inputs[station_or_name]
            for station_or_name in station_and_name_strings
            if user_inputs[station_or_name] != ''
        }

        user_ref = db.reference(f'/users/{user_uid}')

        user_ref.update(updates)

        return {"status": "successful db update!"}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
