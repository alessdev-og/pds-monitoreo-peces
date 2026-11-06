"""Copy the reviewed static demo to the /docs tree used by GitHub Pages."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = root / 'demo-aleteo' / 'dist'
target = root / 'docs' / 'demo'
target.mkdir(parents=True, exist_ok=True)
assets = ('index.html', 'style.css', 'app.js', 'signal.js', 'tracker.js', 'tracking-fixture.mp4')
for name in assets:
    shutil.copyfile(source / name, target / name)
(root / 'docs' / '.nojekyll').write_text('')
(root / 'docs' / 'index.html').write_text('''<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="0;url=./demo/"><title>Aleta · Laboratorio de señales</title>
<p><a href="./demo/">Abrir Aleta · Laboratorio de señales</a></p></html>
''', encoding='utf-8')
print(f'Demo preparada: {target}')
