"""
ElevenLabs Text-to-Speech wrapper.

NOTE: This calls the public ElevenLabs API and requires outbound internet
access + a valid ELEVENLABS_API_KEY environment variable. It will NOT work
inside a network-restricted sandbox.
"""
import os
import requests
import config


class TTSError(Exception):
    pass


def get_available_voices():
    """
    Returns the list of voices your API key can access (pre-made voices +
    any cloned voices already in your account). Useful for picking the
    closest-sounding fallback voice.
    """
    if not config.ELEVENLABS_API_KEY:
        raise TTSError("ELEVENLABS_API_KEY is not set.")

    resp = requests.get(
        config.ELEVENLABS_VOICES_URL,
        headers={"xi-api-key": config.ELEVENLABS_API_KEY},
        timeout=30,
    )
    if resp.status_code != 200:
        raise TTSError(f"Failed to list voices: {resp.status_code} {resp.text}")
    return resp.json().get("voices", [])


def generate_speech(text: str, out_path: str, voice_id: str = None) -> str:
    """
    Generates speech audio for `text` using ElevenLabs TTS and writes it
    to `out_path` (mp3). Returns out_path.
    """
    if not config.ELEVENLABS_API_KEY:
        raise TTSError("ELEVENLABS_API_KEY is not set.")

    voice_id = voice_id or config.CLONED_VOICE_ID or config.FALLBACK_VOICE_ID
    if not voice_id:
        raise TTSError(
            "No voice_id available. Set CLONED_VOICE_ID or FALLBACK_VOICE_ID."
        )

    url = config.ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    payload = {
        "text": text,
        "model_id": config.ELEVENLABS_MODEL_ID,
        "voice_settings": config.VOICE_SETTINGS,
    }
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise TTSError(f"TTS request failed: {resp.status_code} {resp.text}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(resp.content)

    return out_path


if __name__ == "__main__":
    # Quick manual test:
    #   ELEVENLABS_API_KEY=xxx python tts.py
    voices = get_available_voices()
    for v in voices:
        print(v.get("voice_id"), "-", v.get("name"), "-", v.get("labels"))
