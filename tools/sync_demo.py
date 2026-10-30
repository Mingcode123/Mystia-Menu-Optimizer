"""Synchronize the local-file browser bundles with the published JSON data."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
bundles = (
    ('demo', 'synthetic', 'MYSTIA_DEMO_DATA'),
    ('game', 'game-data', 'MYSTIA_GAME_DATA'),
)
outputs = []
for name, kind, variable in bundles:
    data = json.loads((root / f'data/{name}.json').read_text(encoding='utf-8'))
    if data.get('format') != 'mystia-planner-data/v1':
        raise SystemExit(f'data/{name}.json must use mystia-planner-data/v1.')
    if data.get('metadata', {}).get('kind') != kind:
        raise SystemExit(f'data/{name}.json must declare metadata.kind={kind!r}.')
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    outputs.append((name, f'// Generated from data/{name}.json by tools/sync_demo.py.\n'
                    f'window.{variable} = {payload};\n'))

# Validate both inputs before replacing either generated browser bundle.
for name, script in outputs:
    (root / f'web/{name}-data.js').write_text(script, encoding='utf-8')
