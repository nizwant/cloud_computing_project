import os
from typing import Optional, Tuple
from collections import Counter

from src.abracadabra.fingerprint import get_peaks, generate_fingerprints
from src.abracadabra.database import create_fingerprint_db
from src.abracadabra.AbstractFingerprintDB import AbstractFingerprintDB
from pydub import AudioSegment
import numpy as np

def index_song_file(db: AbstractFingerprintDB, song_id: int, path: str, title: str) -> None:
    audio, sr = db.load_audio(path)
    peaks = get_peaks(audio)
    fingerprints = generate_fingerprints(peaks)
    db.add_song(song_id, title, fingerprints)

def index_all_songs(db_type: str = "memory", song_dir: str = None) -> AbstractFingerprintDB:
    db = create_fingerprint_db(db_type)
    if db_type == "memory":
        for idx, filename in enumerate(os.listdir(song_dir)):
            if filename.lower().endswith(".m4a"):
                path = os.path.join(song_dir, filename)
                index_song_file(db, idx, path, filename)
    else:
        tracks = db.load_tracks_from_db()
        n_tracks = len(tracks)
        for song_id, song_name, youtube_url in tracks:
            index_song_file(db, song_id, youtube_url, song_name)
            print(f"Indexed {song_name} ({song_id}/{n_tracks})")
    return db

def recognize_song(
    query_path: str, db: AbstractFingerprintDB, sr: int = 22050
) -> tuple[int, int] | None:
    audio = AudioSegment.from_file(query_path)
    audio = audio.set_channels(1).set_frame_rate(sr)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
    peaks = get_peaks(samples)
    query_fp = generate_fingerprints(peaks)
    matches = db.get_matches(query_fp)
    if not matches:
        return None
    offset_counts = Counter(matches)
    (song_id, offset), score = offset_counts.most_common(1)[0]
    return song_id, score
