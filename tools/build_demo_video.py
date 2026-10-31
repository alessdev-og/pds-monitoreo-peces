"""Crear una demo sincronizada de resultados offline a partir de CSV reales.

No realiza inferencia: las cajas y los IDs proceden de la referencia CVAT.
Ejecutar primero python -m src.development con la secuencia Ancona.
"""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BG = (29, 19, 12)
CARD = (47, 33, 22)
WHITE = (245, 242, 235)
MUTED = (177, 156, 133)
BLUE = (239, 172, 80)
ORANGE = (82, 172, 255)
GRID = (73, 55, 38)


def text(image, value, point, scale=.6, color=WHITE, weight=1):
    cv2.putText(image, str(value), point, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, weight, cv2.LINE_AA)


def panel(image, rect, title, x, series, limits, cursor=None):
    """Dibujar series con ejes numéricos y cursor en el tiempo de presentación."""
    left, top, width, height = rect
    cv2.rectangle(image, (left, top), (left+width, top+height), CARD, -1)
    text(image, title, (left+16, top+24), .52)
    x0, y0, x1, y1 = left+62, top+42, left+width-18, top+height-30
    xmin, xmax, ymin, ymax = limits
    for fraction in [0, .5, 1]:
        yy = round(y1-fraction*(y1-y0))
        cv2.line(image, (x0, yy), (x1, yy), GRID, 1)
        text(image, f'{ymin+fraction*(ymax-ymin):.0f}', (left+7, yy+4), .38, MUTED)
        xx = round(x0+fraction*(x1-x0))
        text(image, f'{xmin+fraction*(xmax-xmin):.1f}', (xx-10, y1+18), .38, MUTED)
    for values, color in series:
        px = x0+(np.asarray(x)-xmin)/(xmax-xmin)*(x1-x0)
        py = y1-(np.asarray(values)-ymin)/(ymax-ymin)*(y1-y0)
        points = np.column_stack([np.clip(px, x0, x1), np.clip(py, y0, y1)]).round().astype(np.int32)
        cv2.polylines(image, [points], False, color, 1, cv2.LINE_AA)
    if cursor is not None:
        xx = round(x0+(cursor-xmin)/(xmax-xmin)*(x1-x0))
        cv2.line(image, (xx, y0), (xx, y1), WHITE, 1, cv2.LINE_AA)


def build_demo(results, output, start=28., duration=15.):
    report = json.loads((results/'analysis_summary.json').read_text())
    if report['sequence'] != 'Ancona':
        raise ValueError('Esta demo está configurada para los resultados de Ancona')
    filtered = np.genfromtxt(results/'filtered_signal.csv', delimiter=',', names=True)
    velocity = np.genfromtxt(results/'speed.csv', delimiter=',', names=True)
    spectrum = np.genfromtxt(results/'spectra.csv', delimiter=',', names=True)
    time = filtered['center_time_s']
    if start < time[0] or duration <= 0 or start+duration > time[-1]:
        raise ValueError('Elegir un intervalo dentro de la señal disponible')
    by_frame = defaultdict(list)
    selected = []
    tid = report['selected_track_id']
    with (results/'reference_coordinates.csv').open() as stream:
        for row in csv.DictReader(stream):
            row = {k: (v if k == 'label' else float(v)) for k, v in row.items()}
            frame = int(row['frame'])
            by_frame[frame].append(row)
            if int(row['track_id']) == tid:
                selected.append(row)
    selected.sort(key=lambda r: r['frame'])
    if len(selected) != report['video']['frames_decoded']:
        raise ValueError('La demo requiere un pez visible en todos los frames')
    source_times = np.array([r['time_pts_s'] for r in selected])
    fs = report['resampling']['target_fs_hz']
    frame_total = round(duration*fs)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'mp4v'), fs, (1600, 900))
    cap = cv2.VideoCapture(report['inputs']['video.mp4']['path'])
    if not writer.isOpened() or not cap.isOpened():
        writer.release()
        cap.release()
        raise ValueError('No se pudo abrir el video o su salida MP4')
    source_index = -1
    image = None
    preview_file = output.with_suffix('.jpg')
    try:
        for number in range(frame_total):
            now = start+number/fs
            # Mostrar el último fotograma disponible en ese instante, sin anticiparlo.
            target = int(np.searchsorted(source_times, now, side='right')-1)
            while source_index < target:
                ok, image = cap.read()
                if not ok:
                    raise ValueError('Lectura incompleta al construir la demo')
                source_index += 1
            canvas = np.full((900, 1600, 3), BG, np.uint8)
            text(canvas, 'PDS  /  MONITOREO DE PECES', (26, 39), .95, WHITE, 2)
            text(canvas, 'Video, trayectoria y senales sincronizadas  |  USIL - Equipo 2', (27, 70), .55, MUTED)
            cv2.rectangle(canvas, (1160, 17), (1574, 77), CARD, -1)
            text(canvas, 'REFERENCIA CVAT  /  ANALISIS OFFLINE', (1173, 43), .49, ORANGE)
            text(canvas, 'Datos anotados, sin detector automatico', (1173, 65), .44, MUTED)

            view = cv2.resize(image, (1000, 562))
            scale = 1000/report['video']['width_px']
            for row in by_frame[target]:
                is_selected = int(row['track_id']) == tid
                x, y, width, height = (row[k]*scale for k in ['x', 'y', 'width', 'height'])
                color = ORANGE if is_selected else (115, 155, 80)
                cv2.rectangle(view, (round(x-width/2), round(y-height/2)),
                              (round(x+width/2), round(y+height/2)), color, 2 if is_selected else 1)
                if is_selected:
                    text(view, f'ID {tid} - referencia', (max(8, round(x-width/2)), max(23, round(y-height/2)-7)), .58, color, 2)
            trail = [r for r in selected[max(0, target-100):target+1] if r['time_pts_s'] >= now-3]
            points = np.array([(round(r['x']*scale), round(r['y']*scale)) for r in trail], np.int32)
            if len(points) > 1:
                cv2.polylines(view, [points], False, ORANGE, 3, cv2.LINE_AA)
            canvas[110:672, 26:1026] = view
            text(canvas, f'ANCONA  |  frame {target:04d}  |  tiempo de archivo {now:05.2f} s', (38, 102), .55, MUTED)

            bounds = [(60, 1300), (300, 900), (0, 750)]
            panel(canvas, (1046, 110, 528, 182), 'POSICION X (px)  /  tiempo (s)', time,
                  [(filtered['x_raw_px'], BLUE), (filtered['x_fir_px'], ORANGE)],
                  (float(time[0]), float(time[-1]), *bounds[0]), now)
            panel(canvas, (1046, 306, 528, 182), 'POSICION Y (px)  /  tiempo (s)', time,
                  [(filtered['y_raw_px'], BLUE), (filtered['y_fir_px'], ORANGE)],
                  (float(time[0]), float(time[-1]), *bounds[1]), now)
            panel(canvas, (1046, 502, 528, 182), 'RAPIDEZ (px/s)  /  tiempo (s)', velocity['interval_end_time_s'],
                  [(velocity['speed_raw_px_s'], BLUE), (velocity['speed_fir_px_s'], ORANGE)],
                  (float(time[0]), float(time[-1]), *bounds[2]), now)
            mask = spectrum['frequency_hz'] <= 3
            panel(canvas, (1046, 698, 528, 160), 'FFT DE X  /  tramo completo  /  frecuencia (Hz)', spectrum['frequency_hz'][mask],
                  [(spectrum['x_raw_px'][mask], BLUE), (spectrum['x_fir_px'][mask], ORANGE)],
                  (0, 3, 0, float(spectrum['x_raw_px'].max())*1.1))

            i = max(0, int(np.searchsorted(velocity['interval_end_time_s'], now, side='right')-1))
            cards = [
                ('PECES ANOTADOS EN EL CUADRO', str(len(by_frame[target])), 'Cajas del XML, no predicciones'),
                ('RAPIDEZ SIN FIR', f"{velocity['speed_raw_px_s'][i]:.1f} px/s", 'Referencia remuestreada'),
                ('RAPIDEZ CON FIR', f"{velocity['speed_fir_px_s'][i]:.1f} px/s", 'Retardo compensado offline'),
            ]
            for col, (title, value, note) in enumerate(cards):
                x0 = 26+col*338
                cv2.rectangle(canvas, (x0, 698), (x0+324, 810), CARD, -1)
                text(canvas, title, (x0+13, 723), .43, MUTED)
                text(canvas, value, (x0+13, 765), 1.0, ORANGE if col == 2 else WHITE, 2)
                text(canvas, note, (x0+13, 792), .40, MUTED)
            text(canvas, f'FIR 5 muestras  |  fs {fs:g} Hz  |  retardo {report["fir"]["delay_s"]:.2f} s', (28, 840), .58, WHITE)
            cv2.line(canvas, (690, 835), (720, 835), BLUE, 3)
            text(canvas, 'Sin FIR', (729, 840), .49, MUTED)
            cv2.line(canvas, (850, 835), (880, 835), ORANGE, 3)
            text(canvas, 'Con FIR', (889, 840), .49, MUTED)
            text(canvas, 'Fuente: DIGI4ECO (CC BY 4.0)  |  PTS irregulares  |  Medidas aparentes en pixeles', (28, 881), .47, MUTED)
            writer.write(canvas)
            if number == frame_total//2:
                if not cv2.imwrite(str(preview_file), canvas):
                    raise OSError('No se pudo guardar la vista previa')
    finally:
        cap.release()
        writer.release()
    verification = cv2.VideoCapture(str(output))
    decoded = 0
    try:
        while True:
            ok, frame = verification.read()
            if not ok: break
            if frame.shape[:2] != (900, 1600): raise ValueError('Resolución de salida incorrecta')
            decoded += 1
    finally:
        verification.release()
    if decoded != frame_total:
        raise ValueError(f'Se esperaban {frame_total} frames y se leyeron {decoded}')
    metadata = {'input_results': str(results), 'source_start_s': start, 'source_end_s': start+duration,
                'frames_generated_and_decoded': decoded, 'output_fps': fs, 'duration_s': decoded/fs,
                'video_size_px': [1600, 900], 'selected_track_id': tid,
                'scope': 'Reproducción sincronizada de resultados offline sobre anotaciones CVAT'}
    output.with_suffix('.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    print('Video:', output)
    print('Vista previa:', preview_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT/'results/avance_56')
    parser.add_argument('--output', type=Path, default=ROOT/'results/demo/demo_pds.mp4')
    parser.add_argument('--start', type=float, default=28.)
    parser.add_argument('--duration', type=float, default=15.)
    args = parser.parse_args()
    build_demo(args.results, args.output, args.start, args.duration)
