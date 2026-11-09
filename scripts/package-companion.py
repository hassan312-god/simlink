"""Produce the downloadable source package from an explicit allowlist."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import shutil
root=Path(__file__).resolve().parent.parent
source=root/'companion'
out=root/'public'/'downloads'
out.mkdir(parents=True,exist_ok=True)
files=[source/'pyproject.toml',source/'README.md',source/'VALIDATION.md',source/'install.sh',source/'install.ps1',*sorted((source/'simlink').glob('*.py')),source/'simlink'/'dashboard.html',*sorted((source/'tests').glob('*.py'))]
archive=out/'simlink-local-0.2.0.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for file in files:
        z.write(file,Path('simlink-local-0.2.0')/file.relative_to(source))
shutil.copyfile(source/'README.md',out/'README-simlink.md')
(out/'simlink-local-0.2.0.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(f'{len(files)} files packaged, {archive.stat().st_size} bytes')
