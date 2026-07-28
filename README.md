# Research and Desire Open Hardware Assembly Instructions

This repository is the public content mirror for the [Open Hardware Assembly Instructions](https://ohai.researchanddesire.com), built with [Fumadocs](https://fumadocs.dev/) from the private `researchanddesire/rad-app` monorepo.

## Contribute

1. Fork this repository and create a branch from `main`.
2. Edit Markdown or MDX under `content/`.
3. Open a focused pull request with screenshots when layout or imagery changes.

After review, automation proposes public changes in `rad-app`. Approved private-source changes are proposed back to this mirror as reviewed pull requests. The `[docs-sync]` commit marker prevents reciprocal loops.

This repository no longer assembles or deploys an independent MkDocs site. Bill of Materials renderers, shared-root tables, product-repository aggregators, and GitHub Pages deployment are intentionally retired. Application code, deployment configuration, credentials, and generated build output do not belong here.
