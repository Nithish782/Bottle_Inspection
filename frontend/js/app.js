// app.js — Multi-camera: Webcam | Mobile | RTSP

const WS_URL = "ws://localhost:8000/ws";

// ── DOM refs ──────────────────────────────────────────────────────────
const videoEl    = document.getElementById("videoEl");
const overlayEl  = document.getElementById("overlayCanvas");
const placeholder= document.getElementById("placeholder");
const placeholderText = document.getElementById("placeholderText");
const placeholderSub  = document.getElementById("placeholderSub");
const btnStart   = document.getElementById("btnStart");
const btnStop    = document.getElementById("btnStop");
const statusPill = document.getElementById("statusPill");
const statusTxt  = document.getElementById("statusText");
const sourceBadge= document.getElementById("sourceBadge");
const recBadge   = document.getElementById("recBadge");
const fpsOvl     = document.getElementById("fpsOverlay");
const latOvl     = document.getElementById("latOverlay");
const mFps       = document.getElementById("mFps");
const mLatency   = document.getElementById("mLatency");
const mBottles   = document.getElementById("mBottles");
const mPass      = document.getElementById("mPass");
const mFail      = document.getElementById("mFail");
const bottleCards= document.getElementById("bottleCards");
const sTotalPass = document.getElementById("sTotalPass");
const sTotalFail = document.getElementById("sTotalFail");
const sYield     = document.getElementById("sYield");
const sAvgConf   = document.getElementById("sAvgConf");
const defectEl   = document.getElementById("defectBreakdown");
const chartEl    = document.getElementById("miniChart");
const logEl      = document.getElementById("logList");
const camConfig  = document.getElementById("camConfig");

// ── State ─────────────────────────────────────────────────────────────
let currentSource = "webcam";   // webcam | mobile | rtsp
let ws            = null;
let running       = false;
let totalPass     = 0;
let totalFail     = 0;
let rafId         = null;

// ── Init ──────────────────────────────────────────────────────────────
Camera.init(videoEl);
Stats.renderChart(chartEl);
Stats.renderDefects(defectEl);
setInterval(clockTick, 1000);
clockTick();
renderConfigPanel("webcam");

function clockTick() {
  const el = document.getElementById("clockEl");
  if (el) el.textContent = new Date().toLocaleTimeString("en-US",{hour12:false});
}

// ── Source switcher ───────────────────────────────────────────────────
function switchSource(src) {
  if (running) stopStream();
  currentSource = src;

  // Update tabs
  ["webcam","mobile","rtsp"].forEach(s => {
    document.getElementById("tab-"+s).classList.toggle("active", s===src);
  });

  renderConfigPanel(src);
  Stats.log(logEl, `Source switched to: ${src.toUpperCase()}`, "blue");
}

function renderConfigPanel(src) {
  if (src === "webcam") {
    camConfig.innerHTML = `
      <span class="config-label">Camera:</span>
      <select id="deviceSelect" style="flex:1;background:var(--surface3);border:1px solid var(--border);color:var(--text);padding:7px 12px;border-radius:8px;font-size:13px;font-family:var(--font)">
        <option value="">Loading cameras...</option>
      </select>`;
    loadWebcamDevices();

  } else if (src === "mobile") {
    camConfig.innerHTML = `
      <span class="config-label">Mobile IP:</span>
      <input id="mobileUrl" type="text"
        placeholder="e.g. http://192.168.1.5:8080/video"
        value="${localStorage.getItem('mobileUrl')||''}"/>
      <span style="font-size:11px;color:var(--text3)">Use IP Webcam app (Android) or EpocCam (iOS)</span>`;

  } else if (src === "rtsp") {
    camConfig.innerHTML = `
      <span class="config-label">RTSP URL:</span>
      <input id="rtspUrl" type="text"
        placeholder="e.g. rtsp://admin:pass@192.168.1.10:554/stream"
        value="${localStorage.getItem('rtspUrl')||''}"/>`;
  }
}

async function loadWebcamDevices() {
  try {
    // Polyfill for older browsers / non-secure contexts
    if (!navigator.mediaDevices) {
      navigator.mediaDevices = {};
    }
    if (!navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia = function(cs) {
        const gUM = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
        if (!gUM) {
          return Promise.reject(new Error(
            "Webcam access requires HTTPS or localhost. " +
            "Please open this page via http://localhost or https://"
          ));
        }
        return new Promise((resolve, reject) => gUM.call(navigator, cs, resolve, reject));
      };
    }
    // Request permission first so labels are populated
    await navigator.mediaDevices.getUserMedia({ video: true });
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter(d => d.kind === "videoinput");
    const sel = document.getElementById("deviceSelect");
    sel.innerHTML = cameras.map((d,i) =>
      `<option value="${d.deviceId}">${d.label || "Camera " + (i+1)}</option>`
    ).join("");
  } catch(e) {
    document.getElementById("deviceSelect").innerHTML =
      `<option value="">Default Camera</option>`;
  }
}

// ── Start stream ──────────────────────────────────────────────────────
async function startStream() {
  if (currentSource === "webcam")  await startWebcam();
  else if (currentSource === "mobile") await startMobile();
  else if (currentSource === "rtsp")   await startRTSP();
}

// 1. WEBCAM
async function startWebcam() {
  try {
    const deviceId = document.getElementById("deviceSelect")?.value;
    const constraints = {
      video: deviceId
        ? { deviceId: { exact: deviceId }, width:{ideal:1280}, height:{ideal:720} }
        : { width:{ideal:1280}, height:{ideal:720} }
    };
    await Camera.start(constraints);
    Camera.onFrame(onFrame);
    setLive(true, "WEBCAM");
    Stats.log(logEl, "Webcam started", "green");
    connectWS();
  } catch(e) {
    Stats.log(logEl, "Webcam error: " + e.message, "red");
    alert("Could not access webcam: " + e.message);
  }
}

// 2. MOBILE CAMERA (IP Webcam / EpocCam)
async function startMobile() {
  const url = document.getElementById("mobileUrl")?.value.trim();
  if (!url) { alert("Enter the mobile camera URL.\nExample: http://192.168.1.5:8080/video"); return; }
  localStorage.setItem("mobileUrl", url);

  try {
    const res = await fetch("http://localhost:8000/open-rtsp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (data.error) { alert("Mobile stream error: " + data.error); return; }

    setLive(true, "MOBILE");
    Stats.log(logEl, "Mobile camera connected via backend: " + url, "green");

    connectWS_RTSP();
  } catch(e) {
    Stats.log(logEl, "Mobile connection failed: " + e.message, "red");
    alert("Could not connect to backend. Make sure backend is running.");
  }
}

// 3. RTSP (via backend proxy — browser can't open RTSP directly)
async function startRTSP() {
  const url = document.getElementById("rtspUrl")?.value.trim();
  if (!url) { alert("Enter the RTSP URL.\nExample: rtsp://admin:password@192.168.1.10:554/stream"); return; }
  localStorage.setItem("rtspUrl", url);

  // Tell backend to open RTSP, then connect WS which streams frames back
  try {
    const res = await fetch("http://localhost:8000/open-rtsp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (data.error) { alert("RTSP error: " + data.error); return; }

    setLive(true, "RTSP");
    Stats.log(logEl, "RTSP stream opened: " + url, "green");

    // For RTSP, backend sends both frame + detections over WS
    connectWS_RTSP();
  } catch(e) {
    Stats.log(logEl, "RTSP connection failed: " + e.message, "red");
    alert("Could not connect to backend. Make sure backend is running.");
  }
}

// ── WebSocket — Webcam/Mobile mode (send frames, get detections) ──────
function connectWS() {
  if (ws) ws.close();
  ws = new WebSocket(WS_URL);
  ws.onopen  = () => Stats.log(logEl, "Backend connected", "green");
  ws.onclose = () => { if(running) Stats.log(logEl, "Backend disconnected", "amber"); }
  ws.onerror = () => Stats.log(logEl, "WebSocket error", "red");
  ws.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.error) { Stats.log(logEl, data.error, "red"); return; }
    handleResults(data.bottles, data.latency_ms, data.total_pass, data.total_fail);
  };
}

// ── WebSocket — RTSP mode (receive frame + detections from backend) ───
function connectWS_RTSP() {
  if (ws) ws.close();
  ws = new WebSocket("ws://localhost:8000/ws-rtsp");
  ws.onopen  = () => Stats.log(logEl, "RTSP stream active", "green");
  ws.onclose = () => { if(running) Stats.log(logEl, "RTSP stream closed", "amber"); }
  ws.onerror = () => Stats.log(logEl, "RTSP WebSocket error", "red");
  ws.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.error) { Stats.log(logEl, data.error, "red"); return; }

    // Draw received JPEG frame onto canvas
    if (data.frame) {
      const img = new Image();
      img.onload = () => {
        const ctx = overlayEl.getContext("2d");
        overlayEl.width  = overlayEl.offsetWidth;
        overlayEl.height = overlayEl.offsetHeight;
        ctx.drawImage(img, 0, 0, overlayEl.width, overlayEl.height);
        if (data.bottles) drawBoxes(data.bottles, overlayEl);
      };
      img.src = "data:image/jpeg;base64," + data.frame;
    }
    handleResults(data.bottles||[], data.latency_ms, data.total_pass, data.total_fail);
  };
}

// ── Frame sender (webcam/mobile) ──────────────────────────────────────
function onFrame(b64) {
  if (!running || !ws || ws.readyState !== WebSocket.OPEN) return;
  const fps = Stats.tickFps();
  mFps.textContent   = fps;
  fpsOvl.textContent = "FPS: " + fps;
  ws.send(JSON.stringify({ frame: b64 }));
}

// ── Draw boxes on canvas ──────────────────────────────────────────────
function drawBoxes(bottles, canvas) {
  const vW = videoEl.videoWidth  || canvas.offsetWidth;
  const vH = videoEl.videoHeight || canvas.offsetHeight;

  // Draw video frame first for webcam
  if (currentSource === "webcam" && videoEl.readyState >= 2) {
    const ctx = canvas.getContext("2d");
    canvas.width  = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
  }
  Overlay.draw(canvas, bottles, vW, vH);
}

// ── Handle detection results ──────────────────────────────────────────
function handleResults(bottles, latency, tp, tf) {
  Stats.pushLatency(latency);
  Stats.processBottles(bottles);
  totalPass = tp; totalFail = tf;

  const fps   = Stats.tickFps();
  const conf  = Stats.avgConf();
  const total = tp + tf;

  mFps.textContent      = fps;
  mLatency.textContent  = latency.toFixed(1) + " ms";
  mBottles.textContent  = bottles.length;
  mPass.textContent     = tp;
  mFail.textContent     = tf;
  fpsOvl.textContent    = "FPS: " + fps;
  latOvl.textContent    = "LAT: " + latency.toFixed(1) + " ms";
  sTotalPass.textContent = tp;
  sTotalFail.textContent = tf;
  sYield.textContent    = total ? Math.round(tp/total*100)+"%" : "--%";
  sAvgConf.textContent  = conf  ? Math.round(conf*100)+"%" : "--%";

  drawBoxes(bottles, overlayEl);
  renderBottleCards(bottles);
  Stats.renderChart(chartEl);
  Stats.renderDefects(defectEl);

  if (bottles.length && Math.random() < 0.04) {
    const b = bottles[0];
    Stats.log(logEl,
      `Bottle #${b.id}: ${b.fill.replace(/_/g," ")}, ${b.label.replace(/_/g," ")}, ${Math.round((b.overall_conf||0)*100)}%`,
      b.pass ? "green" : "red");
  }
}

// ── Stop stream ───────────────────────────────────────────────────────
function stopStream() {
  running = false;
  Camera.stop();
  if (ws) { ws.close(); ws = null; }
  if (rafId) { cancelAnimationFrame(rafId); rafId = null; }

  // Clear video src for mobile
  if (currentSource === "mobile") {
    videoEl.src = "";
  }

  // Tell backend to close RTSP
  if (currentSource === "rtsp") {
    fetch("http://localhost:8000/close-rtsp", { method:"POST" }).catch(()=>{});
  }

  setLive(false);
  resetBottleUI();
  Stats.log(logEl, "Stream stopped", "amber");
}

// ── UI helpers ────────────────────────────────────────────────────────
function setLive(on, label="LIVE") {
  placeholder.style.display  = on ? "none" : "flex";
  videoEl.style.display      = (on && currentSource === "webcam") ? "block" : "none";
  btnStart.style.display     = on ? "none" : "flex";
  btnStop.style.display      = on ? "flex" : "none";
  fpsOvl.style.display       = on ? "block" : "none";
  latOvl.style.display       = on ? "block" : "none";
  recBadge.style.display     = on ? "flex" : "none";
  sourceBadge.style.display  = on ? "block" : "none";
  sourceBadge.textContent    = label;
  statusPill.className       = on ? "status-pill online" : "status-pill offline";
  statusTxt.textContent      = on ? label : "OFFLINE";
  running = on;
}

function renderBottleCards(bottles) {
  if (!bottles.length) { bottleCards.innerHTML = emptyState(); return; }
  bottleCards.innerHTML = bottles.map(b => {
    const cls    = b.pass ? "pass" : (isWarn(b) ? "warn" : "fail");
    const status = b.pass ? "PASS" : (isWarn(b) ? "WARN" : "FAIL");
    const fillPct= b.fill==="proper_fill"?75:b.fill==="under_fill"?32:93;
    const fillCol= b.fill==="proper_fill"?"var(--blue)":b.fill==="under_fill"?"var(--amber)":"var(--red)";
    const fLabel = b.fill.replace(/_/g," ");
    const lLabel = b.label.replace(/_/g," ");
    const fCls   = b.fill==="proper_fill"?"green":b.fill==="under_fill"?"amber":"red";
    const lCls   = b.label==="label_proper"?"green":b.label==="label_torn"?"amber":"red";
    const conf   = Math.round((b.overall_conf||0)*100);
    return `<div class="bottle-card ${cls}">
      <div class="bc-header"><span class="bc-id">BOTTLE #${b.id}</span><span class="bc-badge ${cls}">${status}</span></div>
      <div style="width:100%;height:36px;background:var(--surface3);border-radius:3px;overflow:hidden;display:flex;align-items:flex-end;margin:8px 0">
        <div style="width:100%;height:${fillPct}%;background:${fillCol};border-radius:3px;transition:height .4s"></div>
      </div>
      <div class="bc-rows">
        <div class="bc-row"><span class="bc-row-label">Fill Level</span><span class="bc-row-val ${fCls}">${fLabel}</span></div>
        <div class="bc-row"><span class="bc-row-label">Label</span><span class="bc-row-val ${lCls}">${lLabel}</span></div>
        <div class="bc-row"><span class="bc-row-label">Confidence</span><span class="bc-row-val blue">${conf}%</span></div>
      </div>
      <div class="conf-bar"><div class="conf-fill" style="width:${conf}%;background:${b.pass?"var(--green)":isWarn(b)?"var(--amber)":"var(--red)"}"></div></div>
    </div>`;
  }).join("");
}

function isWarn(b){ return b.fill==="under_fill"||b.label==="label_torn"; }

function emptyState(){
  return`<div class="empty-state"><svg viewBox="0 0 24 24"><path d="M12 2C9 2 7 4 7 7v1H5v12a2 2 0 002 2h10a2 2 0 002-2V8h-2V7c0-3-2-5-5-5z"/></svg>No bottles detected</div>`;
}

function resetBottleUI(){
  bottleCards.innerHTML=emptyState();
  mFps.textContent="--"; mLatency.textContent="-- ms"; mBottles.textContent="0";
  const ctx=overlayEl.getContext("2d");
  ctx.clearRect(0,0,overlayEl.width,overlayEl.height);
}

function resetStats(){
  totalPass=0; totalFail=0;
  mPass.textContent="0"; mFail.textContent="0";
  sTotalPass.textContent="0"; sTotalFail.textContent="0";
  sYield.textContent="--%"; sAvgConf.textContent="--%";
  Stats.reset(); Stats.renderChart(chartEl); Stats.renderDefects(defectEl);
  fetch("http://localhost:8000/reset",{method:"POST"}).catch(()=>{});
  Stats.log(logEl,"Statistics reset","amber");
}

function captureSnapshot(){
  const canvas = document.createElement("canvas");
  canvas.width  = overlayEl.width;
  canvas.height = overlayEl.height;
  canvas.getContext("2d").drawImage(overlayEl,0,0);
  const a=document.createElement("a");
  a.download=`inspection_${Date.now()}.jpg`;
  a.href=canvas.toDataURL("image/jpeg",.92);
  a.click();
  Stats.log(logEl,"Snapshot saved","green");
}