from pydub import AudioSegment
import numpy as np


def load_audio(filename, sr=22050):
    audio = AudioSegment.from_file(filename)
    audio = audio.set_channels(1).set_frame_rate(sr)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
    return samples, sr
