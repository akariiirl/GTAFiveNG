"""Run only source tests and emit a small CI result manifest."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time
import unittest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.discover(str(root/'tests'))
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'seconds':time.monotonic()-started,'python':platform.python_version(),
        'platform':platform.system(),'successful':result.wasSuccessful(),'evidence':'source-only synthetic tests'},indent=2))
    sys.exit(0 if result.wasSuccessful() else 1)
