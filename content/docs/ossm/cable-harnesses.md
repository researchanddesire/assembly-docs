# Cable Harnesses

OSSM cable harness sources live under [`hardware/cables/`](../hardware/cables/).
Wireviz renders each harness source into diagram artifacts and a detailed child
BOM. The product-level [Bill of Materials](bom.md) should list each harness as a
top-level assembly and link to the Wireviz source.

## Motor Control Harness

| Asset | Location |
| --- | --- |
| Wireviz source | [`OSSM-Motor-Control-Harness.yml`](../hardware/cables/OSSM-Motor-Control-Harness.yml) |
| Source notes | [`hardware/cables/README.md`](../hardware/cables/README.md) |
| Generated release assets | [Latest OSSM release](https://github.com/researchanddesire/ossm/releases/latest) |

The cable export workflow publishes generated assets from `cable-export/`,
including:

- `OSSM-Motor-Control-Harness.pdf`
- `OSSM-Motor-Control-Harness.png`
- `OSSM-Motor-Control-Harness.bom.tsv`
