from flask import Flask
from datetime import timedelta

# create instance of flask
app = Flask(__name__)
app.secret_key = "7918hArt"
app.permanent_session_lifetime = timedelta(days=1)
from portfolio import routes


