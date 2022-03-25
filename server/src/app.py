import os
import time

from flask import Flask, render_template, make_response

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
