from collections import defaultdict
from src.AbstractFingerprintDB import AbstractFingerprintDB
from typing import List, Tuple


class InMemoryFingerprintDB(AbstractFingerprintDB):
    def __init__(self):
        self.db: defaultdict[str, List[Tuple[int, float]]] = defaultdict(list)
        self.song_ids: dict[int, str] = {}

    def add_song(self, song_id: int, title: str, fingerprints: List[dict]) -> None:
        self.song_ids[song_id] = title
        for fingerprint in fingerprints:
            hash_val = tuple(fingerprint["hash"].values())
            self.db[str(hash_val)].append((song_id, fingerprint["timestamp"]))

    def get_matches(self, fingerprints: List[dict]) -> List[Tuple[int, float]]:
        matches: List[Tuple[int, float]] = []
        for fingerprint in fingerprints:
            hash_val = tuple(fingerprint["hash"].values())
            if str(hash_val) in self.db:
                for song_id, timestamp in self.db[str(hash_val)]:
                    matches.append((song_id, timestamp - fingerprint["timestamp"]))
        return matches
