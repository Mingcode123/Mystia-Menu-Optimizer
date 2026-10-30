"""Synchronize the local-file browser fixture with the canonical JSON sample."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'data/demo.json').read_text(encoding='utf-8'))
if data.get('metadata', {}).get('kind') != 'synthetic':
    raise SystemExit('Only synthetic demonstration data may be bundled.')
payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
(root / 'web/demo-data.js').write_text('// Generated from data/demo.json by tools/sync_demo.py.\nwindow.MYSTIA_DEMO_DATA = ' + payload + ';\n', encoding='utf-8')
