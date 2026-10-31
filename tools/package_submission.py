"""Empaquetar código, resultados e insumos de Ancona sin modificar la descarga."""

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
DATA=Path.home()/'Downloads/DIGI4ECO_tracking_dataset'
OUTPUT=ROOT/'entregables/ENTREGA_AVANCE_2_PDS.zip'
PREFIX=Path('PDS_AVANCE_2')
files={}
for directory in ['src','tests','notebooks','docs','results/avance_56']:
    for path in (ROOT/directory).rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            files[str(path.relative_to(ROOT))]=path
for name in ['README.md','LEEME_ENTREGA.md','requirements.txt','requirements-notebook.txt',
             'requirements-lock.txt','tools/execute_notebook.py','tools/build_notebook.py',
             'tools/build_demo_video.py','results/demo/demo_pds_h264.mp4',
             'results/demo/demo_pds_h264.json','results/demo/demo_pds.jpg']:
    files[name]=ROOT/name
files['Avance_2_Equipo_2_PARA_ENTREGAR.docx']=ROOT/'entregables/Avance_2_Equipo_2_PARA_ENTREGAR.docx'
for name in ['Ancona/video.mp4','Ancona/annotations.xml','README.md']:
    files['data/DIGI4ECO_tracking_dataset/'+name]=DATA/name
for path in (DATA/'figures').glob('*.png'):
    files['data/DIGI4ECO_tracking_dataset/figures/'+path.name]=path
manifest={name:{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
          for name,path in files.items()}
with ZipFile(OUTPUT,'w',ZIP_DEFLATED) as archive:
    for name,path in sorted(files.items()):archive.write(path,PREFIX/name)
    archive.writestr(str(PREFIX/'manifest.json'),json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with ZipFile(OUTPUT) as archive:
    assert archive.testzip() is None
    for name,item in manifest.items():
        assert hashlib.sha256(archive.read(str(PREFIX/name))).hexdigest()==item['sha256'],name
print(OUTPUT)
print('Archivos:',len(manifest)+1,'Tamaño:',round(OUTPUT.stat().st_size/1024/1024,2),'MiB')
