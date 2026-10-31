"""Remuestreo, convolución FIR, cinemática y FFT con unidades explícitas."""

import numpy as np


def uniform_resample(times, xy, fs: float):
    times, xy = np.asarray(times, dtype=float), np.asarray(xy, dtype=float)
    if (len(times) < 5 or xy.shape != (len(times), 2)
            or not np.isfinite(times).all() or not np.isfinite(xy).all()
            or not np.all(np.diff(times) > 0) or not np.isfinite(fs) or fs <= 0):
        raise ValueError("Tiempos crecientes, coordenadas finitas y fs positiva requeridos")
    # No se extrapola. La frecuencia de salida se elige explícitamente.
    count = int(np.floor((times[-1] - times[0]) * fs + 1e-9)) + 1
    if count < 9:
        raise ValueError("El tramo es demasiado corto para FIR y FFT")
    grid = times[0] + np.arange(count) / fs
    values = np.column_stack([np.interp(grid, times, xy[:, i]) for i in range(2)])
    return grid, values


def moving_average(xy, taps: int = 5):
    """FIR causal h[k]=1/taps. Sólo ventanas completas, sin rellenar con ceros."""
    xy = np.asarray(xy, dtype=float)
    if taps != 5 or xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < taps:
        raise ValueError("Este avance utiliza FIR de cinco muestras y dos coordenadas")
    return np.column_stack([
        np.convolve(xy[:, i], np.ones(taps) / taps, mode="valid") for i in range(2)
    ])


def speed(xy, fs: float):
    """Magnitud de la diferencia de posición por intervalo, en px/s."""
    return np.linalg.norm(np.diff(xy, axis=0), axis=1) * fs


def motion_metrics(xy, fs: float) -> dict:
    velocities = speed(xy, fs)
    return {
        "path_length_px": float(velocities.sum() / fs),
        "net_displacement_px": float(np.linalg.norm(xy[-1] - xy[0])),
        "mean_speed_px_s": float(velocities.mean()),
        "max_speed_px_s": float(velocities.max()),
        "std_speed_px_s": float(velocities.std(ddof=0)),
        "duration_s": (len(xy) - 1) / fs,
    }


def amplitude_spectrum(values, fs: float):
    """Detrend lineal + Hann + rFFT; amplitud unilateral corregida por ventana."""
    values = np.asarray(values, dtype=float)
    if len(values) < 4 or not np.isfinite(values).all():
        raise ValueError("Se requieren al menos cuatro muestras finitas")
    n = np.arange(len(values), dtype=float)
    residual = values - np.polyval(np.polyfit(n, values, 1), n)
    window = np.hanning(len(values))
    amplitude = np.abs(np.fft.rfft(residual * window)) / window.sum()
    if len(values) % 2 == 0:
        amplitude[1:-1] *= 2
    else:
        amplitude[1:] *= 2
    return np.fft.rfftfreq(len(values), d=1/fs), amplitude
