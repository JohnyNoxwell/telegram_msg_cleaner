import os
import sys
import logging
import subprocess
from datetime import datetime

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

async def setup_scheduler():
    """
    Interactive setup for macOS launchd scheduler.
    """
    print("\n--- Setup Background Scheduler (macOS launchd) ---")
    
    project_root = os.getcwd()
    python_path = sys.executable
    
    # Defaults
    hour = 5
    minute = 0
    
    try:
        hour_in = input(f"Enter hour for daily sync [0-23] (default {hour}): ").strip()
        if hour_in: hour = int(hour_in)
        
        min_in = input(f"Enter minute [0-59] (default {minute}): ").strip()
        if min_in: minute = int(min_in)
    except ValueError:
        print("Invalid input, using defaults.")

    plist_content = PLIST_TEMPLATE.format(
        python_path=python_path,
        project_root=project_root,
        hour=hour,
        minute=minute
    )

    home_dir = os.path.expanduser("~")
    plist_path = os.path.join(home_dir, "Library/LaunchAgents/com.tg-msg-manager.update.plist")
    
    try:
        # 1. Write plist
        with open(plist_path, "w") as f:
            f.write(plist_content)
        
        # 2. Ensure LOGS dir exists
        os.makedirs(os.path.join(project_root, "LOGS"), exist_ok=True)
        
        # 3. Register with launchctl
        # Unload if exists first
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        result = subprocess.run(["launchctl", "load", plist_path], capture_output=True)
        
        if result.returncode == 0:
            print(f"\n✅ Scheduler successfully registered!")
            print(f"Task will run daily at {hour:02d}:{minute:02d}")
            print(f"Logs: {project_root}/LOGS/scheduler_*.log")
        else:
            print(f"\n❌ Error registering task: {result.stderr.decode()}")
            
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")
        print(f"\n❌ Unexpected error: {e}")

async def remove_scheduler():
    """Removes the launchd task."""
    home_dir = os.path.expanduser("~")
    plist_path = os.path.join(home_dir, "Library/LaunchAgents/com.tg-msg-manager.update.plist")
    
    if os.path.exists(plist_path):
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        os.remove(plist_path)
        print("✅ Scheduler removed.")
    else:
        print("Scheduler task not found.")
