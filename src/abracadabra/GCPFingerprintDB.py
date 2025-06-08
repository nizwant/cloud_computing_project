import os
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Tuple, Dict
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
from abracadabra.AbstractFingerprintDB import AbstractFingerprintDB
from google.cloud import secretmanager
import yt_dlp
from pydub import AudioSegment
import numpy as np
import re
from typing import Dict
import logging

def get_secret(secret_id: str, project_id: str):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").replace("\n", "")


def sanitize_filename(name: str) -> str:
    # Replace invalid filename characters with underscore
    return re.sub(r'[<>:"/\\|?*\n\r\t]', "_", name)


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
    def load_audio(
        youtube_url: str,
        song_id: int,
        download_dir: str = "../songs/temp",
        sr: int = 22050,
    ):
        print(f"Downloading audio from {youtube_url}...")

        output_path = os.path.join(download_dir, f"{song_id}")

        output_path_m4a = f"{output_path}.m4a"

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
        for attempt, fmt in enumerate(
            ["m4a/bestaudio/best", "bestaudio/best"], start=1
        ):
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
        if not os.path.exists(output_path_m4a) or os.path.getsize(output_path_m4a) == 0:
            print(
                f"Error: The downloaded file for track {song_id} is missing or empty."
            )
            return None

        # Decode audio
        try:
            audio = AudioSegment.from_file(output_path_m4a)
            audio = audio.set_channels(1).set_frame_rate(sr)
            samples = (
                np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
            )
            return samples, sr
        except Exception as e:
            print(f"Error decoding audio for track {song_id}: {e}")
            return None
        finally:
            if os.path.exists(output_path_m4a):
                os.remove(output_path_m4a)

    def load_tracks_from_db(self, min_id: int = None):
        id_condition = ""
        if min_id is not None:
            id_condition = f" AND track_id > {min_id}"
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT track_id, track_name, youtube_url FROM tracks "
                f"WHERE youtube_url != ''{id_condition};"
            )
            rows = cur.fetchall()
            return rows

    def add_song(
        self, song_id: int, title: str, fingerprints: List[Dict[str, any]]
    ) -> None:

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

    def get_matches(
        self, fingerprints: List[Dict[str, any]]
    ) -> List[Tuple[int, float]]:
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
            for query_timestamp in hash_to_query_timestamps.get(
                str(tuple(fp["hash"].values())), []
            ):
                offset = db_timestamp - query_timestamp
                matches.append((song_id, offset))

        return matches

    def show_table(self):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT fingerprints.song_id, tracks.track_name FROM fingerprints "
                "JOIN tracks ON fingerprints.song_id = tracks.track_id "
                "ORDER BY fingerprints.song_id;"
            )
            rows = cur.fetchall()
            for row in rows:
                print(row)

    def check_song_info(self, song_id: int) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT "
                "track_name, artist_names, album_name, album_release_date, "
                "album_image_url, track_duration_ms, explicit, youtube_url FROM tracks "
                "WHERE track_id = %s;",
                (song_id,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "track_name": row[0],
                    "artist_names": row[1],
                    "album_name": row[2],
                    "album_release_date": row[3].isoformat() if row[3] else None,
                    "album_image_url": row[4],
                    "track_duration_ms": row[5],
                    "explicit": row[6],
                    "youtube_url": row[7],
                }
            else:
                return {}

    def get_indexed_song_ids(self) -> List[int]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT song_id FROM fingerprints;")
            return [row[0] for row in cur.fetchall()]
        
    def load_song_to_tracks(self, song_info: Dict):
        with self.conn.cursor() as cursor:
            try:
                # 1. Extract and prepare track data
                original_track_uri = song_info["Track URI"]
                track_name = song_info["Track Name"]

                if not original_track_uri:
                    logging.warning(
                        f"Skipping song due to missing 'Track URI'."
                    )
                    return
                if not track_name:
                    logging.warning(
                        f"Skipping row song (URI: {original_track_uri}) due to missing 'Track Name'."
                    )
                    return

                artist_names = song_info["Artist Name(s)"]
                album_name = song_info["Album Name"]
                album_release_date_str = song_info["Album Release Date"]
                album_image_url = song_info["Album Image URL"]

                track_duration_ms_str = song_info["Track Duration (ms)"]
                track_duration_ms = (
                    int(track_duration_ms_str)
                    if track_duration_ms_str and track_duration_ms_str.isdigit()
                    else None
                )

                explicit_str = song_info["Explicit", ""].strip().lower()
                explicit = explicit_str == "true" if explicit_str else None

                popularity_str = song_info["Popularity"]
                popularity = (
                    int(popularity_str)
                    if popularity_str and popularity_str.isdigit()
                    else None
                )

                youtube_title = song_info["youtube_title"]
                youtube_url = song_info["youtube_url"]
                artist_genres_str = song_info["Artist Genres", ""]

                album_release_date = parse_date(album_release_date_str)

                # 2. Insert/Update Track and get track_id
                track_sql = sql.SQL(
                    """
                    INSERT INTO tracks (
                        original_track_uri, track_name, artist_names, album_name,
                        album_release_date, album_image_url, track_duration_ms,
                        explicit, popularity, youtube_title, youtube_url
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (original_track_uri) DO UPDATE SET
                        track_name = EXCLUDED.track_name,
                        artist_names = EXCLUDED.artist_names,
                        album_name = EXCLUDED.album_name,
                        album_release_date = EXCLUDED.album_release_date,
                        album_image_url = EXCLUDED.album_image_url,
                        track_duration_ms = EXCLUDED.track_duration_ms,
                        explicit = EXCLUDED.explicit,
                        popularity = EXCLUDED.popularity,
                        youtube_title = EXCLUDED.youtube_title,
                        youtube_url = EXCLUDED.youtube_url,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING track_id, (xmax = 0) AS inserted;
                """
                )

                cursor.execute(
                    track_sql,
                    (
                        original_track_uri,
                        track_name,
                        artist_names,
                        album_name,
                        album_release_date,
                        album_image_url,
                        track_duration_ms,
                        explicit,
                        popularity,
                        youtube_title,
                        youtube_url,
                    ),
                )
                track_id_result = cursor.fetchone()
                if not track_id_result:
                    logging.error(
                        f"Failed to insert or update track (URI: {original_track_uri}). Skipping genre processing for this track."
                    )
                    return

                track_id, was_inserted = track_id_result

                # 3. Process and Insert Genres and Track-Genre links
                if artist_genres_str:
                    genres_from_csv = [
                        genre.strip()
                        for genre in artist_genres_str.split(",")
                        if genre.strip()
                    ]
                    for genre_name in genres_from_csv:
                        if not genre_name:
                            continue

                        # a. Insert Genre if not exists, and get genre_id
                        genre_id = None
                        cursor.execute(
                            sql.SQL(
                                "INSERT INTO genres (genre_name) VALUES (%s) ON CONFLICT (genre_name) DO NOTHING RETURNING genre_id;"
                            ),
                            (genre_name,),
                        )
                        result = cursor.fetchone()
                        if result:
                            genre_id = result[0]
                            # logging.info(f"Inserted new genre: '{genre_name}' with ID: {genre_id}")
                        else:  # Genre already existed, fetch its ID
                            cursor.execute(
                                sql.SQL(
                                    "SELECT genre_id FROM genres WHERE genre_name = %s;"
                                ),
                                (genre_name,),
                            )
                            result = cursor.fetchone()
                            if result:
                                genre_id = result[0]
                            else:
                                logging.error(
                                    f"Could not find or insert genre: '{genre_name}' for track ID {track_id}. Skipping this genre link."
                                )
                                continue

                        # b. Insert Track-Genre link
                        try:
                            cursor.execute(
                                sql.SQL(
                                    "INSERT INTO track_genres (track_id, genre_id) VALUES (%s, %s) ON CONFLICT (track_id, genre_id) DO NOTHING;"
                                ),
                                (track_id, genre_id),
                            )
                            if (
                                    cursor.rowcount > 0
                            ):  # rowcount is 1 if inserted, 0 if conflict and did nothing
                                linked_track_genres += 1
                                # logging.info(f"Linked track ID {track_id} to genre ID {genre_id} ('{genre_name}')")
                        except psycopg2.Error as link_err:
                            logging.error(
                                f"Error linking track ID {track_id} to genre ID {genre_id} ('{genre_name}'): {link_err}"
                            )

            except psycopg2.Error as db_err:
                logging.error(
                    f"Database error processing song (Track URI: {song_info['Track URI']}): {db_err}"
                )
                self.conn.rollback()  # Rollback current transaction segment
                # Decide if you want to continue with the next row or stop
            except Exception as e:
                logging.error(
                    f"General error processing song (Track URI: {song_info['Track URI']}): {e}"
                )
                self.conn.rollback()  # Rollback current transaction segment

            self.conn.commit()  # Final commit for any remaining operations
            logging.info("ETL process completed.")

        return track_id

    def close(self):
        self.conn.close()
