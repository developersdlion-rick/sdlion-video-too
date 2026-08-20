"""
Core pipeline: takes a dealer name + shop name, generates the personalized
audio line, swaps it into the source video's segment window, and stitches
everything back into a final downloadable video.

Approach (voiceover swap, no lip-sync):
  1. Generate TTS audio for the personalized line
  2. Time-stretch the TTS audio (atempo) so its duration exactly matches
     the segment's duration (SEGMENT_DURATION) -- keeps A/V in sync
     without needing to touch the video frames at all.
  3. In ONE ffmpeg pass: trim the source video into [before]/[segment]/[after]
     pieces using filter_complex, swap in the new TTS audio for the segment
     piece, and concatenate everything -- all in a single encode.

Why a single pass matters: an earlier version of this ran 5 separate ffmpeg
processes (each fully decoding + re-encoding video), which worked fine on a
powerful machine but exceeded the CPU/RAM available on constrained hosting
(e.g. Render's free tier, 512MB RAM) and caused the process to be silently
killed mid-request (OOM). A single ffmpeg invocation that decodes the
source once and encodes the output once uses dramatically less memory.
"""
import os
import re
import shutil
import subprocess
import uuid

import config
from tts_provider import generate_speech


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result


def _ffprobe_duration(path: str) -> float:
    result = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ])
    return float(result.stdout.strip())


def sanitize_name(text: str) -> str:
    """Basic cleanup so free-text form input can't break the TTS line or filenames."""
    text = text.strip()
    text = re.sub(r"[^\w\s.,'&-]", "", text, flags=re.UNICODE)
    return text[:80]  # reasonable length cap


def build_personalized_video(name: str, shop: str, voice_id: str = None) -> str:
    """
    Returns the path to the final personalized mp4.
    """
    name = sanitize_name(name)
    shop = sanitize_name(shop)
    if not name or not shop:
        raise ValueError("Name and shop name are required.")

    job_id = uuid.uuid4().hex[:8]
    job_temp = os.path.join(config.TEMP_DIR, job_id)
    os.makedirs(job_temp, exist_ok=True)

    line = config.LINE_TEMPLATE.format(name=name, shop=shop)

    # 1. Generate raw TTS audio
    raw_tts_path = os.path.join(job_temp, "tts_raw.mp3")
    generate_speech(line, raw_tts_path, voice_id=voice_id)

    # 2. Time-stretch to match the segment duration exactly
    tts_duration = _ffprobe_duration(raw_tts_path)
    target_duration = config.SEGMENT_DURATION
    tempo = tts_duration / target_duration  # >1 = speed up, <1 = slow down

    # Keep the stretch within a natural-sounding range. If the generated
    # line is wildly longer/shorter than the slot (e.g. a very long shop
    # name), clamp it -- the audio will just be slightly faster/slower
    # than "perfectly natural" rather than distorted.
    tempo = max(0.85, min(1.25, tempo))

    fitted_tts_path = os.path.join(job_temp, "tts_fitted.mp3")
    _run([
        "ffmpeg", "-y", "-i", raw_tts_path,
        "-filter:a", f"atempo={tempo:.4f}",
        fitted_tts_path,
    ])

    # Pad or trim to *exactly* target_duration, and force stereo + 44100Hz
    # so it matches the original video's audio format exactly (mismatched
    # channel layout is what causes corrupted/broken audio at the splice).
    exact_tts_path = os.path.join(job_temp, "tts_exact.mp3")
    _run([
        "ffmpeg", "-y", "-i", fitted_tts_path,
        "-af", f"apad,atrim=0:{target_duration}",
        "-t", str(target_duration),
        "-ar", "44100", "-ac", "2",
        exact_tts_path,
    ])

    # 3. Single-pass trim + swap + concat.
    #    Input 0 = source video (used for all 3 video pieces + before/after audio)
    #    Input 1 = the new TTS audio (used for the segment's audio only)
    source_duration = _ffprobe_duration(config.SOURCE_VIDEO)
    seg_start = config.SEGMENT_START
    seg_end = config.SEGMENT_END

    filter_complex = (
        f"[0:v]trim=start=0:end={seg_start},setpts=PTS-STARTPTS[v0];"
        f"[0:a]atrim=start=0:end={seg_start},asetpts=PTS-STARTPTS[a0];"
        f"[0:v]trim=start={seg_start}:end={seg_end},setpts=PTS-STARTPTS[v1];"
        f"[1:a]asetpts=PTS-STARTPTS[a1];"
        f"[0:v]trim=start={seg_end}:end={source_duration},setpts=PTS-STARTPTS[v2];"
        f"[0:a]atrim=start={seg_end}:end={source_duration},asetpts=PTS-STARTPTS[a2];"
        f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[catv][outa];"
        f"[catv]scale={config.OUTPUT_WIDTH}:{config.OUTPUT_HEIGHT}[outv]"
    )

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    final_path = os.path.join(config.OUTPUT_DIR, f"{job_id}_{name}_{shop}.mp4".replace(" ", "_"))

    _run([
        "ffmpeg", "-y",
        "-i", config.SOURCE_VIDEO,
        "-i", exact_tts_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-threads", "1",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        final_path,
    ])

    # Clean up this job's temp working files. Not strictly necessary
    # locally, but matters on small-disk hosting (e.g. Render's free tier)
    # so temp files from past requests don't pile up and fill the disk.
    shutil.rmtree(job_temp, ignore_errors=True)

    return final_path


if __name__ == "__main__":
    # Manual test:
    #   ELEVENLABS_API_KEY=xxx python video_pipeline.py
    out = build_personalized_video("Ram Sharma", "Sharma Steel Corner Bihar")
    print("Done:", out)
