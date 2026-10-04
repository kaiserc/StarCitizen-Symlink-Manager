"""
assets.py - Resolves bundled assets (fonts, images) and optional RSI Fankit drop-ins.

Official Star Citizen artwork can NOT be redistributed with this repo. Instead, users who have
an RSI account can download the official Fankit (https://robertsspaceindustries.com/fankit)
and drop specific files into ``assets/fankit/``. When present they are picked up automatically:

    assets/fankit/made_by_the_community.png   -> "Made by the Community" badge (shown in footer)
    assets/fankit/header.png | header.jpg     -> replaces the header background art
    assets/fankit/logo.png                    -> replaces the header emblem (e.g. SC logo)

If a file is missing, the bundled original art in ``assets/ui/`` is used instead.
"""

import os
import sys
from typing import Optional, Tuple

import customtkinter as ctk

try:
    from PIL import Image
except ImportError:  # Pillow is a customtkinter dependency, but stay defensive.
    Image = None


def _base_dir() -> str:
    """Project root in source mode, or the PyInstaller extraction dir when frozen."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


ASSETS_DIR = os.path.join(_base_dir(), "assets")
UI_DIR = os.path.join(ASSETS_DIR, "ui")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
FANKIT_DIR = os.path.join(ASSETS_DIR, "fankit")

APP_ICON_PATH = os.path.join(UI_DIR, "app.ico")

# Trademark notice required by RSI when using Fankit material.
FANKIT_NOTICE = (
    "This is an unofficial Star Citizen fan project, not affiliated with the Cloud Imperium group "
    "of companies. Star Citizen®, Roberts Space Industries® and Cloud Imperium® are registered "
    "trademarks of Cloud Imperium Rights LLC."
)


def asset_path(*parts: str) -> str:
    return os.path.join(ASSETS_DIR, *parts)


def _first_existing(*paths: str) -> Optional[str]:
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


def load_fonts() -> None:
    """Registers bundled .ttf/.otf fonts for this process (no system install required)."""
    if not os.path.isdir(FONTS_DIR):
        return
    for name in os.listdir(FONTS_DIR):
        if name.lower().endswith((".ttf", ".otf")):
            path = os.path.abspath(os.path.join(FONTS_DIR, name))
            if sys.platform.startswith("win"):
                try:
                    from ctypes import windll, byref, create_unicode_buffer
                    # FR_PRIVATE = 0x10 makes font accessible to this process only.
                    # We do NOT pass FR_NOT_ENUM (0x20) because Tkinter's internal font
                    # engine enumerates fonts to populate its family cache.
                    path_buffer = create_unicode_buffer(path)
                    windll.gdi32.AddFontResourceExW(byref(path_buffer), 0x10, 0)
                except Exception:
                    pass
            try:
                ctk.FontManager.load_font(path)
            except Exception:
                pass


def load_image(path: Optional[str], size: Tuple[int, int]) -> Optional[ctk.CTkImage]:
    if not path or Image is None or not os.path.isfile(path):
        return None
    try:
        img = Image.open(path)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


def load_cover_image(path: Optional[str], size: Tuple[int, int],
                     fade_left_to: Optional[str] = None) -> Optional[ctk.CTkImage]:
    """
    Loads an image center-cropped to exactly fill ``size`` (like CSS background-size: cover).
    If ``fade_left_to`` (hex colour) is given, the left part fades into that solid colour so
    overlaid text has a clean background.
    """
    if not path or Image is None or not os.path.isfile(path):
        return None
    try:
        img = Image.open(path).convert("RGB")
        tw, th = size
        scale = max(tw / img.width, th / img.height)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        left = (img.width - tw) // 2
        top = (img.height - th) // 2
        img = img.crop((left, top, left + tw, top + th))
        if fade_left_to:
            solid = Image.new("RGB", (tw, th), fade_left_to)
            mask = Image.new("L", (tw, 1))
            start, end = int(tw * 0.42), int(tw * 0.78)
            mask.putdata([0 if x < start else 255 if x > end else int(255 * (x - start) / (end - start))
                          for x in range(tw)])
            img = Image.composite(img, solid, mask.resize((tw, th)))
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


def header_background_path() -> Optional[str]:
    return _first_existing(
        os.path.join(FANKIT_DIR, "header.png"),
        os.path.join(FANKIT_DIR, "header.jpg"),
        os.path.join(UI_DIR, "header_bg.png"),
    )


def emblem_path() -> Optional[str]:
    return _first_existing(
        os.path.join(FANKIT_DIR, "logo.png"),
        os.path.join(UI_DIR, "emblem.png"),
    )


def community_badge_path() -> Optional[str]:
    return _first_existing(os.path.join(FANKIT_DIR, "made_by_the_community.png"))


def fankit_in_use() -> bool:
    return any(
        os.path.isfile(os.path.join(FANKIT_DIR, f))
        for f in ("made_by_the_community.png", "header.png", "header.jpg", "logo.png")
    )
