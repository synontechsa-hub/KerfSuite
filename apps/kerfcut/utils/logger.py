"""
KerfCut — Centralized Logging
Handles all application logging, including rotating file handlers.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Setup logs directory
LOGS_DIR = (Path(__file__).resolve().parent.parent / "logs")
LOGS_DIR.mkdir(exist_ok=True, parents=True)
LOG_FILE = LOGS_DIR / "app.log"

# Create a custom logger
logger = logging.getLogger("KerfCut")
logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

# Prevent logging from propagating to the root logger multiple times
logger.propagate = False

if not logger.handlers:
    # 1. Console Handler (for dev)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    c_handler.setFormatter(c_format)
    logger.addHandler(c_handler)

    # 2. File Handler (Rotating, max 5MB, keep 3 backups)
    f_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    f_handler.setLevel(logging.DEBUG)
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    f_handler.setFormatter(f_format)
    logger.addHandler(f_handler)

logger.info("Logger initialized.")
