"""Synthetic tracking fixture, not footage of a living fish. Uses project OpenCV."""
from pathlib import Path
import math
import cv2
import numpy as np

target = Path('/tmp/aleta-tracking-fixture.avi')
writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*'MJPG'), 60, (480, 270))
if not writer.isOpened():
    raise RuntimeError('No se pudo crear el clip de prueba')
rng = np.random.default_rng(42)
patterns = [rng.integers(40, 240, (13, 13), dtype=np.uint8) for _ in range(3)]
for i in range(480):
    t = i / 60
    frame = np.full((270, 480, 3), (52, 45, 22), dtype=np.uint8)
    angle = math.radians(18) * math.sin(2 * math.pi * 2 * t)
    dx = round(5 * math.sin(t * .4))
    points = [(125 + dx, 135), (250 + dx, 135),
              (round(250 + dx + 75 * math.cos(angle)), round(135 + 75 * math.sin(angle)))]
    cv2.ellipse(frame, (190 + dx, 135), (85, 37), 0, 0, 360, (165, 203, 174), -1)
    cv2.line(frame, points[1], points[2], (110, 175, 145), 18)
    for k, (x, y) in enumerate(points):
        frame[y-6:y+7, x-6:x+7] = patterns[k][..., None]
        cv2.putText(frame, str(k+1), (x-4, y-17), cv2.FONT_HERSHEY_SIMPLEX, .45, (240,240,240), 1, cv2.LINE_AA)
    cv2.putText(frame, 'CLIP SINTETICO - NO ES UN PEZ REAL', (14, 38), cv2.FONT_HERSHEY_SIMPLEX, .46, (215,235,225), 1, cv2.LINE_AA)
    cv2.putText(frame, 'Cola: 2.0 Hz / amplitud: 18 grados', (14, 247), cv2.FONT_HERSHEY_SIMPLEX, .43, (215,235,225), 1, cv2.LINE_AA)
    writer.write(frame)
writer.release()
print(target)
