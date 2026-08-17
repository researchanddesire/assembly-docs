# Contributing

Rendered assembly documentation lives under `content/docs/` as Markdown and MDX. The easiest contribution path is the pencil beside a page title or heading on [ohai.researchanddesire.com](https://ohai.researchanddesire.com), which opens the exact source line on `main`.

Before opening a pull request:

- keep build instructions specific to the supported product and hardware revision
- keep images beside the pages that use them
- do not hand-edit generated BOM tables; update the product repository's `hardware/bom.csv`
- do not add secrets, private production material, or generated build output
- run `node scripts/validate-content.mjs` when working locally

Target `main`. A maintainer review and the `validate-content` check are required. Approved mirrored content is synchronized into the private renderer automatically.

Cross-product prose uses CC BY-SA 4.0. Product hardware documentation and source material retain the product-specific license identified by the relevant file or directory.
