# Research and Desire - Assembly Docs

Unified assembly documentation for Research and Desire hardware products.

Each product's assembly package (bill of materials, assembly guide, cable
harness notes, PCB overview, and supporting images) is maintained in its own
repository under `assembly-docs/` and assembled into this site automatically on
every update.

## Products

<div class="rad-product-grid">
  <a class="rad-product-card" href="dtt/index.html">
    <span class="rad-product-kicker">Assembly Docs</span>
    <strong>Deepthroat Trainer</strong>
    <span>Assembly guide, BOM, PCB overview, and cable harness notes.</span>
  </a>
  <a class="rad-product-card" href="lockbox/index.html">
    <span class="rad-product-kicker">Assembly Docs</span>
    <strong>Lockbox</strong>
    <span>Mechanical build steps, electronics routing, BOM, and PCB context.</span>
  </a>
  <a class="rad-product-card" href="radr/index.html">
    <span class="rad-product-kicker">Assembly Docs</span>
    <strong>RADR Wireless Remote</strong>
    <span>Remote assembly workflow with production images and source links.</span>
  </a>
  <a class="rad-product-card" href="ossm/index.html">
    <span class="rad-product-kicker">Assembly Docs</span>
    <strong>OSSM</strong>
    <span>Assembly package, product BOM, and hardware source references.</span>
  </a>
</div>

These pages are assembled from each product repository's `assembly-docs/`
package:

- `DT_Trainer-OSS/assembly-docs/`
- `Lockbox-OSS/assembly-docs/`
- `RADR-OSS/assembly-docs/`
- `ossm/assembly-docs/`

## Contributing

To change a product's assembly docs, edit the `assembly-docs/` folder in that
product's repository. Cross-product pages like this one live in this repository.

For the full assembly pipeline, CI flow, BOM rendering rules, and contribution
boundaries, see [How This Site Works](how-this-site-works.md).
