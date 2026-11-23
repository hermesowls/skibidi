"""Assemble the real-response mounted regression fixture; no business mocks.

Usage: python -I -B tests/step4_assemble_mark_fixture.py API_LOG OUTPUT_CJS
Run OUTPUT_CJS with the inspected installed-Node sandbox runner, not live HTTP.
"""
import json
import sys
from pathlib import Path


def assemble(log, output):
    root = Path(__file__).resolve().parents[1]
    payload = next(line.split('MARK_API_SNAPSHOTS ', 1)[1]
                   for line in log.read_text().splitlines()
                   if line.startswith('MARK_API_SNAPSHOTS '))
    snapshots, end = json.JSONDecoder().raw_decode(payload)
    # unittest stderr can append its test result to the stdout JSON line.
    if payload[end:].strip() not in ('', 'ok'):
        raise ValueError('Unexpected trailing API log content')
    prelude = (root / 'tests/step4_temporal_render.cjs').read_text().split('async function run(){', 1)[0]
    cases = (root / 'tests/step4_mark_cases.cjs').read_text()
    output.write_text(prelude + 'const snapshots=' + json.dumps(snapshots) + ';\n' + cases)
    print('Assembled actual API snapshots -> mounted component: ' + str(output))


if __name__ == '__main__':
    assemble(Path(sys.argv[1]), Path(sys.argv[2]))
