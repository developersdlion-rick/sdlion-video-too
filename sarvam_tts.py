"""
Sarvam AI Text-to-Speech wrapper.

Docs: https://docs.sarvam.ai/api-reference/text-to-speech/convert

Key differences vs ElevenLabs (see tts.py):
  - Auth header is "api-subscription-key", not "xi-api-key"
  - You pick a `speaker` name (e.g. "aditya", "anushka") instead of a voice_id
  - You must pass `target_language_code` (BCP-47, e.g. "hi-IN")
  - Response is JSON with a base64-encoded "audios" array, NOT raw audio
    bytes -- must be base64-decoded before writing to disk.

NOTE: Requires outbound internet access + a valid SARVAM_API_KEY. Will not
work inside a network-restricted sandbox.
"""
import os
import base64
import requests
import config


class SarvamTTSError(Exception):
    pass


def generate_speech(text: str, out_path: str, speaker: str = None) -> str:
    """
    Generates speech audio for `text` using Sarvam AI's Bulbul TTS and
    writes it to `out_path` (wav). Returns out_path.
    """
    if not config.SARVAM_API_KEY:
        raise SarvamTTSError("SARVAM_API_KEY is not set.")

    speaker = speaker or config.SARVAM_SPEAKER

    payload = {
        "text": text,
        "target_language_code": config.SARVAM_LANGUAGE_CODE,
        "model": config.SARVAM_MODEL,
        "speaker": speaker,
        "pace": config.SARVAM_PACE,
        "speech_sample_rate": config.SARVAM_SAMPLE_RATE,
    }
    headers = {
        "api-subscription-key": config.SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    resp = requests.post(config.SARVAM_TTS_URL, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise SarvamTTSError(f"Sarvam TTS request failed: {resp.status_code} {resp.text}")

    data = resp.json()
    audios = data.get("audios")
    if not audios:
        raise SarvamTTSError(f"No audio returned in response: {data}")

    audio_bytes = base64.b64decode(audios[0])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(audio_bytes)

    return out_path


if __name__ == "__main__":
    # Quick manual test:
    #   SARVAM_API_KEY=xxx python sarvam_tts.py
    out = generate_speech(
        "Namaskar, main test bol raha hoon.",
        os.path.join(config.TEMP_DIR, "sarvam_test.wav"),
    )
    print("Generated:", out)
