import asyncio
import os
import sys
import logging
import subprocess
from typing import Callable, Optional

from ..core.models.setup import SchedulerSetupRequest, SchedulerSetupResult

logger = logging.getLogger(__name__)

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tg-msg-manager.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>tg_msg_manager.cli</string>
        <string>update</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>{project_root}</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>{project_root}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{project_root}/LOGS/scheduler_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{project_root}/LOGS/scheduler_stderr.log</string>
</dict>
</plist>
"""


def _setup_scheduler_sync(
    request: SchedulerSetupRequest,
    *,
    project_root: Optional[str] = None,
    python_path: Optional[str] = None,
    home_dir: Optional[str] = None,
    subprocess_run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> SchedulerSetupResult:
    project_root = os.path.abspath(project_root or os.getcwd())
    python_path = python_path or sys.executable
    logs_dir = os.path.join(project_root, "LOGS")

    plist_content = PLIST_TEMPLATE.format(
        python_path=python_path,
        project_root=project_root,
        hour=request.hour,
        minute=request.minute,
    )

    home_dir = os.path.abspath(home_dir or os.path.expanduser("~"))
    plist_path = os.path.join(
        home_dir, "Library/LaunchAgents/com.tg-msg-manager.update.plist"
    )

    try:
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)

        # 1. Write plist
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # 2. Register with launchctl
        # Unload if exists first
        subprocess_run(["launchctl", "unload", plist_path], capture_output=True)
        result = subprocess_run(["launchctl", "load", plist_path], capture_output=True)

        if result.returncode == 0:
            return SchedulerSetupResult(
                success=True,
                plist_path=plist_path,
                logs_dir=logs_dir,
                hour=request.hour,
                minute=request.minute,
            )

        return SchedulerSetupResult(
            success=False,
            plist_path=plist_path,
            logs_dir=logs_dir,
            hour=request.hour,
            minute=request.minute,
            error_kind="launchctl_load_failed",
            error_detail=result.stderr.decode().strip(),
        )
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")
        return SchedulerSetupResult(
            success=False,
            plist_path=plist_path,
            logs_dir=logs_dir,
            hour=request.hour,
            minute=request.minute,
            error_kind="unexpected",
            error_detail=str(e),
        )


async def setup_scheduler(
    request: SchedulerSetupRequest,
    *,
    project_root: Optional[str] = None,
    python_path: Optional[str] = None,
    home_dir: Optional[str] = None,
    subprocess_run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> SchedulerSetupResult:
    """Registers the macOS launchd scheduler using a structured request."""
    return await asyncio.to_thread(
        _setup_scheduler_sync,
        request,
        project_root=project_root,
        python_path=python_path,
        home_dir=home_dir,
        subprocess_run=subprocess_run,
    )


async def remove_scheduler():
    """Removes the launchd task."""
    home_dir = os.path.expanduser("~")
    plist_path = os.path.join(
        home_dir, "Library/LaunchAgents/com.tg-msg-manager.update.plist"
    )

    if os.path.exists(plist_path):
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        os.remove(plist_path)
        print("✅ Scheduler removed.")
    else:
        print("Scheduler task not found.")
