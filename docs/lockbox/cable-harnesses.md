# Cable Harnesses

Lockbox includes motor, battery, USB-C, screen, and other small cable
connections in the assembly flow. The product-level [Bill of Materials](bom.md)
tracks these as device-level line items.

No Wireviz harness source has been migrated to `hardware/cables/` yet. When a
Wireviz source is added, link its generated diagram and child BOM artifacts
from this page instead of duplicating child cable BOM rows in `hardware/bom.csv`.

| Asset | Location | Notes |
| --- | --- | --- |
| Cable source folder | [`hardware/cables/`](https://github.com/researchanddesire/Lockbox-OSS/tree/main/hardware/cables) | Wireviz YAML sources belong here. |
| Product-level BOM | [`hardware/bom.csv`](https://github.com/researchanddesire/Lockbox-OSS/blob/main/hardware/bom.csv) | Lists cable assemblies and off-the-shelf cable items. |
