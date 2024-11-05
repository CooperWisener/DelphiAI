from portfolio import app
from portfolio import db
from flask import render_template, url_for, redirect, request, session, flash, make_response
import base64
import requests
import json
from portfolio import helper
import jsonify
import os
from dotenv import load_dotenv

REDIRECT_URI = "http://127.0.0.1:5000/callback"
load_dotenv()

class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))

    def __init__(self, name, email):
        self.name = name
        self.email = email


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/login')
def login():
    client_id = os.getenv("CLIENT_ID")
    scope = 'user-read-recently-played user-top-read'

    auth_url = f"https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={REDIRECT_URI}&scope={scope}"
    return redirect(auth_url)


@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Authorization code not found"}), 400
    
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_url = 'https://accounts.spotify.com/api/token'
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    token_headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        r = requests.post(token_url, data=token_data, headers=token_headers)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Token request failed", "message": str(e)}), 500

    token_response_data = r.json()
    if 'access_token' not in token_response_data:
        return jsonify({"error": "Access token not found in the response"}), 500

    session['access_token'] = token_response_data['access_token']
    return redirect(url_for('home'))


    
@app.route("/home", methods=["POST","GET"])
def home():
    return render_template("home.html")


@app.route("/plays")
def plays():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    plays_data = helper.get_plays(access_token)
    plays_dict = helper.extract_information_plays(plays_data) 
    return render_template('plays.html', items=plays_dict['items'])


@app.route("/analysis")
def analysis():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    timeframe = request.args.get('timeframe', '4weeks')  # Default to '4weeks' if not specified
    top_artists, top_tracks = helper.get_top_artists_and_tracks(timeframe, access_token)

    plays_data = helper.get_plays(access_token)
    plays_ids = helper.get_songs_ids(plays_data)

    audio_feats = helper.get_audio_feats(access_token, plays_ids)

    audio_feats_avg = helper.audio_feats_avg(audio_feats)
    audio_feats_main = helper.audio_feats_display(audio_feats_avg)
    tempo = helper.get_tempo_name(audio_feats_main["tempo"])
    return render_template('analysis.html', 
                           top_artists=top_artists, 
                           top_tracks=top_tracks, 
                           tempo_string=tempo,
                           dictionary=audio_feats_main)


@app.route("/discover")
def discover():
    return render_template("discover.html")


@app.route("/discover_plays")
def discover_plays():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))
    
    plays_data = helper.get_plays(access_token)
    plays_names = helper.get_song_names(plays_data)
    rec_songs = helper.get_reccomendations_songs(plays_names)
    artists, songs = helper.parse_artists_and_songs(rec_songs)

    return render_template('discover_plays.html', artists=artists, songs=songs)
    


@app.route("/discover_favs")
def discover_favs():
    return render_template("discover_favs.html")

@app.route('/discover-results')
def discover_results():
    query = request.args.get('query')
    recommendations = helper.get_reccomendations_input(query)
    artists, songs = helper.parse_artists_and_songs(recommendations)
    
    return render_template('discover_plays.html', artists=artists, songs=songs)

# @app.route("/logout")
# def logout():
#     if "user" not in session:
#         return redirect(url_for("login"))
#     session.pop("access_token", None)
#     response = make_response(redirect(url_for('index')))
#     response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
#     response.headers['Pragma'] = 'no-cache'
#     response.headers['Expires'] = 'Thu, 01 Dec 2050 16:00:00 GMT'
#     return response

@app.route('/logout')
def logout():
    access_token = session.pop('auth_token', None)
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if access_token:
        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode()).decode()

        headers = {
            "Authorization": f"Basic {client_creds_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "token": access_token,
            "token_type_hint": "access_token"
        }
        revoke_response = requests.post('https://accounts.spotify.com/api/token/revoke', headers=headers, data=data)
        

        print(f"Status Code: {revoke_response.status_code}")
        print(f"Response: {revoke_response.text}")

    return redirect(url_for('index'))


@app.route('/top-tracks')
def top_tracks():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    top_tracks_url = 'https://api.spotify.com/v1/me/top/tracks'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    r = requests.get(top_tracks_url, headers=headers)
    top_tracks_data = r.json()
    return json.dumps(top_tracks_data, indent=4)

# @app.route("/login", methods=["POST","GET"])
# def login():
#     if request.method == "POST":
#         session.permanent = True
#         user = request.form["username"]
#         password = request.form["password"]
#         session["user"] = user
#         session["password"] = password
#         flash("Login Successful!")
#         return redirect(url_for("home"))
#     else:
#         if "user" in session:
#             flash("Already Logged In!")
#             return redirect(url_for("home"))
#         return render_template("index.html")
