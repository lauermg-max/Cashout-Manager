"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .core.db import init_db
from .ui.main_window import MainWindow


def main() -> int:
    """Initialize resources and start the Qt event loop."""

    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Gift Card Manager")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
