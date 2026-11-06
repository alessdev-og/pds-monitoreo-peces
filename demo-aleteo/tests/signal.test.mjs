import test from 'node:test';
import assert from 'node:assert/strict';
import { analyze, uniformSegment, tailAngle, filterValid, spectrum, parseSensorCSV, seededNoise } from '../dist/signal.js';
const samples = (f = 2.4, amplitude = 18, fs = 60, duration = 8, offset = 0) => Array.from({ length: fs * duration }, (_, i) => ({ t: i / fs, value: offset + amplitude * Math.sin(2 * Math.PI * f * i / fs) }));
test('FFT recovers a known frequency and amplitude with correct Hann normalization', () => {
  const bins = spectrum(samples(3, 4, 64).map(r => r.value), 64), peak = bins.reduce((a,b) => a.amplitude > b.amplitude ? a : b);
  assert.equal(peak.f, 3); assert.ok(Math.abs(peak.amplitude - 4) < .01);
});
test('candidate frequency remains accurate with deterministic noise and a large DC offset', () => {
  const noise = seededNoise(11), rows = samples(2.4, 3, 60, 8, 500).map(r => ({ ...r, value: r.value + noise() }));
  assert.ok(Math.abs(analyze(rows).peak.f - 2.4) < .04);
});
test('zero and constant signals do not produce a tail beat candidate', () => {
  assert.equal(analyze(samples(0, 0)).peak, null);
  assert.equal(analyze(samples(0, 0, 60, 8, 20)).peak, null);
});
test('FIR uses complete windows and preserves the center of a linear ramp', () => {
  assert.deepEqual(filterValid([0,1,2,3,4,5,6]), [2,3,4]);
  assert.deepEqual(filterValid([1,2]), []);
});
test('angle is relative to the body and invariant under translation and rotation', () => {
  const p = [{x:0,y:0},{x:30,y:0},{x:60,y:30}];
  assert.equal(tailAngle(...p), 45);
  const q = p.map(a => ({x:-a.y+200,y:a.x+70}));
  assert.equal(tailAngle(...q), 45);
  assert.ok(Number.isNaN(tailAngle(p[0], p[0], p[2])));
});
test('nonuniform samples of a line interpolate to the known values', () => {
  const rows = Array.from({length:60},(_,i)=>{const t=i*.05+(i%2)*.005; return {t,value:2*t+1};});
  const result = uniformSegment(rows);
  result.values.forEach((v,i)=>assert.ok(Math.abs(v-(2*result.times[i]+1))<1e-10));
});
test('a gap starts a new segment instead of interpolating through lost tracking', () => {
  const rows = [...samples(2,1,30,3), ...samples(2,1,30,3).map(r=>({...r,t:r.t+10}))];
  const result = uniformSegment(rows); assert.ok(result.times[0] >= 10);
});
test('duplicate/nonfinite timestamps are rejected', () => {
  const rows = samples(); rows[9].t = rows[8].t;
  assert.throws(()=>uniformSegment(rows), /crecientes/);
  rows[9].t = NaN; assert.throws(()=>uniformSegment(rows), /finitas/);
});
test('strict CSV input rejects reversed time, missing numbers and invalid headers', () => {
  const csv = 't_s,value\n'+samples(2,1,30,3).map(r=>`${r.t},${r.value}`).join('\n');
  assert.equal(parseSensorCSV(csv).length, 90);
  assert.throws(()=>parseSensorCSV(csv.replace('t_s,value','time,pressure')), /Cabecera/);
  assert.throws(()=>parseSensorCSV(csv.replace('0,0','0,')), /dos números/);
  assert.throws(()=>parseSensorCSV(csv.replace('0,0','100,0')), /aumentar/);
});
