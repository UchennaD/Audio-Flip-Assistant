import time

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import app as app_module
from flip import jobs

client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "DATA_DIR", tmp_path / "jobs")

    def fake_split(path, out_dir, model="htdemucs"):
        d = out_dir / model / "source"
        d.mkdir(parents=True)
        out = {}
        for name in ("vocals", "drums", "bass", "other"):
            sf.write(d / f"{name}.wav", sf.read(path)[0], 22050)
            out[name] = d / f"{name}.wav"
        return out

    def fake_midi(path, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{path.stem}_basic_pitch.mid").write_bytes(b"MThd")

    monkeypatch.setattr(jobs, "split_stems", fake_split)
    monkeypatch.setattr(jobs, "to_midi", fake_midi)


def wait_done(job_id, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.5)
    raise AssertionError("job did not finish")


def upload(path, **form):
    with open(path, "rb") as f:
        return client.post("/api/jobs", files={"file": (path.name, f, "audio/wav")}, data=form)


def test_full_pipeline(click_wav):
    r = upload(click_wav, split="true")
    assert r.status_code == 200
    job = wait_done(r.json()["id"])
    assert job["status"] == "done", job["error"]
    assert job["result"]["track"]["bpm"] > 0
    names = {s["name"] for s in job["result"]["stems"]}
    assert names == {"vocals", "drums", "bass", "other"}
    assert [s["midi"] for s in job["result"]["stems"] if s["name"] == "drums"] == [False]
    jid = job["id"]
    assert client.get(f"/api/jobs/{jid}/audio").status_code == 200
    assert client.get(f"/api/jobs/{jid}/stems/bass.wav").status_code == 200
    assert client.get(f"/api/jobs/{jid}/export/stems").headers["content-type"] == "application/zip"
    assert client.get(f"/api/jobs/{jid}/export/midi").status_code == 200


def test_analyze_only_skips_stems(click_wav):
    job = wait_done(upload(click_wav, split="false").json()["id"])
    assert job["status"] == "done" and job["result"]["stems"] == []
    assert client.get(f"/api/jobs/{job['id']}/export/stems").status_code == 404


def test_rejects_wrong_file_type(tmp_path):
    bad = tmp_path / "virus.exe"
    bad.write_bytes(b"nope")
    assert upload(bad).status_code == 400


def test_rejects_oversized_file(click_wav, monkeypatch):
    monkeypatch.setattr(jobs, "MAX_BYTES", 1000)
    assert upload(click_wav).status_code == 413


def test_rejects_bad_tempo_range(click_wav):
    assert upload(click_wav, bpm_min="60", bpm_max="100").status_code == 400


def test_path_traversal_and_unknown_ids():
    assert client.get("/api/jobs/not-an-id").status_code == 404
    assert client.get("/api/jobs/" + "a" * 32).status_code == 404
    assert client.get("/api/jobs/" + "a" * 32 + "/stems/..%2f..%2fetc.wav").status_code == 404


def test_old_jobs_are_purged(click_wav, monkeypatch):
    job = wait_done(upload(click_wav, split="false").json()["id"])
    j = jobs.get(job["id"])
    j.created -= 25 * 3600
    jobs.purge_old()
    assert jobs.get(job["id"]) is None and not j.dir.exists()
