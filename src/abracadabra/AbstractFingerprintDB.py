from abc import ABC, abstractmethod
from typing import List, Tuple
from abracadabra.fingerprint import Fingerprint


class AbstractFingerprintDB(ABC):
    @abstractmethod
    def add_song(
        self, song_id: int, title: str, fingerprints: List[Fingerprint]
    ) -> None:
        pass

    @abstractmethod
    def get_matches(self, query_fps: List[Fingerprint]) -> List[Tuple[int, int]]:
        """
        Returns list of (song_id, time_offset) matches.
        """
        pass
