import numpy as np
import librosa
import scipy.ndimage
from typing import List, Tuple, Dict


def get_peaks(
    audio, n_fft: int = 2048, hop_length: int = 512, threshold: int = -40
) -> list:
    S = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop_length))
    S_db = librosa.amplitude_to_db(S, ref=np.max)
    local_max = scipy.ndimage.maximum_filter(S_db, size=(20, 10)) == S_db
    detected_peaks = (S_db > threshold) & local_max
    peak_freqs, peak_times = np.where(detected_peaks)
    return list(zip(peak_times, peak_freqs))


def generate_fingerprints(
    peaks: List[Tuple[float, float]],
    fan_value: int = 5,
    min_delta: float = 0,
    max_delta: float = 200,
) -> List[Dict[str, any]]:
    fingerprints: List[Dict[str, any]] = []
    for i in range(len(peaks)):
        t1, f1 = peaks[i]
        for j in range(1, fan_value + 1):
            if i + j >= len(peaks):
                break
            t2, f2 = peaks[i + j]
            delta_t = t2 - t1
            if min_delta <= delta_t <= max_delta:
                fingerprints.append(
                    {"hash": {"f1": f1, "f2": f2, "delta_t": delta_t}, "timestamp": t1}
                )
    return fingerprints
