import os
import sys
import platform
import logging
from typing import Dict, List, Optional
from ..i18n import _

logger = logging.getLogger(__name__)

class AliasManager:
    """
    Handles automatic installation of terminal aliases across different platforms.
    """
    
    ALIASES = {
        "tg": "tg-msg-manager",
        "tgr": "tg-msg-manager clean --dry-run",
        "tgd": "tg-msg-manager clean --apply",
        "tgpm": "tg-msg-manager export-pm",
        "tge": "tg-msg-manager export",
        "tgu": "tg-msg-manager update"
    }

    def __init__(self):
        self.os_type = platform.system()
        self.home_dir = os.path.expanduser("~")

    def install(self) -> Dict[str, str]:
        """
        Detects platform and performs installation.
        Returns a dict with status information.
        """
        if self.os_type == "Windows":
            return self._install_windows()
        elif self.os_type in ("Linux", "Darwin"): # Darwin is macOS
            return self._install_unix()
        else:
            return {"error": _("setup_platform_error", plt=self.os_type)}

    def _install_unix(self) -> Dict[str, str]:
        """Adds aliases to .zshrc or .bashrc based on user template."""
        shell = os.environ.get("SHELL", "")
        rc_file = ".zshrc" if "zsh" in shell else ".bashrc"
        rc_path = os.path.join(self.home_dir, rc_file)
        
        # Dynamically determine project root relative to this file
        # This file is in tg_msg_manager/services/alias_manager.py
        current_file_path = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
        
        python_exe = "./.venv-test/bin/python3"
        
        # User's proven template
        template = 'alias {alias}=\'cd "{root}" && {py} -m tg_msg_manager.cli {cmd}\''
        
        commands = {
            "tg": "",
            "tgr": "clean --dry-run --yes",
            "tgd": "clean --apply --yes",
            "tge": "export --deep --json --user-id",
            "tgu": "update",
            "tgpm": "export-pm --user-id"
        }

        marker_start = "# >>> tg-msg-manager aliases >>>"
        marker_end = "# <<< tg-msg-manager aliases <<<"
        
        lines_to_add = [f"\n{marker_start}\n"]
        for alias, cmd in commands.items():
            line = template.format(alias=alias, root=project_root, py=python_exe, cmd=cmd).strip()
            lines_to_add.append(f"{line}\n")
        lines_to_add.append(f"{marker_end}\n")

        content = ""
        if os.path.exists(rc_path):
            with open(rc_path, "r") as f:
                content = f.read()

        if marker_start in content:
            start_idx = content.find(marker_start)
            end_idx = content.find(marker_end)
            if end_idx != -1:
                content = content[:start_idx] + content[end_idx + len(marker_end):]
                content = content.strip() + "\n"

        with open(rc_path, "a" if content.endswith("\n") else "w") as f:
            if not content.endswith("\n") and content:
                f.write("\n")
            f.writelines(lines_to_add)

        return {
            "success": True,
            "path": rc_path,
            "message": _("setup_success_unix", path=rc_path),
            "activate_cmd": _("setup_activate", path=rc_path)
        }

    def _install_windows(self) -> Dict[str, str]:
        """Creates .bat files in a dedicated bin directory."""
        bin_dir = os.path.join(self.home_dir, "tg_msg_bin")
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)

        for alias, cmd in self.ALIASES.items():
            bat_path = os.path.join(bin_dir, f"{alias}.bat")
            with open(bat_path, "w") as f:
                f.write(f"@echo off\n{cmd} %*\n")

        return {
            "success": True,
            "dir": bin_dir,
            "message": _("setup_success_win", dir=bin_dir)
        }

    def get_alias_help(self) -> List[str]:
        """Returns localized descriptions of available aliases."""
        return [
            _("alias_header"),
            f"  tg   -> { _('alias_tg') }",
            f"  tgd  -> { _('alias_tgd') }",
            f"  tgr  -> { _('alias_tgr') }",
            f"  tgu  -> { _('alias_tgu') }",
            f"  tge  -> { _('alias_tge') }",
            f"  tgpm -> { _('alias_tgpm') }",
        ]
