"""Ejecutar el notebook con el intérprete activo y guardar todas sus salidas."""

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
temporary = Path(tempfile.mkdtemp(prefix='pds_56_jupyter_'))
os.environ['JUPYTER_PATH'] = str(temporary)
os.environ['IPYTHONDIR'] = str(temporary / 'ipython')
os.environ['JUPYTER_RUNTIME_DIR'] = str(temporary / 'runtime')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/pds_matplotlib')
kernel = temporary / 'kernels/pds-proyecto'
kernel.mkdir(parents=True)
(kernel / 'kernel.json').write_text(json.dumps({
    'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
    'display_name': 'PDS Proyecto', 'language': 'python',
}), encoding='utf-8')

import nbformat
from nbclient import NotebookClient

path = ROOT / 'notebooks/05_06_Implementacion_PDS.ipynb'
nb = nbformat.read(path, as_version=4)
client = NotebookClient(nb, timeout=180, kernel_name='pds-proyecto',
                        resources={'metadata': {'path': str(ROOT)}})
client.execute()
nb.metadata['pds_validation'] = {
    'environment': 'local', 'python': sys.version,
    'cloud_executed': False,
}
nbformat.validate(nb)
nbformat.write(nb, path)
print('Notebook completo ejecutado sin errores; salidas guardadas:', path)
print('Celdas de código:', sum(c.cell_type == 'code' for c in nb.cells))
