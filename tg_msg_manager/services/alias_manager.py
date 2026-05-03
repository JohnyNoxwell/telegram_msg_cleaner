import os
import platform
import sys
import shlex
import logging
from typing import List, Optional
from ..core.models.setup import AliasHelpEntry, AliasInstallResult

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
        "tgu": "tg-msg-manager update",
    }
    ALIAS_HELP = (
        AliasHelpEntry("tg", "alias_tg"),
        AliasHelpEntry("tgd", "alias_tgd"),
        AliasHelpEntry("tgr", "alias_tgr"),
        AliasHelpEntry("tgu", "alias_tgu"),
        AliasHelpEntry("tge", "alias_tge"),
        AliasHelpEntry("tgpm", "alias_tgpm"),
    )

    def __init__(
        self,
        *,
        project_root: Optional[str] = None,
        python_executable: Optional[str] = None,
    ):
        self.os_type = platform.system()
        self.home_dir = os.path.expanduser("~")
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.python_executable = python_executable or sys.executable

    def install(self) -> AliasInstallResult:
        """
        Detects platform and performs installation.
        Returns a structured installation result for CLI rendering.
        """
        if self.os_type == "Windows":
            return self._install_windows()
        elif self.os_type in ("Linux", "Darwin"):  # Darwin is macOS
            return self._install_unix()
        else:
            return AliasInstallResult(
                success=False,
                platform=self.os_type,
                error_kind="unsupported_platform",
            )

    def _install_unix(self) -> AliasInstallResult:
        """Adds aliases to .zshrc or .bashrc based on user template."""
        shell = os.environ.get("SHELL", "")
        rc_file = ".zshrc" if "zsh" in shell else ".bashrc"
        rc_path = os.path.join(self.home_dir, rc_file)

        template = 'alias {alias}="cd {root} && {py} -m tg_msg_manager.cli {cmd}"'

        commands = {
            "tg": "",
            "tgr": "clean --dry-run --yes",
            "tgd": "clean --apply --yes",
            "tge": "export --deep --json --user-id",
            "tgu": "update",
            "tgpm": "export-pm --user-id",
        }

        marker_start = "# >>> tg-msg-manager aliases >>>"
        marker_end = "# <<< tg-msg-manager aliases <<<"

        lines_to_add = [f"\n{marker_start}\n"]
        for alias, cmd in commands.items():
            line = template.format(
                alias=alias,
                root=shlex.quote(self.project_root),
                py=shlex.quote(self.python_executable),
                cmd=cmd,
            ).strip()
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
                content = content[:start_idx] + content[end_idx + len(marker_end) :]
                content = content.strip() + "\n"

        with open(rc_path, "a" if content.endswith("\n") else "w") as f:
            if not content.endswith("\n") and content:
                f.write("\n")
            f.writelines(lines_to_add)

        return AliasInstallResult(
            success=True,
            platform=self.os_type,
            rc_path=rc_path,
        )

    def _install_windows(self) -> AliasInstallResult:
        """Creates .bat files in a dedicated bin directory."""
        bin_dir = os.path.join(self.home_dir, "tg_msg_bin")
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)

        for alias, cmd in self.ALIASES.items():
            bat_path = os.path.join(bin_dir, f"{alias}.bat")
            with open(bat_path, "w") as f:
                f.write(
                    "@echo off\n"
                    f'cd /d "{self.project_root}"\n'
                    f'"{self.python_executable}" -m tg_msg_manager.cli {cmd} %*\n'
                )

        return AliasInstallResult(
            success=True,
            platform=self.os_type,
            bin_dir=bin_dir,
        )

    def get_alias_specs(self) -> List[AliasHelpEntry]:
        """Returns structured alias help entries for CLI-side localization."""
        return list(self.ALIAS_HELP)
