"""Compare to a git base; allow only documented corrections for one exact old spec."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

from validate import ROOT, load_contract, walk, METHODS

BASELINE_SHA256 = '1e6e3d6bf4911fa17e93f70b01cc5e0d9d0f56ddc19b75a1d6a0634f43e3a727'


def check(base_ref):
    raw = subprocess.check_output(['git', 'show', f'{base_ref}:openapi.yaml'], cwd=ROOT)
    digest = hashlib.sha256(raw).hexdigest()
    with tempfile.TemporaryDirectory(prefix='sully-oasdiff-') as temp:
        base = Path(temp) / 'base.yaml'
        base.write_bytes(raw)
        before = load_contract(base)
        # The pre-SDK spec used a map for JSON Schema examples and the OAS 3.0
        # nullable keyword. Normalize only that exact historical document.
        if digest == BASELINE_SHA256:
            for node in walk(before):
                if isinstance(node.get('examples'), dict) and 'type' in node:
                    node['examples'] = list(node['examples'].values())
                if node.pop('nullable', False):
                    node['type'] = [node['type'], 'null']
            base.write_text(yaml.safe_dump(before, sort_keys=False))
        result = subprocess.run(
            [os.environ.get('OASDIFF_BIN', 'oasdiff'), 'breaking', str(base), str(ROOT / 'openapi.yaml'), '--format', 'json', '--allow-external-refs=false'],
            capture_output=True, text=True,
        )
    if result.returncode:
        sys.stderr.write(result.stderr)
        result.check_returncode()
    findings = json.loads(result.stdout) or []
    manifest = json.loads((ROOT / 'compatibility/0.3.0.json').read_text())
    allowed = set(manifest['fingerprints']) if digest == manifest['baseSpecSha256'] else set()
    unexpected = [item for item in findings if item['fingerprint'] not in allowed]
    after = load_contract()
    if allowed:
        assert after['info']['version'] == manifest['version'], 'Correction manifest requires its documented contract version'
    # HTTP diffs cannot detect SDK method renames: compare IDs explicitly.
    for path, item in before['paths'].items():
        for method, operation in item.items():
            if method in METHODS and method in after['paths'].get(path, {}):
                assert operation['operationId'] == after['paths'][path][method]['operationId'], f'operationId changed: {method} {path}'
    output = ROOT / '.sdk-smoke'
    output.mkdir(exist_ok=True)
    (output / 'breaking.json').write_text(json.dumps(findings, indent=2) + '\n')
    for item in findings:
        label = 'documented correction' if item['fingerprint'] in allowed else 'UNEXPECTED'
        print(f"{label}: {item['operation']} {item['path']}: {item['text']}")
    print(f'{len(findings)} findings; {len(unexpected)} undocumented breaking changes')
    return bool(unexpected)


if __name__ == '__main__':
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else 'origin/main'))
