import os
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Tuple, Dict, Any
from src.abracadabra.AbstractFingerprintDB import AbstractFingerprintDB
from google.cloud import secretmanager
import yt_dlp
import tempfile
import ffmpeg
import soundfile as sf
import io
from pydub import AudioSegment
import numpy as np
import re

def get_secret(secret_id, project_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").replace("\n", "")

def sanitize_filename(name: str) -> str:
    # Replace invalid filename characters with underscore
    return re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name)


class GCPFingerprintDB(AbstractFingerprintDB):
    def __init__(self, project_id: str = "cloud-computing-project-458205"):
        self.project_id = project_id
        self.dbname = os.getenv("DB_NAME", "database-instance")
        self.user = get_secret("DB_USER", project_id)
        self.password = get_secret("DB_PASSWORD", project_id)
        self.host = get_secret("DB_HOST", project_id)
        self.port = os.getenv("DB_PORT", "5432")

        self.conn = psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
        self.conn.autocommit = True

    @staticmethod
    def load_audio(youtube_url: str, song_id: int, download_dir: str = "../../songs", sr: int = 22050):
        print(f"Downloading audio from {youtube_url}...")

        output_path = os.path.join(download_dir, f"{song_id}.m4a")

        ydl_opts = {
            "format": "m4a/bestaudio/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                }
            ],
            "noplaylist": True,
        }

        # Try primary and fallback download formats
        for attempt, fmt in enumerate(["m4a/bestaudio/best", "bestaudio/best"], start=1):
            ydl_opts["format"] = fmt
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                break  # Success, exit loop
            except yt_dlp.utils.DownloadError as e:
                print(f"[Attempt {attempt}] Download error: {e}")
                if attempt == 2:
                    return None

        # Check if file exists and is not empty
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            print(f"Error: The downloaded file for track {song_id} is missing or empty.")
            return None

        # Decode audio
        try:
            audio = AudioSegment.from_file(output_path)
            audio = audio.set_channels(1).set_frame_rate(sr)
            samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
            return samples, sr
        except Exception as e:
            print(f"Error decoding audio for track {song_id}: {e}")
            return None
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def load_tracks_from_db(self, min_id: int = None):
        id_condition = ""
        if min_id is not None:
            id_condition = f" AND track_id > {min_id}"
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT track_id, track_name, youtube_url FROM tracks WHERE youtube_url != ''{id_condition};")
            rows = cur.fetchall()
            return rows
    def add_song(self, song_id: int, title: str, fingerprints: List[Dict[str, any]]) -> None:

        # Insert fingerprints in bulk
        records = []
        for fp in fingerprints:
            # Convert hash dict to a consistent string key
            hash_val = tuple(fp["hash"].values())
            hash_str = str(hash_val)
            timestamp = float(fp["timestamp"])
            records.append((int(song_id), hash_str, timestamp))

        with self.conn.cursor() as cur:
            # Insert fingerprints; ON CONFLICT do nothing to avoid duplicates
            insert_query = """
                INSERT INTO fingerprints (song_id, hash, timestamp)
                VALUES %s
                ON CONFLICT (song_id, hash, timestamp) DO NOTHING;
            """
            execute_values(cur, insert_query, records)

    def get_matches(self, fingerprints: List[Dict[str, any]]) -> List[Tuple[int, float]]:
        matches = []
        if not fingerprints:
            return matches

        # Prepare list of hash strings for query
        hash_list = [str(tuple(fp["hash"].values())) for fp in fingerprints]

        with self.conn.cursor() as cur:
            # Query matching fingerprints from DB
            query = """
                SELECT song_id, timestamp FROM fingerprints
                WHERE hash = ANY(%s);
            """
            cur.execute(query, (hash_list,))
            results = cur.fetchall()

        # For each match, compute offset = DB_timestamp - query_timestamp
        # Use dict to map hash to query timestamps for fast lookup
        hash_to_query_timestamps = {}
        for fp in fingerprints:
            hash_str = str(tuple(fp["hash"].values()))
            hash_to_query_timestamps.setdefault(hash_str, []).append(fp["timestamp"])

        for song_id, db_timestamp in results:
            # Calculate offsets for all query timestamps with the same hash
            # Append all matches
            for query_timestamp in hash_to_query_timestamps.get(str(tuple(fp["hash"].values())), []):
                offset = db_timestamp - query_timestamp
                matches.append((song_id, offset))

        return matches

    def show_table(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT distinct fingerprints.song_id, tracks.track_name FROM fingerprints "
                        "JOIN tracks ON fingerprints.song_id = tracks.track_id order by fingerprints.song_id;")
            rows = cur.fetchall()
            for row in rows:
                print(row)

    def check_song_info(self, song_id: int) -> tuple[Any, Any, Any, Any] | tuple[None, None, None, None]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT track_name, artist_names, album_name, youtube_url FROM tracks WHERE track_id = %s;", (song_id,))
            row = cur.fetchone()
            if row:
                return row[0], row[1], row[2], row[3]
            else:
                return None, None, None, None

    def get_indexed_song_ids(self) -> List[int]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT song_id FROM fingerprints;")
            return [row[0] for row in cur.fetchall()]

    def close(self):
        self.conn.close()
