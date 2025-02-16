from flask import Flask, jsonify
import os

app = Flask(__name__)


@app.route("/home")
def home():
    SERVER_ID = os.environ["SERVER_ID"]

    response = {"message": f"Hello from Server: {SERVER_ID}", "status": "successful"}
    return jsonify(response), 200


@app.route("/heartbeat")
def heartbeat():
    return jsonify({}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
