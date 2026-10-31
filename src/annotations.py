"""Lectura de trayectorias de referencia CVAT XML 1.1; no es un detector."""

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class Observation:
    track_id: int
    label: str
    frame: int
    x: float
    y: float
    width: float
    height: float
    occluded: int
    keyframe: int


def load_annotations(path: Path) -> tuple[dict[int, list[Observation]], dict]:
    """Conservar subpíxeles y oclusiones; excluir las cajas outside=1."""
    root = ET.parse(path).getroot()
    if root.tag != "annotations" or root.findtext("version") != "1.1":
        raise ValueError("Se requiere CVAT XML 1.1")
    meta = {
        "width_px": int(root.findtext("meta/original_size/width", "0")),
        "height_px": int(root.findtext("meta/original_size/height", "0")),
        "frames_declared": int(root.findtext("meta/sequence_info/total_frames", "0")),
        "outside_boxes_excluded": 0,
    }
    if min(meta["width_px"], meta["height_px"], meta["frames_declared"]) <= 0:
        raise ValueError("Faltan resolución o total_frames en el XML")
    tracks = {}
    for track in root.findall("track"):
        tid = int(track.attrib["id"])
        if tid in tracks:
            raise ValueError(f"Identificador duplicado: {tid}")
        observations = []
        seen = set()
        for box in track.findall("box"):
            frame = int(box.attrib["frame"])
            if frame in seen or not 0 <= frame < meta["frames_declared"]:
                raise ValueError(f"Índice duplicado o inválido en trayectoria {tid}")
            seen.add(frame)
            flags = [int(box.attrib[k]) for k in ("outside", "occluded", "keyframe")]
            if any(flag not in (0, 1) for flag in flags):
                raise ValueError("Las banderas CVAT deben ser 0 o 1")
            if flags[0]:
                meta["outside_boxes_excluded"] += 1
                continue
            x1, y1, x2, y2 = (float(box.attrib[k]) for k in ("xtl", "ytl", "xbr", "ybr"))
            if not (0 <= x1 < x2 <= meta["width_px"] and 0 <= y1 < y2 <= meta["height_px"]):
                raise ValueError(f"Caja inválida en trayectoria {tid}, frame {frame}")
            observations.append(Observation(
                tid, track.attrib["label"], frame, (x1+x2)/2, (y1+y2)/2,
                x2-x1, y2-y1, flags[1], flags[2],
            ))
        tracks[tid] = sorted(observations, key=lambda o: o.frame)
    return tracks, meta


def continuous_segments(observations: list[Observation]) -> list[list[Observation]]:
    """Separar ausencias sin unir ni interpolar reentradas del pez."""
    segments = []
    for observation in observations:
        if not segments or observation.frame != segments[-1][-1].frame + 1:
            segments.append([])
        segments[-1].append(observation)
    return segments


def select_segment(tracks: dict, track_id: int | None, min_samples: int = 32) -> list:
    candidates = [
        segment for tid, observations in tracks.items()
        if track_id is None or tid == track_id
        for segment in continuous_segments(observations)
        if len(segment) >= min_samples
    ]
    if not candidates:
        raise ValueError(f"No hay un tramo continuo con al menos {min_samples} muestras")
    # Selección reproducible: mayor longitud, menor ID, menor frame inicial.
    return min(candidates, key=lambda s: (-len(s), s[0].track_id, s[0].frame))
