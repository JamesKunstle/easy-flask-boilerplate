# Purpose

Document the mile-markers of progress in this project.
These are high-level goals- issues should be created in their service.

# List

- Use Kompose to create Helm charts from docker-compose, or write bespoke.
- Add celery background workers and configure correctly for reasonable-effor deployment

# Finished

- Containerize Flask application
- Compose Flask application
- Connect Flask application to Redis instance via DNS
- Add load balancer in front of Flask application for scalability
- Run Flask app w/ gunicorn
- Configure a non-default compose network
- enable Flask app logging w/ 'logging' package
- Flask-Login w/ Redis as user session storage.
- Add generic OAuth handling, /login and /register
