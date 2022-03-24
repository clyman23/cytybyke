from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def homepage():
    return render_template("main.html")

@app.route("/sign-in")
def sign_in():
    return render_template("sign-in.html")

@app.route("/sign-up")
def sign_up():
    return render_template("sign-up.html")


if __name__ == "__main__":
    app.run(debug=True)
