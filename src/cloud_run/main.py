from flask import Flask, request
import base64
import json
import logging
import os
from video_handler import handle_youtube_url
from spotify_handler import get_track_metadata

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route("/", methods=["POST"])
def process_pubsub_message():
    envelope = request.get_json()

    if not envelope or "message" not in envelope:
        logger.error("No Pub/Sub message received")
        return "[Song Processor] Bad Request: no Pub/Sub message received", 400
    
    if not isinstance(envelope, dict) or 'message' not in envelope:
        logger.error("Invalid Pub/Sub message format")
        return '[Song Processor] Bad Request: Invalid Pub/Sub message format', 400
    
    # Extract message data from Pub/Sub 
    pubsub_message = envelope['message']
    
    if 'data' not in pubsub_message:
        logger.warning("Empty Pub/Sub message received")
        return '[Song Processor] Success: No message data', 200
    
    try:
        # Decode message payload from base64
        message_data = base64.b64decode(pubsub_message['data']).decode('utf-8') 
        logger.info(f"[Song Processor] Received message data: {message_data}")
        
        try:
            song_info = json.loads(message_data)
            title = song_info.get('title')
            artist = song_info.get('artist')
            logger.info(f"[Song Processor] Processing song: {title} by {artist}")
            
            # TODO: Add logic to:
            # 1. Search for song metadata via Spotify APIs
            if title and artist:
                track_metadata = get_track_metadata(title, artist)
                
                if track_metadata:
                    logger.info(f"Found metadata for '{title}' by '{artist}'")
                    logger.info(f"Track URI: {track_metadata.get('original_track_uri')}")
                    # Album uri
                    logger.info(f"Album URL: {track_metadata.get('album_image_url')}")
                    logger.info(f"Release Date: {track_metadata.get('album_release_date')}")
                    # track_duration_ms
                    logger.info(f"Track Duration (ms): {track_metadata.get('track_duration_ms')}")
                    # Explicit content
                    logger.info(f"Explicit Content: {track_metadata.get('explicit')}")
                    # Popularity
                    logger.info(f"Popularity: {track_metadata.get('popularity')}")
                    logger.info(f"Genres: {', '.join(track_metadata.get('genres', []))}")
                    
                    # Store the metadata for further processing (will be used in next steps)
                    song_info['metadata'] = track_metadata
                else:
                    logger.warning(f"No metadata found for '{title}' by '{artist}'")
            else:
                logger.error("Title or artist is missing in the song info")
                return "[Song Processor] Bad Request: Title or artist is missing", 400
            # 2. Search for YouTube url via YouTube APIs
            # 3. Download m4a file from YouTube
            # 4. Create fingerprint of the audio file
            # 5. Upload song data and fingerprint to the database 
            
            return "OK", 200
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {message_data} - Error: {str(e)}")
            # Return 200 to acknowledge invalid messages
            return "[Song Processor] Success: Invalid JSON acknowledged", 200

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        # Return 200 to stop the retry cycle
        return "[Song Processor] Success: Error logged", 200
        
    
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'Healthy', 200

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=PORT)