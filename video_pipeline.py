"""
Core pipeline: takes a dealer name + shop name, generates the personalized
audio line, swaps it into the source video's 39.5s-44.0s segment, and
stitches everything back into a final downloadable video.

Approach (voiceover swap, no lip-sync):
  1. Split source video into 3 parts: [before] [segment] [after]
  2. Generate TTS audio for the personalized line
  3. Time-stretch the TTS audio (atempo) so its duration exactly matches
     the segment's duration (SEGMENT_DURATION) -- keeps A/V in sync
     without needing to touch the video frames at all.
  4. Replace the segment's audio track with the new TTS audio
     (original segment audio is dropped so there's no double-voice;
     you can optionally duck in background music instead -- see notes below)
  5. Concatenate [before] + [new segment] + [after] -> final video
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

    # Pad or trim to *exactly* target_duration so the concat is frame-tight.
    # Force stereo + 44100Hz here so it matches the original video's audio
    # format exactly -- mismatched channel layout (mono TTS vs stereo
    # original) is what causes corrupted/broken audio after this point.
    exact_tts_path = os.path.join(job_temp, "tts_exact.mp3")
    _run([
        "ffmpeg", "-y", "-i", fitted_tts_path,
        "-af", f"apad,atrim=0:{target_duration}",
        "-t", str(target_duration),
        "-ar", "44100", "-ac", "2",
        exact_tts_path,
    ])

    # 3. Split source video into before / segment / after (video only cuts,
    #    re-encoded for frame-accurate splits)
    before_path = os.path.join(job_temp, "before.mp4")
    segment_video_path = os.path.join(job_temp, "segment_video.mp4")
    after_path = os.path.join(job_temp, "after.mp4")

    _run([
        "ffmpeg", "-y", "-i", config.SOURCE_VIDEO,
        "-to", str(config.SEGMENT_START),
        "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero",
        before_path,
    ])
    _run([
        "ffmpeg", "-y", "-ss", str(config.SEGMENT_START), "-i", config.SOURCE_VIDEO,
        "-t", str(target_duration),
        "-c:v", "libx264", "-an",  # drop original segment audio
        segment_video_path,
    ])
    _run([
        "ffmpeg", "-y", "-ss", str(config.SEGMENT_END), "-i", config.SOURCE_VIDEO,
        "-c:v", "libx264", "-c:a", "aac", "-avoid_negative_ts", "make_zero",
        after_path,
    ])

    # 4. Attach the new TTS audio to the segment video
    segment_final_path = os.path.join(job_temp, "segment_final.mp4")
    _run([
        "ffmpeg", "-y", "-i", segment_video_path, "-i", exact_tts_path,
        "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest",
        segment_final_path,
    ])

    # 5. Concatenate before + segment_final + after using the CONCAT FILTER
    # (not the concat demuxer). The concat demuxer does raw packet-level
    # splicing and breaks badly when inputs have even slightly different
    # audio formats/timestamps -- it produced corrupted/noisy audio after
    # the splice point. The concat filter instead fully decodes each input
    # and re-encodes the joined result, which is slower but reliable.
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    final_path = os.path.join(config.OUTPUT_DIR, f"{job_id}_{name}_{shop}.mp4".replace(" ", "_"))
    filter_complex = (
        "[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]"
        "concat=n=3:v=1:a=1[outv][outa]"
    )
    _run([
        "ffmpeg", "-y",
        "-i", before_path, "-i", segment_final_path, "-i", after_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac", "-ar", "44100", "-ac", "2",
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
    out = build_personalized_video("Hansraj Kumbhkar", "Krishna Trading Company Gejgarh")
    print("Done:", out)
