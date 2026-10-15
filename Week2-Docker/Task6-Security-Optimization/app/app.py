import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(
        message="Task 6 security lab",
        version=os.getenv("APP_VERSION", "dev")
    )

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

@app.get("/config")
def config():
    # Report only whether the token exists.
    # Never return the token itself.
    return jsonify(
        api_token_configured=bool(os.getenv("API_TOKEN"))
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
