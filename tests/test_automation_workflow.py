import os
import subprocess
import textwrap
from pathlib import Path

import pytest


@pytest.mark.parametrize('event,schedule,operation,expected', [
    ('schedule', '50,55 11 * * *', '', 'prepare'),
    ('schedule', '10,15,30,35 12 * * *', '', 'prepare'),
    ('schedule', '0,20,40 12 * * *', '', 'run'),
    ('workflow_dispatch', '', 'prepare', 'prepare'),
    ('workflow_dispatch', '', 'run', 'run'),
])
def test_workflow_routes_preparation_without_retrying_sends(tmp_path, event, schedule, operation, expected):
    workflow = Path(__file__).resolve().parents[1] / '.github/workflows/automation.yml'
    shell = textwrap.dedent(workflow.read_text().split('        run: |\n', 1)[1])
    capture = tmp_path / 'args.txt'
    curl = tmp_path / 'curl'
    curl.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CAPTURE_PATH"\n')
    curl.chmod(0o700)
    env = {**os.environ, 'PATH': str(tmp_path) + os.pathsep + os.environ['PATH'],
           'CAPTURE_PATH': str(capture), 'CRM_BASE_URL': 'https://crm.example.test',
           'CRM_WORKER_TOKEN': 'fake-test-only', 'EVENT_NAME': event,
           'EVENT_SCHEDULE': schedule, 'MANUAL_OPERATION': operation}
    result = subprocess.run(['bash', '-c', shell], env=env, capture_output=True)
    assert result.returncode == 0
    args = capture.read_text().splitlines()
    assert args[-1] == 'https://crm.example.test/api/automation/' + expected
    assert ('--retry' in args) == (expected == 'prepare')
