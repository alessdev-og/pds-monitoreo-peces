"""Preparar una copia coherente del avance con resultados reales y evidencias."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'entregables/Avance_2_Equipo_2_con_5_6.docx'
OUTPUT = ROOT/'entregables/Avance_2_Equipo_2_PARA_ENTREGAR.docx'
RESULTS = ROOT/'results/avance_56'
report = json.loads((RESULTS/'analysis_summary.json').read_text())
doc = Document(SOURCE)


def find(prefix):
    return next(p for p in doc.paragraphs if p.text.startswith(prefix))


def font(run, size=12, bold=False, italic=False):
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    run.bold = bold
    run.italic = italic


def replace(paragraph, value):
    paragraph.clear()
    font(paragraph.add_run(value))


def body_before(anchor, value, bold_prefix=None):
    p = anchor.insert_paragraph_before()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 2
    p.paragraph_format.first_line_indent = Inches(.5)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.widow_control = True
    if bold_prefix:
        font(p.add_run(bold_prefix+' '), bold=True)
    font(p.add_run(value))
    return p


def caption_before(anchor, number, value, kind='Figura'):
    p = anchor.insert_paragraph_before()
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(3)
    font(p.add_run(f'{kind} {number}'), size=11, bold=True)
    title = anchor.insert_paragraph_before()
    title.paragraph_format.keep_with_next = True
    title.paragraph_format.space_after = Pt(5)
    font(title.add_run(value), size=11, italic=True)


def image_before(anchor, filename):
    p = anchor.insert_paragraph_before()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    p.add_run().add_picture(str(RESULTS/filename), width=Inches(6.05))


def table_before(anchor, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for col, width in zip(table.columns, widths): col.width = Inches(width)
    for cell, value in zip(table.rows[0].cells, headers): cell.text = value
    for values in rows:
        for cell, value in zip(table.add_row().cells, values): cell.text = str(value)
    for index, row in enumerate(table.rows):
        # Evitar que una fila se parta entre páginas.
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.1
                p.paragraph_format.space_after = Pt(5)
                p.paragraph_format.space_before = Pt(5)
                for r in p.runs: font(r, size=11, bold=index == 0)
            if index == 0:
                shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'EDEDED')
                cell._tc.get_or_add_tcPr().append(shade)
    borders = OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        el = OxmlElement('w:'+edge)
        for name,value in [('val','single'),('sz','4'),('color','808080')]: el.set(qn('w:'+name),value)
        borders.append(el)
    table._tbl.tblPr.append(borders)
    repeat = OxmlElement('w:tblHeader'); repeat.set(qn('w:val'),'true')
    table.rows[0]._tr.get_or_add_trPr().append(repeat)
    anchor._p.addprevious(table._tbl)


# Completar el resumen usando únicamente la implementación y los resultados reales.
summary_heading = find('Resumen')
summary_end = find('Descripción del caso de estudio y problemática')
element = summary_heading._p.getnext()
while element is not None and element is not summary_end._p:
    following = element.getnext()
    # Conservar los saltos de página del documento de referencia.
    if element.tag == qn('w:p') and not ''.join(element.itertext()).strip():
        if not element.xpath('.//w:br'):
            element.getparent().remove(element)
    element = following
summary = body_before(summary_end,
    'Este avance presenta la implementación del módulo de procesamiento digital de señales '
    'para un sistema de monitoreo de peces. Se trabajó con la secuencia submarina Ancona del '
    'dataset público DIGI4ECO, compuesta por 1200 fotogramas y 86 trayectorias de referencia. '
    'Se extrajeron los centros de las cajas CVAT para formar señales discretas de posición. '
    'Debido a la irregularidad de los tiempos del archivo, se remuestreó un tramo continuo a '
    '20 Hz y se aplicó un filtro FIR de promedio móvil de cinco muestras. Se calcularon '
    'recorrido, desplazamiento neto, rapidez y espectros mediante FFT. El notebook se ejecutó '
    'completo en macOS Apple Silicon y se superaron cinco pruebas numéricas. Para el pez con '
    'ID 66, la rapidez media en el intervalo común pasó de 106.96 a 92.78 píxeles por segundo '
    'tras el filtrado; esta diferencia describe el suavizado y no demuestra una mejora de '
    'exactitud. Se generaron tablas, gráficos y una demostración sincronizada. La detección '
    'y el seguimiento automáticos, la clasificación y la validación en criaderos rurales '
    'constituyen las siguientes etapas del proyecto.')
# Situar el resumen inmediatamente después de su encabezado.
summary_heading._p.addnext(summary._p)

# Ajustar los datos preliminares para que coincidan con la secuencia implementada.
replace(find('El proyecto utilizará secuencias de video'),
    'Para este avance se utilizó la secuencia Ancona del DIGI4ECO Underwater Fish Tracking '
    'Dataset. El conjunto proporciona videos submarinos y anotaciones de referencia que '
    'permiten validar la construcción y el procesamiento de las señales de movimiento. '
    'La aplicación en criaderos rurales es el objetivo del proyecto y requiere una '
    'validación posterior con datos del entorno de uso.')
replace(find('Los videos podrán obtenerse'),
    'Los archivos se obtuvieron del dataset de González-Villà et al. (2026), '
    'publicado en Zenodo con DOI 10.5281/zenodo.20701225. '
    'El README de la descarga declara licencia Creative Commons Attribution 4.0 '
    'International y proporciona la cita bibliográfica. Se conservan los archivos '
    'originales y se registra su hash SHA-256 para identificar los datos analizados.')
for prefix in ['Para este avance se utilizó', 'Los archivos se obtuvieron']:
    p=find(prefix)
    p.paragraph_format.space_before=Pt(0)
    p.paragraph_format.space_after=Pt(6)
specifications = [
    ('Fuente','Video submarino Ancona y anotaciones de seguimiento CVAT'),
    ('Procedencia','DIGI4ECO Underwater Fish Tracking Dataset, Zenodo'),
    ('Licencia o permiso','Creative Commons Attribution 4.0 International'),
    ('Formato','Video MP4 y anotaciones XML CVAT 1.1'),
    ('Resolución','1920 × 1080 píxeles'),
    ('Frecuencia de muestreo','FPS medio del archivo: 19.974731; grilla de análisis: 20 Hz'),
    ('Duración','1200 fotogramas; PTS de 0 a 59.885904 s; duración nominal N/FPS: 60.075904 s'),
    ('Canales','Imagen decodificada de 3 canales; orden BGR en OpenCV'),
    ('Unidades','Posición y tamaño aparente: px; tiempo: s; rapidez: px/s; frecuencia: Hz'),
    ('Calidad de datos','Oclusiones, cajas interpoladas y tiempos irregulares; requieren comprobación'),
]
table = doc.tables[3]
table.autofit=False
table.alignment=WD_TABLE_ALIGNMENT.CENTER
table._tbl.tblPr.find(qn('w:tblW')).set(qn('w:w'),'8784')
for indent in table._tbl.tblPr.findall(qn('w:tblInd')):
    table._tbl.tblPr.remove(indent)
for column,width in zip(table.columns,[1.7,4.4]):column.width=Inches(width)
table.cell(0,1).text = 'Especificación verificada en Ancona'
for row,(name,value) in zip(table.rows[1:],specifications):
    row.cells[0].text=name;row.cells[1].text=value
for row in table.rows:
    row.height=None
    for existing in row._tr.get_or_add_trPr().findall(qn('w:cantSplit')):
        existing.getparent().remove(existing)
    row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    for cell,width in zip(row.cells,[1.7,4.4]):
        cell.width=Inches(width)
        for p in cell.paragraphs:
            p.paragraph_format.line_spacing=1.1
            p.paragraph_format.space_before=Pt(0)
            p.paragraph_format.space_after=Pt(4)
            for run in p.runs:font(run,11)
for existing in table.rows[0]._tr.get_or_add_trPr().findall(qn('w:tblHeader')):
    existing.getparent().remove(existing)
repeat=OxmlElement('w:tblHeader');repeat.set(qn('w:val'),'true')
table.rows[0]._tr.get_or_add_trPr().append(repeat)

replace(find('A partir de los videos se obtendrán'),
    'Las posiciones de referencia se obtienen del centro de cada caja del XML. '
    'Para cada pez se conservan el identificador, el fotograma, los centros x e y '
    'en píxeles y las marcas de oclusión e interpolación. Los tiempos se consultan '
    'en el video; el FPS medio no implica que los intervalos sean uniformes.')
replace(find('La adquisición de datos se realizará'),
    'La carga de datos se implementó en Python con OpenCV y se comprobó localmente '
    'en macOS Apple Silicon. El notebook también incluye preparación y carga de '
    'archivos para Google Colab; esa rama queda pendiente de ejecución en la nube. '
    'En esta etapa se leen los fotogramas y sus anotaciones de referencia. La '
    'detección automática se integrará posteriormente.')
replace(find('Muestreo:'),
    'Muestreo: se leen las marcas de presentación de cada fotograma. Ancona '
    'informa un promedio de 19.974731 FPS, pero sus intervalos son irregulares. '
    'Se interpola cada tramo continuo a una grilla de 20 Hz, con un intervalo '
    'de 0.05 s, antes del filtrado y la FFT.')
replace(find('Remuestreo:'),
    'Remuestreo: se emplea interpolación lineal dentro de cada tramo visible '
    'continuo, sin extrapolar ni unir ausencias del pez. El procedimiento no '
    'recupera información perdida ni sustituye un filtro antialias. Se registran '
    'las irregularidades temporales y se mantiene pendiente validar la cadencia '
    'física de la cámara.')
replace(find('Donde fs es la frecuencia'),
    'Donde fs es la frecuencia de la señal uniformemente remuestreada, '
    'expresada en Hz. La magnitud calculada corresponde a la rapidez aproximada '
    'en píxeles por segundo. No representa velocidad física en metros por segundo.')
replace(find('Se aplicarán técnicas de filtrado digital'),
    'Se aplica filtrado digital para suavizar variaciones rápidas de la señal '
    'de posición. La comparación antes y después permite estudiar ese efecto; '
    'para afirmar una mejora de exactitud se requiere una referencia independiente '
    'y un protocolo adicional de evaluación.')

# Títulos de sección breves; se conserva su numeración original.
heading_pairs = [
    ('Requerimientos y fuente de las señales:', 'Requerimientos y fuente de las señales'),
    ('Fundamento técnico:', 'Fundamento técnico'),
    ('Adquisición o carga y digitalización:', 'Adquisición carga y digitalización'),
    ('Análisis de señales:', 'Análisis de señales'),
    ('Procesamiento: sistemas discretos', 'Procesamiento y filtrado digital'),
    ('Implementación computacional:', 'Implementación computacional'),
    ('Pruebas, métricas y resultados:', 'Pruebas métricas y resultados'),
    ('Limitaciones, riesgos, consideraciones', 'Limitaciones y posibilidades de mejora'),
]
for prefix,value in heading_pairs:
    p=find(prefix);replace(p,value);p.paragraph_format.keep_with_next=True

p = find('Datos y alcance del avance.')
replace(p,p.text.replace('Estas características corresponden a los datos inspeccionados y reemplazan, '
    'para esta implementación, los valores preliminares propuestos en el apartado 5.1.',
    'Estas características corresponden a los datos inspeccionados y se detallan en el apartado 5.1.'))

# Completar 5.7 con métricas y gráficos generados, sin atribuir precisión al sistema.
section7=find('Pruebas métricas y resultados')
section8=find('Limitaciones y posibilidades de mejora')
empty=section7._p.getnext()
if empty is not section8._p and not ''.join(empty.itertext()).strip():empty.getparent().remove(empty)
body_before(section8,
    'La validación del avance comprende pruebas numéricas de las funciones de PDS y '
    'una ejecución completa sobre datos reales de Ancona. Se decodificaron los 1200 '
    'fotogramas y se verificó su correspondencia en cantidad y resolución con el XML. '
    'Se exportaron 27006 cajas visibles de 86 trayectorias y se seleccionó de manera '
    'reproducible el tramo continuo del pez con ID 66, presente de los fotogramas 0 a 1199.')
caption_before(section8,5,'Comprobaciones ejecutadas para el módulo PDS',kind='Tabla')
table_before(section8,['Comprobación','Criterio verificado','Resultado'],[
    ['FIR sobre una rampa','Media de cada ventana de cinco muestras y bordes sin ceros','Correcto'],
    ['Interpolación y rapidez','Movimiento lineal de tiempos irregulares con rapidez conocida','Correcto'],
    ['Tiempos repetidos','Rechazo de tiempos no estrictamente crecientes','Correcto'],
    ['FFT de prueba','Recuperación de una sinusoide de 2 Hz y amplitud 3 px','Correcto'],
    ['Ausencias de trayectoria','Separación de tramos sin unir huecos','Correcto'],
    ['Video Ancona','1200 fotogramas decodificados y resolución coincidente','Correcto'],
    ['Control de OBSEA','Rechazo de 148 fotogramas de video frente a 150 en XML','Correcto'],
], [2.0,3.1,1.0])
body_before(section8,
    'El tramo se remuestreó a 20 Hz y produjo 1198 posiciones. La convolución valid '
    'con el FIR de cinco muestras y la comparación con retardo compensado dejaron '
    '1194 posiciones sobre el mismo intervalo de 59.65 s. La tabla 6 compara ambas '
    'versiones. La señal denominada sin FIR ya está remuestreada; no es la derivada '
    'calculada directamente sobre los intervalos irregulares del archivo.')
raw,fir=report['metrics_without_fir'],report['metrics_with_fir']
metrics=[('Recorrido acumulado (px)','path_length_px'),('Desplazamiento neto (px)','net_displacement_px'),
    ('Rapidez media (px/s)','mean_speed_px_s'),('Rapidez máxima (px/s)','max_speed_px_s'),
    ('Desviación estándar de rapidez (px/s)','std_speed_px_s')]
caption_before(section8,6,'Comparación en el mismo intervalo para el pez 66',kind='Tabla')
table_before(section8,['Métrica','Sin FIR','Con FIR'],
    [[label,f'{raw[key]:.4f}',f'{fir[key]:.4f}'] for label,key in metrics],[3.3,1.4,1.4])
body_before(section8,
    'El filtrado redujo la rapidez media y los picos observados en la señal. '
    'La reducción de recorrido refleja el suavizado de la trayectoria y no permite '
    'concluir una mejora de exactitud. El desplazamiento neto varía ligeramente '
    'porque el promedio también modifica las posiciones de los extremos. '
    'Las observaciones de este pez incluyen 29 cajas marcadas como ocluidas y '
    '787 cajas clave; las demás fueron interpoladas por CVAT.')
caption_before(section8,1,'Cajas de referencia CVAT en el fotograma 600 de Ancona')
image_before(section8,'reference_frame_0600.jpg')
body_before(section8,
    'La figura 1 muestra una comprobación visual de correspondencia entre cajas e '
    'imagen. El amarillo identifica el pez seleccionado y el verde las demás '
    'referencias visibles. Esta inspección de tres fotogramas distribuidos por el '
    'tramo no constituye una validación exhaustiva de las identidades.')
caption_before(section8,2,'Señales de posición y rapidez antes y después del FIR')
image_before(section8,'signals_and_speed.png')
body_before(section8,
    'En la figura 2, el FIR conserva las variaciones amplias y atenúa fluctuaciones '
    'rápidas. La comparación offline utiliza los tiempos centrales de cada ventana '
    'para compensar el retardo de dos muestras. Los CSV conservan tanto los tiempos '
    'de salida causal como los tiempos centrales usados en las figuras.')
caption_before(section8,3,'Espectros de posición con tendencia lineal eliminada y ventana Hann')
image_before(section8,'spectra.png')
body_before(section8,
    'La DFT mediante FFT utiliza 1194 muestras. La separación de bins es '
    'aproximadamente 0.0167504 Hz y el límite numérico de Nyquist es 10 Hz. '
    'La figura 3 describe componentes de las posiciones anotadas y remuestreadas; '
    'los picos no prueban periodicidad biológica. El muestreo original y las '
    'interpolaciones de CVAT limitan la información interpretable.')
caption_before(section8,4,'Respuesta en frecuencia del FIR de cinco muestras a 20 Hz')
image_before(section8,'fir_response.png')
body_before(section8,
    'La figura 4 muestra la ganancia del FIR y permite relacionar el suavizado '
    'temporal con su respuesta en frecuencia. Se generó además un video de apoyo '
    'de 15 s que sincroniza imagen, trayectoria, posiciones y rapidez. Su salida '
    'H.264 se verificó mediante la lectura de 300 fotogramas a 20 FPS y resolución '
    'de 1280 × 720; es una reproducción de resultados offline sobre referencias.')

# Completar 5.8 con limitaciones constatadas y acciones futuras concretas.
bibliography=find('Bibliografía')
empty=section8._p.getnext()
if empty is not bibliography._p and not ''.join(empty.itertext()).strip():empty.getparent().remove(empty)
limitations=[
    ('Alcance de la implementación.',
     'El avance valida el procesamiento PDS de coordenadas de referencia. La detección y '
     'el seguimiento automáticos aún no están implementados; por ello no se reportan '
     'precisión de detección, continuidad de identidades predichas ni porcentajes de '
     'clasificación. Las categorías de tamaño y actividad requieren criterios y '
     'etiquetas independientes para ser evaluadas.'),
    ('Calidad temporal y de anotación.',
     'Ancona presenta tiempos de archivo irregulares, incluido un intervalo inferior a '
     '1 ms. El remuestreo permite aplicar las operaciones sobre una grilla uniforme, '
     'pero no valida la cadencia física de captura ni corrige errores de anotación. '
     'Las oclusiones y las cajas interpoladas pueden afectar el movimiento estimado. '
     'OBSEA contiene 148 imágenes y declara 150 en el XML; se rechaza su análisis '
     'mientras no se determine la correspondencia correcta.'),
    ('Unidades y transferencia al entorno rural.',
     'El tamaño y el movimiento son aparentes en píxeles. La perspectiva, la distancia '
     'a la cámara y las condiciones del agua impiden convertirlos directamente en '
     'longitud o velocidad físicas. El dataset contiene escenas submarinas públicas, '
     'por lo que hace falta una validación adicional en criaderos rurales. '
     'Los resultados no permiten inferir enfermedades, estrés o alimentación.'),
    ('Uso responsable y mejoras.',
     'Se conserva la atribución del dataset y su licencia CC BY 4.0, y se identifican '
     'las figuras como referencias anotadas. No se realizaron intervenciones sobre '
     'animales. Las siguientes tareas son investigar los tiempos del archivo, '
     'integrar un detector y un seguidor, evaluar sus predicciones sobre datos '
     'reservados y verificar la ejecución en Google Colab. Se mantendrán separadas '
     'las coordenadas de referencia y las predichas para evitar confundir los '
     'resultados de ambos procesos.'),
]
for title,value in limitations:body_before(bibliography,value,bold_prefix=title)

# Conclusiones preliminares sustentadas en lo implementado y recomendaciones.
conclusions=bibliography.insert_paragraph_before()
conclusions.alignment=WD_ALIGN_PARAGRAPH.CENTER
conclusions.paragraph_format.keep_with_next=True
conclusions.paragraph_format.space_before=Pt(12)
conclusions.paragraph_format.space_after=Pt(12)
font(conclusions.add_run('Conclusiones y recomendaciones'),bold=True)
body_before(bibliography,
    'Se implementó y verificó el objetivo específico de procesamiento de señales '
    'sobre trayectorias de referencia: extracción de posiciones, remuestreo, '
    'filtrado FIR, cálculo de movimiento y análisis frecuencial. La ejecución '
    'completa del notebook y las cinco pruebas numéricas respaldan el funcionamiento '
    'computacional de este módulo. Los objetivos de detección, seguimiento '
    'automático y clasificación permanecen parcialmente desarrollados o pendientes; '
    'no se considera alcanzado todavía el objetivo general del sistema completo.',
    bold_prefix='Conclusión sobre los objetivos.')
body_before(bibliography,
    'En el intervalo común del pez 66, el FIR de cinco muestras cambió la rapidez '
    'media de 106.9604 a 92.7752 px/s y la máxima de 678.4244 a 445.3956 px/s. '
    'Estos resultados evidencian el efecto del suavizado. No prueban mayor exactitud '
    'ni una clasificación de actividad. La FFT describe componentes de las posiciones '
    'anotadas y remuestreadas, sin demostrar periodicidad biológica.',
    bold_prefix='Conclusión sobre los resultados.')
body_before(bibliography,
    'Se recomienda investigar las irregularidades temporales y el desfase de OBSEA '
    'antes de usar esas observaciones como referencia temporal fiable. También '
    'debe ejecutarse el notebook en Google Colab, conservar sus salidas e integrar '
    'un detector y un seguidor evaluados contra anotaciones reservadas. Los umbrales '
    'de tamaño aparente y actividad deberán justificarse y validarse de manera '
    'independiente. Antes de transferir el sistema a criaderos se requiere '
    'comprobarlo con datos del entorno y, para unidades físicas, calibrar la cámara.',
    bold_prefix='Recomendaciones para la siguiente etapa.')

# Referencias en orden alfabético y con sangría francesa, conforme a APA 7.
replace(bibliography,'Referencias')
bibliography.paragraph_format.page_break_before=True
reference_starts=['Liu et al. (2023) es una revisión','Xiao et al. (2026) es un artículo',
                  'Liu, H.,','Xiao, F.,']
for prefix in reference_starts:
    p=find(prefix);p._p.getparent().remove(p._p)
dataset_authors = (
    'González-Villà, S., Burns Font, D., Aguzzi, J., Bahamon, N., Baños Castelló, P., '
    'Batet Xaus, G., Berry, A., Campos, R., Carandell Widmer, M., Català Gonell, A., '
    'Chatzevangelou, D., Clavel-Henry, M., Conversano, F., Conway, A., Danovaro, R., '
    'del Rio, J., Dell’Anno, A., Francescangeli, M., Gallegati, S., … Toma, D. M. (2026). ')
references=[
    [(dataset_authors,False),('DIGI4ECO underwater fish tracking dataset',True),
     (' [Conjunto de datos]. Zenodo. https://doi.org/10.5281/zenodo.20701225',False)],
    [('Liu, H., Ma, X., Yu, Y., Wang, L., & Hao, L. (2023). Application of deep '
      'learning-based object detection techniques in fish aquaculture: A review. ',False),
     ('Journal of Marine Science and Engineering, 11',True),
     ('(4), Article 867. https://doi.org/10.3390/jmse11040867',False)],
    [('Xiao, F., Han, P., Zhang, H., Ding, J., Gansel, L. C., & Cao, Y. (2026). '
      'Quantifying fish behavior in aquaculture using visual open-world tracking models. ',False),
     ('Applied Ocean Research, 171',True),
     (', Article 105076. https://doi.org/10.1016/j.apor.2026.105076',False)],
]
for parts in references:
    p=doc.add_paragraph()
    p.paragraph_format.line_spacing=2
    p.paragraph_format.left_indent=Inches(.5)
    p.paragraph_format.first_line_indent=Inches(-.5)
    p.paragraph_format.space_after=Pt(8)
    for value,italic in parts:font(p.add_run(value),italic=italic)

annex=doc.add_paragraph()
annex.alignment=WD_ALIGN_PARAGRAPH.CENTER
annex.paragraph_format.page_break_before=True
annex.paragraph_format.keep_with_next=True
font(annex.add_run('Anexos'),bold=True)
anchor=doc.add_paragraph()
body_before(anchor,'Se consignan los parámetros y los archivos que permiten '
    'repetir el experimento. Las figuras 1 a 4 y las tablas 5 y 6 del cuerpo '
    'principal contienen las evidencias gráficas y numéricas del avance.',
    bold_prefix='Anexo A Parámetros reproducibles.')
table_before(anchor,['Parámetro','Valor utilizado'],[
    ['Secuencia e identificador','Ancona, ID 66 de referencia CVAT'],
    ['Tramo de entrada','Fotogramas 0 a 1199, 1200 posiciones'],
    ['Tratamiento de ausencias','Tramos continuos; outside=1 excluido'],
    ['Remuestreo','Interpolación lineal a 20 Hz; 1198 posiciones'],
    ['FIR','5 coeficientes de 0.2, convolución valid'],
    ['Retardo y comparación','2 muestras, 0.10 s; compensación offline'],
    ['Ventana común','1194 posiciones; 59.65 s'],
    ['DFT por FFT','rfft; detrend lineal; ventana Hann'],
    ['Frecuencia de bins y Nyquist','0.0167504 Hz y 10 Hz, respectivamente'],
    ['Entorno validado','Python 3.12.14; NumPy 2.5.4; OpenCV 5.0.0; macOS ARM64'],
], [2.2,3.9])
body_before(anchor,
    'El paquete incluye el notebook ejecutado, código, pruebas, dependencias y '
    'el par original de Ancona. results/avance_56 contiene CSV, gráficos y '
    'analysis_summary.json con parámetros, versiones y hashes. El README '
    'original documenta procedencia y licencia; LEEME_ENTREGA.md explica la ejecución.',
    bold_prefix='Anexo B Evidencias y procedencia.')
p=body_before(anchor,
    'Los archivos de entrada se conservan sin modificaciones. Las siguientes '
    'huellas permiten verificar que se utilizan exactamente los mismos datos:',
    bold_prefix='Anexo C Identificación de entradas.')
p.paragraph_format.keep_with_next=True
for name in ['video.mp4','annotations.xml']:
    p=body_before(anchor,name+'\n'+report['inputs'][name]['sha256'])
    p.paragraph_format.first_line_indent=Inches(0)
    p.paragraph_format.line_spacing=1.2
    p.paragraph_format.keep_with_next=(name=='video.mp4')
    for run in p.runs:
        run.font.name='Courier New';run.font.size=Pt(10)

# Sustituir el índice previo desbordado por un índice explícito de esta versión.
sdt=doc._element.body.find(qn('w:sdt'))
if sdt is None:raise ValueError('No se encontró el índice de referencia')
position=list(doc._element.body).index(sdt)
doc._element.body.remove(sdt)
toc_items=[
    ('Introducción','Introducción'),('Resumen','Resumen'),
    ('Descripción del caso de estudio y problemática','Descripción del caso de estudio y problemática'),
    ('Objetivos','Objetivos'),('Desarrollo','Desarrollo'),
    ('5.1 Requerimientos y fuente de las señales','Requerimientos y fuente de las señales'),
    ('5.2 Fundamento técnico','Fundamento técnico'),
    ('5.3 Adquisición carga y digitalización','Adquisición carga y digitalización'),
    ('5.4 Análisis de señales','Análisis de señales'),
    ('5.5 Procesamiento y filtrado digital','Procesamiento y filtrado digital'),
    ('5.6 Implementación computacional','Implementación computacional'),
    ('5.7 Pruebas métricas y resultados','Pruebas métricas y resultados'),
    ('5.8 Limitaciones y posibilidades de mejora','Limitaciones y posibilidades de mejora'),
    ('Conclusiones y recomendaciones','Conclusiones y recomendaciones'),
    ('Referencias','Referencias'),('Anexos','Anexos'),
]
parser=argparse.ArgumentParser()
parser.add_argument('--toc-map',type=Path)
args=parser.parse_args()
pages=json.loads(args.toc_map.read_text()) if args.toc_map else {}
for offset,(label,key) in enumerate(toc_items):
    p=doc.add_paragraph()
    p.paragraph_format.line_spacing=1.3
    p.paragraph_format.space_after=Pt(6)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.05), WD_TAB_ALIGNMENT.RIGHT)
    font(p.add_run(label))
    font(p.add_run('\t'+str(pages.get(key,0))))
    doc._element.body.insert(position+offset,p._p)

# Numeración visible para consultar el índice de esta versión.
for section in doc.sections:
    footer=section.footer.paragraphs[0]
    footer.clear()
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=footer.add_run()
    font(r,size=10)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE')
    r._r.addnext(field)

doc.save(OUTPUT)
# Los medios originales se mantienen byte por byte.
with ZipFile(SOURCE) as old, ZipFile(OUTPUT) as new:
    for name in old.namelist():
        if name.startswith('word/media/'):
            assert old.read(name)==new.read(name),name
print(OUTPUT)
