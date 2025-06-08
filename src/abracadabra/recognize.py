import os
from collections import Counter
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from abracadabra.fingerprint import get_peaks, generate_fingerprints
from abracadabra.database import create_fingerprint_db
from abracadabra.AbstractFingerprintDB import AbstractFingerprintDB
from pydub import AudioSegment
import numpy as np

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import Union
from io import BytesIO

# from pydub.utils import which
# AudioSegment.converter = which("ffmpeg")
# import pydub
# pydub.AudioSegment.ffmpeg = "ffmpeg"

def process_single_song(
    db: AbstractFingerprintDB, song_id: int, path: str, title: str
) -> None:
    audio, sr = db.load_audio(path, song_id)
    peaks = get_peaks(audio)
    fingerprints = generate_fingerprints(peaks)
    db.add_song(song_id, title, fingerprints)


def index_single_song_memory(
    song_id: int, filename: str, db: AbstractFingerprintDB, song_dir: str = "../songs"
):
    if filename.lower().endswith(".m4a"):
        try:
            path = os.path.join(song_dir, filename)
            process_single_song(db, song_id, path, filename)
        except Exception as e:
            print(f"Error indexing {filename}: {e}")


def index_single_song_gcp(
    song_id: int,
    song_name: str,
    youtube_url: str,
    db: AbstractFingerprintDB,
    existing_ids: set,
    skip_duplicates: bool = False,
):
    if skip_duplicates and song_id in existing_ids:
        print(f"Skipping {song_name} (ID {song_id}) — already indexed.")
        return
    try:
        process_single_song(db, song_id, youtube_url, song_name)
    except Exception as e:
        print(f"Error indexing {song_name} (ID {song_id}): {e}")


def index_all_songs(
    db_type: str = "memory", song_dir: str = None, skip_duplicates: bool = False
) -> AbstractFingerprintDB:
    db = create_fingerprint_db(db_type)
    existing_ids = set()

    if skip_duplicates and db_type != "memory":
        existing_ids = set(db.get_indexed_song_ids())

    if db_type == "memory":
        files = [
            (idx, f, db)
            for idx, f in enumerate(os.listdir(song_dir))
            if f.lower().endswith(".m4a")
        ]
        with ThreadPoolExecutor() as executor:
            list(
                tqdm(
                    executor.map(lambda args: index_single_song_memory(*args), files),
                    total=len(files),
                )
            )
    else:
        tracks = db.load_tracks_from_db()
        n_tracks = len(tracks)

        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(
                    index_single_song_gcp,
                    song_id,
                    song_name,
                    youtube_url,
                    db,
                    existing_ids,
                    skip_duplicates,
                ): (song_id, song_name)
                for song_id, song_name, youtube_url in tracks
            }
            for _ in tqdm(as_completed(futures), total=n_tracks):
                pass  # Progress shown by tqdm; errors are printed inside `index_single_song_gcp`

    return db


# def recognize_song(
#     query_path: str,
#     db: AbstractFingerprintDB = None,
#     sr: int = 22050,
#     db_type: str = "gcp",
# ) -> tuple[int, int] | dict | None:
#     if db is None:
#         db = create_fingerprint_db(db_type)
#     audio = AudioSegment.from_file(query_path)
#     audio = audio.set_channels(1).set_frame_rate(sr)
#     samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
#     peaks = get_peaks(samples)
#     query_fp = generate_fingerprints(peaks)
#     matches = db.get_matches(query_fp)
#     if not matches:
#         return None
#     offset_counts = Counter(matches)
#     (song_id, offset), score = offset_counts.most_common(1)[0]
#
#     if db_type == "gcp":
#         return db.check_song_info(song_id)
#     else:
#         return song_id, score

def recognize_song(
    query: Union[str, BytesIO],
    db: AbstractFingerprintDB = None,
    sr: int = 22050,
    db_type: str = "gcp",
) -> tuple[int, int] | dict | None:
    if db is None:
        db = create_fingerprint_db(db_type)

    audio = AudioSegment.from_file(query)
    audio = audio.set_channels(1).set_frame_rate(sr)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
    peaks = get_peaks(samples)
    query_fp = generate_fingerprints(peaks)
    matches = db.get_matches(query_fp)

    if not matches:
        return None

    offset_counts = Counter(matches)
    (song_id, offset), score = offset_counts.most_common(1)[0]

    return db.check_song_info(song_id) if db_type == "gcp" else (song_id, score)

