"""Avance 5.6: análisis PDS de trayectorias de referencia y evidencias exportables."""

import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/pds_matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cv2
import numpy as np

from .annotations import load_annotations, select_segment
from .signals import amplitude_spectrum, motion_metrics, moving_average, speed, uniform_resample


def write_csv(path, fields, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_video_timing(video, annotation_meta, preview_indices):
    """Decodificar completo y leer PTS de OpenCV, sin inferirlos del FPS medio."""
    cap = cv2.VideoCapture(str(video))
    times, previews = [], {}
    try:
        if not cap.isOpened():
            raise ValueError(f"No se pudo abrir {video}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width, height = (int(cap.get(k)) for k in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT))
        if count != annotation_meta["frames_declared"]:
            raise ValueError(
                f"Video/XML desalineados: {count} frames en MP4 frente a "
                f"{annotation_meta['frames_declared']} declarados en XML. "
                "No se recortan anotaciones automáticamente."
            )
        if (width, height) != (annotation_meta["width_px"], annotation_meta["height_px"]):
            raise ValueError("La resolución del video no coincide con el XML")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame is None or frame.shape[:2] != (height, width):
                raise ValueError("Fotograma vacío o resolución variable")
            index = len(times)
            times.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
            if index in preview_indices:
                previews[index] = frame.copy()
    finally:
        cap.release()
    times = np.asarray(times)
    if len(times) != count or len(times) < 2:
        raise ValueError("No se decodificó el conteo completo del archivo")
    dt = np.diff(times)
    if not np.isfinite(times).all() or np.any(dt <= 0):
        raise ValueError("PTS ausentes, repetidos o no crecientes: revisar el video")
    return times, previews, {
        "frames_decoded": len(times), "fps_file": fps,
        "width_px": width, "height_px": height,
        "pts_first_s": float(times[0]), "pts_last_s": float(times[-1]),
        "dt_min_s": float(dt.min()), "dt_max_s": float(dt.max()),
        "dt_median_s": float(np.median(dt)),
        "intervals_below_1ms": int(np.count_nonzero(dt < .001)),
        "timing_note": "PTS del archivo; no se ha validado la cadencia física de la cámara",
        "timing_source": "OpenCV CAP_PROP_POS_MSEC después de cada lectura",
    }


def save_overlays(previews, tracks, output_dir, selected_id):
    for index, original in previews.items():
        image = original.copy()
        for tid, observations in tracks.items():
            for o in observations:
                if o.frame != index:
                    continue
                color = (0, 255, 255) if tid == selected_id else (0, 220, 0)
                x1, y1 = round(o.x-o.width/2), round(o.y-o.height/2)
                x2, y2 = round(o.x+o.width/2), round(o.y+o.height/2)
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                cv2.putText(image, f"GT {tid}", (x1, max(18, y1-5)),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2)
        cv2.putText(image, f"REFERENCIA CVAT | frame {index} | seleccionado {selected_id}",
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, .75, (255, 255, 255), 2)
        path = output_dir / f"reference_frame_{index:04d}.jpg"
        if not cv2.imwrite(str(path), image):
            raise OSError(f"No se pudo guardar {path}")


def make_plots(output_dir, times, xy, grid, uniform, center_times, raw, filtered, fs, tid):
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, layout="constrained")
    for i, axis in enumerate(axes[:2]):
        axis.plot(times, xy[:, i], color=".65", lw=.9, label="Referencia en tiempos originales")
        axis.plot(grid, uniform[:, i], color="#2b6cb0", alpha=.55, lw=.9, label=f"Remuestreo {fs:g} Hz")
        axis.plot(center_times, filtered[:, i], color="#c05621", lw=1.4, label="FIR 5 con retardo compensado")
        axis.set_ylabel(f"{'x' if i == 0 else 'y'} (px)")
        axis.grid(alpha=.2)
    axes[0].legend(fontsize=8, loc="best")
    axes[2].plot(center_times[1:], speed(raw, fs), color="#2b6cb0", lw=.9, label="Sin FIR")
    axes[2].plot(center_times[1:], speed(filtered, fs), color="#c05621", lw=1.2, label="Con FIR")
    axes[2].set(xlabel="Tiempo de presentación del video (s)", ylabel="Rapidez (px/s)")
    axes[2].legend(fontsize=9)
    axes[2].grid(alpha=.2)
    fig.suptitle(f"Análisis de referencia CVAT · trayectoria {tid}")
    fig.savefig(output_dir / "signals_and_speed.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, layout="constrained")
    spectra = []
    for i, axis in enumerate(axes):
        freq, amp_raw = amplitude_spectrum(raw[:, i], fs)
        _, amp_filtered = amplitude_spectrum(filtered[:, i], fs)
        axis.plot(freq, amp_raw, color="#2b6cb0", lw=1, label="Sin FIR")
        axis.plot(freq, amp_filtered, color="#c05621", lw=1, label="Con FIR")
        axis.set_ylabel(f"Amplitud {'x' if i == 0 else 'y'} (px)")
        axis.grid(alpha=.2)
        axis.legend(fontsize=9)
        spectra.append((amp_raw, amp_filtered))
    axes[1].set_xlabel("Frecuencia (Hz)")
    fig.suptitle("DFT por FFT · tendencia lineal eliminada · ventana Hann")
    fig.savefig(output_dir / "spectra.png", dpi=160)
    plt.close(fig)
    write_csv(output_dir / "spectra.csv", ["frequency_hz", "x_raw_px", "x_fir_px", "y_raw_px", "y_fir_px"],
              zip(freq, spectra[0][0], spectra[0][1], spectra[1][0], spectra[1][1]))

    frequency = np.linspace(0, fs/2, 1001)
    response = np.exp(-2j*np.pi*frequency[:, None]*np.arange(5)[None, :]/fs).mean(axis=1)
    fig, axis = plt.subplots(figsize=(9, 3.5), layout="constrained")
    axis.plot(frequency, np.abs(response), color="#2b6cb0")
    axis.set(xlabel="Frecuencia (Hz)", ylabel="Ganancia |H|", title="Respuesta del FIR de promedio móvil de 5 muestras")
    axis.grid(alpha=.2)
    fig.savefig(output_dir / "fir_response.png", dpi=160)
    plt.close(fig)


def run_analysis(dataset_root: Path, sequence="Ancona", output_dir=Path("results/avance_56"),
                 target_fs=20.0, track_id=None):
    if sequence not in {"Ancona", "OBSEA", "SmartBay1", "SmartBay2"}:
        raise ValueError("Secuencia desconocida")
    folder = Path(dataset_root).expanduser().resolve() / sequence
    video, xml = folder / "video.mp4", folder / "annotations.xml"
    if not video.is_file() or not xml.is_file():
        raise FileNotFoundError(f"Se requieren video.mp4 y annotations.xml en {folder}")
    tracks, annotation_meta = load_annotations(xml)
    segment = select_segment(tracks, track_id)
    indices = [segment[0].frame, segment[len(segment)//2].frame, segment[-1].frame]
    pts, previews, video_meta = read_video_timing(video, annotation_meta, indices)
    times = pts[[o.frame for o in segment]]
    xy = np.array([(o.x, o.y) for o in segment])
    grid, uniform = uniform_resample(times, xy, target_fs)
    filtered = moving_average(uniform)
    # FIR causal: salidas n=4..N-1. En comparación offline se resta su retardo
    # de 2/fs y se confronta con la señal original en los mismos tiempos centrales.
    center_times, raw = grid[2:-2], uniform[2:-2]
    if len(raw) < 32:
        raise ValueError("El remuestreo deja menos de 32 muestras comparables para FFT")
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tid = segment[0].track_id
    save_overlays(previews, tracks, output_dir, tid)
    all_observations = [o for tid_ in sorted(tracks) for o in tracks[tid_]]
    fields = list(asdict(all_observations[0]))
    write_csv(output_dir / "reference_coordinates.csv", fields + ["time_pts_s"],
              [list(asdict(o).values()) + [pts[o.frame]] for o in all_observations])
    write_csv(output_dir / "uniform_signal.csv", ["time_s", "x_px", "y_px"], zip(grid, *uniform.T))
    v_raw, v_filtered = speed(raw, target_fs), speed(filtered, target_fs)
    write_csv(output_dir / "filtered_signal.csv",
              ["causal_output_time_s", "center_time_s", "x_raw_px", "y_raw_px", "x_fir_px", "y_fir_px"],
              zip(grid[4:], center_times, *raw.T, *filtered.T))
    write_csv(output_dir / "speed.csv", ["interval_end_time_s", "speed_raw_px_s", "speed_fir_px_s"],
              zip(center_times[1:], v_raw, v_filtered))
    raw_metrics, fir_metrics = motion_metrics(raw, target_fs), motion_metrics(filtered, target_fs)
    write_csv(output_dir / "metrics.csv", ["metric", "without_fir", "with_fir"],
              [(key, raw_metrics[key], fir_metrics[key]) for key in raw_metrics])
    make_plots(output_dir, times, xy, grid, uniform, center_times, raw, filtered, target_fs, tid)
    report = {
        "scope": "PDS sobre trayectorias CVAT de referencia; sin detección automática ni clasificación",
        "sequence": sequence, "video": video_meta, "annotations": annotation_meta,
        "tracks": len(tracks), "visible_boxes": len(all_observations),
        "labels_by_track": dict(Counter(observations[0].label for observations in tracks.values() if observations)),
        "selected_track_id": tid, "selected_frame_start": segment[0].frame,
        "selected_frame_end": segment[-1].frame, "source_samples": len(segment),
        "occluded_source_samples": sum(o.occluded for o in segment),
        "keyframe_source_samples": sum(o.keyframe for o in segment),
        "resampling": {"method": "linear interpolation within continuous visible segment",
                       "target_fs_hz": target_fs, "samples": len(grid),
                       "note": "No es un filtro antialias; no se garantiza recuperar movimiento fuera de la cadencia original"},
        "fir": {"coefficients": [.2]*5, "delay_samples": 2, "delay_s": 2/target_fs,
                "edge_handling": "valid: no padding", "comparison": "delay compensated offline at window center"},
        "fft": {"samples": len(raw), "frequency_bin_hz": target_fs/len(raw),
                "nyquist_hz": target_fs/2, "detrend": "linear", "window": "Hann",
                "note": "Espectro descriptivo de posiciones anotadas e interpoladas; no valida periodicidad biológica"},
        "metrics_without_fir": raw_metrics, "metrics_with_fir": fir_metrics,
        "inputs": {str(p.name): {"path": str(p), "sha256": sha256(p)} for p in (video, xml)},
        "environment": {"python": platform.python_version(), "architecture": platform.machine(),
                        "numpy": np.__version__, "opencv": cv2.__version__, "matplotlib": matplotlib.__version__},
    }
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--sequence", default="Ancona")
    parser.add_argument("--output-dir", type=Path, default=Path("results/avance_56"))
    parser.add_argument("--target-fs", type=float, default=20.0)
    parser.add_argument("--track-id", type=int)
    args = parser.parse_args()
    try:
        report = run_analysis(args.dataset_root, args.sequence, args.output_dir, args.target_fs, args.track_id)
    except (OSError, ValueError, KeyError, cv2.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
