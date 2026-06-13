# utils/logging_setup.py
# Author: Emsii (refactored)
# Konfiguracja logowania — zastępuje Another.save_logs_to_file i error_insert.
# Jeden miejsce dla całej konfiguracji loggerów.

import logging
import logging.handlers
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def setup_logging(level: int = logging.INFO) -> None:
    """
    Skonfiguruj logging dla całej aplikacji.

    Zastępuje:
    - Another.error_insert()      → ERROR level → error.log
    - Another.save_logs_to_file() → INFO level  → app.log
    - traceback.print_exc()       → wbudowane w logging.exception()

    Użycie w module:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Coś się stało")
        logger.error("Błąd")
        logger.exception("Błąd z traceback")  # automatycznie dołącza stack trace
    """
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)-30s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Handler: plik app.log (rotujący co 5MB, max 3 pliki) ──
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(formatter)

    # ── Handler: plik error.log (tylko ERROR i wyżej) ──
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # ── Handler: konsola ──
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    ))

    # ── Root logger ──
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(app_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)

    # Wycisz nadmiernie gadatliwe biblioteki
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
