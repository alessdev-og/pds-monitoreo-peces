"""Fase 1: decodificar un video local y guardar evidencia de lectura."""

import argparse
import json
import math
from pathlib import Path
import platform
import sys

import cv2


def inspect_video(video_path: Path, output_dir: Path) -> dict:
    """Leer todos los fotogramas; los FPS corresponden al archivo de video."""
    video_path = video_path.expanduser().resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"No existe el video: {video_path}")

    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise ValueError(f"OpenCV no pudo abrir: {video_path}")

        fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError(f"FPS del archivo no válidos: {fps}")
        reported_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        backend = capture.getBackendName()
        first_frame = None
        decoded_frames = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame is None or frame.size == 0:
                raise ValueError(f"Fotograma vacío en índice {decoded_frames}")
            if first_frame is None:
                first_frame = frame.copy()
            elif frame.shape != first_frame.shape:
                raise ValueError(f"Cambió la resolución en índice {decoded_frames}")
            decoded_frames += 1
    finally:
        capture.release()

    if first_frame is None:
        raise ValueError("El archivo se abrió pero no se decodificó ningún fotograma")
    # read() devuelve False tanto al final como ante algunos errores de lectura.
    # Comparar el conteo ayuda a detectar un final prematuro en este dataset.
    if reported_frames > 0 and decoded_frames != reported_frames:
        raise ValueError(
            f"Conteo inconsistente: {decoded_frames} leídos, "
            f"{reported_frames} declarados. Revisar el archivo o su metadata."
        )

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_path = output_dir / "first_frame.jpg"
    if not cv2.imwrite(str(preview_path), first_frame):
        raise OSError(f"No se pudo guardar: {preview_path}")

    height, width = first_frame.shape[:2]
    report = {
        "video_path": str(video_path),
        "width_px": width,
        "height_px": height,
        "fps_file": fps,
        "frames_reported": reported_frames,
        "frames_decoded": decoded_frames,
        "duration_s_at_file_fps": decoded_frames / fps,
        "last_frame_time_s_at_file_fps": (decoded_frames - 1) / fps,
        "backend": backend,
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "opencv_version": cv2.__version__,
        "first_frame_path": str(preview_path),
        "timing_note": (
            "Duración y tiempos derivados del FPS del archivo, suponiendo "
            "muestreo uniforme. No valida la cadencia original de la cámara."
        ),
    }
    report_path = output_dir / "video_info.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Ruta al video local")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/video_check"),
        help="Carpeta para el primer fotograma y el informe JSON",
    )
    args = parser.parse_args()
    try:
        report = inspect_video(args.video, args.output_dir)
    except (OSError, ValueError, cv2.error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
