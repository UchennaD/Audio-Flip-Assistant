"""Web server. Run: uvicorn app:app --reload   then open http://127.0.0.1:8000"""
import re
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from flip import jobs
from flip.split import MODELS

app = FastAPI(title="Flip Assistant")
WEB_DIR = Path(__file__).parent / "web"
ID_RE = re.compile(r"^[0-9a-f]{32}$")
NAME_RE = re.compile(r"^[a-z0-9_]{1,24}$")


def _job(job_id):
    if not ID_RE.match(job_id):
        raise HTTPException(404, "No such job")
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "No such job")
    return job


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    split: bool = Form(True),
    model: str = Form("htdemucs"),
    bpm_min: float = Form(None),
    bpm_max: float = Form(None),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in jobs.ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type. Use one of: {', '.join(sorted(jobs.ALLOWED_EXT))}")
    if model not in MODELS:
        raise HTTPException(400, "Unknown stem model")
    if bpm_min and bpm_max and not (20 <= bpm_min < bpm_max <= 400 and bpm_max / bpm_min >= 2):
        raise HTTPException(400, "Tempo range must span at least one octave (for example 70 to 180)")

    job = jobs.create(Path(file.filename).name)
    dest = job.dir / f"source{ext}"
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > jobs.MAX_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File is over {jobs.MAX_BYTES // (1024 * 1024)} MB")
            out.write(chunk)
    jobs.submit(job, split=split, model=model, bpm_min=bpm_min, bpm_max=bpm_max)
    return {"id": job.id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return _job(job_id).public()


@app.get("/api/jobs/{job_id}/audio")
def job_audio(job_id: str):
    src = _job(job_id).source
    if not src:
        raise HTTPException(404, "No audio")
    return FileResponse(src)


@app.get("/api/jobs/{job_id}/stems/{name}.wav")
def job_stem(job_id: str, name: str):
    job = _job(job_id)
    if not NAME_RE.match(name) or name not in {s["name"] for s in job.stems}:
        raise HTTPException(404, "No such stem")
    path = next((job.dir / "stems").glob(f"*/*/{name}.wav"), None)
    if not path:
        raise HTTPException(404, "No such stem")
    return FileResponse(path, media_type="audio/wav")


@app.get("/api/jobs/{job_id}/export/{kind}")
def job_export(job_id: str, kind: str):
    job = _job(job_id)
    if kind == "stems":
        files = [p for p in (job.dir / "stems").glob("*/*/*.wav")]
    elif kind == "midi":
        files = list((job.dir / "midi").glob("*.mid"))
    else:
        raise HTTPException(404, "Unknown export")
    if not files:
        raise HTTPException(404, "Nothing to export yet")
    archive = job.dir / f"{kind}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
        for p in files:
            z.write(p, p.name)
    stem = Path(job.filename).stem
    return FileResponse(archive, media_type="application/zip", filename=f"{stem}_{kind}.zip")


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
