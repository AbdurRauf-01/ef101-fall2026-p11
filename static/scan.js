/* Scan page (version 20). Reads QR codes from the camera or an uploaded photo.
   Uses the browser's built-in BarcodeDetector when it exists, otherwise the bundled jsQR (static/vendor/jsQR.js).
   Everything runs in the browser; the only request made is to this app's /api/scan-lookup. */
(function () {
  'use strict';
  var view = document.getElementById('scan-view');
  var video = document.getElementById('scan-video');
  var canvas = document.getElementById('scan-canvas');
  var statusEl = document.getElementById('scan-status');
  var startBtn = document.getElementById('scan-start');
  var stopBtn = document.getElementById('scan-stop');
  var fileInput = document.getElementById('scan-file');
  var ctx = canvas.getContext('2d', { willReadFrequently: true });
  var stream = null, timer = null, busy = false, detector = null;
  var lastText = '', lastTime = 0;

  function say(msg) { statusEl.textContent = msg; }

  if ('BarcodeDetector' in window) {
    try { detector = new BarcodeDetector({ formats: ['qr_code'] }); } catch (e) { detector = null; }
  }

  function decodeCanvas() {
    // Returns a Promise of the text in the QR code on the canvas, or ''.
    if (detector) {
      return detector.detect(canvas).then(function (r) { return r.length ? r[0].rawValue : ''; })
        .catch(function () { return jsQrText(); });
    }
    return Promise.resolve(jsQrText());
  }

  function jsQrText() {
    if (typeof jsQR !== 'function') return '';
    var img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    var hit = jsQR(img.data, img.width, img.height, { inversionAttempts: 'attemptBoth' });
    return hit ? hit.data : '';
  }

  function lookup(text) {
    // Ask the app what the text means, then open the asset (or report that it is unknown).
    return fetch('/api/scan-lookup?code=' + encodeURIComponent(text), { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.found) {
          say('Found ' + j.asset_id + '. Opening ...');
          stopCamera();
          window.location.href = j.url;
          return true;
        }
        say('Read "' + text.slice(0, 60) + '", but no asset in this inventory matches it.');
        return false;
      })
      .catch(function () { say('Could not reach the app. Is it still running?'); return false; });
  }

  function handleText(text) {
    var now = Date.now();
    if (!text || (text === lastText && now - lastTime < 3000)) return Promise.resolve();
    lastText = text; lastTime = now;
    return lookup(text);
  }

  function tick() {
    if (!stream) return;
    if (!busy && video.readyState >= 2 && video.videoWidth) {
      busy = true;
      var scale = Math.min(1, 800 / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      decodeCanvas().then(handleText).then(function () { busy = false; }, function () { busy = false; });
    }
    timer = setTimeout(tick, 120);
  }

  function stopCamera() {
    if (timer) { clearTimeout(timer); timer = null; }
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    video.srcObject = null;
    view.hidden = true; stopBtn.hidden = true; startBtn.hidden = false;
  }

  startBtn.addEventListener('click', function () {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      say('This browser cannot use the camera here. Open the app at http://127.0.0.1 or localhost, or use the photo upload or the text box.');
      return;
    }
    say('Asking for camera permission ...');
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then(function (s) {
        stream = s; video.srcObject = s;
        view.hidden = false; stopBtn.hidden = false; startBtn.hidden = true;
        return video.play();
      })
      .then(function () { say('Looking for a QR code ...'); tick(); })
      .catch(function (err) {
        stopCamera();
        say(err && err.name === 'NotAllowedError'
          ? 'Camera permission was refused. Allow it for this address, or use the photo upload or the text box.'
          : 'No usable camera was found. Use the photo upload or the text box.');
      });
  });
  stopBtn.addEventListener('click', function () { stopCamera(); say('Camera is off.'); });
  window.addEventListener('pagehide', stopCamera);

  function readPhoto(source, w, h) {
    var scale = Math.min(1, 1200 / Math.max(w, h));
    canvas.width = Math.max(1, Math.round(w * scale));
    canvas.height = Math.max(1, Math.round(h * scale));
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
    decodeCanvas().then(function (text) {
      if (!text) { say('No QR code was found in that image.'); return; }
      lastText = ''; handleText(text);
    });
  }

  fileInput.addEventListener('change', function () {
    var f = fileInput.files && fileInput.files[0];
    if (!f) return;
    // The page's security policy allows data: images but not blob: images, so the file is read as a data: URL.
    var reader = new FileReader();
    reader.onload = function () {
      var img = new Image();
      img.onload = function () { readPhoto(img, img.naturalWidth, img.naturalHeight); };
      img.onerror = function () { say('That file could not be read as an image.'); };
      img.src = reader.result;
    };
    reader.onerror = function () { say('That file could not be read.'); };
    reader.readAsDataURL(f);
    fileInput.value = '';
  });
})();
