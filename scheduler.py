"""Windows Task Scheduler support. No administrator privileges required for current user."""
import csv, io, os, subprocess, sys
from pathlib import Path
TASK_NAME='ForeverMarketTrackerHourly'

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
    result=subprocess.run(['schtasks','/Create','/TN',TASK_NAME,'/TR',f'"{exe}"','/SC','HOURLY','/MO','1','/ST','00:05','/F'],capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError((result.stderr or result.stdout).strip())

def disable_task():
    if os.name!='nt':raise RuntimeError('Windows Task Scheduler is only available on Windows')
    result=subprocess.run(['schtasks','/Delete','/TN',TASK_NAME,'/F'],capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError((result.stderr or result.stdout).strip())

def task_status():
    if os.name!='nt':return {'enabled':False,'next':'Not available outside Windows'}
    result=subprocess.run(['schtasks','/Query','/TN',TASK_NAME,'/FO','CSV','/V'],capture_output=True,text=True,timeout=20)
    if result.returncode:return {'enabled':False,'next':'Not scheduled'}
    try:
        row=next(csv.DictReader(io.StringIO(result.stdout)))
        next_run=next((v for k,v in row.items() if k.strip().lower()=='next run time'),'Unknown')
        return {'enabled':True,'next':next_run}
    except (StopIteration,ValueError):return {'enabled':True,'next':'See Windows Task Scheduler'}
