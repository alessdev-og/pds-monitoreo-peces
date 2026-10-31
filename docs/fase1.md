# Inspección local — 31 de octubre de 2026

Nota posterior: el desarrollo del apartado 5.6 añadió lectura de trayectorias,
superposiciones, comprobación de PTS y análisis PDS. Este documento conserva
el estado de la inspección inicial; consultar `guia_5_6.md` para el avance actual.

## Estado inicial y estructura

`/Users/jmendivilv/Documents/PDS_PROYECTO` estaba vacío, sin repositorio Git,
entorno virtual, código ni configuraciones. No había instrucciones AGENTS.md
aplicables en el proyecto ni en sus directorios ascendientes.

Dataset encontrado en
`/Users/jmendivilv/Downloads/DIGI4ECO_tracking_dataset`, aproximadamente 147 MiB
según `du -sh`. Contiene README, cuatro pares `video.mp4` / `annotations.xml`
y cuatro PNG de referencia dentro de `figures/`. No se modificaron esos archivos.
Se mantiene la organización por secuencia porque conserva juntos video y XML.

## Entorno comprobado

- macOS 26.6.2, arquitectura de proceso `arm64`.
- Python predeterminado: Homebrew 3.14.7; Python 3.12.14 también disponible.
- Se creó `.venv` con Python 3.12.14 nativo `arm64`.
- Instalación real de `opencv-python-headless==5.0.0.93` y `numpy==2.5.4`,
  mediante wheels macOS ARM64. Importación y decodificación verificadas.
- `pip check`: sin dependencias rotas. No se verificó todavía YOLO ni ByteTrack.

## Videos: lectura real de todos los fotogramas

Resultados de OpenCV con backend FFMPEG. Duraciones derivadas de fotogramas/FPS;
no se asume que equivalgan a la cadencia de captura original.

| Secuencia | Resolución | FPS del archivo | Leídos | Duración calculada (s) | Trayectorias XML |
|---|---|---:|---:|---:|---:|
| Ancona | 1920 × 1080 | 19.974731 | 1200 | 60.075904 | 86 |
| OBSEA | 1912 × 1080 | 30.204082 | 148 | 4.900000 | 12 |
| SmartBay1 | 1920 × 1080 | 20.010172 | 2400 | 119.939000 | 92 |
| SmartBay2 | 1920 × 1080 | 29.970030 | 2101 | 70.103367 | 301 |

Se decodificaron 5849 fotogramas en total. En cada MP4, el conteo leído coincide
con el conteo informado por OpenCV. Los informes completos y el primer fotograma
se guardaron en `results/<secuencia>/`.

## Anotaciones inspeccionadas

Los cuatro XML se pudieron analizar con `xml.etree.ElementTree`. Declaran
versión CVAT 1.1 y contienen `<track>` con identificadores y cajas `<box>`.
La resolución XML coincide con la decodificada en cada secuencia.

| Secuencia | Índices XML | Cajas totales | Cajas `outside=0` | Cajas `outside=1` | Etiquetas por trayectoria |
|---|---|---:|---:|---:|---|
| Ancona | 0–1199 | 27078 | 27006 | 72 | Fish: 86 |
| OBSEA | 0–149 | 1384 | 1380 | 4 | Fish: 12 |
| SmartBay1 | 0–2399 | 42696 | 42601 | 95 | Fish: 90; Apogon sp: 2 |
| SmartBay2 | 0–2100 | 55351 | 55033 | 318 | Fish: 301 |

Los índices empiezan en cero. `outside=1` no es una observación visible;
`occluded` indica oclusión y `keyframe` distingue las cajas clave de las
interpoladas por CVAT. Los identificadores pertenecen a cada secuencia;
no identifican necesariamente al mismo pez entre videos.

### Discrepancia de OBSEA

El XML y README declaran 150 fotogramas; el MP4 tiene 148 muestras de video
y OpenCV decodifica 148. Se comprobó también la tabla `stsz` del contenedor MP4
con la biblioteca estándar de Python: el conteo de muestras de la pista `vide`
es 148. Esto respalda que no se trata solamente de una lectura interrumpida
de OpenCV. Su tabla de tiempos `stts` incluye una muestra de duración cero.
El XML declara duración de 4.97 s, mientras que 148/FPS da 4.90 s.

No se determinó qué correspondencia tienen las 148 imágenes con las 150
posiciones anotadas. No basta con eliminar las dos últimas anotaciones ni
con asumir que el resto está alineado. OBSEA queda pendiente de comprobación
visual y temporal antes de utilizarlo para evaluación.

## Implementación y verificaciones

Se añadió únicamente el lector `src/main.py`, las dependencias fijadas,
`.gitignore` y documentación. El lector comprueba apertura, FPS positivo,
fotogramas no vacíos, resolución constante y conteo completo; libera el archivo
incluso ante errores. Exporta un JPEG y un JSON por ejecución.

Pruebas realizadas: lectura secuencial completa de los cuatro MP4, comparación
con el conteo del archivo, importación nativa ARM64, comprobación de dependencias
y rechazo de una ruta inexistente sin generar resultados.

## Acciones inmediatas para cerrar Fase 1

1. Empezar con Ancona para la siguiente comprobación de anotaciones; su conteo
   coincide y no requiere resolver primero el problema de OBSEA.
2. Superponer cajas XML en varios fotogramas distribuidos por cada secuencia
   para verificar alineación, límites e interpolaciones. Esta fase todavía
   no implementa el lector de trayectorias ni esa superposición.
3. Investigar el desfase de OBSEA contra sus imágenes anotadas y, si es necesario,
   la fuente del dataset. Documentar la correspondencia antes de usarlo.
4. Verificar marcas de tiempo y cadencia de muestreo antes de calcular
   velocidades y FFT; no redondear los FPS automáticamente a 20 o 30.

Todavía no hay detección, seguimiento automático, clasificación ni métricas de
precisión. El tamaño futuro será aparente en píxeles; el dataset es submarino
y no valida por sí solo el funcionamiento en criaderos rurales.
