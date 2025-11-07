"""Application settings management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the application."""

    app_name: str = "Gift Card Manager"
    author: str = ""
    data_dir: Path = field(default_factory=lambda: Path.home() / ".gift_card_manager")
    database_filename: str = "gift_card_manager.sqlite3"
    debug: bool = False

    @property
    def database_path(self) -> Path:
        """Return the absolute path to the SQLite database file."""

        self.ensure_data_dir()
        return self.data_dir / self.database_filename

    def ensure_data_dir(self) -> None:
        """Create the user data directory if it does not exist."""

        self.data_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Load settings using environment overrides (placeholder for future logic)."""

    settings = Settings()
    settings.ensure_data_dir()
    return settings


settings = load_settings()
