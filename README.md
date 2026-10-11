# Flip Assistant

Upload a track, get stems, BPM, key, and MIDI in one pass.

Built on librosa (BPM/key), Demucs (stem separation), and Basic Pitch (audio-to-MIDI).
Only processes files you provide. Clearing samples for release is your responsibility.

## Run
    pip install -r requirements.txt
    python run.py my_track.mp3

## Roadmap
1. [ ] CLI works end to end on 5 of your own tracks
2. [ ] Tests for analyze.py (use a click track at known BPM)
3. [ ] FastAPI backend + job queue for the slow split step
4. [ ] Simple web UI (upload, preview stems, download MIDI)
5. [ ] Auth, upload validation, file size/type limits, auto-delete after 24h
6. [ ] THREAT_MODEL.md and PRIVACY.md
7. [ ] Dockerize, deploy, get the live link 
