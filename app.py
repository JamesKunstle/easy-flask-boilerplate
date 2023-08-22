import uuid
import logging
import requests
import secrets
import sys
import os
import json
from dotenv import load_dotenv
from flask import Flask, url_for, redirect, abort, session, request, flash, current_app
from redis import Redis
from flask_login import (
    current_user,
    LoginManager,
    logout_user,
    login_user,
    UserMixin,
    login_required,
)
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from urllib.parse import urlencode

load_dotenv()

# configures logging to use standard out. logs were
# lost before.
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

app = Flask(__name__)
app.config["SECRET_KEY"] = "top secret!"
app.config["OAUTH2_PROVIDERS"] = {
    os.environ.get("OAUTH_CLIENT_NAME"): {
        "client_id": os.environ.get("OAUTH_CLIENT_ID"),
        "client_secret": os.environ.get("OAUTH_CLIENT_SECRET"),
        "authorize_url": os.environ.get("OAUTH_AUTHORIZE_URL"),
        "token_url": os.environ.get("OAUTH_TOKEN_URL"),
        "redirect_uri": os.environ.get("OAUTH_REDIRECT_URI"),
    }
}

# handles cross-origin resource sharing
CORS(app)

# handles login
login = LoginManager(app)
login.login_view = "index"

# hashing functionality
bcrypt = Bcrypt(app)

THREAD_ID = str(uuid.uuid1())

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


class User(UserMixin):
    def __init__(self, un_hash):
        self.id = un_hash


@login.user_loader
def load_user(id):
    # return the JSON of a user that was set in the Redis instance
    if cache.exists(id):
        usn = json.loads(cache.get(id))["username"]
        return User(id)
    return None


@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        c_id = current_user.get_id()
        cache.delete(c_id)
        logout_user()
        logging.debug(f"USER {c_id} LOGGED OUT")
    return redirect(url_for("index"))


@app.route("/authorize/")
def oauth2_authorize():
    provider = os.environ.get("OAUTH_CLIENT_NAME")

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
    provider = os.environ.get("OAUTH_CLIENT_NAME")

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
    logging.debug("Received response from authorize endpoint")

    # check whether login worked
    if response.status_code != 200:
        abort(401)

    # if login worked, get the token
    resp = response.json()
    oauth2_token = resp.get("access_token")
    if not oauth2_token:
        abort(401)
    logging.debug("Got token from authorize endpoint")

    # get remaining credentials
    username = resp.get("username")
    oauth2_refresh = resp.get("refresh_token")
    oauth2_token_expires = resp.get("expires")

    # random ID used to identify user.
    id_number = str(uuid.uuid1())

    logging.debug("Creating new user")
    serverside_user_data = {
        "username": username,
        "access_token": oauth2_token,
        "refresh_token": oauth2_refresh,
        "expiration": oauth2_token_expires,
    }
    cache.set(id_number, json.dumps(serverside_user_data))

    # TODO: have to log in the user object w.r.t the un_hash
    login_user(User(id_number))
    logging.debug("User logged in")

    # return redirect(url_for("index"))
    return redirect(url_for("index"))


"""
BASIC ROUTES
"""


@app.route("/")
def index():
    logging.debug(f"{THREAD_ID} INDEX ROUTE HIT, {current_user.get_id()}")
    # return redirect(url_for("index"))
    if current_user.is_authenticated:
        return (
            f"YOU'RE LOGGED IN: {current_user.get_id()}" + f" Flask Server {THREAD_ID}"
        )
    return f"Flask Server {THREAD_ID}"


@app.route("/get")
def get():
    logging.debug(f"{THREAD_ID} GET ROUTE HIT")
    val = cache.get("key")
    return f"got {val}: {THREAD_ID}"


@app.route("/set/<value>")
def set(value):
    logging.debug(f"{THREAD_ID} SET ROUTE HIT")
    cache.set("key", value)
    return f"set {value}: {THREAD_ID}"


@app.route("/secret/")
@login_required
def secret_route():
    usn = json.loads(cache.get(current_user.get_id()))["username"]
    return f"Your username is: {usn}" + f" Flask Server {THREAD_ID}"


# won't be used if using Gunicorn as
# WSGI server.
if __name__ == "__main__":
    app.run(port=5001, host="0.0.0.0")
