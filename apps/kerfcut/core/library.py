"""
KerfCut — Material Library
Handles persistent storage of standard sheet materials via QSettings.
"""
import json
from PyQt6.QtCore import QSettings
from core.models import Sheet
from utils.logger import logger
from version import APP_AUTHOR, APP_NAME

def get_library() -> list[Sheet]:
    """Retrieve the saved material library as a list of Sheet objects."""
    settings = QSettings(APP_AUTHOR, APP_NAME)
    data = settings.value("materials/library", None)
    
    # Default starter library if nothing exists
    if not data:
        return [
            Sheet(width=2440, height=1220, active=True, quantity=10, label="Standard Plywood 18mm", thickness=18.0),
            Sheet(width=4100, height=1200, active=True, quantity=10, label="Standard Countertop"),
            Sheet(width=2800, height=1850, active=True, quantity=10, label="Standard Melamine 16mm", thickness=16.0)
        ]
        
    try:
        if isinstance(data, str):
            dicts = json.loads(data)
        elif isinstance(data, bytes):
            dicts = json.loads(data.decode("utf-8"))
        else:
            dicts = data # assume it's already a list if PySide/PyQt converted it
            
        sheets = []
        for d in dicts:
            # We don't save 'active' or 'quantity' into the library meaningfully, but we provide defaults
            sheets.append(Sheet(
                width=d.get("width", 2440),
                height=d.get("height", 1220),
                active=True,
                quantity=d.get("quantity", 10),
                buy_price=d.get("buy_price", 0.0),
                sell_price=d.get("sell_price", 0.0),
                thickness=d.get("thickness", 0.0),
                label=d.get("label", "Saved Material")
            ))
        return sheets
    except Exception as e:
        logger.error(f"Failed to parse material library: {e}", exc_info=True)
        return []

def save_library(sheets: list[Sheet]):
    """Save a list of Sheet objects to the persistent library."""
    try:
        settings = QSettings(APP_AUTHOR, APP_NAME)
        dicts = []
        for s in sheets:
            dicts.append({
                "width": s.width,
                "height": s.height,
                "quantity": s.quantity,
                "buy_price": s.buy_price,
                "sell_price": s.sell_price,
                "thickness": s.thickness,
                "label": s.label
            })
        
        settings.setValue("materials/library", json.dumps(dicts))
        logger.info(f"Saved {len(sheets)} materials to library.")
    except Exception as e:
        logger.error(f"Failed to save material library: {e}", exc_info=True)

def add_to_library(sheet: Sheet):
    """Add a single sheet to the library if it doesn't already exist."""
    lib = get_library()
    # Basic deduplication based on WxHxThickness and Label
    for existing in lib:
        if (existing.width == sheet.width and 
            existing.height == sheet.height and 
            existing.thickness == sheet.thickness and 
            existing.label == sheet.label):
            return # Already exists
            
    lib.append(sheet)
    save_library(lib)
