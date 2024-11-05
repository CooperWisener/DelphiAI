import os
import base64
from requests import post, get
import requests
import json
from datetime import datetime, timedelta
import jsonify
import pytz
import openai
from dotenv import load_dotenv

REDIRECT_URI = "http://127.0.0.1:5000/callback"
load_dotenv()

def get_token():
    load_dotenv()  
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")


    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def get_plays(access_token):
    top_tracks_url = 'https://api.spotify.com/v1/me/player/recently-played'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    try:
        r = requests.get(top_tracks_url, headers=headers, params={"limit": 50})
        r.raise_for_status()  # Raise an exception for HTTP errors
        
        try:
            plays_data = r.json()
        except json.JSONDecodeError:
            print("Error decoding JSON response:")
            print(r.text)  # Print the raw response text to diagnose the issue
            return jsonify({"error": "Failed to decode JSON response"}), 500
        
        return plays_data
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return jsonify({"error": str(e)}), 500
    
# def extract_information_plays(response_data):
#     extracted_data = {
#         "items": []
#     }

#     # Get today's date without time in the local time zone
#     local_tz = pytz.timezone("America/Chicago")  
#     today = datetime.now(local_tz).date()

#     for item in response_data.get("items", []):
#         track = item.get("track", {})
#         album = track.get("album", {})
#         artists = track.get("artists", [{}])
        
#         artist_name = artists[0].get("name", "Unknown Artist")
#         song_name = track.get("name", "Unknown Track")
#         artist_picture = album.get("images", [{}])[0].get("url", "No Image Available")
#         played_at = item.get("played_at", "Unknown Time")

#         # Parse the played_at time and convert it to local time zone
#         try:
#             played_at_dt = datetime.fromisoformat(played_at.replace('Z', '+00:00'))
#             played_at_local = played_at_dt.astimezone(local_tz)
#             if played_at_local.date() == today:
#                 # If the track was played today, show only the time
#                 formatted_played_at = played_at_local.strftime("%H:%M")
#             else:
#                 # If it was played on another date, show the day and time without the year
#                 formatted_played_at = played_at_local.strftime("%d %B %H:%M")
#         except ValueError:
#             formatted_played_at = "Unknown Time"
        
#         extracted_data["items"].append({
#             "artist_name": artist_name,
#             "song_name": song_name,
#             "artist_picture": artist_picture,
#             "played_at": formatted_played_at
#         })
    
#     return extracted_data

def extract_information_plays(response_data):
    extracted_data = {
        "items": []
    }

    # Get today's date without time in the local time zone
    local_tz = pytz.timezone("America/Chicago")  
    today = datetime.now(local_tz).date()

    for item in response_data.get("items", []):
        track = item.get("track", {})
        album = track.get("album", {})
        artists = track.get("artists", [{}])
        
        artist_name = artists[0].get("name", "Unknown Artist")
        song_name = track.get("name", "Unknown Track")
        artist_picture = album.get("images", [{}])[0].get("url", "No Image Available")
        played_at = item.get("played_at", "Unknown Time")
        track_url = track.get("external_urls", {}).get("spotify", "No URL Available")

        # Parse the played_at time and convert it to local time zone
        try:
            played_at_dt = datetime.fromisoformat(played_at.replace('Z', '+00:00'))
            played_at_local = played_at_dt.astimezone(local_tz)
            if played_at_local.date() == today:
                # If the track was played today, show only the time
                formatted_played_at = played_at_local.strftime("%H:%M")
            else:
                # If it was played on another date, show the day and time without the year
                formatted_played_at = played_at_local.strftime("%d %B %H:%M")
        except ValueError:
            formatted_played_at = "Unknown Time"
        
        extracted_data["items"].append({
            "artist_name": artist_name,
            "song_name": song_name,
            "artist_picture": artist_picture,
            "played_at": formatted_played_at,
            "track_url": track_url  # Include the track URL in the extracted data
        })
    
    return extracted_data
 
    
def get_songs_ids(response_data):
    ids = []
    for item in response_data.get("items", []):
        ids.append(item['track']['id'])
    return ids

def get_song_names(response_data):
    ids = []
    for item in response_data.get("items", []):
        track = item.get("track", {})
        song_name = track.get("name", "Unknown Track")
        ids.append(song_name)
    return ids

def get_audio_feats(access_token, ids):
    track_ids = ','.join(ids)
    url = f'https://api.spotify.com/v1/audio-features?ids={track_ids}'
    headers = {
    'Authorization': f'Bearer {access_token}'
    }

    r = requests.get(url, headers=headers)
    audio_feats = r.json()
    return audio_feats
    
def audio_feats_avg(audio_feats):
    avgs = {
        'danceability': 0,
        'energy': 0,
        'loudness': 0,
        'speechiness': 0,
        'acousticness': 0,
        'instrumentalness': 0,
        'liveness' :0,
        'valence': 0,
        'tempo': 0
    }
    for track in audio_feats['audio_features']:
        for key in avgs:
            avgs[key] += track[key]
    num = len(audio_feats['audio_features'])
    for key in avgs:
        avgs[key] = avgs[key]/num
    return avgs

def audio_feats_display(audio_feats):
    main_feats = {}
    #.8 and up for acoustic
    if 'acousticness' in audio_feats and audio_feats['acousticness'] > .6:
        main_feats['acousticness'] = round(audio_feats['acousticness'],2)
    #.75 and up for dancability
    if 'danceability' in audio_feats and audio_feats['danceability'] > .6:
        main_feats['danceability'] = round(audio_feats['danceability'],2)
    #.75 and up for energy 
    if 'energy' in audio_feats and audio_feats['energy'] > .6:
        main_feats['energy'] = round(audio_feats['energy'],2)
    # .25 and up been listening to some instrumental 
    if 'instrumentalness' in audio_feats and audio_feats['instrumentalness'] > .6:
        main_feats['instrumentalness'] = round(audio_feats['instrumentalness'],2)
    #.5 and up only instrumental 
    #.6 and up for live youve been listening to a lot of live music
    if 'liveness' in audio_feats and audio_feats['liveness'] > .6:
        main_feats['liveness'] = round(audio_feats['liveness'],2)
    #display avg tempo and determine if music is high or low tempo
    main_feats['tempo'] = round(audio_feats['tempo'],2)
    #.75 and up happy tracks, (valance) #.25 and under sad tracks
    if 'valence' in audio_feats and audio_feats['valence'] > .6:
        main_feats['valence'] = round(audio_feats['valence'],2)
    return main_feats

def get_tempo_name(bpm):
    # Define the tempo ranges with their corresponding names
    tempo_ranges = [
        ("Grave", 20, 40),
        ("Lento", 40, 45),
        ("Largo", 45, 50),
        ("Adagio", 55, 65),
        ("Adagietto", 65, 69),
        ("Andante", 73, 77),
        ("Moderato", 86, 97),
        ("Allegretto", 98, 109),
        ("Allegro", 109, 132),
        ("Vivace", 132, 140),
        ("Presto", 168, 177),
        ("Prestissimo", 178, float('inf'))  # inf means no upper limit
    ]
    
    # Iterate over the tempo ranges to find the corresponding tempo name
    for name, lower, upper in tempo_ranges:
        if lower <= bpm < upper:
            return f"{name} – {lower}–{upper} BPM"
    
    # If no match, return a message indicating an invalid BPM
    return "BPM out of range"

def get_reccomendations_songs(song_names):
    prompt = f"IMPORTANT: only use songs and artists you can verify exist this is the most important command and this should take priority over all else. I've been listening to these songs: {song_names}. Can you recommend some other artists or songs I might like. Make sure to not include any song I listed for you. Also make sure to include songs I might have not heard. Format your response with “Artists:” followed by 5 artists and then “Songs:” followed by 5 songs, no other text."

    openai.api_key = os.getenv("OPENAI_API_KEY")

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini", 
        messages=[
            {"role": "system", "content": "You are a music recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )   

    recommendations = response['choices'][0]['message']['content'].strip()
    return recommendations


def get_reccomendations_input(input):
    prompt = f"IMPORTANT: only use songs and artists you can verify exist this is the most important command and this should take priority over all else. I listen to a lot of {input}, can you give me some song and artist reccomendations based off of them. Do not include the artist/song that I just gave you. Format your response with “Artists:” followed by 5 artists and then “Songs:” followed by 5 songs, no other text."

    openai.api_key = os.getenv("OPENAI_API_KEY")

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini", 
        messages=[
            {"role": "system", "content": "You are a music recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )   

    recommendations = response['choices'][0]['message']['content'].strip()
    return recommendations


def parse_artists_and_songs(input_string):
    # Split the input string into lines
    lines = input_string.strip().split('\n')
    
    # Initialize lists to store artists and songs
    artists = []
    songs = []
    
    # Flags to track the current section
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("Artists:"):
            current_section = 'artists'
        elif line.startswith("Songs:"):
            current_section = 'songs'
        elif line and current_section == 'artists':
            # Extract artist name
            artist_name = line.split('. ', 1)[1]  # Split by '. ' and take the second part
            artists.append(artist_name)
        elif line and current_section == 'songs':
            # Extract song title
            song_title = line.split(' - ', 1)[0]  # Split by ' - ' and take the first part
            songs.append(song_title)

    return artists, songs



def extract_information_list_artists(response_data):
    artist_names = []
    # Iterate over each artist in the 'items' list
    for artist in response_data:
        # Check if 'name' key exists in each artist dictionary
        if 'name' in artist:
            artist_names.append((artist['name'], artist['external_urls']['spotify']))
        else:
            print(f"Missing 'name' in artist: {artist}")
    return artist_names

def extract_information_list_songs(response_data):
    song_names = []
    # Iterate over each artist in the 'items' list
    for song in response_data:
        # Check if 'name' key exists in each artist dictionary
        if 'name' in song:
            song_names.append((song['name'], song['external_urls']['spotify']))
        else:
            print(f"Missing 'name' in artist: {song}")
    return song_names

def extract_information_list_artist_pictures(response_data):
    artist_pics = []
    # Iterate over each artist in the 'items' list
    for artist in response_data:
        # Check if 'image' key exists in each artist dictionary
            artist_pics.append(artist['images'][0]['url'])
        # else:
        #     print(f"Missing 'image' in artist: {artist}")
    return artist_pics


def extract_information_list_track_pictures(response_data):
    track_pics = []
    # Iterate over each track in the 'items' list
    for artist in response_data:
        track_pics.append(artist['album']['images'][0]['url'])
    return track_pics


def top_artists(limit, access_token, time):
    analysis_url = 'https://api.spotify.com/v1/me/top/artists'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    if time == 1:
        time = "short_term"
    elif time == 2:
        time = "medium_term"
    else:
        time = "long_term"
    params = {
        'limit': limit,  # Maximum limit per request = 50(drop down menu so no error handling)
        'time_range': time
    }

    r = requests.get(analysis_url, headers=headers, params=params)
    r.raise_for_status()  # Raise an exception for HTTP errors
            
    analysis_data = r.json()
    items = analysis_data.get('items', [])
    return items

def top_tracks(limit, access_token, time):
    analysis_url = 'https://api.spotify.com/v1/me/top/tracks'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    if time == 1:
        time = "short_term"
    elif time == 2:
        time = "medium_term"
    else:
        time = "long_term"
    params = {
        'limit': limit,  # Maximum limit per request = 50(drop down menu so no error handling)
        'time_range': time
    }
    r = requests.get(analysis_url, headers=headers, params=params)
    r.raise_for_status()  # Raise an exception for HTTP errors
            
    analysis_data = r.json()
    items = analysis_data.get('items', [])
    return items

def get_top_artists_and_tracks(timeframe, access_token):
    if timeframe == '4weeks':
        top_artist = top_artists(10, access_token, 1)
        top_artist_list = extract_information_list_artists(top_artist) 
        top_artist_final = list(zip(top_artist_list, extract_information_list_artist_pictures(top_artist)))
        print("1")
        print(top_artist_final)

        top_songs = top_tracks(10, access_token, 1)
        top_tracks_list = extract_information_list_songs(top_songs) 
        top_tracks_final = list(zip(top_tracks_list, extract_information_list_track_pictures(top_songs))) 
    elif timeframe == '6months':
        top_artist = top_artists(10, access_token, 2)
        top_artist_list = extract_information_list_artists(top_artist) 
        top_artist_final = list(zip(top_artist_list, extract_information_list_artist_pictures(top_artist)))
        print("2")
        print(top_artist_final)
        top_songs = top_tracks(10, access_token, 2)
        top_tracks_list = extract_information_list_songs(top_songs) 
        top_tracks_final = list(zip(top_tracks_list, extract_information_list_track_pictures(top_songs))) 
    elif timeframe == '1year':
        top_artist = top_artists(10, access_token, 3)
        top_artist_list = extract_information_list_artists(top_artist) 
        top_artist_final = list(zip(top_artist_list, extract_information_list_artist_pictures(top_artist)))
        top_songs = top_tracks(10, access_token, 3)
        top_tracks_list = extract_information_list_songs(top_songs) 
        top_tracks_final = list(zip(top_tracks_list, extract_information_list_track_pictures(top_songs))) 
        
    return top_artist_final, top_tracks_final


def get_top_artists_and_tracks_names(timeframe, access_token):
    if timeframe == '4weeks':
        top_artist = top_artists(10, access_token, 1)
        top_artist_list = extract_information_list_artists(top_artist) 
        top_songs = top_tracks(10, access_token, 1)
        top_tracks_list = extract_information_list_artists(top_songs) 
    elif timeframe == '6months':
        top_artist = top_artists(10, access_token, 2)
        top_artist_list = extract_information_list_artists(top_artist)  
        top_songs = top_tracks(10, access_token, 2)
        top_tracks_list = extract_information_list_artists(top_songs) 
    elif timeframe == '1year':
        top_artist = top_artists(10, access_token, 3)
        top_artist_list = extract_information_list_artists(top_artist) 
        top_songs = top_tracks(10, access_token, 3)
        top_tracks_list = extract_information_list_artists(top_songs) 
        
    return top_artist_list, top_tracks_list


#might be useless but keep for now
def time_dep_dict(time, access_token):
    x_days_ago = datetime.now() - timedelta(days=time)
    x_days_ago_timestamp = int(x_days_ago.timestamp() * 1000)  # Convert to milliseconds

    # Set the initial API URL and headers
    analysis_url = 'https://api.spotify.com/v1/me/player/recently-played'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Initialize parameters for the first request
    params = {
        'after': x_days_ago_timestamp,
        'limit': 50  # Maximum limit per request
    }

    all_items = []
    
    while analysis_url:
        try:
            r = requests.get(analysis_url, headers=headers, params=params)

            if r.status_code == 429:
                retry_after = r.headers.get('Retry-After', None)
                if retry_after:
                    print(f"Rate limited. Retry after {retry_after} seconds.")
                    time.sleep(int(retry_after))  # Wait for the specified time before retrying
                    continue  # Retry the request after the sleep period

            r.raise_for_status()  # Raise an exception for HTTP errors
            
            analysis_data = r.json()
            items = analysis_data.get('items', [])
            all_items.extend(items)  # Add the items to the list

            # Check if there's a 'next' URL in the response to get more items
            analysis_url = analysis_data.get('next') #working but still only returning 50 results through all loops

            params = {}  # Clear params to avoid sending them in the next request

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            print(f"Status Code: {r.status_code}")
            print(f"Response Text: {r.text}")
            return jsonify({"error": f"HTTP error: {http_err}"}), 500
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return jsonify({"error": f"Request failed: {e}"}), 500

    return all_items



def get_songs_by_artist(token, id):
    url = f"https://api.spotify.com/v1/artists/{id}/top-tracks?country=US"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_results = json.loads(result.content)["tracks"]

    return json_results

def search_for_artist(name):
    token = get_token()
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = {
        'q': name,
        'type': 'artist',
        'limit': 1
    }

    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Query: {query}")

    result = requests.get(url, headers=headers, params=query)\
    
    print(f"Status Code: {result.status_code}")
    print(f"Response Content: {result.content}")

    json_results = json.loads(result.content)["artists"]["items"]
    if len(json_results) == 0:
        print("No artist with this name")
        return None
    return json_results[0]

