import os
import subprocess
import sys
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tg_msg_manager.core.models.setup import SchedulerSetupRequest
from tg_msg_manager.services.scheduler import setup_scheduler


class TestScheduler(unittest.IsolatedAsyncioTestCase):
    async def test_setup_scheduler_returns_success_result_and_writes_plist(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, b"", b"")

        with (
            tempfile.TemporaryDirectory() as project_root,
            tempfile.TemporaryDirectory() as home_dir,
        ):
            result = await setup_scheduler(
                SchedulerSetupRequest(hour=7, minute=30),
                project_root=project_root,
                python_path="/usr/bin/python3",
                home_dir=home_dir,
                subprocess_run=fake_run,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.hour, 7)
            self.assertEqual(result.minute, 30)
            self.assertTrue(os.path.exists(result.plist_path))
            self.assertTrue(os.path.isdir(result.logs_dir))
            self.assertEqual(calls[0][0][:2], ["launchctl", "unload"])
            self.assertEqual(calls[1][0][:2], ["launchctl", "load"])

            with open(result.plist_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("/usr/bin/python3", content)
            self.assertIn(project_root, content)
            self.assertIn("<integer>7</integer>", content)
            self.assertIn("<integer>30</integer>", content)

    async def test_setup_scheduler_returns_launchctl_error_result(self):
        def fake_run(args, **kwargs):
            if args[1] == "load":
                return subprocess.CompletedProcess(args, 1, b"", b"boom")
            return subprocess.CompletedProcess(args, 0, b"", b"")

        with (
            tempfile.TemporaryDirectory() as project_root,
            tempfile.TemporaryDirectory() as home_dir,
        ):
            result = await setup_scheduler(
                SchedulerSetupRequest(hour=5, minute=0),
                project_root=project_root,
                python_path="/usr/bin/python3",
                home_dir=home_dir,
                subprocess_run=fake_run,
            )

            self.assertFalse(result.success)
            self.assertEqual(result.error_kind, "launchctl_load_failed")
            self.assertEqual(result.error_detail, "boom")

    def test_scheduler_setup_request_validates_hour_and_minute_ranges(self):
        with self.assertRaises(ValueError):
            SchedulerSetupRequest(hour=24, minute=0)
        with self.assertRaises(ValueError):
            SchedulerSetupRequest(hour=5, minute=60)


if __name__ == "__main__":
    unittest.main()
