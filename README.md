# SD Lion — Personalized Video Generator

Generates a personalized version of the SD Lion promo video for each dealer,
swapping the 39.5s–44.0s segment's audio with a TTS line containing their
own name and shop name.

## How it works

1. Dealer submits **Name** + **Shop Name** via the web form.
2. `tts.py` calls the ElevenLabs Text-to-Speech API to generate:
   `"Namaste, main {name}, {shop} me aapka swagat karta hu"`
3. `video_pipeline.py`:
   - Splits `source_video.mp4` into `before` / `segment` / `after`
   - Time-stretches the new audio to exactly match the segment's duration
     (so timing always lines up, whether the name is short or long)
   - Drops the segment's original audio, attaches the new TTS audio
   - Re-joins everything into one final MP4
4. The dealer gets a download link to their personalized video.

This is a **voiceover swap** (no lip-sync) — the visuals in that segment
stay exactly the same; only the spoken audio changes.

## Setup

```bash
pip install -r requirements.txt
```

You need:
- **ffmpeg** and **ffprobe** installed and on PATH
- An API key for **at least one** TTS provider: ElevenLabs or Sarvam AI (see below)

### Choosing a TTS provider

Set `TTS_PROVIDER` to switch between them — everything else in the pipeline
stays the same regardless of which one is active:

```bash
export TTS_PROVIDER="elevenlabs"   # or "sarvam"
```

#### Option A: ElevenLabs

```bash
export ELEVENLABS_API_KEY="sk_xxxxxxxxxxxxxxxxxxxxxxxx"
```

Your key needs **Text-to-Speech** access at minimum. To pick a voice, your
key also needs **Voices → Read** permission:

```bash
python list_voices.py
export FALLBACK_VOICE_ID="the_voice_id_you_picked"
```

If your key only has Text-to-Speech access (no Voices → Read), you can skip
`list_voices.py` — the pipeline already has a working default voice built in.

(If you later get a properly cloned voice of the actual presenter, set
`CLONED_VOICE_ID` instead, and the pipeline will automatically prefer it
over the fallback.)

#### Option B: Sarvam AI

```bash
export SARVAM_API_KEY="sk_xxxxxxxxxxxxxxxxxxxxxxxx"
```

Sarvam uses named speakers rather than voice IDs. The default is `"aditya"`
(a male Hindi voice) — check Sarvam's Voices page for previews of other
options and override it if needed:

```bash
export SARVAM_SPEAKER="aditya"
```

### 1. Test the pipeline directly (no web form)

```bash
python video_pipeline.py
```

This generates one test video using the sample name "Ram Sharma" /
"Sharma Steel Corner Bihar" (using whichever `TTS_PROVIDER` you set) and
prints the output path.

### 2. Run the web app

```bash
python app.py
```

Open `http://localhost:5000`, enter a name + shop name, and download the
result.

## Files

| File | Purpose |
|---|---|
| `config.py` | Segment timing, script template, TTS provider + settings for both |
| `tts.py` | ElevenLabs API wrapper |
| `sarvam_tts.py` | Sarvam AI API wrapper |
| `tts_provider.py` | Picks the active provider based on `TTS_PROVIDER` |
| `video_pipeline.py` | ffmpeg-based segment swap logic |
| `app.py` | Flask web server |
| `templates/index.html` | Dealer-facing form |
| `list_voices.py` | Helper to list voices available to your API key |
| `source_video.mp4` | The master video (replace with your final-edit master) |

## Notes / things to double check before scaling to many dealers

- **Rights/consent**: confirm you have the presenter's consent to reuse his
  likeness/voice across many personalized dealer videos.
- **Rotate the API key** you tested with if it was ever shared in plaintext
  anywhere (chat, email, etc.) — regenerate it in the ElevenLabs dashboard.
- **Segment window** (`SEGMENT_START` / `SEGMENT_END` in `config.py`) is set
  to 39.5s–44.0s based on the sample video. Re-check these timestamps if you
  swap in a different master video/export.
- **Long names/shop names**: the pipeline clamps time-stretching to 0.85x–1.25x
  so audio never gets distorted; extremely long shop names will just sound
  slightly faster rather than being cut off.
- **Concurrent requests**: this basic version processes one video per request
  in the same process. For real dealer-scale traffic, put `build_personalized_video()`
  behind a task queue (e.g. Celery + Redis) so requests don't block each other.
