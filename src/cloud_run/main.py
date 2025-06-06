from flask import Flask, jsonify
import base64
import json
import logging
import os
import time
from google.cloud import pubsub_v1
from video_handler import handle_youtube_url

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure the subscriber client
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path("cloud-computing-project-458205", "sub-songs-to-process")
BATCH_SIZE = 100  # Process 100 songs at a time

@app.route("/process_batch", methods=["GET"])
def process_batch():
    """Process a batch of songs from Pub/Sub queue."""
    messages = []
    songs_processed = 0
    
    try:
        # Pull a batch of messages
        response = subscriber.pull(
            request={"subscription": subscription_path, "max_messages": BATCH_SIZE}
        )
        
        if not response.received_messages:
            return jsonify({"status": "success", "messages": "No messages to process"})
            
        logger.info(f"Received {len(response.received_messages)} messages")
        
        # Process all messages in the batch
        for received_message in response.received_messages:
            try:
                # Extract message data
                message = received_message.message
                message_data = base64.b64decode(message.data).decode('utf-8')
                
                try:
                    song_info = json.loads(message_data)
                    messages.append({
                        "ack_id": received_message.ack_id,
                        "song_info": song_info,
                        "status": "pending"
                    })
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {message_data} - Error: {str(e)}")
                    # Mark invalid messages for acknowledgment
                    messages.append({
                        "ack_id": received_message.ack_id,
                        "error": f"Invalid JSON: {str(e)}",
                        "status": "invalid"
                    })
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                messages.append({
                    "ack_id": received_message.ack_id,
                    "error": str(e),
                    "status": "error"
                })
        
        # Batch process the valid songs
        valid_songs = [m for m in messages if m.get("status") == "pending"]
        if valid_songs:
            logger.info(f"Processing batch of {len(valid_songs)} valid songs")
            
            # TODO: Add logic to:
            # 1. Search for song metadata via Spotify APIs
            # 2. Search for YouTube url via YouTube APIs
            # 3. Download m4a file from YouTube
            # 4. Create fingerprint of the audio file
            # 5. Upload song data and fingerprint to the database
            
            songs_processed = len(valid_songs)
        
        # Acknowledge all messages
        ack_ids = [msg["ack_id"] for msg in messages]
        if ack_ids:
            subscriber.acknowledge(
                request={"subscription": subscription_path, "ack_ids": ack_ids}
            )
        
        return jsonify({
            "status": "success", 
            "total_messages": len(messages),
            "processed": songs_processed,
            "invalid": len([m for m in messages if m.get("status") == "invalid"]),
            "errors": len([m for m in messages if m.get("status") == "error"])
        })
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
    
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return 'Healthy. GG', 200

@app.route("/debug", methods=["GET"])
def debug_info():
    """Return debug information about the service."""
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    return jsonify({
        "routes": routes,
        "version": "1.0.0",
        "timestamp": time.time()
    })

@app.route("/debug2", methods=["GET"])
def debug_info():
    return "Debug endpoint is working!", 200

@app.route("/", methods=["GET"])
def root():
    """Root endpoint."""
    return "Root endpoint. Service is running.", 200

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=PORT)