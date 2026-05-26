// camera.js — Webcam capture + frame encoding

const Camera = (() => {
  let stream        = null;
  let videoEl       = null;
  let captureCanvas = null;
  let captureCtx    = null;
  let running       = false;
  let frameCallback = null;
  let _rafId        = null;
  const TARGET_FPS  = 30;
  const FRAME_MS    = 1000 / TARGET_FPS;
  const JPEG_Q      = 0.72;
  let lastSent      = 0;

  function init(el) {
    videoEl       = el;
    captureCanvas = document.createElement("canvas");
    captureCtx    = captureCanvas.getContext("2d");
  }

  // For mobile MJPEG stream — video element already has src set
  function initFromVideo(el) {
    videoEl = el;
    if (!captureCanvas) {
      captureCanvas = document.createElement("canvas");
      captureCtx    = captureCanvas.getContext("2d");
    }
    running = true;
    _loop();
  }

  async function start(constraints) {
    const c = constraints || { video: { width:{ideal:1280}, height:{ideal:720} } };

    // Polyfill for older browsers
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

    stream = await navigator.mediaDevices.getUserMedia(c);
    videoEl.srcObject = stream;
    await videoEl.play();
    captureCanvas.width  = videoEl.videoWidth  || 1280;
    captureCanvas.height = videoEl.videoHeight || 720;
    running = true;
    _loop();
  }

  function stop() {
    running = false;
    if (_rafId) cancelAnimationFrame(_rafId);
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = null;
    if (videoEl) { videoEl.srcObject = null; videoEl.src = ""; }
  }

  function _loop() {
    if (!running) return;
    _rafId = requestAnimationFrame(_loop);
    const now = performance.now();
    if (now - lastSent < FRAME_MS) return;
    lastSent = now;
    _capture();
  }

  function _capture() {
    if (!videoEl || videoEl.readyState < 2) return;
    captureCanvas.width  = videoEl.videoWidth  || 640;
    captureCanvas.height = videoEl.videoHeight || 480;
    captureCtx.drawImage(videoEl, 0, 0, captureCanvas.width, captureCanvas.height);
    const b64 = captureCanvas.toDataURL("image/jpeg", JPEG_Q).split(",")[1];
    if (frameCallback) frameCallback(b64, performance.now());
  }

  function onFrame(cb) { frameCallback = cb; }

  function snapshot() {
    if (!videoEl) return null;
    captureCtx.drawImage(videoEl, 0, 0, captureCanvas.width, captureCanvas.height);
    return captureCanvas.toDataURL("image/jpeg", 0.92);
  }

  return { init, initFromVideo, start, stop, onFrame, snapshot };
})();