from collections import defaultdict
from AbstractFingerprintDB import AbstractFingerprintDB
from typing import List, Tuple, Dict
from pydub import AudioSegment
import numpy as np

class InMemoryFingerprintDB(AbstractFingerprintDB):
    def __init__(self):
        self.db: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
        self.song_ids: Dict[int, str] = {}

    def add_song(self, song_id: int, title: str, fingerprints: List[dict]) -> None:
        self.song_ids[song_id] = title
        for fingerprint in fingerprints:
            hash_tuple = (fingerprint["hash"]["f1"], fingerprint["hash"]["f2"], fingerprint["hash"]["delta_t"])
            self.db[str(hash_tuple)].append((song_id, fingerprint["timestamp"]))

    def get_matches(self, fingerprints: List[dict]) -> List[Tuple[int, float]]:
        matches: List[Tuple[int, float]] = []
        for fingerprint in fingerprints:
            hash_tuple = (fingerprint["hash"]["f1"], fingerprint["hash"]["f2"], fingerprint["hash"]["delta_t"])
            for song_id, ts in self.db.get(str(hash_tuple), []):
                matches.append((song_id, ts - fingerprint["timestamp"]))
        return matches

    @staticmethod
    def load_audio(filename: str, sr: int = 22050) -> Tuple[np.ndarray, int]:
        audio = AudioSegment.from_file(filename)
        audio = audio.set_channels(1).set_frame_rate(sr)
        samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
        return samples, sr