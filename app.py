import uuid
import logging
import requests
import secrets
import sys
import os
from dotenv import load_dotenv
from flask import Flask, url_for, redirect, abort, session, request, flash, current_app
from redis import Redis
from flask_login import current_user, LoginManager, logout_user
from flask_cors import CORS
from urllib.parse import urlencode

load_dotenv()

# configures logging to use standard out. logs were
# lost before.
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

app = Flask(__name__)
app.config["SECRET_KEY"] = "top secret!"
app.config["OAUTH2_PROVIDERS"] = {
    "augur": {
        "client_id": os.environ.get("OAUTH_CLIENT_ID"),
        "client_secret": os.environ.get("OAUTH_CLIENT_SECRET"),
        "authorize_url": "https://eightknot.chaoss.tv/user/authorize",
        "token_url": "https://eightknot.chaoss.tv/api/unstable/user/session/generate",
        "redirect_uri": "127.0.0.1:5001/callback",
    }
}

CORS(app)

login = LoginManager(app)
login.login_view = "index"

APP_ID = str(uuid.uuid1())

# Redis' IP is discovered by DNS, connection done
# by service name within another service
cache = Redis(host="redis-cache", port=6379)


"""
OAUTH MANAGEMENT STUFF

Credit to Miguel Grinberg's implementation:
https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023

Licensed MIT.

His code made this implementation work very nicely.
"""


@login.user_loader
def load_user(id):
    # return the JSON of a user that was set in the Redis instance
    return cache.get(int(id))


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("index"))


@app.route("/authorize/")
def oauth2_authorize():
    provider = "augur"

    if not current_user.is_anonymous:
        return redirect(url_for("index"))

    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    # generate a random string for the state parameter
    session["oauth2_state"] = secrets.token_urlsafe(16)

    # create a query string with all the OAuth2 parameters
    qs = urlencode(
        {
            "client_id": provider_data["client_id"],
            # "redirect_uri": url_for("oauth2_callback", _external=True),
            "response_type": "code",
            # "state": session["oauth2_state"],
        }
    )

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data["authorize_url"] + "?" + qs)


@app.route("/callback/")
def oauth2_callback():
    provider = "augur"

    if not current_user.is_anonymous:
        return redirect(url_for("index"))

    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if "error" in request.args:
        for k, v in request.args.items():
            if k.startswith("error"):
                flash(f"{k}: {v}")
        return redirect(url_for("index"))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    # if request.args["state"] != session.get("oauth2_state"):
    #     abort(401)

    # make sure that the authorization code is present
    if "code" not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    response = requests.post(
        provider_data["token_url"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": request.args["code"],
            "grant_type": "code",
            "redirect_uri": url_for("oauth2_callback", _external=True),
        },
        headers={
            "Accept": "application/json",
            "Authorization": f"Client {provider_data['client_secret']}",
        },
    )
    if response.status_code != 200:
        abort(401)
    oauth2_token = response.json().get("access_token")
    if not oauth2_token:
        abort(401)

    # return redirect(url_for("index"))
    return f"YOU'RE LOGGED IN: {oauth2_token}"


"""
BASIC ROUTES
"""


@app.route("/")
def index():
    logging.debug(f"{APP_ID} INDEX ROUTE HIT")
    return f"Flask Server {APP_ID}"


@app.route("/get")
def get():
    logging.debug(f"{APP_ID} GET ROUTE HIT")
    val = cache.get("key")
    return f"got {val}: {APP_ID}"


@app.route("/set/<value>")
def set(value):
    logging.debug(f"{APP_ID} SET ROUTE HIT")
    cache.set("key", value)
    return f"set {value}: {APP_ID}"


# won't be used if using Gunicorn as
# WSGI server.
if __name__ == "__main__":
    app.run(port=5001, host="0.0.0.0")
