import datetime
import json
import os
import pytz
import requests

import firebase_admin
from firebase_admin import credentials, auth, exceptions, db
import flask
from flask import Flask, render_template, make_response, request, redirect, flash, url_for, Markup
import pandas as pd
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

def format_server_time() -> str:
    """
    Formats the server time as a string of HH:MM, followed by AM or PM. Assumes US East Coast
    """
    server_time = datetime.datetime.now(tz=pytz.timezone("US/Eastern"))
    return server_time.strftime("%I:%M %p")

@app.route("/")
def index():
    # A good example of how to use the cache. This is great because it will let us cache information and not
    # rerun code for every page load
    # The Citi Bike API should only be updating every 5 minutes (ish) so we can limit our page to store in the cache
    # every 5 minutes!
    template = render_template("index.html")
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

    except auth.InvalidSessionCookieError as e:
        # Session cookie is invalid, expired or revoked. Force user to login.
        print("ERROR")
        print(e)
        print("Invalid session cookie")
        response = {"error": e}
        return response

    user_uid = decoded_claims.get("uid", None)
    user_db_data = _get_user_db_data(user_uid)

    stations_list = _get_station_list(user_db_data)

    # getting station information
    top_station_status_df = _get_station_status(stations_list)

    context = {
        "server_time": format_server_time(),
        "name": user_db_data.get("name", "You"),
        "first_station": stations_list[0],
        "second_station": stations_list[1],
        "third_station": stations_list[2],
        "first_station_bikes": top_station_status_df['num_bikes_available'][0],
        "first_station_ebikes": top_station_status_df['num_ebikes_available'][0],
        "first_station_lat": top_station_status_df['lat'][0],
        "first_station_lon": top_station_status_df['lon'][0],
        "first_station_parking": top_station_status_df['num_docks_available'][0],
        "second_station_bikes": top_station_status_df['num_bikes_available'][1],
        "second_station_ebikes": top_station_status_df['num_ebikes_available'][1],
        "second_station_parking": top_station_status_df['num_docks_available'][1],
        "third_station_bikes": top_station_status_df['num_bikes_available'][2],
        "third_station_ebikes": top_station_status_df['num_ebikes_available'][2],
        "third_station_parking": top_station_status_df['num_docks_available'][2],
    }

    response = make_response(render_template("dashboard.html", context=context))
    # TODO: fix cache control
    # response.headers["Cache-Control"] = "public, max-age=300, s-maxage=300"
    return response

def _get_user_db_data(user_uid: str) -> dict:
    user_ref = db.reference(f'/users/{user_uid}')
    user_db_data = user_ref.get()
    return user_db_data

def _get_station_list(user_db_data: dict) -> list:
    return [
        user_db_data.get("first_station", FIRST_STATION),
        user_db_data.get("second_station", SECOND_STATION),
        user_db_data.get("third_station", THIRD_STATION)
    ]

def _get_station_status(stations_list: list):
    # Ping CitiBike API
    status_url = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"
    station_status_url = requests.get(status_url).json()
    status_cols = ['station_id','num_docks_available','num_bikes_available','num_ebikes_available']

    info_url = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
    station_info_url = requests.get(info_url).json()
    cols = ['station_id','name','lat','lon','capacity']

    # Get station info
    station_data_df = pd.DataFrame(station_info_url['data']['stations'])
    station_data_df = station_data_df[cols]
    stations_list_df = station_data_df.loc[station_data_df['name'].isin(stations_list)]

    # Get bike status for stations
    stations_status_df = pd.DataFrame(station_status_url['data']['stations'])
    stations_status_df = stations_status_df[status_cols]
    stations_list_status_df = stations_list_df.merge(stations_status_df, how='left', on='station_id')
    
    # return df with top three station information and status in order of preference
    final_stations_df = stations_list_status_df.loc[stations_list_status_df['name']==stations_list[0]]
    final_stations_df = final_stations_df.append(stations_list_status_df.loc[stations_list_status_df['name']==stations_list[1]])
    final_stations_df = final_stations_df.append(stations_list_status_df.loc[stations_list_status_df['name']==stations_list[2]])
    final_stations_df = final_stations_df.reset_index()

    return final_stations_df

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

@app.route("/sessionLogout", methods=["GET"])
def session_logout():
    if request.method=="GET":
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
