import { analyze, seededNoise, tailAngle, parseSensorCSV } from './signal.js';
import { PatchTracker } from './tracker.js';

const $ = id => document.getElementById(id);
const scene = $('scene'), ctx = scene.getContext('2d'), video = $('video');
const work = document.createElement('canvas'), workCtx = work.getContext('2d', { willReadFrequently: true });
const tracker = new PatchTracker();
const state = { mode: 'demo', running: true, marking: false, lost: false, gray: null, stream: null,
  visual: [], sensor: [], imported: null, importedName: null, t: 0, sample: 0, startMedia: null,
  lastMedia: -1, lastAnalysis: 0, visualResult: null, sensorResult: null, sourceName: null,
  frequency: 2.4, amplitude: 18, noise: .2, offset: 0, objectURL: null, quality: null,
  rng: seededNoise(20261106), sensorRng: seededNoise(20261107), videoFrameId: null };
let toastTimer;
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 5200); }
function notice(message) { $('notice-text').textContent = message; }
function formatTime(t) { return `${String(Math.floor(t / 60)).padStart(2, '0')}:${(t % 60).toFixed(1).padStart(4, '0')}`; }
function stopStream() {
  state.stream?.getTracks().forEach(track => track.stop()); state.stream = null;
  video.pause(); video.srcObject = null;
  if (state.videoFrameId != null && video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(state.videoFrameId);
  state.videoFrameId = null;
  if (state.objectURL) { URL.revokeObjectURL(state.objectURL); state.objectURL = null; }
  video.removeAttribute('src'); video.load();
}
function resetData(keepMarkers = false) {
  state.visual = []; state.sensor = []; state.visualResult = null; state.sensorResult = null;
  state.t = 0; state.sample = 0; state.startMedia = null; state.lastMedia = -1; state.lost = false;
  state.rng = seededNoise(20261106); state.sensorRng = seededNoise(20261107);
  if (!keepMarkers) { tracker.reset(); state.quality = null; }
  state.lastAnalysis = 0;
  updateMetrics(); drawCharts();
}
function updateToggle() {
  $('toggle').textContent = state.running ? 'Ⅱ Pausar' : '▶ Continuar';
  $('live-dot').style.background = state.running ? '#73dfc3' : '#e4b277';
}
function switchMode(mode) {
  stopStream(); state.mode = mode; state.marking = false; state.running = mode === 'demo';
  state.gray = null; state.sourceName = null; state.imported = null; state.importedName = null;
  resetData();
  for (const name of ['demo', 'camera', 'video']) {
    $(`mode-${name}`).classList.toggle('active', mode === name);
    $(`mode-${name}`).setAttribute('aria-pressed', String(mode === name));
  }
  $('simulation-controls').hidden = mode !== 'demo'; $('real-controls').hidden = mode === 'demo';
  $('camera-start').hidden = mode !== 'camera'; $('video-label').hidden = mode !== 'video'; $('fixture').hidden = mode !== 'video';
  $('video-scrub').hidden = true; $('empty-stage').hidden = mode === 'demo';
  $('empty-title').textContent = mode === 'camera' ? 'La pecera, desde tu celular' : 'Elige un video de tu pecera';
  $('video').hidden = mode === 'demo'; $('mark').disabled = true;
  $('mark-help').textContent = 'Activa la cámara o elige un video. Después marca cabeza, cuerpo y un punto visible de la cola.';
  $('source-badge').textContent = mode === 'demo' ? 'IMAGEN SIMULADA' : mode === 'camera' ? 'CÁMARA · ASISTIDA' : 'VIDEO IMPORTADO · ASISTIDO';
  $('source-badge').className = `badge ${mode === 'demo' ? 'amber' : 'green'}`;
  $('stage-label').textContent = mode === 'demo' ? 'Modelo ilustrativo · sin especie asignada' : 'Procesamiento local · sin envío de imágenes';
  $('tracking-state').textContent = mode === 'demo' ? 'Ángulo de cola respecto al cuerpo' : 'Sin puntos de seguimiento';
  $('quality-label').textContent = mode === 'demo' ? 'Señal sintética reproducible' : 'Seguimiento experimental';
  $('sensor-file-info').textContent = 'Valores en unidades arbitrarias; requieren calibración para interpretarlos físicamente.';
  scene.width = 800; scene.height = 450; $('stage').style.aspectRatio = '16 / 9';
  ctx.clearRect(0, 0, scene.width, scene.height);
  notice(mode === 'demo' ? 'Modo demostración: el pez y ambos canales son simulados. No hay sensor físico conectado.' : 'Imagen real, seguimiento asistido. No hay sensor sumergido conectado. Una pérdida de seguimiento detiene la medición.');
  updateToggle();
}
for (const mode of ['demo', 'camera', 'video']) $(`mode-${mode}`).onclick = () => switchMode(mode);
$('toggle').onclick = async () => {
  if (state.mode === 'demo') { state.running = !state.running; updateToggle(); return; }
  if (!video.videoWidth) { toast('Primero activa la cámara o elige un video.'); return; }
  if (state.running) { state.running = false; video.pause(); updateToggle(); return; }
  if (tracker.points.length !== 3 || state.lost) { toast('Marca primero los tres puntos del pez.'); return; }
  if (state.mode === 'camera') { toast('Tras pausar la cámara, vuelve a marcar los puntos para evitar saltos.'); beginMarking(); return; }
  if (video.ended) { toast('El video terminó. Elige un nuevo instante y vuelve a marcar.'); return; }
  try { await video.play(); state.running = true; updateToggle(); } catch { toast('No se pudo reproducir este video. Prueba con un MP4 compatible.'); }
};
$('reset').onclick = () => {
  if (state.mode === 'demo') { resetData(); state.running = true; }
  else { state.running = false; video.pause(); resetData(); $('tracking-state').textContent = 'Marca nuevamente los tres puntos'; }
  updateToggle(); toast('Registro reiniciado.');
};
for (const [id, key, suffix, scale] of [['frequency', 'frequency', ' Hz', 1], ['angle-amplitude', 'amplitude', '°', 1], ['noise', 'noise', '%', .01], ['sensor-offset', 'offset', ' Hz', 1]]) {
  $(id).oninput = () => {
    const value = Number($(id).value); state[key] = value * scale;
    const outId = { frequency: 'frequency-value', amplitude: 'amplitude-value', noise: 'noise-value', offset: 'offset-value' }[key];
    $(outId).textContent = (key === 'frequency' || key === 'offset' ? value.toFixed(1) : value) + suffix;
    resetData(); state.running = true; updateToggle();
  };
}
function configureVideo() {
  const width = Math.min(480, video.videoWidth), height = Math.round(width * video.videoHeight / video.videoWidth);
  work.width = width; work.height = height; scene.width = width; scene.height = height;
  $('stage').style.aspectRatio = `${width} / ${height}`;
  $('empty-stage').hidden = true; $('mark').disabled = false;
  state.running = false; updateToggle();
  if (state.mode === 'video' && Number.isFinite(video.duration)) {
    $('video-scrub').hidden = false; $('seek').max = video.duration; $('seek').value = video.currentTime;
  }
  grayFrame();
  if (video.requestVideoFrameCallback) scheduleVideoFrame();
  else notice('Este navegador no ofrece tiempos por fotograma. Se usará currentTime; la cadencia y la frecuencia estimada requieren verificación adicional.');
}
video.addEventListener('loadeddata', configureVideo);
video.addEventListener('ended', () => { state.running = false; updateToggle(); $('tracking-state').textContent = 'Video finalizado · registro disponible'; });
video.addEventListener('error', () => { if (state.mode !== 'demo' && (video.src || video.srcObject)) toast('El navegador no pudo leer este video. Prueba un MP4 H.264.'); });
$('camera-start').onclick = async () => {
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    toast('La cámara necesita HTTPS o localhost. También puedes cargar una grabación en «Mi video».'); return;
  }
  $('camera-start').disabled = true;
  try {
    stopStream();
    state.stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 60 } } });
    video.srcObject = state.stream; await video.play();
    notice('Cámara activa. Marca tres puntos sobre el pez. La frecuencia solicitada a la cámara no garantiza la cadencia procesada; se mide con los tiempos recibidos.');
  } catch (error) {
    stopStream();
    toast(error.name === 'NotAllowedError' ? 'Acceso a la cámara denegado. Habilítalo en el navegador o carga un video.' : 'No se pudo abrir la cámara. Carga un video grabado desde «Mi video».');
  } finally { $('camera-start').disabled = false; }
};
$('video-file').onchange = () => {
  const file = $('video-file').files[0]; if (!file) return;
  if (file.size > 500 * 1024 * 1024) { toast('Para esta demo usa un video menor de 500 MB.'); return; }
  stopStream(); resetData(); state.running = false; state.marking = false;
  state.sourceName = file.name; state.objectURL = URL.createObjectURL(file); video.src = state.objectURL; video.load();
  $('source-badge').textContent = 'VIDEO IMPORTADO · ASISTIDO';
  $('mark-help').textContent = 'Busca un tramo con un pez visible, marca los tres puntos y comienza. Puedes analizar un pez por registro.';
  updateToggle();
};
$('fixture').onclick = () => {
  stopStream(); resetData(); state.running = false; state.marking = false;
  state.sourceName = 'synthetic-tracking-fixture-2hz.mp4'; video.src = './tracking-fixture.mp4'; video.load();
  $('source-badge').textContent = 'CLIP DE PRUEBA SINTÉTICO';
  $('source-badge').className = 'badge amber';
  $('mark-help').textContent = 'Prueba del algoritmo: marca los cuadrados 1 (cabeza), 2 (cuerpo), 3 (cola). Frecuencia de referencia: 2 Hz. No es validación con peces reales.';
  notice('Clip sintético de 2 Hz para comprobar el seguimiento asistido. No contiene un pez real ni adquisición de un sensor sumergido.');
  updateToggle();
};
$('seek').oninput = () => {
  state.running = false; video.pause(); resetData(); state.marking = false;
  video.currentTime = Number($('seek').value); $('seek-label').textContent = `${video.currentTime.toFixed(1)} s`;
  $('tracking-state').textContent = 'Instante cambiado · vuelve a marcar'; updateToggle();
};
video.addEventListener('seeked', () => { grayFrame(); drawReal(); });
function grayFrame() {
  if (!video.videoWidth || video.readyState < 2 || !work.width) return null;
  workCtx.drawImage(video, 0, 0, work.width, work.height);
  const data = workCtx.getImageData(0, 0, work.width, work.height).data, gray = new Uint8Array(work.width * work.height);
  for (let i = 0; i < gray.length; i++) gray[i] = .299 * data[i * 4] + .587 * data[i * 4 + 1] + .114 * data[i * 4 + 2];
  state.gray = gray; return gray;
}
function beginMarking() {
  if (!video.videoWidth) return;
  video.pause(); state.running = false; resetData(); state.marking = true; grayFrame();
  $('mark-help').textContent = '1 de 3: toca un detalle con contraste en la cabeza. Después cuerpo y cola. Evita puntos uniformes o muy próximos.';
  $('tracking-state').textContent = 'Selecciona: cabeza → cuerpo → cola'; updateToggle(); drawReal();
}
$('mark').onclick = beginMarking;
scene.addEventListener('pointerdown', async event => {
  if (state.mode === 'demo' || !state.marking || !state.gray) return;
  const rect = scene.getBoundingClientRect(), x = (event.clientX - rect.left) / rect.width * scene.width, y = (event.clientY - rect.top) / rect.height * scene.height;
  if (tracker.points.some(p => Math.hypot(p.x - x, p.y - y) < 15)) { toast('Separa los puntos para distinguir cabeza, cuerpo y cola.'); return; }
  try { tracker.add(state.gray, work.width, work.height, x, y); } catch (error) { toast(error.message); return; }
  drawReal();
  if (tracker.points.length === 1) $('mark-help').textContent = '2 de 3: toca un detalle con contraste en el cuerpo, antes del inicio de la cola.';
  if (tracker.points.length === 2) $('mark-help').textContent = '3 de 3: toca un punto visible de la cola que oscile respecto al cuerpo.';
  if (tracker.points.length === 3) {
    const angle = tailAngle(...tracker.points);
    if (!Number.isFinite(angle) || Math.abs(angle) > 100) { toast('La geometría no parece alineada. Marca cabeza, cuerpo y cola en ese orden.'); beginMarking(); return; }
    state.marking = false; state.lost = false;
    $('mark-help').textContent = 'Seguimiento asistido activo. Comprueba que cada marcador permanezca en su punto anatómico; vuelve a marcar si deriva.';
    try { await video.play(); state.running = true; updateToggle(); } catch { toast('Pulsa Continuar para comenzar la reproducción.'); }
  }
});
function scheduleVideoFrame() {
  if (state.mode === 'demo') return;
  state.videoFrameId = video.requestVideoFrameCallback((now, metadata) => {
    if (state.mode !== 'demo') { processVideoFrame(metadata.mediaTime); scheduleVideoFrame(); }
  });
}
function processVideoFrame(mediaTime) {
  if (!state.running || state.marking || state.lost || tracker.points.length !== 3 || mediaTime <= state.lastMedia) return;
  const delta = state.lastMedia < 0 ? 0 : mediaTime - state.lastMedia;
  state.lastMedia = mediaTime;
  if (state.startMedia === null) state.startMedia = mediaTime;
  const gray = grayFrame(); if (!gray) return;
  const result = delta > .2 ? null : tracker.update(gray, work.width, work.height);
  const angle = result ? tailAngle(...result.points) : NaN;
  if (!result || !Number.isFinite(angle) || Math.abs(angle) > 100) {
    state.lost = true; state.running = false; video.pause(); updateToggle();
    $('tracking-state').textContent = 'Seguimiento perdido · vuelve a marcar'; $('quality-label').textContent = 'Registro detenido';
    notice('Se perdió el seguimiento o la geometría dejó de ser válida. No se inventan muestras: revisa el video y vuelve a marcar para iniciar otro registro.'); return;
  }
  state.t = mediaTime - state.startMedia; state.quality = result.quality;
  if (state.visual.length === 0 || state.t > state.visual.at(-1).t) state.visual.push({ t: state.t, value: angle, quality: result.quality });
  $('tracking-state').textContent = 'Tres parches · revisión visual necesaria';
  $('quality-label').textContent = `Correlación mínima ${(result.quality * 100).toFixed(0)}% · no es exactitud`;
  if (state.mode === 'video') { $('seek').value = mediaTime; $('seek-label').textContent = `${mediaTime.toFixed(1)} s`; }
  if (state.t >= 120) { state.running = false; video.pause(); updateToggle(); toast('Registro de 120 s completo. Descarga los datos.'); }
}
function pointsOverlay(points) {
  if (!points.length) return;
  const colors = ['#73dfc3', '#6bace2', '#f1a482'];
  ctx.lineWidth = 1.5; ctx.strokeStyle = '#ddf8eeaa'; ctx.setLineDash([4, 4]);
  ctx.beginPath(); points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.stroke(); ctx.setLineDash([]);
  points.forEach((p, i) => {
    ctx.strokeStyle = colors[i]; ctx.fillStyle = colors[i]; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2); ctx.fill();
    ctx.font = `${Math.max(8, scene.width / 70)}px ui-monospace,monospace`; ctx.fillText(['CABEZA', 'CUERPO', 'COLA'][i], p.x + 9, p.y - 9);
  });
}
function drawReal() { ctx.clearRect(0, 0, scene.width, scene.height); pointsOverlay(tracker.points); }
function drawFish() {
  const w = scene.width, h = scene.height, t = state.t, angle = state.amplitude * Math.sin(2 * Math.PI * state.frequency * t) * Math.PI / 180;
  ctx.clearRect(0, 0, w, h); const bg = ctx.createLinearGradient(0, 0, w, h); bg.addColorStop(0, '#173f48'); bg.addColorStop(1, '#0c2733'); ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = '#91c9b60b'; ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let y = 0; y < h; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
  for (let i = 0; i < 17; i++) {
    const x = (i * 127.7 + t * (3 + i % 4)) % w, y = h - (i * 57.8 + t * 7) % h;
    ctx.fillStyle = '#a8d8c51d'; ctx.beginPath(); ctx.arc(x, y, 1 + i % 3, 0, Math.PI * 2); ctx.fill();
  }
  const cx = w * .51, cy = h * .51, scale = w / 800;
  ctx.save(); ctx.translate(cx, cy); ctx.scale(scale, scale);
  const tailX = 105 + 95 * Math.cos(angle), tailY = 95 * Math.sin(angle);
  ctx.strokeStyle = '#b3e8d147'; ctx.setLineDash([3, 6]); ctx.beginPath(); ctx.ellipse(126, 0, 74, 48, 0, -.65, .65); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#8ac6aa'; ctx.beginPath(); ctx.moveTo(100, -17); ctx.quadraticCurveTo(145, tailY * .5 - 9, tailX, tailY - 43); ctx.lineTo(tailX - 9, tailY); ctx.lineTo(tailX, tailY + 43); ctx.quadraticCurveTo(145, tailY * .5 + 9, 100, 17); ctx.closePath(); ctx.fill();
  const body = ctx.createLinearGradient(0, -65, 0, 65); body.addColorStop(0, '#a8d8ba'); body.addColorStop(.55, '#c9e8cd'); body.addColorStop(1, '#73a989'); ctx.fillStyle = body;
  ctx.beginPath(); ctx.moveTo(-147, 0); ctx.bezierCurveTo(-120, -58, -5, -75, 106, -16); ctx.quadraticCurveTo(135, 0, 106, 16); ctx.bezierCurveTo(-5, 75, -120, 58, -147, 0); ctx.fill();
  ctx.fillStyle = '#80b79a'; ctx.beginPath(); ctx.moveTo(-20, -47); ctx.lineTo(24, -81); ctx.lineTo(75, -34); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#649a82'; ctx.beginPath(); ctx.moveTo(-11, 8); ctx.lineTo(35, 46); ctx.lineTo(33, 13); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = '#477c6755'; ctx.lineWidth = 1;
  for (let x = -50; x < 95; x += 19) { ctx.beginPath(); ctx.ellipse(x, 0, 12, 35 - Math.abs(x) * .1, 0, -.95, .95); ctx.stroke(); }
  ctx.beginPath(); ctx.arc(-102, -2, 31, -.8, .85); ctx.stroke();
  ctx.fillStyle = '#102d35'; ctx.beginPath(); ctx.arc(-119, -10, 5, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = '#eefae8'; ctx.beginPath(); ctx.arc(-120, -11, 1.6, 0, Math.PI * 2); ctx.fill();
  pointsOverlay([{ x: -119, y: 0 }, { x: 105, y: 0 }, { x: tailX, y: tailY }]);
  ctx.strokeStyle = '#f1a482'; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(105, 0, 45, Math.min(0, angle), Math.max(0, angle)); ctx.stroke();
  ctx.fillStyle = '#f1bc9b'; ctx.font = '12px ui-monospace,monospace'; ctx.fillText(`${(angle * 180 / Math.PI).toFixed(1)}°`, 150, 72);
  ctx.restore();
  ctx.fillStyle = '#8eb5aa'; ctx.font = '10px ui-monospace,monospace'; ctx.fillText('MODELO SINTÉTICO / NO ES UNA MEDICIÓN DE FUERZA', 22, h - 48);
}
function updateMetrics() {
  const v = state.visualResult, s = state.sensorResult;
  $('visual-frequency').textContent = v?.peak ? v.peak.f.toFixed(2) : '—';
  $('visual-detail').textContent = v ? (v.peak ? `Pico candidato · ${v.duration.toFixed(1)} s analizados` : 'Sin periodicidad clara en la banda analizada') : 'Reuniendo al menos 2 segundos…';
  $('amplitude').textContent = v?.peak ? `${v.peak.amplitude.toFixed(1)} °` : '— °';
  $('sensor-frequency').textContent = s?.peak ? s.peak.f.toFixed(2) : '—';
  $('sensor-metric-label').textContent = state.imported ? 'CSV independiente' : state.mode === 'demo' ? 'Sensor simulado' : 'Sensor físico';
  $('sensor-detail').textContent = state.imported ? 'Origen y calibración sin verificar' : state.mode === 'demo' ? 'Sin adquisición física' : 'Sin registro importado';
  const diff = v?.peak && s?.peak ? Math.abs(v.peak.f - s.peak.f) : null;
  $('difference').textContent = diff === null ? '—' : diff.toFixed(2);
  $('comparison-detail').textContent = state.imported ? 'Ventanas no sincronizadas' : state.mode === 'demo' ? 'Canales del mismo modelo' : 'Falta canal independiente';
  $('sensor-badge').textContent = state.imported ? 'CSV IMPORTADO' : 'NO CONECTADO';
  $('sensor-badge').className = `badge ${state.imported ? 'green' : 'neutral'}`;
  $('sampling').textContent = v ? `${state.mode === 'demo' ? 'Simulado' : 'Procesado'} · ${v.fs.toFixed(1)} muestras/s${v.interpolated ? ' · remuestreado' : ''}` : 'Cadencia pendiente de medición';
  $('resolution').textContent = v ? `Resolución física ≈ ${v.resolution.toFixed(2)} Hz · Hann` : 'Ventana de análisis: hasta 8 s';
  $('peak-label').textContent = v?.peak ? `Pico ${v.peak.f.toFixed(2)} Hz` : 'Sin pico confirmado';
}
function plotBase(canvas, minX, maxX, minY, maxY, xLabel, yDecimals = 0) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2), width = canvas.clientWidth, height = canvas.clientHeight;
  if (!width || !height) return null;
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) { canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); }
  const c = canvas.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, width, height);
  const pad = { l: 42, r: 18, t: 18, b: 26 }, iw = width - pad.l - pad.r, ih = height - pad.t - pad.b;
  const x = v => pad.l + (v - minX) / (maxX - minX) * iw, y = v => pad.t + (maxY - v) / (maxY - minY) * ih;
  c.font = '9px system-ui,sans-serif'; c.fillStyle = '#90a297'; c.strokeStyle = '#e8ede7'; c.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = minY + (maxY - minY) * i / 4, yy = y(v); c.beginPath(); c.moveTo(pad.l, yy); c.lineTo(width - pad.r, yy); c.stroke();
    c.textAlign = 'right'; c.fillText(v.toFixed(yDecimals), pad.l - 8, yy + 3);
  }
  for (let i = 0; i <= 4; i++) { const v = minX + (maxX - minX) * i / 4; c.textAlign = 'center'; c.fillText(v.toFixed(xLabel === 's' ? 1 : 0), x(v), height - 8); }
  return { c, x, y, pad, width, height };
}
function drawLine(p, values, color, lineWidth = 1.6) {
  p.c.strokeStyle = color; p.c.lineWidth = lineWidth; p.c.beginPath();
  values.forEach((v, i) => i ? p.c.lineTo(p.x(v.x), p.y(v.y)) : p.c.moveTo(p.x(v.x), p.y(v.y))); p.c.stroke();
}
function drawCharts() {
  const v = state.visualResult;
  const raw = state.visual.filter(r => r.t >= state.t - 8), maxT = raw.at(-1)?.t || 8, minT = Math.max(0, maxT - 8);
  const limit = Math.max(10, ...raw.map(r => Math.abs(r.value))) * 1.2;
  const timePlot = plotBase($('time-chart'), minT, Math.max(minT + 2, maxT), -limit, limit, 's');
  if (timePlot) {
    drawLine(timePlot, raw.map(r => ({ x: r.t, y: r.value })), '#adc9c1', 1.2);
    if (v) drawLine(timePlot, v.filtered.map((a, i) => ({ x: v.filteredTimes[i], y: a })), '#087d70', 2);
  }
  const maxF = v ? Math.min(12, v.fs / 2) : 12, bins = v ? v.bins.filter(b => b.f <= maxF) : [];
  const maxA = Math.max(1, ...bins.map(b => b.amplitude)) * 1.2;
  const freqPlot = plotBase($('fft-chart'), 0, maxF, 0, maxA, 'Hz', maxA < 3 ? 1 : 0);
  if (freqPlot && bins.length) {
    const c = freqPlot.c;
    c.beginPath(); c.moveTo(freqPlot.x(0), freqPlot.y(0)); bins.forEach(b => c.lineTo(freqPlot.x(b.f), freqPlot.y(b.amplitude))); c.lineTo(freqPlot.x(bins.at(-1).f), freqPlot.y(0)); c.closePath(); c.fillStyle = '#087d7012'; c.fill();
    drawLine(freqPlot, bins.map(b => ({ x: b.f, y: b.amplitude })), '#087d70', 1.8);
    if (v.peak) { c.fillStyle = '#087d70'; c.beginPath(); c.arc(freqPlot.x(v.peak.f), freqPlot.y(v.peak.amplitude), 3, 0, Math.PI * 2); c.fill(); }
  }
}
$('sensor-file').onchange = async () => {
  const file = $('sensor-file').files[0]; if (!file) return;
  if (file.size > 10 * 1024 * 1024) { toast('El CSV debe pesar menos de 10 MB.'); return; }
  try {
    const rows = parseSensorCSV(await file.text()); state.imported = rows; state.importedName = file.name;
    state.sensorResult = analyze(rows);
    $('sensor-file-info').textContent = `${file.name} · ${rows.length} muestras · u.a. · sin sincronización ni calibración verificadas.`;
    updateMetrics(); toast(state.sensorResult ? 'CSV analizado. La comparación usa ventanas independientes.' : 'CSV leído. Falta un tramo continuo de al menos 2 segundos.');
  } catch (error) { toast(error.message); }
  $('sensor-file').value = '';
};
function provenance() {
  return { app: 'Aleta PDS Lab', version: '1.0.0', created_at: new Date().toISOString(),
    visual_source: state.mode === 'demo' ? 'synthetic_model' : 'assisted_three_patch_tracking',
    media_source: state.mode === 'video' ? state.sourceName : state.mode,
    physical_sensor_connected: false,
    sensor_source: state.imported ? 'external_csv_unverified' : state.mode === 'demo' ? 'synthetic_model_not_independent' : 'absent',
    sensor_file: state.importedName, sensor_units: 'arbitrary_units_uncalibrated',
    species: null, force_newtons: null, production_classification: null,
    simulation: state.mode === 'demo' ? { frequency_hz: state.frequency, amplitude_degrees: state.amplitude, noise_fraction: state.noise, sensor_frequency_offset_hz: state.offset, seed_visual: 20261106, seed_sensor: 20261107 } : null,
    method: { visual_units: 'degrees', angle_reference: 'head_body_axis', fir: [1,4,6,4,1].map(x => x / 16),
      filter_delay_display_compensation_only: true, fft_input: 'original_resampled_angle', detrend: 'linear', window: 'Hann', analysis_window_s: 8,
      frequency_band_hz: 'max(0.3,2/duration) to min(12,0.4*fs)', interpolation: 'linear_without_antialias_filter', synchronized_with_csv: false },
    limits: ['No mide fuerza.', 'No determina salud, tamaño ni aptitud productiva.', 'Seguimiento experimental, puede derivar pese a una correlación alta.', 'Un pico espectral requiere conteo visual de ciclos.', 'CSV externo sin calibración ni procedencia verificadas.'],
    visual_summary: summary(state.visualResult), sensor_summary: summary(state.sensorResult) };
}
function summary(result) { return result ? { processed_fs_hz: result.fs, duration_s: result.duration, resolution_hz: result.resolution, candidate_frequency_hz: result.peak?.f ?? null, spectral_amplitude: result.peak?.amplitude ?? null, fir_group_delay_s: result.filterDelay } : null; }
function download(name, text, type) { const url = URL.createObjectURL(new Blob([text], { type })), a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
$('export-csv').onclick = () => {
  if (!state.visual.length && !state.imported) { toast('Primero reúne un registro.'); return; }
  const rows = ['t_s,value,unit,channel,provenance,tracking_correlation'];
  const visualSource = state.mode === 'demo' ? 'synthetic' : 'assisted_tracking_experimental';
  state.visual.forEach(r => rows.push(`${r.t},${r.value},degrees,visual_original,${visualSource},${r.quality ?? ''}`));
  if (state.visualResult) state.visualResult.filtered.forEach((v, i) => rows.push(`${state.visualResult.filteredTimes[i]},${v},degrees,visual_filtered_centered,${visualSource},`));
  (state.imported || state.sensor).forEach(r => rows.push(`${r.t},${r.value},arbitrary,sensor_original,${state.imported ? 'external_csv_unverified' : 'synthetic_not_independent'},`));
  download(`aleta-${state.mode}-registro.csv`, rows.join('\n'), 'text/csv;charset=utf-8'); toast('Registro descargado. Exporta también el informe con los parámetros.');
};
$('export-json').onclick = () => download(`aleta-${state.mode}-informe.json`, JSON.stringify({ ...provenance(), visual_samples: state.visual, sensor_samples: state.imported || state.sensor }, null, 2), 'application/json');
let lastWall = performance.now(), accumulator = 0;
function frame(now) {
  const dt = (now - lastWall) / 1000; lastWall = now;
  if (state.mode === 'demo') {
    if (state.running) {
      accumulator += Math.min(dt, .2);
      while (accumulator >= 1 / 60) {
        accumulator -= 1 / 60; state.t = state.sample++ / 60;
        const theta = state.amplitude * Math.sin(2 * Math.PI * state.frequency * state.t);
        state.visual.push({ t: state.t, value: theta + state.amplitude * state.noise * state.rng() });
        state.sensor.push({ t: state.t, value: Math.sin(2 * Math.PI * (state.frequency + state.offset) * (state.t - .04)) + state.noise * 2 * state.sensorRng() });
        if (state.t >= 120) { state.running = false; updateToggle(); toast('Registro de 120 s completo. Descarga o reinicia.'); break; }
      }
    } else accumulator = 0;
    drawFish();
  } else {
    accumulator = 0;
    if (!video.requestVideoFrameCallback && state.running) processVideoFrame(video.currentTime);
    drawReal();
  }
  if (now - state.lastAnalysis > 300) {
    state.lastAnalysis = now;
    try { state.visualResult = analyze(state.visual); if (!state.imported) state.sensorResult = state.mode === 'demo' ? analyze(state.sensor) : null; }
    catch (error) { state.running = false; updateToggle(); toast(`Análisis detenido: ${error.message}`); }
    updateMetrics(); drawCharts();
  }
  $('timecode').textContent = formatTime(state.t);
  requestAnimationFrame(frame);
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden && state.running) { state.running = false; if (state.mode !== 'demo') video.pause(); updateToggle(); }
});
window.addEventListener('pagehide', stopStream);
window.addEventListener('resize', drawCharts);
updateToggle(); requestAnimationFrame(frame);
