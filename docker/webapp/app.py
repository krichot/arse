from flask import Flask, render_template
import json

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", template_folder = "templates", config=configs)

@app.route("/settings")
def help():
    return render_template("settings.html", template_folder = "templates", configs=configs)

if __name__ == "__main__":

    # load configuration
    # Read configuration JSON
    with open('../config.json', 'r') as configFile:
        data = configFile.read()
    # Parse JSON file
    configs = json.loads(data)

    # run flask
    app.run(host='0.0.0.0', debug=True)
