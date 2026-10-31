"""Completar sólo el espacio 5.6; preservar las demás partes del DOCX original."""

from copy import deepcopy
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / 'Downloads/Avance 2 - Equipo 2 - PDS.docx'
OUTPUT = ROOT / 'entregables/Avance_2_Equipo_2_con_5_6.docx'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
XML = '{http://www.w3.org/XML/1998/namespace}'

with ZipFile(SOURCE) as archive:
    document = ET.fromstring(archive.read('word/document.xml'))
    body = document.find('w:body', NS)
    heading = next(p for p in body.findall('w:p', NS)
                   if ''.join(p.itertext()).startswith('Implementación computacional:'))
    following = heading.getnext()
    if ''.join(following.itertext()).strip():
        raise ValueError('El espacio siguiente al encabezado no está vacío')
    # El párrafo de prosa anterior define Times New Roman 12 y doble espacio.
    body_pattern = heading.getprevious()
    insert_index = list(body).index(following)
    body.remove(following)
    paragraphs = (ROOT / 'docs/seccion_5_6.md').read_text(encoding='utf-8').strip().split('\n\n')[1:]
    for offset, text in enumerate(paragraphs):
        p = ET.Element(W+'p')
        ppr = deepcopy(body_pattern.find('w:pPr', NS))
        # Mantener tipografía, sangría e interlineado de la prosa original.
        for tag in ['numPr', 'pageBreakBefore', 'keepNext']:
            for child in ppr.findall('w:'+tag, NS): ppr.remove(child)
        spacing = ppr.find('w:spacing', NS)
        if spacing is not None:
            spacing.set(W+'before', '0')
            spacing.set(W+'after', '120')
        p.append(ppr)
        for fragment in re.split(r'(\*\*.*?\*\*)', text):
            if not fragment: continue
            r = ET.SubElement(p, W+'r')
            rpr = ET.SubElement(r, W+'rPr')
            fonts = ET.SubElement(rpr, W+'rFonts')
            for attr in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
                fonts.set(W+attr, 'Times New Roman')
            ET.SubElement(rpr, W+'sz').set(W+'val', '24')
            ET.SubElement(rpr, W+'color').set(W+'val', '000000')
            if fragment.startswith('**'):
                ET.SubElement(rpr, W+'b')
                fragment = fragment[2:-2]
            t = ET.SubElement(r, W+'t')
            t.set(XML+'space', 'preserve')
            t.text = fragment
        body.insert(insert_index+offset, p)
    # Mantener el encabezado con la primera línea de su contenido.
    heading.find('w:pPr', NS).append(ET.Element(W+'keepNext'))
    payload = ET.tostring(document, xml_declaration=True, encoding='UTF-8', standalone=True)
    with ZipFile(OUTPUT, 'w') as out:
        for item in archive.infolist():
            out.writestr(item, payload if item.filename == 'word/document.xml' else archive.read(item.filename))

with ZipFile(SOURCE) as original, ZipFile(OUTPUT) as final:
    assert original.namelist() == final.namelist()
    changed = [n for n in original.namelist() if original.read(n) != final.read(n)]
    assert changed == ['word/document.xml'], changed
print(OUTPUT)
print('Única parte modificada:', changed)
