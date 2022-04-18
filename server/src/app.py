import json
import os
import time

import firebase_admin
from firebase_admin import credentials, auth, exceptions
from flask import Flask, render_template, make_response, request, redirect, flash, url_for, Markup
# import pyrebase

app = Flask(__name__)

# Required for things like flash
SECRET_KEY = "webeb1king@llday3verydayalri6ht"
app.secret_key = SECRET_KEY


LOCAL = os.environ.get("LOCAL", True)
if LOCAL:
    cred_filepath = "./server/config/firebase_admin_config.json"
else:
    cred_filepath = "./config/firebase_admin_config.json"

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred)
# pb = pyrebase.initialize_app(json.load(open("./config/firebase_config.json")))

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

@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    return render_template("sign-in.html")

@app.route("/sign-up")
def sign_up():
    return render_template("sign-up.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 6:
            # TODO: Need to understand why flash messages show up in Cloud Run but not Firebase Hosting
            flash("Password must be at least 6 characters long!")
            return redirect(url_for("sign_up"))

        try:
            user = auth.create_user(email=email, password=password)
            flash("Welcome to CytyByke!")
            return redirect(url_for("settings"))
        
        except exceptions.AlreadyExistsError:
            print("USER ALREADY EXISTS")
            #TODO: Is Markup the right thing to use here to embed a link in a flash message?
            flash(Markup("User already exists! Please try again with a new email or <a href='sign-in'>sign-in</a>."))
            return redirect(url_for("sign_up"))

        except Exception as e:
            print(e)
            flash("Unknown error! Please try again.")
            return redirect(url_for("sign_up"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
