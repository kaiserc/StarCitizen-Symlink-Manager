"""
theme.py - Star Citizen dark HUD theme: colors, typography, and font tokens.

Typography is aligned with StarCitizen-StreamDock-Studio:
    - Orbitron: Sci-fi high-tech brand title and large metric numbers
    - Exo 2: Clean, futuristic headings, tabs, and section headers
    - Inter: Highly legible modern UI body font and button labels
    - Consolas / Mono: Technical path, version, and footprint readouts

Fonts are bundled in assets/fonts/ and loaded dynamically on startup.
"""

# --- Color Palette -----------------------------------------------------------
# Backgrounds (deep space -> raised HUD panels)
COLOR_BG_DARK = "#060A12"         # Deep space / void
COLOR_BG_SIDEBAR = "#0A111C"      # Header / chrome
COLOR_BG_INPUT = "#04070D"        # Entry fields, consoles
COLOR_CARD_BG = "#0D1624"         # Surface cards
COLOR_CARD_BORDER = "#1A2B40"     # Card border outline
COLOR_CARD_HOVER = "#12203A"      # Hover state
COLOR_BTN = "#13223A"             # Neutral (secondary) button
COLOR_BTN_HOVER = "#1C3254"       # Neutral button hover

# mobiGlas cyan accent
COLOR_ACCENT = "#00F0FF"          # Vibrant cyber cyan (matches StreamDock Studio)
COLOR_ACCENT_HOVER = "#00B4D8"
COLOR_ACCENT_MUTED = "#0B4A6E"    # Primary button fill
COLOR_ACCENT_GLOW = "#0F2E44"     # Subtle accent surfaces (badges, selected states)

# RSI gold (used sparingly for "master"/featured items)
COLOR_GOLD = "#E8B547"
COLOR_GOLD_HOVER = "#C9962E"
COLOR_GOLD_MUTED = "#3A2C0E"

# Status colors
COLOR_SUCCESS = "#3DDC97"         # Linked / healthy
COLOR_SUCCESS_BG = "#0B3326"
COLOR_WARNING = "#F2A93B"         # Warning / elevation required
COLOR_WARNING_BG = "#3A2A0B"
COLOR_DANGER = "#FF5C6C"          # Broken / destructive
COLOR_DANGER_BG = "#3A0F16"
COLOR_DANGER_HOVER = "#5A1622"
COLOR_MUTED = "#5B6B82"           # Subdued text / icons

# Text
COLOR_TEXT_PRIMARY = "#E6F1FA"    # Cool white
COLOR_TEXT_SECONDARY = "#9AB0C6"  # Steel silver
COLOR_TEXT_MUTED = "#647894"      # Readable hint text

# Tooltip
COLOR_TOOLTIP_BG = "#0B1830"
COLOR_TOOLTIP_BORDER = "#2A6F96"

# --- Typography Hierarchy ----------------------------------------------------
FONT_BRAND_FAMILY = "Orbitron"
FONT_HEADING_FAMILY = "Exo 2"
FONT_DISPLAY_FAMILY = "Exo 2"
FONT_UI_FAMILY = "Inter"
FONT_MONO_FAMILY = "JetBrains Mono"

# Font tokens - scaled for crisp desktop readability (proportional with StreamDock Studio)
FONT_TITLE = (FONT_BRAND_FAMILY, 18, "bold")         # App Brand Title
FONT_SUBTITLE = (FONT_HEADING_FAMILY, 13)            # Tagline / Subtitle
FONT_TAB = (FONT_HEADING_FAMILY, 15, "bold")         # Tab bar navigation
FONT_HEADING = (FONT_HEADING_FAMILY, 20, "bold")     # Card titles (e.g. Channel name)
FONT_SUBHEADING = (FONT_HEADING_FAMILY, 16, "bold")  # Sub-card titles
FONT_SECTION = (FONT_HEADING_FAMILY, 13, "bold")     # Uppercase section labels
FONT_METRIC = (FONT_BRAND_FAMILY, 38, "bold")        # Large KPI numbers (GB, channels)
FONT_METRIC_LABEL = (FONT_HEADING_FAMILY, 13, "bold")
FONT_BODY = (FONT_UI_FAMILY, 14)                     # Standard reading text
FONT_BODY_BOLD = (FONT_UI_FAMILY, 14, "bold")        # Emphasized body text
FONT_SMALL = (FONT_UI_FAMILY, 13)                    # Secondary labels, subtitles
FONT_SMALL_BOLD = (FONT_UI_FAMILY, 13, "bold")       # Badges, chips, button labels
FONT_CHIP = (FONT_UI_FAMILY, 12, "bold")             # Status chips
FONT_BTN = (FONT_UI_FAMILY, 13, "bold")              # Standard buttons
FONT_BTN_LARGE = (FONT_HEADING_FAMILY, 14, "bold")   # Primary action buttons
FONT_MONO = (FONT_MONO_FAMILY, 13)                   # Paths, branches, code
FONT_MONO_SMALL = (FONT_MONO_FAMILY, 12)             # Footprint, cache hashes, logs
