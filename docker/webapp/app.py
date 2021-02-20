from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, World!"

@app.route("/help")
def help():
    return render_template("help.html", template_folder = "templates", appVersion="1.1")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
