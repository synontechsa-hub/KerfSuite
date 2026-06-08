"""
KerfCut — Global App Settings
Handles persistent configuration like Currency.
"""
from PyQt6.QtCore import QSettings
from version import APP_AUTHOR, APP_NAME

CURRENCIES = ["€", "$", "£", "R"]

def get_currency() -> str:
    return QSettings(APP_AUTHOR, APP_NAME).value("app/currency", "R")

def set_currency(symbol: str):
    QSettings(APP_AUTHOR, APP_NAME).setValue("app/currency", symbol)
