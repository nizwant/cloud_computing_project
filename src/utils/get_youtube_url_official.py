import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def find_song_url(title, artist, youtube, max_results=5):
    """
    Search for a song on YouTube and return the top video URLs.

    Args:
        title (str): The song title
        artist (str): The artist name
        max_results (int): Maximum number of results to return

    Returns:
        list: List of dictionaries containing video titles and URLs
    """
    try:
        # Create the search query
        query = f"{title} {artist} official"

        # Call the search.list method to retrieve results
        search_response = (
            youtube.search()
            .list(q=query, part="id,snippet", maxResults=max_results, type="video")
            .execute()
        )

        # Collect the results
        videos = []
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                video_id = search_result["id"]["videoId"]
                video_title = search_result["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                videos.append({"title": video_title, "url": video_url})

        return videos

    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def find_urls_for_songs(songs_list):
    """
    Find YouTube URLs for a list of songs.

    Args:
        songs_list (list): List of dictionaries with 'title' and 'artist' keys

    Returns:
        dict: Dictionary with song info and top YouTube URL
    """

    load_dotenv()
    API_KEY = os.getenv("YOUTUBE_API_KEY")

    # Verify API key is loaded
    if not API_KEY:
        print("WARNING: API_KEY not found in environment variables!")
        print("Please create a .env file with your YOUTUBE_API_KEY=your_key_here")
    else:
        print("API key loaded successfully!")

    # Create YouTube API client
    youtube = build("youtube", "v3", developerKey=API_KEY)

    results = {}

    for song in songs_list:
        title = song["title"]
        artist = song["artist"]

        print(f"Searching for '{title}' by {artist}...")
        videos = find_song_url(title, artist, max_results=1, youtube=youtube)

        key = f"{title} - {artist}"
        if videos:
            results[key] = {
                "title": title,
                "artist": artist,
                "youtube_title": videos[0]["title"],
                "youtube_url": videos[0]["url"],
            }
        else:
            results[key] = {
                "title": title,
                "artist": artist,
                "youtube_title": "Not found",
                "youtube_url": "Not found",
            }

    return results
