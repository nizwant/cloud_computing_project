import numpy as np
import librosa
import scipy.ndimage
from typing import TypedDict, List, Tuple

class Fingerprint(TypedDict):
    hash: dict
    timestamp: float

Peak = Tuple[int, int]  # (time_index, freq_index)

def get_peaks(
    audio: np.ndarray, n_fft: int = 2048, hop_length: int = 512, threshold: int = -40
) -> List[Peak]:
    S = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop_length))
    S_db = librosa.amplitude_to_db(S, ref=np.max)
    local_max = scipy.ndimage.maximum_filter(S_db, size=(20, 10)) == S_db
    detected_peaks = (S_db > threshold) & local_max
    freqs, times = np.where(detected_peaks)
    return list(zip(times, freqs))

def generate_fingerprints(
    peaks: List[Peak], fan_value: int = 5, min_delta: float = 0, max_delta: float = 200
) -> List[Fingerprint]:
    fingerprints: List[Fingerprint] = []
    for i in range(len(peaks)):
        t1, f1 = peaks[i]
        for j in range(1, fan_value + 1):
            if i + j >= len(peaks):
                break
            t2, f2 = peaks[i + j]
            delta_t = t2 - t1
            if min_delta <= delta_t <= max_delta:
                fingerprints.append({
                    "hash": {"f1": f1, "f2": f2, "delta_t": delta_t},
                    "timestamp": t1
                })
    return fingerprints
