import os
import time

from flask import Flask, render_template

app = Flask(__name__)

def format_server_time():
  server_time = time.localtime()
  return time.strftime("%I:%M:%S %p", server_time)

@app.route("/")
def homepage():
    context = { 'server_time': format_server_time() }
    return render_template("main.html", context=context)

@app.route("/sign-in")
def sign_in():
    return render_template("sign-in.html")

@app.route("/sign-up")
def sign_up():
    return render_template("sign-up.html")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
