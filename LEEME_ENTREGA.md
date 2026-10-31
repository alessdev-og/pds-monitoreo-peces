# Entrega del avance 2 de PDS

## Archivo del informe

`Avance_2_Equipo_2_PARA_ENTREGAR.docx` es la versión de entrega incluida en este
paquete. Completa el resumen y los apartados 5.6, 5.7 y 5.8; sincroniza los datos
de 5.1 y 5.3 y las unidades de 5.4. Contiene cuatro figuras, tablas con métricas
reales, conclusiones y recomendaciones, referencias ajustadas a APA 7, anexos e
índice revisado contra su render de 24 páginas.

La revisión de la rúbrica oficial del Avance 2 está en
`docs/revision_rubrica_avance_2.md`. **Permanece pendiente comprobar la ejecución
en una sesión remota de Google Colab**, solicitada por la guía. La ejecución local
completa y la reproducción desde el ZIP extraído sí se comprobaron.

## Notebook y datos para reproducir el avance

Abrir `notebooks/05_06_Implementacion_PDS.ipynb` en VS Code con un kernel de
Python. El notebook ya conserva las salidas de una ejecución local completa.
En este paquete se incluye el par original `video.mp4` y `annotations.xml`
de Ancona en `data/DIGI4ECO_tracking_dataset/Ancona/`. No se incluyen los videos
de las otras tres secuencias.

En un equipo con Python 3.12, ejecutar desde la carpeta extraída:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-notebook.txt
python tools/execute_notebook.py
```

En Windows, la activación es `.venv\Scripts\activate` y puede usarse `py -3.12`
para crear el entorno. La ejecución fue comprobada en macOS Apple Silicon;
no se ha probado en Windows ni en una sesión remota de Colab.

También se puede ejecutar sólo el módulo de análisis:

```bash
python -m src.development data/DIGI4ECO_tracking_dataset \
  --sequence Ancona --target-fs 20 --output-dir results/avance_56
```

Para Colab, subir el notebook y seleccionar los dos archivos de Ancona cuando
la celda de datos lo solicite. No se necesita subir todo el ZIP a Colab.

## Evidencias y demostración

- `results/avance_56/`: CSV de coordenadas, señales, rapidez, métricas y espectros;
  gráficos, tres fotogramas y resumen JSON con hashes y versiones.
- `results/demo/demo_pds_h264.mp4`: demo sincronizada de 15 segundos, 300
  fotogramas a 20 FPS. El MP4 H.264 tiene resolución de 1280 × 720.
- `docs/guia_5_6.md`: explicación técnica y resultados.
- `docs/guion_demo_20_minutos.md`: guion para el expositor sorteado y preguntas.
- `tests/test_signals.py`: cinco comprobaciones numéricas.

## Alcance declarado

Las posiciones y los IDs proceden de las anotaciones CVAT del dataset.
La implementación validada corresponde a remuestreo, FIR, rapidez y FFT.
La detección y el seguimiento automáticos, la clasificación y la validación
en criaderos rurales siguen pendientes. Las reducciones tras el filtrado no
son porcentajes de precisión. Los tiempos del video contienen irregularidades.

## Atribución de los datos

Subconjunto Ancona de González-Villà y colaboradores, DIGI4ECO Underwater Fish
Tracking Dataset, Zenodo, DOI 10.5281/zenodo.20701225. Se redistribuyen los dos
archivos de Ancona sin modificaciones. El README original del dataset se
conserva junto a los datos y contiene la cita completa y la licencia CC BY 4.0.
Las figuras superpuestas y la demo son visualizaciones derivadas de esos datos.
