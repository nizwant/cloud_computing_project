from abc import ABC, abstractmethod
from typing import List, Tuple


class AbstractFingerprintDB(ABC):
    @abstractmethod
    def add_song(self, song_id: int, title: str, fingerprints: List[dict]) -> None:
        pass

    @abstractmethod
    def get_matches(self, fingerprints: List[dict]) -> List[Tuple[int, int]]:
        pass
