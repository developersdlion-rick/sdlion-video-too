"""
Unified TTS entry point. Picks the active provider based on
config.TTS_PROVIDER so the rest of the pipeline doesn't need to know or
care which backend is generating the audio.

Usage is identical regardless of provider:
    from tts_provider import generate_speech
    generate_speech("some text", "/path/to/out.mp3")
"""
import config


def generate_speech(text: str, out_path: str, voice_id: str = None) -> str:
    provider = config.TTS_PROVIDER.lower()

    if provider == "elevenlabs":
        from tts import generate_speech as _gen
        return _gen(text, out_path, voice_id=voice_id)

    elif provider == "sarvam":
        from sarvam_tts import generate_speech as _gen
        return _gen(text, out_path, speaker=voice_id)

    else:
        raise ValueError(
            f"Unknown TTS_PROVIDER '{config.TTS_PROVIDER}'. "
            f"Use 'elevenlabs' or 'sarvam'."
        )
