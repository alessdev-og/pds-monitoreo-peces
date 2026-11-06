# PDS Monitoreo de Peces

Prototipo académico de **Procesamiento Digital de Señales — USIL** para analizar
el movimiento aparente de peces a partir de secuencias de video.

El avance actual utiliza las **trayectorias de referencia CVAT** del dataset
DIGI4ECO. Extrae posiciones, conserva los tiempos del video, remuestrea a una
grilla uniforme y aplica un FIR de cinco muestras, análisis de rapidez y FFT.
La detección y el seguimiento automáticos y las clasificaciones de tamaño y
actividad son etapas pendientes.

## Demo de batido de cola

La nueva [demo Aleta](demo-aleteo/README.md) incorpora una interfaz para celular
y computadora con simulación, cámara/video, seguimiento visual asistido de tres
puntos, señal angular, FIR y FFT. Incluye un clip sintético de 2 Hz, exportación
de registros e importación de CSV de un sensor independiente. La adquisición
física sumergida y la validación con peces reales siguen pendientes. Esta demo
no mide fuerza ni determina aptitud productiva. Su implementación es separada
del notebook de trayectorias de referencia descrito a continuación.

[Abrir la demo móvil](https://alessdev-og.github.io/pds-monitoreo-peces/demo/).
Para actualizar la copia de GitHub Pages después de editar la demo, ejecutar
`python3 tools/build_mobile_demo.py` y publicar los cambios de `docs/`.

## Notebook de trayectorias CVAT

[Abrir en Google Colab](https://colab.research.google.com/github/alessdev-og/pds-monitoreo-peces/blob/main/notebooks/05_06_Implementacion_PDS.ipynb)

El [notebook](notebooks/05_06_Implementacion_PDS.ipynb) incluye los módulos de
código, instrucciones y salidas de una ejecución local completa. En Colab pide
`video.mp4` y `annotations.xml` de **Ancona**. La ejecución remota en Colab
todavía está pendiente de comprobación; la ejecución local se verificó.

## Preparación

Entorno comprobado: Python 3.12.14 en macOS Apple Silicon ARM64. El lector usa
OpenCV sin interfaz gráfica y guarda las imágenes y resultados en archivos.

```bash
git clone https://github.com/alessdev-og/pds-monitoreo-peces.git
cd pds-monitoreo-peces
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-notebook.txt
```

En Windows se puede crear el entorno con `py -3.12 -m venv .venv` y activarlo
con `.venv\Scripts\activate`. Esa plataforma no se ha probado.

## Datos

Fuente: [DIGI4ECO Underwater Fish Tracking Dataset en Zenodo](https://doi.org/10.5281/zenodo.20701225).
El README de la descarga declara licencia **CC BY 4.0** y contiene la cita
completa de González-Villà y colaboradores. Conservar la atribución al usar
los datos y sus visualizaciones.

Los videos y XML originales no se incluyen en Git. Obtenerlos del registro y
conservar su organización. Para reproducir el avance basta la secuencia Ancona:

```text
data/
└── DIGI4ECO_tracking_dataset/
    └── Ancona/
        ├── video.mp4
        └── annotations.xml
```

El notebook busca primero en `data/DIGI4ECO_tracking_dataset` y, en local,
también contempla la carpeta `Downloads/DIGI4ECO_tracking_dataset` del usuario.

## Ejecución

Comprobar que se decodifica un video completo:

```bash
python src/main.py data/DIGI4ECO_tracking_dataset/Ancona/video.mp4 \
  --output-dir results/video_check
```

Ejecutar el análisis PDS:

```bash
python -m src.development data/DIGI4ECO_tracking_dataset \
  --sequence Ancona --target-fs 20 --output-dir results/avance_56
```

`--track-id 66` permite elegir un identificador. Por defecto se selecciona el
tramo continuo más largo y se desempata por menor ID. Repetir el análisis
sobrescribe los resultados de la carpeta de salida.

Se exportan coordenadas de referencia por pez, señales uniformes y filtradas,
rapidez, métricas, espectros, gráficos, tres fotogramas superpuestos y un JSON
con parámetros, versiones y hashes SHA-256 de las entradas.

Para ejecutar el notebook con el intérprete activo y guardar sus salidas:

```bash
python tools/execute_notebook.py
```

## Verificación

```bash
python -m unittest discover -s tests -v
```

Las cinco pruebas comprueban FIR sobre una rampa, interpolación y rapidez de
movimiento lineal, rechazo de tiempos repetidos, una sinusoide conocida en
FFT y separación de ausencias. El notebook completo se ejecutó localmente y
el análisis se reprodujo desde una copia extraída del paquete de entrega.

## Demo sincronizada

Después de generar los resultados de Ancona:

```bash
python tools/build_demo_video.py
```

Genera un video de 15 segundos que sincroniza imagen, trayectoria de referencia,
posiciones y rapidez. La FFT corresponde al tramo completo analizado. Es una
reproducción de resultados **offline** sobre anotaciones, sin inferencia de un
detector. El fragmento inicial corresponde a los segundos 28 a 43 del archivo y
puede cambiarse mediante `--start` y `--duration`.

## Estructura

```text
src/
  main.py               # Lectura completa y metadatos del video
  annotations.py        # Validación CVAT y tramos continuos
  signals.py            # Remuestreo, FIR, rapidez y FFT
  development.py        # Análisis integrado y exportación
notebooks/              # Notebook autocontenido y ejecutado
tests/                  # Pruebas numéricas
tools/                  # Ejecución del notebook, demo y preparación de informes
docs/                   # Inspección de datos, alcance y guía técnica
```

`tools/build_notebook.py` reconstruye el notebook desde los módulos y borra
las salidas anteriores. Tras modificar el código se debe reconstruir y volver
a ejecutar. Los scripts de preparación de documentos requieren además el
informe original del equipo y dependencias de autoría; no forman parte del
análisis PDS ni de `requirements.txt`.

## Límites del avance

- Los identificadores y cajas provienen del XML de referencia.
- El tamaño y el movimiento son aparentes: píxeles y píxeles por segundo.
- Los PTS de Ancona son irregulares; el remuestreo no valida la cadencia física
  de captura ni recupera información perdida y no sustituye un filtro antialias.
- El retardo del FIR se compensa para comparar las señales offline. La reducción
  de rapidez tras suavizar no demuestra una mejora de exactitud.
- OBSEA contiene 148 fotogramas frente a 150 declarados en el XML. El análisis
  rechaza ese caso hasta resolver su correspondencia.
- Los resultados no permiten inferir salud, estrés o alimentación ni validan
  todavía el uso en criaderos rurales.

Consultar la [guía técnica del avance](docs/guia_5_6.md) y la
[revisión de su rúbrica](docs/revision_rubrica_avance_2.md).

El entorno virtual, los datos, modelos, resultados y documentos o ZIP generados
se conservan fuera del historial de Git mediante `.gitignore`.
