(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const AMBER = "#ffb000", DIM = "#6b4a06", LINE = "#232a34", FLASH = "#fff3d1";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  /* ---------- state ---------- */
  const S = {
    job: null, filename: "", status: "idle", error: null,
    track: null, stems: [], stemsLoaded: false, stemsLoading: false,
    pick: "bpm", keyIdx: 0, tab: "analyze", loop: false, mix: {},
    set: { split: true, model: "htdemucs", range: "70,180", hd: true, grid: true },
  };
  try { Object.assign(S.set, JSON.parse(localStorage.getItem("flip.settings") || "{}")); } catch (e) { /* storage blocked */ }
  const saveSettings = () => { try { localStorage.setItem("flip.settings", JSON.stringify(S.set)); } catch (e) { /* ignore */ } };

  /* ---------- formatting ---------- */
  const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const fmtBpm = (v) => String(Math.round(v * 10) / 10);
  const fmtKey = (k) => k.replace(" minor", "m").replace(" major", " maj");
  const LABELS = { idle: "IDLE", uploading: "UPLOADING", queued: "QUEUED", analyzing: "ANALYZING", splitting: "SPLITTING STEMS", midi: "MAKING MIDI", done: "READY", error: "ERROR" };
  const BUSY = new Set(["uploading", "queued", "analyzing", "splitting", "midi"]);

  /* ---------- audio engine (Web Audio) ---------- */
  const eng = { ctx: null, bufs: {}, nodes: [], playing: false, t0: 0, offset: 0 };
  const ctx = () => (eng.ctx ||= new (window.AudioContext || window.webkitAudioContext)());
  async function decode(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Could not load audio (${r.status})`);
    return ctx().decodeAudioData(await r.arrayBuffer());
  }
  const activeSet = () => (S.tab === "stems" && S.stemsLoaded ? S.stems.map((s) => s.name) : eng.bufs.mix ? ["mix"] : []);
  function dur() {
    const b = eng.bufs[activeSet()[0]] || eng.bufs.mix;
    return b ? b.duration : S.track ? S.track.duration : 0;
  }
  function pos() {
    const d = dur();
    if (!d) return 0;
    let p = eng.playing ? eng.ctx.currentTime - eng.t0 : eng.offset;
    if (S.loop && eng.playing) p %= d;
    return Math.max(0, Math.min(p, d));
  }
  function stopNodes() {
    eng.nodes.forEach(({ src }) => { try { src.stop(); } catch (e) { /* already stopped */ } src.disconnect(); });
    eng.nodes = [];
  }
  function applyGains() {
    const solo = S.stems.some((s) => S.mix[s.name] && S.mix[s.name].solo);
    eng.nodes.forEach(({ n, g }) => {
      const m = S.mix[n];
      const audible = n === "mix" ? true : solo ? m.solo : !m.mute;
      g.gain.value = audible ? (m ? m.vol : 1) : 0;
    });
    $$(".ch").forEach((ch) => {
      const m = S.mix[ch.dataset.name];
      ch.dataset.silent = String(solo ? !m.solo : m.mute);
    });
  }
  function startPlay() {
    const names = activeSet();
    if (!names.length) return;
    const c = ctx();
    c.resume();
    stopNodes();
    const d = dur();
    const off = eng.offset >= d ? 0 : eng.offset;
    eng.t0 = c.currentTime - off;
    names.forEach((n) => {
      const src = c.createBufferSource();
      src.buffer = eng.bufs[n];
      src.loop = S.loop;
      const g = c.createGain();
      src.connect(g).connect(c.destination);
      src.start(0, off);
      eng.nodes.push({ n, src, g });
    });
    eng.playing = true;
    applyGains();
    render();
    if (!eng.raf) { eng.raf = true; requestAnimationFrame(tick); }
  }
  function pause() {
    eng.offset = pos();
    stopNodes();
    eng.playing = false;
    render();
  }
  function stopAll() { stopNodes(); eng.playing = false; eng.offset = 0; }
  function refreshPlayback() { if (eng.playing) { eng.offset = pos(); startPlay(); } }
  function seek(frac) { eng.offset = Math.max(0, Math.min(1, frac)) * dur(); if (eng.playing) startPlay(); else drawWave(); }
  function tick() {
    if (!eng.playing) { eng.raf = false; return; }
    if (!S.loop && eng.ctx.currentTime - eng.t0 >= dur()) { stopNodes(); eng.playing = false; eng.offset = 0; eng.raf = false; render(); return; }
    drawWave();
    requestAnimationFrame(tick);
  }

  /* ---------- drawing ---------- */
  function fit(c) {
    const d = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
    if (!w || !h) return null;
    c.width = Math.round(w * d); c.height = Math.round(h * d);
    const x = c.getContext("2d"); x.setTransform(d, 0, 0, d, 0, 0);
    return { x, w, h };
  }
  function bar(x, bx, by, bw, bh) {
    x.beginPath();
    if (x.roundRect) x.roundRect(bx, by, bw, bh, Math.min(bw / 2, 2)); else x.rect(bx, by, bw, bh);
    x.fill();
  }
  function drawWave() {
    const f = fit($("#wave")); if (!f) return;
    const { x, w, h } = f, mid = h / 2;
    x.clearRect(0, 0, w, h);
    if (!S.track) {
      x.strokeStyle = DIM; x.setLineDash([2, 5]); x.beginPath(); x.moveTo(0, mid); x.lineTo(w, mid); x.stroke(); x.setLineDash([]);
      return;
    }
    const d = S.track.duration || dur();
    const bpm = S.track[S.pick];
    if (S.set.grid && bpm && d) {
      x.strokeStyle = LINE; x.lineWidth = 1; x.setLineDash([3, 4]);
      for (let t = S.track.first_beat || 0; t < d; t += (60 / bpm) * 4) {
        const gx = Math.round((t / d) * w) + 0.5;
        x.beginPath(); x.moveTo(gx, 0); x.lineTo(gx, h); x.stroke();
      }
      x.setLineDash([]);
    }
    const p = S.track.peaks, n = p.length, step = w / n, bw = Math.max(2, step * 0.5);
    const px = d ? (pos() / dur()) * w : 0;
    for (let i = 0; i < n; i++) {
      const bh = Math.max(3, p[i] * h * 0.8), bx = i * step + (step - bw) / 2;
      x.fillStyle = bx < px ? AMBER : DIM;
      bar(x, bx, mid - bh / 2, bw, bh);
    }
    x.fillStyle = FLASH; x.fillRect(Math.round(px) - 1, 0, 2, h);
  }
  function drawMinis() {
    $$(".mini").forEach((c) => {
      const s = S.stems.find((st) => st.name === c.dataset.name); if (!s) return;
      const f = fit(c); if (!f) return;
      const N = 24, per = s.peaks.length / N, step = f.w / N, bw = Math.max(2, step * 0.5);
      f.x.fillStyle = AMBER;
      const avg = Array.from({ length: N }, (_, i) => {
        const sl = s.peaks.slice(Math.floor(i * per), Math.max(Math.floor(i * per) + 1, Math.floor((i + 1) * per)));
        return sl.reduce((a, v) => a + v, 0) / sl.length;
      });
      const top = Math.max(...avg, 0.001);
      avg.forEach((v, i) => {
        const bh = Math.max(3, (v / top) * f.h * 0.85);
        bar(f.x, i * step + (step - bw) / 2, (f.h - bh) / 2, bw, bh);
      });
    });
  }

  /* ---------- render ---------- */
  function render() {
    const t = S.track, busy = BUSY.has(S.status);
    $("#fname").textContent = S.filename || "no file loaded";
    const st = $("#status");
    st.textContent = S.status === "done" ? S.tab.replace("settings", "setup").toUpperCase() : LABELS[S.status];
    st.classList.toggle("live", busy);
    $("#idle").hidden = !!t;
    if (!t) $("#idle").innerHTML = busy
      ? `<div><b>${LABELS[S.status].toLowerCase()}…</b><small>this can take a minute for long tracks</small></div>`
      : "<div><b>Drop a track here</b><small>mp3 · wav · flac · m4a · ogg · up to 100 MB</small></div>";
    $(".readout").classList.toggle("busy", busy && !t);
    $("#bpm").textContent = t ? fmtBpm(t[S.pick]) : "---";
    $("#key").textContent = t ? fmtKey(t.key_candidates[S.keyIdx].key) : "---";
    $("#len").textContent = t ? fmtTime(t.duration) : "-:--";

    $$("#tempo .key").forEach((b) => {
      const k = b.dataset.pick;
      b.disabled = !t;
      b.setAttribute("aria-pressed", String(!!t && S.pick === k));
      $(".sub", b).textContent = t ? fmtBpm(t[k]) : "--";
    });
    $("#tempo-block").hidden = !S.set.hd;
    $$("#altkeys .key").forEach((b, i) => {
      const c = t && t.key_candidates[i];
      b.disabled = !c;
      b.setAttribute("aria-pressed", String(!!c && S.keyIdx === i));
      $(".silk", b).textContent = c ? fmtKey(c.key) : "--";
      $(".sub", b).textContent = c ? c.score.toFixed(2) : " ";
    });

    const playable = !!eng.bufs.mix;
    $("#play").disabled = !playable;
    $("#play").setAttribute("aria-label", eng.playing ? "Pause" : "Play");
    $("#playicon").innerHTML = eng.playing ? '<path d="M6 4h4v16H6zM14 4h4v16h-4z"/>' : '<path d="M7 4.5v15l12-7.5z"/>';
    $("#loop").setAttribute("aria-pressed", String(S.loop));

    const hasStems = S.stems.length > 0;
    $("#stems-empty").hidden = hasStems;
    $("#stems-empty").textContent = S.status === "error" ? "" : BUSY.has(S.status)
      ? "Stems appear here when splitting finishes." : "Scan a track with stem splitting on to get channels here.";
    $("#stems-title").textContent = hasStems ? `${S.stems.length} channels${S.stemsLoading ? " · loading audio" : ""}` : "Stems";
    setLink("#export-stems", hasStems ? `/api/jobs/${S.job}/export/stems` : null);
    setLink("#export-midi", S.stems.some((s) => s.midi) ? `/api/jobs/${S.job}/export/midi` : null);

    $("#note").textContent = S.error ? S.error : "Local only · files delete after 24 h";
    drawWave();
  }
  function setLink(sel, href) {
    const a = $(sel);
    if (href) { a.href = href; a.removeAttribute("aria-disabled"); } else { a.removeAttribute("href"); a.setAttribute("aria-disabled", "true"); }
  }
  function buildMixer() {
    const m = $("#mixer"); m.innerHTML = "";
    S.stems.forEach((s) => {
      S.mix[s.name] ||= { vol: 0.8, mute: false, solo: false };
      const ch = document.createElement("div");
      ch.className = "ch"; ch.dataset.name = s.name; ch.dataset.silent = "false";
      const tag = s.midi ? "audio · midi" : "audio only";
      ch.innerHTML = `<canvas class="mini" data-name="${s.name}" aria-label="${s.name} waveform"></canvas>
        <h3>${s.name}</h3><div class="tag">${tag}</div>
        <div class="fader-wrap"><input class="fader" type="range" min="0" max="100" value="80" aria-label="${s.name} level"></div>
        <div class="ms"><button data-k="mute" aria-pressed="false" aria-label="Mute ${s.name}">M</button><button data-k="solo" aria-pressed="false" aria-label="Solo ${s.name}">S</button></div>`;
      m.appendChild(ch);
      $(".fader", ch).addEventListener("input", (e) => { S.mix[s.name].vol = e.target.value / 100; applyGains(); });
      $$(".ms button", ch).forEach((b) => b.addEventListener("click", () => {
        const k = b.dataset.k; S.mix[s.name][k] = !S.mix[s.name][k];
        b.setAttribute("aria-pressed", String(S.mix[s.name][k])); applyGains();
      }));
    });
    drawMinis();
  }

  /* ---------- upload + polling ---------- */
  function reset() {
    stopAll(); eng.bufs = {};
    Object.assign(S, { job: null, status: "idle", error: null, track: null, stems: [], stemsLoaded: false, stemsLoading: false, pick: "bpm", keyIdx: 0, mix: {} });
    $("#mixer").innerHTML = "";
  }
  function fail(msg) { S.status = "error"; S.error = msg; render(); }
  async function submit(file) {
    if (!file) return;
    reset();
    S.filename = file.name; S.status = "uploading"; render();
    const [lo, hi] = S.set.range.split(",");
    const fd = new FormData();
    fd.append("file", file); fd.append("split", S.set.split); fd.append("model", S.set.model);
    fd.append("bpm_min", lo); fd.append("bpm_max", hi);
    let r;
    try { r = await fetch("/api/jobs", { method: "POST", body: fd }); } catch (e) { return fail("Could not reach the server"); }
    if (!r.ok) { const e = await r.json().catch(() => ({})); return fail(e.detail || `Upload failed (${r.status})`); }
    const { id } = await r.json();
    S.job = id; S.status = "queued"; render();
    decode(`/api/jobs/${id}/audio`).then((b) => { if (S.job === id) { eng.bufs.mix = b; render(); } })
      .catch(() => { if (S.job === id) fail("This browser could not decode that file"); });
    poll(id);
  }
  async function poll(id) {
    while (S.job === id) {
      let j;
      try { const r = await fetch(`/api/jobs/${id}`); if (!r.ok) return fail("Lost track of the job"); j = await r.json(); }
      catch (e) { return fail("Lost connection to the server"); }
      if (S.job !== id) return;
      S.status = j.status;
      if (j.result.track && !S.track) { S.track = j.result.track; }
      if (j.result.stems.length && !S.stems.length) { S.stems = j.result.stems; buildMixer(); if (S.tab === "stems") loadStems(); }
      if (j.status === "error") { S.error = j.error || "Something went wrong"; render(); return; }
      render();
      if (j.status === "done") return;
      await sleep(1000);
    }
  }
  async function loadStems() {
    if (S.stemsLoaded || S.stemsLoading || !S.stems.length) return;
    const id = S.job; S.stemsLoading = true; render();
    try {
      await Promise.all(S.stems.map(async (s) => { eng.bufs[s.name] = await decode(`/api/jobs/${id}/stems/${s.name}.wav`); }));
      if (S.job !== id) return;
      S.stemsLoaded = true;
    } catch (e) { if (S.job === id) S.error = "Could not load stem audio"; }
    S.stemsLoading = false; render(); refreshPlayback();
  }

  /* ---------- wiring ---------- */
  const fileInput = $("#file");
  const pickFile = () => fileInput.click();
  fileInput.addEventListener("change", () => { submit(fileInput.files[0]); fileInput.value = ""; });
  $("#scan").addEventListener("click", pickFile);
  $(".wavebox").addEventListener("click", (e) => {
    if (!S.track) { if (!BUSY.has(S.status)) pickFile(); return; }
    const b = e.currentTarget.getBoundingClientRect(); seek((e.clientX - b.left) / b.width);
  });
  const unit = $("#unit");
  ["dragenter", "dragover"].forEach((ev) => unit.addEventListener(ev, (e) => { e.preventDefault(); unit.classList.add("dragging"); }));
  unit.addEventListener("dragleave", (e) => { if (!unit.contains(e.relatedTarget)) unit.classList.remove("dragging"); });
  unit.addEventListener("drop", (e) => { e.preventDefault(); unit.classList.remove("dragging"); submit(e.dataTransfer.files[0]); });

  $("#play").addEventListener("click", () => (eng.playing ? pause() : startPlay()));
  $("#rewind").addEventListener("click", () => { eng.offset = 0; if (eng.playing) startPlay(); else drawWave(); });
  $("#loop").addEventListener("click", () => { S.loop = !S.loop; eng.nodes.forEach(({ src }) => { src.loop = S.loop; }); render(); });
  document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && document.activeElement === document.body && eng.bufs.mix) { e.preventDefault(); eng.playing ? pause() : startPlay(); }
  });

  $$("#tempo .key").forEach((b) => b.addEventListener("click", () => { S.pick = b.dataset.pick; render(); }));
  $$("#altkeys .key").forEach((b, i) => b.addEventListener("click", () => { S.keyIdx = i; render(); }));
  $$("#export-stems, #export-midi").forEach((a) => a.addEventListener("click", (e) => { if (a.getAttribute("aria-disabled") === "true") e.preventDefault(); }));

  $$("[data-tab]").forEach((t) => t.addEventListener("click", () => {
    S.tab = t.dataset.tab;
    $$("[data-tab]").forEach((o) => o.setAttribute("aria-selected", String(o === t)));
    $$(".view").forEach((v) => v.classList.toggle("on", v.id === "v-" + S.tab));
    if (S.tab === "stems") loadStems();
    refreshPlayback(); render(); drawMinis();
  }));

  function bindToggle(id, key, after) {
    const el = $(id);
    el.setAttribute("aria-pressed", String(S.set[key]));
    el.addEventListener("click", () => { S.set[key] = !S.set[key]; el.setAttribute("aria-pressed", String(S.set[key])); saveSettings(); if (after) after(); });
  }
  function bindChoice(id, key) {
    const btns = $$(`${id} button`);
    btns.forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.v === S.set[key]));
      b.addEventListener("click", () => { S.set[key] = b.dataset.v; btns.forEach((o) => o.setAttribute("aria-pressed", String(o === b))); saveSettings(); });
    });
  }
  bindToggle("#set-split", "split"); bindToggle("#set-hd", "hd", render); bindToggle("#set-grid", "grid", drawWave);
  bindChoice("#set-model", "model"); bindChoice("#set-range", "range");

  window.addEventListener("resize", () => { drawWave(); drawMinis(); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { drawWave(); drawMinis(); });
  render();
})();
