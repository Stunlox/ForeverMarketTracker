import unittest
from unittest.mock import patch, Mock
import scheduler

class SchedulerStatusTests(unittest.TestCase):
    def query(self, state, command='C:\\Apps\\ForeverMarketCollector\\ForeverMarketCollector.exe'):
        output='"TaskName","Next Run Time","Status","Scheduled Task State","Task To Run"\n"\\\\ForeverMarketTrackerHourly","24/11/2026 00:05:00","'+state+'","'+state+'","'+command+'"\n'
        with patch.object(scheduler.os,'name','nt'), patch.object(scheduler,'collector_executable',return_value=command),patch.object(scheduler,'_run_schtasks',return_value=Mock(returncode=0,stdout=output)):
            return scheduler.task_status()
    def test_enabled(self): self.assertEqual(self.query('Ready')['state'],'enabled')
    def test_disabled(self): self.assertEqual(self.query('Disabled')['state'],'disabled')
    def test_missing(self):
        with patch.object(scheduler.os,'name','nt'),patch.object(scheduler,'_run_schtasks',return_value=Mock(returncode=1,stdout='',stderr='ERROR: The system cannot find the file specified.')):
            self.assertEqual(scheduler.task_status()['state'],'missing')
    def test_stale_executable(self):
        with patch.object(scheduler.os,'name','nt'),patch.object(scheduler,'collector_executable',return_value='C:\\New\\ForeverMarketCollector.exe'),patch.object(scheduler,'_run_schtasks',return_value=Mock(returncode=0,stdout='"Next Run Time","Status","Task To Run"\n"Tomorrow","Ready","C:\\Old\\ForeverMarketCollector.exe"\n')):
            self.assertEqual(scheduler.task_status()['state'],'misconfigured')
if __name__=='__main__':unittest.main()
