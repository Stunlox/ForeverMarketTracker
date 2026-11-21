import unittest
from unittest.mock import patch
import scheduler

class SchedulerBehaviorTests(unittest.TestCase):
    def test_schtasks_wrapper_uses_no_console_on_windows(self):
        with patch.object(scheduler.os, 'name', 'nt'), patch.object(scheduler.subprocess, 'CREATE_NO_WINDOW', 0x08000000, create=True), patch.object(scheduler.subprocess, 'run') as run:
            scheduler._run_schtasks(['/Query','/TN','x'])
            self.assertEqual(run.call_args.kwargs['creationflags'], scheduler.subprocess.CREATE_NO_WINDOW)
    def test_schtasks_wrapper_without_windows_flag(self):
        with patch.object(scheduler.os, 'name', 'posix'), patch.object(scheduler.subprocess, 'run') as run:
            scheduler._run_schtasks(['/Query'])
            self.assertNotIn('creationflags',run.call_args.kwargs)

if __name__=='__main__': unittest.main()
