# some basic container image with 
# python interpreter and package manager
FROM python:3.11-alpine

WORKDIR /flaskapp

COPY ./app.py .

# in lieu of a requirements.txt file
RUN pip3 install Flask redis gunicorn

# when using a real WSGI server
# binds gunicorn to communicate on port 5001 (within container)
CMD [ "gunicorn", "--bind", ":5001", "app:app"]

# for debugging, no gunicorn
#CMD ["python3", "app.py"]
