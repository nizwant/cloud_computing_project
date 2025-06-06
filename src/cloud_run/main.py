from flask import Flask, request
import base64
import json
import logging
import os
from video_handler import handle_youtube_url

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route("/", methods=["POST"])
def process_pubsub_message():
    envelope = request.get_json()

    if not envelope or "message" not in envelope:
        logger.error("No Pub/Sub message received")
        return "Bad Request: no Pub/Sub message received", 400
    
    if not isinstance(envelope, dict) or 'message' not in envelope:
        logger.error("Invalid Pub/Sub message format")
        return 'Bad Request: Invalid Pub/Sub message format', 400
    
    # Extract message data from Pub/Sub message
    pubsub_message = envelope['message']
    
    if 'data' not in pubsub_message:
        logger.warning("Empty Pub/Sub message received")
        return 'Success: No message data', 200
    
    try:
        # Decode message payload from base64
        message_data = base64.b64decode(pubsub_message['data']).decode('utf-8') 
        logger.info(f"Received message data: {message_data}")
        
        try:
            song_info = json.loads(message_data)
            logger.info(f"Processing song: {song_info.get('title')} by {song_info.get('artist')}")
            
            # TODO: Add logic to:
            # 1. Search for song metadata via Spotify APIs
            # 2. Search for YouTube url via YouTube APIs
            # 3. Download m4a file from YouTube
            # 4. Create fingerprint of the audio file
            # 5. Upload song data and fingerprint to the database 
            
            return "OK", 200
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {message_data} - Error: {str(e)}")
            # Return 200 to acknowledge invalid messages
            return "Success: Invalid JSON acknowledged", 200

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        # Return 200 to stop the retry cycle
        return "Success: Error logged", 200
        
    
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'Healthy', 200

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=PORT)