"""Transcribe a video and make screenshot contact sheets so Claude can study voice and screen together. Local only.

  outputs/tmp/whisper-venv/bin/python research/video_study_v1/study_video.py "<video.mp4>" outputs/tmp/<name> [--every 30]

Steps, each skipped on rerun if its output exists (so an interrupted run resumes):
1. audio.wav: 16 kHz mono via ffmpeg.
2. chunks/NNNNN.txt: Whisper "medium" on CPU, 10 minutes at a time, `condition_on_previous_text=False`
   (stops repetition loops); lines look like "[h:mm:ss] text". Joined into transcript.txt at the end.
3. every<N>/fNNNN.jpg: one frame every N seconds, then sheets/sheet_NN.jpg: 3x3 grids in time order
   (sheet k covers frames 9(k-1)+1 .. 9k, i.e. from (k-1)*9*N seconds).
Long videos: run it detached (nohup ... &) and watch transcribe.log; about 1 minute of CPU per minute of audio.
After it finishes, scan transcript.txt for repeated lines (Whisper loops) before trusting a section.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import time


def run(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return int(float(out.strip()))


def frames(video, out, every):
    shots = out / f"every{every}"
    if not shots.exists():
        shots.mkdir(parents=True)
        run("-i", str(video), "-vf", f"fps=1/{every},scale=640:-2", str(shots / "f%04d.jpg"))
    sheets = out / "sheets"
    if not sheets.exists():
        sheets.mkdir()
        run("-framerate", "1", "-i", str(shots / "f%04d.jpg"), "-vf", "tile=3x3:padding=4", str(sheets / "sheet_%02d.jpg"))
    print(f"frames: {len(list(shots.glob('*.jpg')))}, sheets: {len(list(sheets.glob('*.jpg')))}", flush=True)


def transcribe(out, total, model_name, limit):
    import whisper  # only inside the whisper venv

    chunks = out / "chunks"
    chunks.mkdir(exist_ok=True)
    model = whisper.load_model(model_name, device="cpu")
    end = min(total, limit) if limit else total
    for start in range(0, end, 600):
        target = chunks / f"{start:05d}.txt"
        if target.exists():
            continue
        wav = chunks / f"{start:05d}.wav"
        run("-ss", str(start), "-t", str(min(600, end - start)), "-i", str(out / "audio.wav"), str(wav))
        t0 = time.time()
        result = model.transcribe(str(wav), fp16=False, language="en", condition_on_previous_text=False,
                                  temperature=(0.0, 0.2, 0.4, 0.6))
        lines = []
        for seg in result["segments"]:
            t = int(start + seg["start"])
            lines.append(f"[{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}] {seg['text'].strip()}")
        tmp = target.with_suffix(".tmp")
        tmp.write_text("\n".join(lines) + "\n")
        tmp.replace(target)
        wav.unlink()
        print(f"chunk {start // 600 + 1}/{(end + 599) // 600} done in {time.time() - t0:.0f}s", flush=True)
    (out / "transcript.txt").write_text("".join(p.read_text() for p in sorted(chunks.glob("*.txt"))))
    print("ALL DONE", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video")
    parser.add_argument("out")
    parser.add_argument("--every", type=int, default=30, help="seconds between screenshots (use 3-5 for short clips)")
    parser.add_argument("--model", default="medium")
    parser.add_argument("--limit", type=int, default=0, help="transcribe only the first N seconds (testing)")
    parser.add_argument("--no-transcribe", action="store_true")
    args = parser.parse_args()
    video, out = Path(args.video).expanduser(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    total = duration(video)
    print(f"video: {total // 60}m{total % 60:02d}s", flush=True)
    frames(video, out, args.every)
    if args.no_transcribe:
        return
    if not (out / "audio.wav").exists():
        run("-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(out / "audio.wav"))
    transcribe(out, total, args.model, args.limit)


if __name__ == "__main__":
    main()
