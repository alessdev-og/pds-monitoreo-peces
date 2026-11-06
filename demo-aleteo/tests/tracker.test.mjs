import test from 'node:test';
import assert from 'node:assert/strict';
import { PatchTracker } from '../dist/tracker.js';
import { seededNoise } from '../dist/signal.js';
const width = 180, height = 100, seed = seededNoise(3);
const patterns = Array.from({length:3},()=>Array.from({length:121},()=>Math.round(100+80*seed())));
const origins = [{x:30,y:40},{x:85,y:40},{x:140,y:45}];
function image(dx = 0, dy = 0) {
  const gray = new Uint8Array(width*height).fill(30);
  origins.forEach((p,k)=>{for(let y=-5;y<=5;y++)for(let x=-5;x<=5;x++) gray[(p.y+dy+y)*width+p.x+dx+x]=patterns[k][(y+5)*11+x+5];});
  return gray;
}
test('three textured points track a known translation',()=>{
  const tracker = new PatchTracker();
  origins.forEach(p=>tracker.add(image(),width,height,p.x,p.y));
  const result = tracker.update(image(3,1),width,height);
  assert.ok(result); assert.ok(result.quality>.99);
  result.points.forEach((p,i)=>{assert.equal(p.x,origins[i].x+3); assert.equal(p.y,origins[i].y+1);});
});
test('loss of texture rejects tracking rather than manufacturing a position',()=>{
  const tracker=new PatchTracker(); origins.forEach(p=>tracker.add(image(),width,height,p.x,p.y));
  assert.equal(tracker.update(new Uint8Array(width*height).fill(30),width,height),null);
  assert.throws(()=>new PatchTracker().add(new Uint8Array(width*height),width,height,30,30), /contraste/);
});
