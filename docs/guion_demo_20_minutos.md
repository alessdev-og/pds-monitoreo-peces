# Guion para una exposición de 20 minutos

## Estructura para el expositor seleccionado

La guía oficial indica que la exposición principal del trabajo final la realiza
un integrante elegido por sorteo. Todos deben conocer la solución completa y
los demás pueden responder preguntas. La siguiente tabla organiza los temas
para ese expositor; no reparte la exposición entre tres personas.

| Minutos | Responsable sugerido | Qué mostrar |
|---|---|---|
| 0 a 3 | Expositor sorteado | Problema, objetivos y qué señales se van a medir |
| 3 a 6 | Expositor sorteado | Dataset real, licencia, anotaciones y flujo del sistema |
| 6 a 12 | Expositor sorteado | Demostración sincronizada y ejecución del notebook |
| 12 a 16 | Expositor sorteado | Muestreo, remuestreo, FIR, retardo y FFT |
| 16 a 18 | Expositor sorteado | Resultados medidos, límites y desarrollo pendiente |
| 18 a 20 | Equipo | Preguntas del profesor |

## Qué conviene destacar

Mostrar el movimiento del pez junto al cursor que recorre las señales. El video
`results/demo/demo_pds_h264.mp4` dura 15 segundos y corresponde al intervalo
28 a 43 segundos de Ancona. Incluye el ID seleccionado, la trayectoria reciente,
las posiciones, la rapidez antes y después del FIR y el espectro del tramo
completo analizado. Está rotulado como referencia CVAT y análisis offline.

La imagen sigue el último fotograma disponible según los tiempos del archivo.
El cursor avanza en esos mismos segundos, mientras las métricas proceden de
las señales remuestreadas. La FFT es global: no cambia con cada fotograma.

El video es un apoyo visual reproducible; el notebook permite enseñar el
cálculo y sus parámetros. No presentarlo como inferencia en tiempo real.

## Demostración de seis minutos

1. Reproducir el video una vez y señalar el pez 66, su trayectoria y el cursor.
2. Repetir o pausar donde la rapidez cambia. Identificar azul como sin FIR y
   naranja como con FIR. Las curvas de posición se parecen porque la escala
   espacial es grande; el efecto resulta más visible en la rapidez.
3. Abrir el notebook ya ejecutado y mostrar los parámetros de la celda 3.
4. Mostrar las pruebas numéricas y un CSV para vincular figura y cálculo.
5. Explicar el remuestreo a 20 Hz y el retardo FIR de 0.10 segundos, compensado
   para esta comparación offline.
6. Mostrar el JSON con versiones, hashes y procedencia de los archivos.

Conviene tener el notebook ejecutado y el video local como respaldo. La
ejecución completa del notebook ya fue comprobada localmente. La presentación
puede incluir una nueva ejecución, conservando una copia de los resultados.

## Preguntas técnicas que deben poder responder

**¿De dónde salen las coordenadas?** Del centro de las cajas CVAT del dataset.
En este avance son referencias anotadas, con cajas clave e interpoladas.
Todavía no son predicciones de nuestro detector.

**¿Por qué no usan simplemente 30 FPS?** Ancona informa 19.974731 FPS de media
y sus tiempos de presentación son irregulares. Se conserva la información
temporal y se interpola a una grilla uniforme de 20 Hz para el análisis PDS.
Existen anomalías de tiempo pendientes de investigar.

**¿Por qué cinco muestras?** Es el FIR inicial propuesto por el proyecto.
Sus cinco coeficientes valen 0.2 y su retardo es de dos muestras. Su respuesta
en frecuencia y su efecto temporal se pueden observar en los gráficos. No
se ha probado que sea la longitud óptima para todo movimiento.

**¿Una rapidez menor después del filtro significa mayor precisión?** No.
Demuestra suavizado. Para afirmar mejora de exactitud se necesita una referencia
independiente y un experimento de evaluación definido.

**¿Las medidas están en centímetros?** No; son píxeles y píxeles por segundo.
Hace falta calibración y considerar la perspectiva para obtener medidas físicas.

**¿Un pico en la FFT prueba un comportamiento del pez?** No. El espectro describe
las posiciones anotadas, interpoladas y remuestreadas. Hay que considerar la
duración, el detrend, la ventana, el muestreo y la calidad de las anotaciones.

## Siguiente mejora de mayor impacto

Integrar detección y seguimiento automáticos, guardar sus coordenadas y
compararlas con la referencia. Conservar ambos orígenes identificados. Medir
detecciones correctas, omisiones, falsas detecciones y continuidad de identidad
sobre un intervalo reservado para evaluación. El resultado deberá conectar con
este mismo módulo de PDS.

Después se pueden incorporar categorías de tamaño aparente y actividad,
con umbrales justificados y evaluación independiente. Esas funciones siguen
pendientes; no aparecen como resultados validados en la demo actual.
