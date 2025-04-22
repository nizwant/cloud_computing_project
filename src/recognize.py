import os
from collections import Counter
from src.audio import load_audio
from src.fingerprint import get_peaks, generate_fingerprints
from src.database import create_fingerprint_db
from src.AbstractFingerprintDB import AbstractFingerprintDB
from typing import Optional, Tuple


def load_database(song_dir: str, db_type: str = "memory") -> AbstractFingerprintDB:
    db = create_fingerprint_db(db_type)
    song_id = 0
    for filename in os.listdir(song_dir):
        if filename.lower().endswith(".m4a"):
            audio, sr = load_audio(os.path.join(song_dir, filename))
            peaks = get_peaks(audio)
            fingerprints = generate_fingerprints(peaks)
            db.add_song(song_id, filename, fingerprints)
            song_id += 1
    return db


def recognize_song(query_path: str, db: AbstractFingerprintDB) -> Optional[Tuple[str, int]]:
    audio, sr = load_audio(query_path)
    peaks = get_peaks(audio)
    query_fp = generate_fingerprints(peaks)

    matches = db.get_matches(query_fp)
    if not matches:
        return None

    offset_counts = Counter(matches)
    (song_id, offset), score = offset_counts.most_common(1)[0]
    return db.song_ids[song_id], score
