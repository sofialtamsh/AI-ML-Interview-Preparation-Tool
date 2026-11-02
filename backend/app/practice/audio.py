"""Checks an uploaded answer recording before anything is stored or sent to the AI.

The browser converts the microphone track to 16 kHz mono 16-bit WAV: every speech-to-text model
accepts it, and its length can be read exactly from the file instead of trusting the client.
"""

import io
import wave

MIN_SECONDS = 3
MAX_RATE = 24_000
# A little slack over the time limit for the recorder's stop to land.
SLACK_SECONDS = 2


class AudioProblem(ValueError):
    pass


def max_upload_bytes(max_seconds: int) -> int:
    return (max_seconds + SLACK_SECONDS) * MAX_RATE * 2 + 1024


def wav_duration_ms(data: bytes, max_seconds: int) -> int:
    try:
        with wave.open(io.BytesIO(data)) as wav:
            channels, width = wav.getnchannels(), wav.getsampwidth()
            rate, frames = wav.getframerate(), wav.getnframes()
    except (wave.Error, EOFError) as exc:
        raise AudioProblem("The recording isn't a WAV file. Record your answer again.") from exc
    if channels != 1 or width != 2 or not 8_000 <= rate <= MAX_RATE:
        raise AudioProblem("The recording must be 16-bit mono audio. Record your answer again.")
    if frames * width > len(data):
        raise AudioProblem("The recording is incomplete. Record your answer again.")
    seconds = frames / rate
    if seconds < MIN_SECONDS:
        raise AudioProblem("That recording is too short to give feedback on.")
    if seconds > max_seconds + SLACK_SECONDS:
        raise AudioProblem(f"Answers can be at most {max_seconds // 60} minutes long.")
    return round(seconds * 1000)
