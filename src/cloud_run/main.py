#gcloud builds submit --tag gcr.io/cloud-computing-project-458205/song-processor
#gcloud run deploy song-processor --image gcr.io/cloud-computing-project-458205/song-processor --platform managed --region europe-west3 --allow-unauthenticated
from flask import Flask, request
import base64
import json
import logging
import os
from video_handler import handle_youtube_url
from spotify_handler import get_track_metadata
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import secretmanager
import sys
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
from abracadabra.database import create_fingerprint_db
from abracadabra.recognize import index_single_song_gcp

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def get_secret(secret_id):
    """Retrieve a secret from Google Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = 'cloud-computing-project-458205'
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error retrieving {secret_id} secret: {str(e)}")
        raise

def fetch_youtube_video(title, artist):
    """Search for a YouTube video based on song title and artist."""
    try:
        api_key = get_secret("YOUTUBE_API_KEY")
        youtube = build('youtube', 'v3', developerKey=api_key)

        query = f"{title} {artist} official audio"
        search_response = (
            youtube.search()
            .list(q=query, part="id,snippet", maxResults=1, type="video")
            .execute()
        )
        
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                video_id = search_result["id"]["videoId"]
                video_title = search_result["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                return {"title": video_title, "url": video_url}
        
        return None
    except HttpError as e:
        logger.error(f"YouTube API error: {e.resp.status} - {e.content}")
        raise

@app.route("/", methods=["POST"])
def process_pubsub_message():
    envelope = request.get_json()
    logger.info(f"[Song Processor] Received envelope: {envelope}")
    if not envelope or "message" not in envelope:
        logger.error("No Pub/Sub message received")
        return "[Song Processor] Bad Request: no Pub/Sub message received", 400
    
    # Extract message data from Pub/Sub 
    pubsub_message = envelope['message']
    
    if 'data' not in pubsub_message:
        logger.warning("Empty Pub/Sub message received")
        return '[Song Processor] Success: No message data', 200
    
    try:
        # Decode message payload from base64
        message_data = base64.b64decode(pubsub_message['data']).decode('utf-8')
        logger.info(f"[Song Processor] Received message data: {message_data}")
        # track_metadata = {'Track URI': 'spotify:track:6NFyWDv5CjfwuzoCkw47Xf', 'Track Name': 'Delicate',
        #                   'Artist Name(s)': 'Taylor Swift', 'Album Name': 'reputation',
        #                   'Album Release Date': '2017-11-10',
        #                   'Album Image URL': 'https://i.scdn.co/image/ab67616d0000b273da5d5aeeabacacc1263c0f4b',
        #                   'Track Duration (ms)': 232253, 'Explicit': False, 'Popularity': 84, 'Artist Genres': [],
        #                   'youtube_url': 'https://www.youtube.com/watch?v=0KSOMA3QBU0',
        #                   'youtube_title': 'Taylor Swift - Delicate (Official Audio)'}

        try:
            song_info = json.loads(message_data)
            title = song_info.get('title')
            artist = song_info.get('artist')

            if not (title and artist):
                logger.error("[Song Processor] Title or artist is missing in the song info")
                return "Bad Request: Title or artist is missing", 400

            logger.info(f"[Song Processor] Processing song: {title} by {artist}")

            # 1. Search for song metadata via Spotify APIs
            track_metadata = get_track_metadata(title, artist)

            if not track_metadata:
                logger.warning(f"[Song Processor] No metadata found for '{title}' by '{artist}'")
                return "Bad Request: No metadata found for the song - probably niche song or not a song at all", 400
            # elif track_metadata['track_name'] != title or artist not in track_metadata['artist_names']:
            #     logger.warning(f"[Song Processor] Metadata mismatch for '{title}' by '{artist}' - Found '{track_metadata['track_name']}' by '{track_metadata['artist_names']}'")
            #     return "Bad Request: Metadata mismatch", 400

            # Log metadata
            logger.info(f"[Song Processor] Found metadata for '{title}' by '{artist}': {track_metadata}")

            # 2. Search for YouTube url via YouTube APIs
            try:
                video_info = fetch_youtube_video(title, artist)
                if video_info:
                    logger.info(f"Found YouTube video: {video_info['title']} - {video_info['url']}")
                    track_metadata['youtube_url'] = video_info['url']
                    track_metadata['youtube_title'] = video_info['title']
                else:
                    logger.warning(f"No YouTube videos found for '{title}' by '{artist}'")
                    return "Bad Request: No YouTube video found for the song", 400
            except Exception as e:
                logger.error(f"YouTube search error: {str(e)}")
                return "Internal Server Error: YouTube search failed", 500

            # 3. Download m4a file from YouTube
            # 4. Create fingerprint of the audio file
            # 5. Upload song data and fingerprint to the database
            db = create_fingerprint_db(db_type="gcp")
            if not db:
                logger.error("[Song Processor] Failed to create fingerprint database")
                return "Internal Server Error: Database connection failed", 500
            logger.info(f"[Song Processor] Successfully connected to the database")

            track_id = db.load_song_to_tracks(track_metadata)
            if not track_id:
                logger.error(f"[Song Processor] Failed to load song '{title}' by '{artist}' to the database")
                return "Internal Server Error: Failed to load song to the database", 500
            logger.info(f"[Song Processor] Successfully loaded song '{title}' by '{artist}' to the database with ID {track_id}")
            index_single_song_gcp(song_id = track_id,
                                  song_name = title,
                                  youtube_url = track_metadata['youtube_url'],
                                  db = db,
                                  existing_ids = set(),
                                  skip_duplicates = False)
            logger.info(f"[Song Processor] Successfully processed song: {title} by {artist}")

            return "OK", 200

        except json.JSONDecodeError as e:
            logger.error(f"[Song Processor] Invalid JSON: {message_data} - Error: {str(e)}")
            # Return 200 to acknowledge invalid messages
            return "Success: Invalid JSON acknowledged", 200

    except Exception as e:
        logger.error(f"[Song Processor] Error: {str(e)}")
        # Return 200 to stop the retry cycle
        return "Success: Error logged", 200
    
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'Healthy', 200

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=PORT)