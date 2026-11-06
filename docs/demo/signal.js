// Numerical routines shared by the browser and node:test. No biological thresholds.
export const FIR = [1 / 16, 4 / 16, 6 / 16, 4 / 16, 1 / 16];
export const median = a => {
  if (!a.length) return NaN;
  const v = [...a].sort((x, y) => x - y), m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
};
export function tailAngle(head, body, tail) {
  const a = [body.x - head.x, body.y - head.y];
  const b = [tail.x - body.x, tail.y - body.y];
  if (Math.hypot(...a) < 3 || Math.hypot(...b) < 3) return NaN;
  return Math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]) * 180 / Math.PI;
}
export function filterValid(values, taps = FIR) {
  if (values.length < taps.length) return [];
  return values.slice(taps.length - 1).map((_, j) => taps.reduce((s, h, k) => s + h * values[j + taps.length - 1 - k], 0));
}
export function uniformSegment(rows, maxSeconds = 8) {
  if (rows.length < 8) return null;
  if (!rows.every(r => Number.isFinite(r.t) && Number.isFinite(r.value))) throw new Error('Muestras no finitas');
  const allDt = rows.slice(1).map((r, i) => r.t - rows[i].t);
  if (allDt.some(v => v <= 0)) throw new Error('Los tiempos deben ser estrictamente crecientes');
  const dt = median(allDt);
  let start = 0;
  allDt.forEach((v, i) => { if (v > 3 * dt) start = i + 1; });
  const endTime = rows.at(-1).t;
  while (start < rows.length && rows[start].t < endTime - maxSeconds) start++;
  const input = rows.slice(start);
  if (input.length < 8) return null;
  const localDt = median(input.slice(1).map((r, i) => r.t - input[i].t));
  const fs = 1 / localDt, n = Math.floor((input.at(-1).t - input[0].t) * fs + 1e-7) + 1;
  if (n < 8 || n > 8192) return null;
  const times = [], values = [];
  let j = 0;
  for (let i = 0; i < n; i++) {
    const t = input[0].t + i / fs;
    while (j < input.length - 2 && input[j + 1].t < t) j++;
    const a = input[j], b = input[j + 1];
    times.push(t);
    values.push(a.value + (b.value - a.value) * (t - a.t) / (b.t - a.t));
  }
  return { times, values, fs, dt: localDt, interpolated: allDt.some(v => Math.abs(v - dt) > dt * .05) };
}
function fft(real, imag) {
  const n = real.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [real[i], real[j]] = [real[j], real[i]]; [imag[i], imag[j]] = [imag[j], imag[i]]; }
  }
  for (let size = 2; size <= n; size <<= 1) {
    const angle = -2 * Math.PI / size;
    for (let i = 0; i < n; i += size) {
      for (let j = 0; j < size / 2; j++) {
        const c = Math.cos(angle * j), s = Math.sin(angle * j), p = i + j, q = p + size / 2;
        const tr = c * real[q] - s * imag[q], ti = s * real[q] + c * imag[q];
        real[q] = real[p] - tr; imag[q] = imag[p] - ti; real[p] += tr; imag[p] += ti;
      }
    }
  }
}
export function spectrum(values, fs) {
  const n = values.length;
  if (n < 8 || !Number.isFinite(fs) || fs <= 0) throw new Error('FFT: entrada inválida');
  let nfft = 1; while (nfft < n) nfft *= 2;
  const re = new Float64Array(nfft), im = new Float64Array(nfft);
  const mid = (n - 1) / 2, mean = values.reduce((a, b) => a + b, 0) / n;
  let cov = 0, variance = 0, sumWindow = 0;
  for (let i = 0; i < n; i++) { cov += (i - mid) * (values[i] - mean); variance += (i - mid) ** 2; }
  const slope = cov / variance;
  for (let i = 0; i < n; i++) {
    const w = .5 - .5 * Math.cos(2 * Math.PI * i / (n - 1));
    re[i] = (values[i] - mean - slope * (i - mid)) * w; sumWindow += w;
  }
  fft(re, im);
  return Array.from({ length: nfft / 2 + 1 }, (_, k) => ({
    f: k * fs / nfft,
    amplitude: Math.hypot(re[k], im[k]) / sumWindow * (k === 0 || k === nfft / 2 ? 1 : 2)
  }));
}
export function analyze(rows) {
  const uniform = uniformSegment(rows);
  if (!uniform || uniform.times.at(-1) - uniform.times[0] < 2) return null;
  const filtered = filterValid(uniform.values), times = uniform.times.slice(2, -2);
  // Estimate on the ORIGINAL detrended signal: a smoothing filter attenuates tail beats.
  const bins = spectrum(uniform.values, uniform.fs);
  const duration = uniform.times.at(-1) - uniform.times[0];
  const band = bins.filter(b => b.f >= Math.max(.3, 2 / duration) && b.f <= Math.min(12, .4 * uniform.fs));
  let peak = band.reduce((a, b) => !a || b.amplitude > a.amplitude ? b : a, null);
  if (peak) {
    const k = bins.indexOf(peak), left = bins[k - 1], right = bins[k + 1];
    if (left && right && left.amplitude > 0 && peak.amplitude > 0 && right.amplitude > 0) {
      const a = Math.log(left.amplitude), b = Math.log(peak.amplitude), c = Math.log(right.amplitude);
      const shift = .5 * (a - c) / (a - 2 * b + c);
      if (Number.isFinite(shift) && Math.abs(shift) <= .5) peak = { f: peak.f + shift * (right.f - peak.f), amplitude: peak.amplitude };
    }
  }
  const noise = median(band.map(b => b.amplitude));
  const mean = uniform.values.reduce((s, v) => s + v, 0) / uniform.values.length;
  const rms = Math.sqrt(uniform.values.reduce((s, v) => s + (v - mean) ** 2, 0) / uniform.values.length);
  const periodic = !!peak && peak.amplitude > 1e-5 && peak.amplitude > 5 * noise && peak.amplitude > .08 * rms;
  return { ...uniform, filtered, filteredTimes: times, bins, peak: periodic ? peak : null,
    duration, resolution: uniform.fs / uniform.values.length, noise, rms,
    filterDelay: 2 / uniform.fs };
}
export function parseSensorCSV(text) {
  const lines = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 9) throw new Error('El CSV necesita al menos 8 muestras.');
  if (lines.length > 100001) throw new Error('Máximo 100 000 muestras.');
  const header = lines.shift().trim();
  if (header !== 't_s,value') throw new Error('Cabecera requerida: t_s,value (tiempo en segundos).');
  const rows = lines.map((line, i) => {
    const fields = line.split(',');
    if (fields.length !== 2 || fields.some(s => s.trim() === '')) throw new Error(`Fila ${i + 2}: se esperan dos números.`);
    const [t, value] = fields.map(Number);
    if (!Number.isFinite(t) || !Number.isFinite(value) || t < 0) throw new Error(`Fila ${i + 2}: valor inválido.`);
    return { t, value };
  });
  if (rows.some((r, i) => i > 0 && r.t <= rows[i - 1].t)) throw new Error('El tiempo debe aumentar en cada fila.');
  return rows;
}
export function seededNoise(seed) {
  let state = seed >>> 0;
  return () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296 * 2 - 1; };
}
