# Aleta · Laboratorio de señales de batido de cola

Demo web adaptable a celular y computadora, sin servidor de procesamiento ni
dependencias JavaScript externas. Los videos y CSV se procesan en el dispositivo.
La tipografía web es opcional; hay fuentes de sistema de respaldo.

## Qué funciona

- **Simulación:** pez ilustrativo, señal angular y canal de sensor sintético a
  60 muestras/s. Controles de frecuencia, amplitud, ruido y desajuste. Las dos
  señales comparten un modelo; no son una validación independiente.
- **Cámara:** solicita solo video, preferentemente la cámara trasera, mediante
  HTTPS o localhost. La adquisición no requiere micrófono.
- **Mi video:** carga local de un archivo compatible con el navegador. No se sube.
- **Marcado asistido:** el usuario marca cabeza, cuerpo y un punto de la cola.
  Un seguidor de tres parches por correlación normalizada estima sus posiciones.
  Si falla la correlación, hay un salto temporal mayor de 0.2 s o la geometría
  deja de ser válida, se detiene sin fabricar muestras. Una correlación alta
  no descarta deriva: se debe revisar la superposición.
- **Clip de prueba:** MP4 sintético de 8 segundos, 60 fps, frecuencia conocida
  de 2 Hz. Permite probar el flujo de seguimiento; no valida peces reales.
- **PDS:** ángulo de cola respecto al eje cabeza-cuerpo, tiempos del video,
  remuestreo lineal, FIR binomial, FFT y exportación CSV/JSON con procedencia.
- **CSV independiente:** acepta `t_s,value`; calcula su frecuencia por separado.
  No verifica el sensor, no convierte a unidades físicas y no sincroniza video.

No mide fuerza en newtons ni decide salud, tamaño, madurez o aptitud productiva.
No hay un sensor físico conectado ni un modelo biológico entrenado.

## Abrir y probar

Publicación preparada para GitHub Pages en
`https://alessdev-og.github.io/pds-monitoreo-peces/demo/`.
La copia servida se genera desde `dist/` con `python3 tools/build_mobile_demo.py`
desde la raíz del proyecto. El registro `.openai/hosting.json` corresponde a un
intento de alojamiento en Sites que no pudo completarse por conectividad; no
representa una publicación activa allí.

```bash
cd demo-aleteo
python3 -m http.server 8765 --directory dist --bind 127.0.0.1
```

Abrir `http://127.0.0.1:8765` en la computadora. Para usar la cámara desde otro
dispositivo se necesita el enlace HTTPS publicado: una dirección HTTP de la red
local no habilita necesariamente la cámara del celular. Abrirlo en el navegador
del celular y permitir cámara cuando se vaya a usar. La compatibilidad y el rendimiento en el
teléfono físico del equipo todavía deben comprobarse.

1. En **Simulación**, observar las señales y cambiar frecuencia/ruido. Cada
   cambio reinicia el registro para no mezclar condiciones. Máximo 120 segundos.
2. En **Mi video**, pulsar **Clip de prueba**.
3. Pulsar **Marcar 3 puntos** y tocar el centro de los cuadrados 1, 2 y 3.
4. El video comienza. Tras varios segundos, comprobar que el pico candidato
   está cerca de **2 Hz**. Revisar los marcadores durante todo el tramo.
5. Descargar CSV e informe JSON.
6. Repetir con una grabación real en la que un pez y su cola tengan suficiente
   tamaño, contraste y visibilidad. Registrar un pez por vez para la primera
   validación y contrastar con conteos manuales del mismo intervalo.

Al cambiar de pestaña se pausa. Al pausar una cámara en vivo hay que volver a
marcar los puntos, porque el pez puede haberse movido. En un video se puede
continuar; cambiar el instante reinicia el registro y exige otro marcado.

## Tratamiento de señales

La señal angular firmada es `atan2(cross(body-head, tail-body), dot(...))`, en
grados. Las tres posiciones provienen del usuario y del seguimiento por parches,
no de un detector de peces. Se rechazan ejes de menos de 3 píxeles y ángulos de
magnitud mayor de 100 grados en el flujo de seguimiento.

Se usa el último tramo continuo, hasta 8 s. El intervalo mediano estima la
cadencia procesada; huecos mayores de tres intervalos separan los tramos. Se
interpola sin extrapolar. Este procedimiento no reemplaza un filtro antialias
ni recupera batidos que la cámara o el procesamiento no hayan muestreado.

El FIR es `[1,4,6,4,1]/16`, solo ventanas completas. Su retardo de 2 muestras se
compensa **para dibujar**, no para prometer latencia nula. Atenúa frecuencias
altas; el pico y su amplitud se calculan sobre la señal original remuestreada.
No se reutiliza sin modificación el filtro del notebook de trayectorias CVAT.

FFT radix-2 con detrend lineal, ventana Hann y amplitud unilateral corregida por
la suma de la ventana. El relleno a potencia de dos permite interpolar el pico,
sin mejorar la resolución física aproximada `fs/N`. La amplitud mostrada es la
del bin máximo, no una medida de fuerza. Banda exploratoria: desde
`max(0.3, 2/duración)` hasta `min(12, 0.4*fs)` Hz. No es una banda biológica
validada para una especie. Un criterio heurístico de contraste espectral oculta
picos no claros; no constituye una prueba estadística de periodicidad.

## Sensor futuro

Importar muestras con esta cabecera exacta y tiempos crecientes en segundos:

```csv
t_s,value
0.000,512
0.010,515
0.020,519
```

Se requieren al menos 8 muestras y un tramo de al menos 2 s para analizar. Los
valores se tratan como unidades arbitrarias hasta calibrar el sensor. El CSV de
exportación de la app tiene varias columnas/canales y no es este formato de
importación: seleccionar un canal y convertirlo explícitamente si se reutiliza.

Para el Mega se debe definir primero el sensor de presión/flujo, su rango,
sensibilidad, acondicionamiento, antialias, adquisición y sincronización. No se
conecta un sensor desconocido directamente ni se convierte una lectura ADC a
fuerza mediante una regla inventada. Una sonda DS18B20 mide temperatura y no
sustituye esta adquisición.

## Comprobación

```bash
npm test
```

Las pruebas cubren frecuencia/amplitud conocidas, ruido y offset, señales
constantes, FIR, ángulos invariantes a traslación/rotación, tiempos irregulares,
huecos, CSV incorrectos y seguimiento/pérdida de puntos sintéticos.

`tests/make_fixture.py` genera un AVI sintético en `/tmp` usando las dependencias
OpenCV del proyecto principal; convertirlo a MP4 H.264 para reemplazar el clip.
El archivo servido es `dist/tracking-fixture.mp4`.

## Referencias

- [Estimación de batido de cola mediante imagen, EUSIPCO 2018](https://eurasip.org/Proceedings/Eusipco/Eusipco2018/papers/1570437333.pdf).
- [Tiempos por fotograma en el navegador](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback).
- [Acceso a cámara y contexto seguro](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

El notebook y el análisis CVAT anteriores permanecen separados de esta demo.
