"""In-memory job runner. One worker at a time, because stem splitting is heavy."""
import os
import shutil
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flip.analyze import analyze_file, waveform
from flip.midi import to_midi
from flip.split import split_stems

DATA_DIR = Path(os.environ.get("FLIP_DATA", "data")) / "jobs"
MAX_AGE_SECONDS = 24 * 3600
MAX_BYTES = 100 * 1024 * 1024
ALLOWED_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aif", ".aiff"}
MELODIC = ("vocals", "bass", "other", "guitar", "piano")

_pool = ThreadPoolExecutor(max_workers=1)
_jobs = {}
_lock = threading.Lock()


class Job:
    def __init__(self, filename):
        self.id = uuid.uuid4().hex
        self.filename = filename
        self.status = "queued"  # queued, analyzing, splitting, midi, done, error
        self.error = None
        self.track = None
        self.stems = []  # [{name, duration, peaks, midi}]
        self.created = time.time()
        self.dir = DATA_DIR / self.id

    @property
    def source(self):
        return next(self.dir.glob("source.*"), None)

    def public(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "error": self.error,
            "result": {"track": self.track, "stems": self.stems},
        }


def create(filename):
    job = Job(filename)
    job.dir.mkdir(parents=True, exist_ok=True)
    with _lock:
        _jobs[job.id] = job
    return job


def get(job_id):
    with _lock:
        return _jobs.get(job_id)


def submit(job, split=True, model="htdemucs", bpm_min=None, bpm_max=None):
    purge_old()
    _pool.submit(_run, job, split, model, bpm_min, bpm_max)


def _run(job, split, model, bpm_min, bpm_max):
    try:
        src = job.source
        job.status = "analyzing"
        job.track = analyze_file(src, bpm_min, bpm_max)
        if split:
            job.status = "splitting"
            stems = split_stems(src, job.dir / "stems", model)
            job.status = "midi"
            out = []
            for name, path in stems.items():
                entry = {"name": name, **waveform(path), "midi": False}
                if name in MELODIC:
                    try:
                        to_midi(path, job.dir / "midi")
                        entry["midi"] = True
                    except Exception:
                        traceback.print_exc()  # a failed MIDI pass should not fail the job
                out.append(entry)
            job.stems = out
        job.status = "done"
    except Exception as exc:
        traceback.print_exc()
        job.status = "error"
        job.error = f"{type(exc).__name__}: {exc}"[:300]


def purge_old():
    """Delete uploads and results older than MAX_AGE_SECONDS."""
    cutoff = time.time() - MAX_AGE_SECONDS
    with _lock:
        stale = [j for j in _jobs.values() if j.created < cutoff and j.status in ("done", "error")]
        for j in stale:
            del _jobs[j.id]
    for j in stale:
        shutil.rmtree(j.dir, ignore_errors=True)
