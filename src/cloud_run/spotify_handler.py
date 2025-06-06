import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Dict, Any, Optional, List
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

def get_secret(secret_id: str) -> str:
    """Retrieve secret from Google Cloud Secret Manager"""
    try:
        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Build the resource name of the secret version
        name = f"projects/100420581963/secrets/{secret_id}/versions/latest"
        
        # Access the secret version
        response = client.access_secret_version(request={"name": name})
        
        # Return the secret value
        return response.payload.data.decode("UTF-8")
    
    except Exception as e:
        logger.error(f"Error retrieving secret {secret_id}: {str(e)}")
        # Fall back to environment variables if Secret Manager access fails
        return os.environ.get(secret_id, '')

def create_spotify_client() -> spotipy.Spotify:
    """Create and return a configured Spotify client"""
    client_id = get_secret("SPOTIFY_CLIENT_ID")
    client_secret = get_secret("SPOTIFY_API")
    
    if not client_id or not client_secret:
        logger.error("Spotify credentials not found")
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_API must be set in Secret Manager or as environment variables")
    
    client_credentials_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def get_track_metadata(title: str, artist: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive track metadata including genres
    
    Returns a dictionary with track details or None if not found
    """
    try:
        sp = create_spotify_client()
        
        # Search for the track
        query = f"track:{title} artist:{artist}"
        search_results = sp.search(q=query, type='track', limit=1)
        
        tracks = search_results.get('tracks', {}).get('items', [])
        if not tracks:
            logger.warning(f"No track found for '{title}' by '{artist}'")
            return None
        
        track_data = tracks[0]
        
        # Extract basic track information
        track_uri = track_data.get('uri')
        track_name = track_data.get('name')
        album = track_data.get('album', {})
        album_name = album.get('name')
        
        # Format album release date
        release_date = album.get('release_date')
        if release_date:
            # Handle different date formats (YYYY, YYYY-MM, YYYY-MM-DD)
            if len(release_date) == 4:  # YYYY
                release_date += "-01-01"
            elif len(release_date) == 7:  # YYYY-MM
                release_date += "-01"
        
        # Get album cover image
        album_image_url = None
        images = album.get('images', [])
        if images:
            album_image_url = images[0].get('url')
        
        # Get artist names
        artists = track_data.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists])
        
        # Get track genres from primary artist
        genres = []
        if artists:
            primary_artist_id = artists[0].get('id')
            if primary_artist_id:
                artist_info = sp.artist(primary_artist_id)
                genres = artist_info.get('genres', [])
        
        # Compile metadata
        metadata = {
            'original_track_uri': track_uri,
            'track_name': track_name,
            'artist_names': artist_names,
            'album_name': album_name,
            'album_release_date': release_date,
            'album_image_url': album_image_url,
            'track_duration_ms': track_data.get('duration_ms'),
            'explicit': track_data.get('explicit', False),
            'popularity': track_data.get('popularity', 0),
            'genres': genres
        }
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error getting track metadata: {str(e)}")
        return None