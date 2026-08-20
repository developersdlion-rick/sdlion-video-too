"""
Configuration for the personalized video pipeline.
"""
import os

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_VIDEO = os.path.join(BASE_DIR, "source_video.mp4")   # the master/original ad video
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# ── Segment to replace (seconds) ─────────────────────────────────────
# The window in the source video that contains the name/shop-name line.
# Kept slightly wider than the exact spoken words so the new TTS audio
# always has room to fit (we time-stretch it to match this exact duration).
SEGMENT_START = 26.0
SEGMENT_END = 36.0
SEGMENT_DURATION = round(SEGMENT_END - SEGMENT_START, 3)

# ── Script template ───────────────────────────────────────────────────
# {name} and {shop} are filled in per-dealer.
LINE_TEMPLATE = "Namaskar, main {name}, {shop} me apka swagat karta hu. Apne ghar ko dijiye SD Lion 600 EQR TMT bar ka bharosa."

# ── TTS Provider selection ────────────────────────────────────────────
# "elevenlabs" or "sarvam" -- switch this to test the other provider.
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "elevenlabs")

# ── ElevenLabs settings ───────────────────────────────────────────────
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# If you later get a real Instant Voice Clone of the presenter, put its
# voice_id here and it will be used automatically instead of the fallback.
CLONED_VOICE_ID = os.environ.get("CLONED_VOICE_ID", "")

# Fallback: a close pre-made ElevenLabs multilingual male voice to use
# when no cloned voice is available. Replace this with whichever voice_id
# you pick from `python list_voices.py` (see that script).
FALLBACK_VOICE_ID = os.environ.get("FALLBACK_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"  # supports Hindi
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ELEVENLABS_VOICES_URL = "https://api.elevenlabs.io/v1/voices"

# Voice tuning — stability/similarity affect how close-to-natural vs
# consistent the output is. These are reasonable defaults for a
# confident, warm, businessman tone.
VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.8,
    "style": 0.3,
    "use_speaker_boost": True,
}

# ── Sarvam AI settings ────────────────────────────────────────────────
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Pick a male Hindi-friendly speaker. See Sarvam's Voices page for the
# full list/audio previews and swap this if another voice fits better.
SARVAM_SPEAKER = os.environ.get("SARVAM_SPEAKER", "aditya")

SARVAM_MODEL = "bulbul:v3"        # latest Sarvam TTS model
SARVAM_LANGUAGE_CODE = "hi-IN"    # Hindi
SARVAM_PACE = 1.0                 # 0.5 (slow) - 2.0 (fast) for bulbul:v3
SARVAM_SAMPLE_RATE = 44100        # matches our video's audio sample rate
