import uuid
import logging
import sys
from flask import Flask
from redis import Redis

# configures logging to use standard out. logs were
# lost before.
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Redis' IP is discovered by DNS, connection done 
# by service name within another service
cache = Redis(host="redis-cache", port=6379)

app = Flask(__name__)
app_id = str(uuid.uuid1())

@app.route("/")
def index():
    logging.debug(f"{app_id} INDEX ROUTE HIT")
    return f"Flask Server {app_id}"

@app.route("/get")
def get():
    logging.debug(f"{app_id} GET ROUTE HIT")
    val = cache.get("key")
    return f"got {val}: {app_id}"

@app.route("/set/<value>")
def set(value):
    logging.debug(f"{app_id} SET ROUTE HIT")
    cache.set("key", value)
    return f"set {value}: {app_id}"

# won't be used if using Gunicorn as
# WSGI server.
if __name__ == "__main__":
    app.run(port="5001", host="0.0.0.0")
