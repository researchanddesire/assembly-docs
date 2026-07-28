# Chastity Lockbox (BOM demo)

!!! note "Validation demo"
    This section is a **self-contained demo** that validates the standard RAD
    assembly-docs BOM rendering workflow before it is applied to the real
    product repos. Its BOM is rendered from a sample `hardware/bom.csv` shipped
    with the `assembly-docs` repo — not from the real Lockbox repo. Disable it
    by assembling with `ASSEMBLE_BOM_DEMO=0`.

The [Bill of Materials](bom.md) is generated from `hardware/bom.csv` by
`scripts/render_bom.py` at assemble time and embedded between stable
generated-content markers.
