import os
import sys
from dataclasses import dataclass
from typing import List, Optional

from .config import Settings, load_settings


def _resolve_under_root(root: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


@dataclass(frozen=True)
class AppPaths:
    project_root: str
    config_path: str
    db_path: str
    lock_path: str
    logs_dir: str
    db_exports_dir: str
    private_dialogs_dir: str
    public_groups_dir: str

    def artifact_roots(self) -> List[str]:
        return [
            self.public_groups_dir,
            self.private_dialogs_dir,
            self.db_exports_dir,
        ]


@dataclass(frozen=True)
class AppRuntime:
    settings: Settings
    paths: AppPaths
    python_executable: str


def build_app_runtime(
    *,
    project_root: Optional[str] = None,
    config_path: Optional[str] = None,
    python_executable: Optional[str] = None,
) -> AppRuntime:
    if project_root is None and config_path:
        resolved_config_path = os.path.abspath(config_path)
        resolved_project_root = os.path.dirname(resolved_config_path)
    else:
        resolved_project_root = os.path.abspath(project_root or os.getcwd())
        resolved_config_path = os.path.abspath(
            config_path or os.path.join(resolved_project_root, "config.json")
        )

    settings = load_settings(resolved_config_path)
    paths = AppPaths(
        project_root=resolved_project_root,
        config_path=resolved_config_path,
        db_path=_resolve_under_root(resolved_project_root, settings.db_path),
        lock_path=os.path.join(resolved_project_root, ".tg_msg_manager.lock"),
        logs_dir=os.path.join(resolved_project_root, "LOGS"),
        db_exports_dir=os.path.join(resolved_project_root, "DB_EXPORTS"),
        private_dialogs_dir=os.path.join(resolved_project_root, "PRIVAT_DIALOGS"),
        public_groups_dir=os.path.join(resolved_project_root, "PUBLIC_GROUPS"),
    )
    return AppRuntime(
        settings=settings,
        paths=paths,
        python_executable=python_executable or sys.executable,
    )
