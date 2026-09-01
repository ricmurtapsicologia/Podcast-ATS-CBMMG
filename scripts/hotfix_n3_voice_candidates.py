from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXTRA = [
    ('pt-BR-HumbertoNeural', 'M'),
    ('pt-BR-JulioNeural', 'M'),
    ('pt-BR-NicolauNeural', 'M'),
    ('pt-BR-ValerioNeural', 'M'),
    ('pt-BR-LeilaNeural', 'F'),
    ('pt-BR-ManuelaNeural', 'F'),
    ('pt-BR-YaraNeural', 'F'),
]

for rel in ('scripts/remaster_series1_n3.py', 'scripts/remaster_series2_n3.py'):
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    if 'pt-BR-HumbertoNeural' in text:
        continue
    marker = '    ("pt-BR-GiovannaNeural", "F"),\n]'
    insertion = ''.join(f'    ("{voice}", "{gender}"),\n' for voice, gender in EXTRA)
    if marker not in text:
        raise RuntimeError(f'Lista VOICE_CANDIDATES não localizada em {rel}')
    text = text.replace(marker, '    ("pt-BR-GiovannaNeural", "F"),\n' + insertion + ']', 1)
    path.write_text(text, encoding='utf-8')
    print(f'Atualizado: {rel}')
