// Assisted three-patch tracking, not fish recognition or a validated pose estimator.
export class PatchTracker {
  constructor(radius = 5, search = 14) { this.radius = radius; this.search = search; this.points = []; }
  reset() { this.points = []; }
  template(gray, width, height, x, y) {
    const r = this.radius, out = [];
    x = Math.round(x); y = Math.round(y);
    if (x < r || y < r || x >= width - r || y >= height - r) return null;
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) out.push(gray[(y + dy) * width + x + dx]);
    const mean = out.reduce((a, b) => a + b, 0) / out.length;
    const centered = out.map(v => v - mean), norm = Math.hypot(...centered);
    return norm < 25 ? null : { centered, norm };
  }
  add(gray, width, height, x, y) {
    const template = this.template(gray, width, height, x, y);
    if (!template) throw new Error('Elige un punto con textura o contraste y alejado del borde.');
    this.points.push({ x: Math.round(x), y: Math.round(y), template, score: 1 });
  }
  update(gray, width, height) {
    if (this.points.length !== 3) return null;
    const result = [];
    for (const point of this.points) {
      let best = null;
      const test = (x, y) => {
        const r = this.radius;
        if (x < r || y < r || x >= width - r || y >= height - r) return;
        let dot = 0, sum = 0, sumSq = 0, i = 0;
        for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
          const v = gray[(y + dy) * width + x + dx];
          dot += point.template.centered[i++] * v; sum += v; sumSq += v * v;
        }
        const norm = Math.sqrt(Math.max(0, sumSq - sum * sum / i));
        if (norm < 25) return;
        const score = dot / (point.template.norm * norm);
        if (!best || score > best.score) best = { x, y, score };
      };
      for (let dy = -this.search; dy <= this.search; dy++) for (let dx = -this.search; dx <= this.search; dx++) test(point.x + dx, point.y + dy);
      if (!best) return null;
      const coarse = { ...best };
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) test(coarse.x + dx, coarse.y + dy);
      if (best.score < .72 || Math.abs(best.x - point.x) >= this.search || Math.abs(best.y - point.y) >= this.search) return null;
      result.push({ ...best, template: point.template });
    }
    this.points = result;
    return { points: result, quality: Math.min(...result.map(p => p.score)) };
  }
}
