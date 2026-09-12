import unittest
from unittest.mock import patch
import subprocess
from linux_notifier import LinuxNotifier


class TestLinuxNotifier(unittest.TestCase):
    
    @patch('subprocess.run')
    def test_system_calls_mocked(self, mock_subprocess):
        notifier = LinuxNotifier()
        test_title = "Mock Test"
        test_msg = "Background subprocess calls are mocked for this test."
        
        notifier.send(test_title, test_msg)
        
        # critical check
        mock_subprocess.assert_any_call(
            ['notify-send', test_title, test_msg, '-u', 'critical', '-i', 'dialog-warning']
        )
        
        # paplay - sound path check
        mock_subprocess.assert_any_call(
            ['paplay', notifier.sound_path], stderr=subprocess.DEVNULL
        )

    def test_live_notification_fire(self):
        notifier = LinuxNotifier()
        try:
            notifier.send("🔔 System Test", "I works fine if you see & hear this")
        except Exception as e:
            self.fail(f"Live notification triggering failed with critical error: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=1)