"""Construir un notebook autocontenido a partir de los módulos comprobados."""

import json
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
bundle = {str(p.relative_to(ROOT)): p.read_text(encoding="utf-8") for p in [
    ROOT / "src/__init__.py", ROOT / "src/annotations.py", ROOT / "src/signals.py",
    ROOT / "src/development.py",
]}
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
md("""# 5.6 Implementación computacional del análisis de movimiento de peces

**Curso:** Procesamiento Digital de Señales · USIL · Equipo 2  
**Objetivo de este avance:** convertir trayectorias CVAT de referencia en señales,
remuestrearlas, aplicar un FIR de cinco muestras y comparar movimiento y espectros.

Se emplea la secuencia **Ancona** del dataset DIGI4ECO. Las cajas y los IDs proceden
del XML del dataset: **este notebook no detecta peces automáticamente**. No entrena
YOLO ni calcula precisión de un detector, ni clasifica actividad o tamaño.

**Cómo ejecutar:** en VS Code seleccionar el kernel `.venv`; en Google Colab subir
este `.ipynb` mediante *Archivo → Subir notebook*, ejecutar en orden y, cuando se
solicite, seleccionar `video.mp4` y `annotations.xml` de la carpeta **Ancona**.
El notebook contiene los módulos Python necesarios; no necesita descargar código
de un repositorio. La validación entregada corresponde a ejecución local en macOS.
"""),
md("""## 1 Preparación del entorno

Se comprueban las bibliotecas necesarias. Si alguna falta, se instala en el kernel
actual. Las versiones utilizadas quedan registradas en el resumen. Para replicar
el entorno local exacto se incluyen `requirements.txt` y `requirements-notebook.txt`
en el proyecto. La ejecución no requiere GPU.
"""),
code("""from pathlib import Path
import importlib.util
import os
import subprocess
import sys

IN_COLAB = importlib.util.find_spec('google.colab') is not None if importlib.util.find_spec('google') else False
required = {'numpy': 'numpy==2.5.4', 'cv2': 'opencv-python-headless==5.0.0.93',
            'matplotlib': 'matplotlib==3.11.2'}
missing = [package for module, package in required.items() if importlib.util.find_spec(module) is None]
if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
print('Intérprete:', sys.executable)
print('Entorno:', 'Colab' if IN_COLAB else 'local')
"""),
md("""## 2 Módulos del desarrollo

El siguiente bloque materializa una copia del código del avance en una carpeta
temporal. `annotations.py` valida CVAT y separa tramos; `signals.py` implementa
remuestreo, FIR, métricas y FFT; `development.py` lee el video y exporta evidencias.
Las funciones de PDS se comprueban antes de ejecutar el caso real.
"""),
code("""import json
import tempfile

CODE_BUNDLE = json.loads(""" + repr(json.dumps(bundle, ensure_ascii=False)) + """)
CODE_ROOT = Path(tempfile.mkdtemp(prefix='pds_56_code_'))
for relative, content in CODE_BUNDLE.items():
    destination = CODE_ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding='utf-8')
sys.path.insert(0, str(CODE_ROOT))
from src.annotations import load_annotations, select_segment
from src.signals import uniform_resample, moving_average, amplitude_spectrum, motion_metrics
from src.development import run_analysis
print('Módulos cargados desde', CODE_ROOT)
"""),
md("""## 3 Parámetros del experimento y carga de archivos

Cambiar los parámetros en esta celda, sin modificar las funciones:

| Parámetro | Valor inicial | Significado |
|---|---|---|
| `SEQUENCE` | Ancona | Secuencia usada en el avance |
| `TARGET_FS` | 20.0 Hz | Frecuencia elegida para la grilla uniforme, distinta del FPS medio del archivo |
| `TRACK_ID` | None | Mayor tramo continuo; desempate por menor ID |
| FIR | 5 coeficientes de 0.2 | Filtro causal, ventanas completas y retardo de 2 muestras |

En Colab se solicitan los dos archivos originales de la secuencia. También se
pueden ubicar en `/content/DIGI4ECO_tracking_dataset/Ancona/` desde el explorador de
archivos antes de ejecutar. En local se usa Descargas y puede editarse `DATASET_ROOT`.
"""),
code("""SEQUENCE = 'Ancona'
TARGET_FS = 20.0
TRACK_ID = None
PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
BUNDLED_DATA = PROJECT_ROOT / 'data' / 'DIGI4ECO_tracking_dataset'
DATASET_ROOT = (Path('/content/DIGI4ECO_tracking_dataset') if IN_COLAB else
                BUNDLED_DATA if (BUNDLED_DATA / SEQUENCE / 'video.mp4').is_file() else
                Path.home() / 'Downloads' / 'DIGI4ECO_tracking_dataset')
OUTPUT_DIR = (Path('/content/results/avance_56') if IN_COLAB
              else PROJECT_ROOT / 'results/avance_56')

sequence_dir = DATASET_ROOT / SEQUENCE
if IN_COLAB and not all((sequence_dir / n).is_file() for n in ['video.mp4', 'annotations.xml']):
    from google.colab import files
    print('Seleccionar video.mp4 y annotations.xml de la carpeta', SEQUENCE)
    uploaded = files.upload()
    expected = {'video.mp4', 'annotations.xml'}
    if set(uploaded) != expected:
        raise ValueError('Sube exactamente video.mp4 y annotations.xml de la misma secuencia')
    sequence_dir.mkdir(parents=True, exist_ok=True)
    for name, contents in uploaded.items():
        (sequence_dir / name).write_bytes(contents)
for name in ['video.mp4', 'annotations.xml']:
    if not (sequence_dir / name).is_file():
        raise FileNotFoundError(f'Falta {sequence_dir / name}; revisar DATASET_ROOT')
print('Datos:', sequence_dir)
print('Resultados:', OUTPUT_DIR)
"""),
md("""## 4 Pruebas numéricas y lectura de anotaciones

Una rampa permite comprobar el retardo y los bordes del FIR; un movimiento
lineal de tiempos irregulares verifica interpolación y unidades; una sinusoide
conocida comprueba el eje de frecuencias de la FFT. Son pruebas de código,
no resultados de precisión sobre peces.
"""),
code("""import numpy as np
from collections import Counter

ramp = np.column_stack([np.arange(10.), np.ones(10)*7])
np.testing.assert_allclose(moving_average(ramp)[:, 0], np.arange(2., 8.))
t_test = np.array([0, .04, .12, .16, .20, .24, .32, .40, .48, .56])
grid_test, xy_test = uniform_resample(t_test, np.column_stack([10*t_test, -5*t_test]), 20)
np.testing.assert_allclose(xy_test[:, 0], 10*grid_test)
assert abs(motion_metrics(xy_test, 20)['mean_speed_px_s'] - np.sqrt(125)) < 1e-9
t_fft = np.arange(400)/20
f_test, a_test = amplitude_spectrum(3*np.sin(2*np.pi*2*t_fft) + 4*t_fft, 20)
peak = 1 + np.argmax(a_test[1:])
assert abs(f_test[peak] - 2) < 1e-9 and abs(a_test[peak] - 3) < .01
print('Pruebas numéricas: correctas')

tracks, metadata = load_annotations(sequence_dir / 'annotations.xml')
segment = select_segment(tracks, TRACK_ID)
print('Metadatos XML:', metadata)
print('Trayectorias:', len(tracks))
print('Etiquetas:', dict(Counter(obs[0].label for obs in tracks.values() if obs)))
print('ID seleccionado:', segment[0].track_id, 'tramo:', segment[0].frame, 'a', segment[-1].frame)
"""),
md("""## 5 Ejecución del caso real

El procesamiento sigue esta secuencia:

1. Decodificar todos los fotogramas y comprobar conteo y resolución frente al XML.
2. Leer tiempos de presentación (PTS) por fotograma. Rechazar tiempos no crecientes.
3. Calcular centros de cajas con coordenadas subpíxel, conservando flags de oclusión
   e interpolación. Excluir `outside=1` y separar ausencias sin rellenarlas.
4. Remuestrear un tramo continuo con interpolación lineal a `TARGET_FS`.
5. Convolucionar cada coordenada con cinco coeficientes 0.2, en modo `valid`.
6. Comparar sobre los mismos tiempos centrales, compensando en análisis offline
   el retardo de 2/`TARGET_FS` segundos. Los CSV conservan también el tiempo causal.
7. Obtener rapidez en px/s y métricas en el intervalo común.
8. Eliminar tendencia lineal, aplicar Hann y calcular la DFT mediante `rfft`,
   con corrección de amplitud de la ventana y eje de frecuencias en Hz.

El remuestreo no corrige errores de identidad o anotación, ni recupera información
perdida; tampoco constituye un filtro antialias. Los PTS pueden contener anomalías
y no prueban la cadencia física de la cámara. El cálculo permite estudiar el
procesamiento de la trayectoria de referencia bajo estas limitaciones.
"""),
code("""report = run_analysis(DATASET_ROOT, SEQUENCE, OUTPUT_DIR, TARGET_FS, TRACK_ID)
print(json.dumps(report, indent=2, ensure_ascii=False))
"""),
md("""## 6 Comprobación visual de la referencia

Se exportan tres fotogramas del tramo. Las cajas verdes y amarillas proceden del
XML; el amarillo identifica la trayectoria seleccionada. Revisar que cajas y
peces se correspondan. Tres imágenes no validan todas las identidades del video.
"""),
code("""from IPython.display import display, Image, Markdown
for path in sorted(OUTPUT_DIR.glob('reference_frame_*.jpg')):
    print(path.name)
    display(Image(filename=str(path), width=950))
"""),
md("""## 7 Señales y rapidez antes y después del FIR

El origen de imagen está arriba a la izquierda; x crece hacia la derecha e y
hacia abajo. Las distancias y velocidades son aparentes en píxeles. Las curvas
filtradas se muestran con retardo compensado para la comparación offline.
"""),
code("""display(Image(filename=str(OUTPUT_DIR / 'signals_and_speed.png'), width=1000))
import csv
rows = list(csv.reader((OUTPUT_DIR / 'metrics.csv').open(encoding='utf-8')))
table = '| Métrica | Sin FIR | Con FIR |\\n|---|---:|---:|\\n'
table += '\\n'.join(f'| {r[0]} | {float(r[1]):.4f} | {float(r[2]):.4f} |' for r in rows[1:])
display(Markdown(table))
print('Una reducción de rapidez o recorrido describe el suavizado; no prueba mayor exactitud.')
"""),
md("""## 8 Espectros y respuesta del filtro

El espectro representa posiciones anotadas y remuestreadas, con tendencia
lineal eliminada. La resolución de los bins es fs/N y el límite numérico de
Nyquist es fs/2. Los picos no demuestran por sí solos periodicidad biológica,
estrés, salud o alimentación. La frecuencia más alta interpretable depende
también de la captura original y de las anotaciones interpoladas.
"""),
code("""display(Image(filename=str(OUTPUT_DIR / 'spectra.png'), width=1000))
display(Image(filename=str(OUTPUT_DIR / 'fir_response.png'), width=900))
print('Resolución FFT (Hz):', report['fft']['frequency_bin_hz'])
print('Retardo FIR (s):', report['fir']['delay_s'])
"""),
md("""## 9 Exportación y límites del avance

Se generan coordenadas de referencia por pez, señales uniformes y filtradas,
rapidez, métricas, espectros, figuras y un JSON con parámetros, versiones y hashes
SHA-256 de los archivos de entrada. El ZIP permite conservar los resultados
antes de terminar la sesión de Colab.

**Pendiente:** detector, seguimiento automático, calibración de tamaño, umbrales
de actividad y evaluación independiente. No existen etiquetas de actividad o
tamaño que permitan reportar exactitud de esas clasificaciones en este avance.
**OBSEA se rechaza** si se intenta analizar porque su MP4 tiene 148 fotogramas
y su XML declara 150. Se requiere resolver esa correspondencia.

**Fuentes:**
- DIGI4ECO, [dataset y cita](https://doi.org/10.5281/zenodo.20701225), licencia
  CC BY 4.0 según el README de la descarga; conservar la atribución al compartir.
- NumPy, [convolución](https://numpy.org/doc/stable/reference/generated/numpy.convolve.html)
  y [DFT para datos reales](https://numpy.org/doc/stable/reference/generated/numpy.fft.rfft.html).
- Google, [preguntas frecuentes de Colab](https://research.google.com/colaboratory/faq.html).
"""),
code("""import shutil
archive_path = shutil.make_archive(str(OUTPUT_DIR.parent / 'resultados_avance_56'), 'zip', OUTPUT_DIR)
print('Resultados guardados:', archive_path)
if IN_COLAB:
    from google.colab import files
    files.download(archive_path)
"""),
]
nb.metadata = {
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python', 'version': '3.12'},
    'colab': {'name': '05_06_Implementacion_PDS.ipynb', 'provenance': []},
}
nbf.validate(nb)
path = ROOT / 'notebooks/05_06_Implementacion_PDS.ipynb'
nbf.write(nb, path)
print(path)
