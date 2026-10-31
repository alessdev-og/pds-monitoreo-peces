# Guía para presentar el apartado 5.6

## Qué está listo

El archivo `entregables/Avance_2_Equipo_2_PARA_ENTREGAR.docx` es la copia final
del informe. En el ZIP está en la raíz. Incluye el 5.6, resumen, pruebas y
limitaciones, con datos y unidades sincronizados. El original de Descargas se conserva.
El texto también está en `docs/seccion_5_6.md` para copiarlo al documento del equipo.

El notebook `notebooks/05_06_Implementacion_PDS.ipynb` se ejecutó completo en un
kernel local de Python 3.12.14 ARM64. Sus nueve celdas de código finalizaron sin
errores y conservan las salidas. Las cinco pruebas de `tests/test_signals.py`
también pasaron. El rechazo de OBSEA se comprobó con el comando de análisis.
Los trece archivos de resultados están en `results/avance_56`.

## Demostración breve

1. Abrir el notebook en VS Code con el kernel `.venv`, o subirlo a Colab.
2. Mostrar los parámetros: Ancona, remuestreo de 20 Hz y selección automática
   del mayor tramo continuo. La selección reproducible da el ID 66.
3. Mostrar un fotograma superpuesto: verde y amarillo son anotaciones CVAT;
   amarillo es la trayectoria elegida. No son predicciones de un modelo.
4. Mostrar posiciones y rapidez: el FIR de cinco muestras suaviza variaciones
   rápidas. Su retardo es 2 muestras, o 0.10 s, y se compensa para comparar offline.
5. Mostrar los espectros y la respuesta del FIR. Explicar que la FFT trabaja
   sobre una señal uniforme, con tendencia lineal eliminada y ventana Hann.
6. Mostrar `metrics.csv` y `analysis_summary.json`: incluyen resultados,
   parámetros, versiones y hashes de entrada para repetir el experimento.

En Colab, la celda de datos pide los archivos `video.mp4` y `annotations.xml`
de **Ancona**. Se puede abrir el notebook por *Archivo → Subir notebook*.
Ejecutar las celdas en orden y descargar el ZIP al final. Esta rama se preparó
en el código, pero no se ejecutó en una sesión de Google Colab.

## Resultados calculados

Secuencia Ancona, ID 66, frames 0 a 1199. El XML contiene 29 observaciones
marcadas como ocluidas para ese pez y 787 cajas clave; las demás son interpoladas
por CVAT. Se conservaron ambas clases de cajas y sus marcas.

Los 1200 tiempos de presentación abarcan 0 a 59.885904 s. Los intervalos varían
de aproximadamente 0.000001 a 0.083619 s; hay un intervalo menor que 1 ms.
Esto debe investigarse antes de atribuir significado físico a los tiempos.
El remuestreo a 20 Hz produce 1198 posiciones; el FIR y el recorte para la
comparación dejan 1194, con duración común de 59.65 s. El FPS medio del archivo
es 19.974731; no es la frecuencia uniforme elegida para el análisis.

| Métrica en el mismo intervalo | Sin FIR | Con FIR |
|---|---:|---:|
| Recorrido acumulado (px) | 6380.1873 | 5534.0386 |
| Desplazamiento neto (px) | 916.5738 | 917.7947 |
| Rapidez media (px/s) | 106.9604 | 92.7752 |
| Rapidez máxima (px/s) | 678.4244 | 445.3956 |
| Desviación estándar de rapidez (px/s) | 93.8138 | 72.0755 |

Estos resultados describen el efecto del filtro sobre una trayectoria anotada,
remuestreada y con incertidumbre temporal. La reducción de recorrido o rapidez
no demuestra mayor exactitud. Los extremos suavizados también cambian, por eso
el desplazamiento neto puede variar ligeramente. Las métricas sin FIR ya están
remuestreadas; no corresponden a diferencias divididas por los intervalos
irregulares originales.

La separación de bins de FFT es aproximadamente 0.0167504 Hz. El límite numérico
de Nyquist es 10 Hz; no implica que las anotaciones o la captura contengan
información física fiable hasta esa frecuencia. La interpolación no sustituye
un filtro antialias y no aporta nuevas observaciones.

## Explicación para la exposición

“En este avance implementamos el procesamiento digital de las trayectorias
de referencia. Leemos el video y el XML, verificamos su compatibilidad y
transformamos el centro de las cajas en señales de posición. Como los tiempos
del archivo son irregulares, remuestreamos un tramo continuo a 20 Hz. Aplicamos
un promedio móvil de cinco muestras y comparamos posiciones, rapidez y espectros.
El notebook permite repetir el experimento cambiando parámetros y exporta las
evidencias. La detección y el seguimiento automáticos se integrarán después.”

## Qué falta y qué debe sincronizar el equipo

- Implementar y evaluar detección y seguimiento automáticos. Las 86 trayectorias
  son de referencia; no representan 86 peces detectados por nuestro programa.
- Comprobar visualmente más fotogramas y la continuidad de identidades. Las tres
  imágenes exportadas no validan exhaustivamente toda la secuencia.
- Investigar las anomalías temporales de Ancona. OBSEA se rechaza porque contiene
  148 imágenes frente a las 150 declaradas en el XML; no se recorta por conveniencia.
- Definir y validar tamaño aparente y actividad con criterios independientes.
  No existen porcentajes de acierto de estas clasificaciones en este avance.
- Mantener en las siguientes versiones los datos corregidos de 5.1: Ancona es
  1920 × 1080, FPS medio 19.974731 y origen submarino público.
- Conservar la unidad de rapidez **píxeles por segundo** y distinguir recorrido
  acumulado de desplazamiento neto. El informe de entrega ya incorpora la corrección.
- Revisar de nuevo el índice si el equipo edita el Word. La versión de entrega
  tiene índice comprobado contra su render de 24 páginas; completa el resumen,
  los apartados 5.7 y 5.8, conclusiones y recomendaciones, referencias y anexos.
- Conservar la referencia DIGI4ECO incorporada en la bibliografía y el README
  original del dataset para atribuir las imágenes y coordenadas al compartirlas.

La prueba local confirma el funcionamiento del módulo PDS. No valida todavía
su uso en criaderos rurales ni permite inferir salud, estrés o alimentación.
