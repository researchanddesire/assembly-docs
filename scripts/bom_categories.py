"""Single reusable source for the RAD BOM part-category vocabulary.

This is the one place the category code -> label -> color mapping lives. The
BOM renderer (``render_bom.py``) and the generated category chips all read from
here so the label/color aesthetic stays consistent across every Research and
Desire product's assembly docs.

The closed category-code enum mirrors the canonical BOM standard documented in
``dev-docs`` (``docs/meta/bom-standard.md`` + ``schemas/bom.schema.json``). This
module does NOT define or mutate the BOM *schema*; it only describes how the
already-defined ``Category`` codes are labelled and coloured when rendered.

Adding or removing a code here is a deliberate change that must follow the
canonical list in ``dev-docs`` -- never an ad-hoc per-repo addition.
"""

from __future__ import annotations

# code -> (full label, chip background colour).
# Colours are grouped by part family so the table reads as strong, consistent
# colour-coding: fabricated parts run warm, electronics run blue/indigo, power
# runs green, motion runs purple, cabling runs teal, materials run olive/grey,
# and assembly/admin runs red/pink.
CATEGORIES: dict[str, tuple[str, str]] = {
    # Fabricated / printed parts -- warm oranges & browns
    "FDM": ("FDM Printed Part", "#d9480f"),
    "SLA": ("SLA Printed Part", "#e8590c"),
    "FIL": ("FDM Filament", "#f08c00"),
    "MCM": ("Machined Plastic", "#ad6200"),
    "CSM": ("Machined Metal", "#846358"),
    "FBO": ("Fabricated, Other", "#a8703a"),
    "EXT": ("Extruded Aluminum", "#9c6b1f"),
    # Electronics -- blues & indigos
    "PCA": ("Printed Circuit Board Assembly", "#1864ab"),
    "PCB": ("Printed Circuit Board", "#1971c2"),
    "PCP": ("Printed Circuit Board Panel", "#1c7ed6"),
    "IC": ("Integrated Circuit", "#3b5bdb"),
    "CAP": ("Capacitor", "#4263eb"),
    "RES": ("Resistor", "#4c6ef5"),
    "IND": ("Inductor", "#5c7cfa"),
    "OSC": ("Oscillator", "#3741a3"),
    "FUS": ("Fuse", "#364fc7"),
    "CON": ("Connector", "#2b6cb0"),
    # Power -- greens
    "BTY": ("Battery", "#2b8a3e"),
    "PSU": ("Power Supply Unit", "#2f9e44"),
    "PWT": ("Power Transmission", "#37b24d"),
    # Motion -- purples
    "MTR": ("Motor", "#6741d9"),
    "LNM": ("Linear Motion", "#7048e8"),
    "BTP": ("Belt and Pulley", "#7950f2"),
    "SPR": ("Spring", "#9c36b5"),
    "PNU": ("Pneumatic", "#ae3ec9"),
    # Cabling & switching -- teals/cyans
    "CBL": ("Cable", "#0c8599"),
    "CHA": ("Cable Harness Assembly", "#0b7285"),
    "SWI": ("Switch", "#1098ad"),
    # Materials & consumables -- olive / grey
    "ADH": ("Adhesive", "#5c5f00"),
    "LUB": ("Lubricant", "#66730a"),
    "INS": ("Insulation", "#6b7280"),
    # Fasteners & assembly / admin -- reds & pinks
    "FST": ("Fastener", "#c92a2a"),
    "ASM": ("Assembly", "#a61e4d"),
    "SKU": ("Stock Keeping Unit", "#862e9c"),
    "SOP": ("Standard Operating Procedure", "#495057"),
    "PKG": ("Packaging", "#d6336c"),
    "PPG": ("Paper Goods", "#e64980"),
}


def label_for(code: str) -> str:
    """Full human label for a category code, or the code itself if unknown."""
    entry = CATEGORIES.get(code.strip().upper())
    return entry[0] if entry else code


def color_for(code: str) -> str:
    """Chip background colour for a category code, or a neutral grey fallback."""
    entry = CATEGORIES.get(code.strip().upper())
    return entry[1] if entry else "#868e96"


def text_color_for(background: str) -> str:
    """Pick black or white text for legibility against ``background`` (#rrggbb)."""
    hexval = background.lstrip("#")
    r, g, b = (int(hexval[i : i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#111111" if luminance > 0.6 else "#ffffff"
