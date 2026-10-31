# Revisión de la rúbrica del Avance 2

Fuente: guía oficial del Trabajo Final de Procesamiento Digital de Señales
2026, Anexo 01, páginas 8 y 9. Se inspeccionaron ambas páginas completas.

## Qué evalúa el segundo avance

| Criterio de la rúbrica | Puntaje máximo | Evidencia del avance actual |
|---|---:|---|
| Ajustes al primer avance y consistencia del contexto y objetivos | 1 | Datos y unidades actualizados; el alcance PDS y los objetivos pendientes se declaran |
| Resumen con problema, fuente, metodología, resultados y conclusión | 1.5 | Resumen completado con datos reales y límites |
| Desarrollo con técnicas PDS, notebook organizado, pruebas y resultados preliminares | 1.5 | Notebook ejecutado localmente, FIR, rapidez, FFT, cinco pruebas, CSV y gráficos; falta comprobar Colab |
| Conclusiones y recomendaciones sustentadas en los objetivos y resultados | 1 | Sección incorporada con conclusiones preliminares y tareas pendientes |
| Referencias en APA 7 y anexos de evidencia técnica y fuente de datos | 1 | Referencias ajustadas, parámetros y hashes anexados; datos originales y README incluidos |
| Total | 6 | No se estima una nota ni se garantiza la calificación |

El bloque de desarrollo empieza en la página 8 y continúa en la página 9:
su puntaje de 1.5 abarca las dos páginas. Incluye procedencia y licencia,
formato, unidades, muestreo, duración, canales, calidad, fundamentos, carga y
digitalización, análisis temporal y frecuencial, convolución y filtrado,
implementación, comparaciones, interpretación y limitaciones.

## Lectura aplicada al proyecto

La rúbrica pide resultados preliminares y no dice explícitamente que la
detección y el seguimiento automáticos deban estar terminados en el Avance 2.
Es razonable presentar un módulo PDS funcional sobre trayectorias de referencia,
si se identifica ese origen y se reconoce que el objetivo general del sistema
completo todavía no está alcanzado. Esta interpretación no sustituye una
instrucción específica del docente ni garantiza una nota.

Las cajas de la demo y los IDs proceden de CVAT. No deben presentarse como
predicciones del sistema. La clasificación de tamaño y actividad sigue pendiente.

## Pendiente crítico antes de declarar cumplimiento completo

La guía solicita Python mediante Google Colab. El notebook tiene una rama de
carga y descarga para Colab, pero sólo se comprobó la ejecución local. Se debe
abrir el notebook en Colab, subir los dos archivos de Ancona, ejecutar todas
las celdas y descargar el `.ipynb` conservando las salidas. También se debe
conservar el ZIP de resultados que genera la última celda.

## Otras precisiones de la guía

- Las conclusiones y las recomendaciones ya se evalúan en el segundo avance.
- La presentación PPTX y Planificación.pdf aparecen en el paquete de entrega
  final; no figuran como requisitos expresos de la tabla del segundo avance.
- La exposición principal del trabajo final corresponde a un integrante elegido
  por sorteo; todos deben poder explicar la solución y responder preguntas.
  Se corrigió el guion previo que repartía la exposición entre tres personas.
- La guía menciona equipos de cuatro integrantes y el informe contiene tres.
  Debe comprobarse si el docente autorizó esa composición.
- Hay una discrepancia de semanas entre el cronograma y las indicaciones;
  corresponde seguir la fecha que el docente comunicó para esta entrega.
