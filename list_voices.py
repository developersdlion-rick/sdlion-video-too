"""
Run this first (with internet + your API key) to see which voices your
ElevenLabs account can use, so you can pick the closest match to the
presenter's voice and set it as FALLBACK_VOICE_ID (or CLONED_VOICE_ID if
you later create a real clone).

Usage:
    export ELEVENLABS_API_KEY=sk_xxx
    python list_voices.py
"""
from tts import get_available_voices

if __name__ == "__main__":
    voices = get_available_voices()
    if not voices:
        print("No voices returned. Check your API key / permissions.")
    for v in voices:
        print(f"{v.get('voice_id')}  |  {v.get('name')}  |  labels: {v.get('labels')}")
