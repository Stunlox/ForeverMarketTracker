"""Windows Task Scheduler support. No administrator privileges required for current user."""
import csv, io, os, subprocess, sys
from pathlib import Path
TASK_NAME='ForeverMarketTrackerHourly'

def _run_schtasks(args, timeout=30):
    # Windows console tools must not create a flashing command window.
    kwargs = {'capture_output': True, 'text': True, 'timeout': timeout}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(['schtasks', *args], **kwargs)


def collector_executable():
    # Portable release layout: sibling ForeverMarketCollector folder.
    return (Path(sys.executable).resolve().parent.parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent) / 'ForeverMarketCollector' / 'ForeverMarketCollector.exe'

def task_command():
    exe=collector_executable()
    if not exe.exists():raise FileNotFoundError(f'Collector executable not found: {exe}. Run the packaged Windows release, not source mode.')
    return str(exe)

def enable_task():
    if os.name!='nt':raise RuntimeError('Windows Task Scheduler is only available on Windows')
    exe=task_command()
    result=_run_schtasks(['/Create','/TN',TASK_NAME,'/TR',f'"{exe}"','/SC','HOURLY','/MO','1','/ST','00:05','/F'])
    if result.returncode:raise RuntimeError((result.stderr or result.stdout).strip())

def disable_task():
    if os.name!='nt':raise RuntimeError('Windows Task Scheduler is only available on Windows')
    result=_run_schtasks(['/Delete','/TN',TASK_NAME,'/F'])
    if result.returncode:raise RuntimeError((result.stderr or result.stdout).strip())

def task_status():
    """Report actual scheduler state, not merely whether a task exists."""
    if os.name != 'nt':
        return {'enabled': False, 'next': 'Unavailable outside Windows', 'state': 'unknown', 'detail': 'Windows only'}
    try:
        result = _run_schtasks(['/Query', '/TN', TASK_NAME, '/FO', 'CSV', '/V'], timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'enabled': False, 'next': 'Unknown', 'state': 'unknown', 'detail': str(exc)}
    if result.returncode:
        output = (result.stderr or result.stdout or '').strip()
        missing = any(word in output.lower() for word in ('cannot find', 'does not exist', 'not found'))
        return {'enabled': False, 'next': 'Not scheduled' if missing else 'Unknown',
                'state': 'missing' if missing else 'unknown', 'detail': output}
    try:
        row = next(csv.DictReader(io.StringIO(result.stdout)))
        fields = {k.strip().lower(): str(v).strip() for k, v in row.items() if k}
        next_run = fields.get('next run time', 'Unknown')
        status = fields.get('status', '').lower()
        schedule_state = fields.get('scheduled task state', '').lower()
        disabled = 'disabled' in status or 'disabled' in schedule_state
        command = fields.get('task to run', '')
        expected = str(collector_executable())
        wrong_path = bool(command and expected.lower() not in command.lower())
        if disabled:
            state = 'disabled'
        elif wrong_path:
            state = 'misconfigured'
        elif not command:
            state = 'unknown'
        else:
            state = 'enabled'
        return {'enabled': state == 'enabled', 'next': next_run, 'state': state,
                'detail': ('Collector executable path differs from this release' if wrong_path else status or schedule_state or 'No status supplied')}
    except (StopIteration, ValueError, csv.Error) as exc:
        return {'enabled': False, 'next': 'Unknown', 'state': 'unknown', 'detail': str(exc)}
