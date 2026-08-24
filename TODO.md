# TODO

- [ ] **Review and approve the USBTMC/USB488 design spec** —
  `docs/superpowers/specs/2026-08-24-usbtmc-design.md` (status: Proposed).
  Key decisions to sign off on: opt-in build flag off by default (F303-only,
  `#error` on F072), composite CDC+TMC device keeping existing apps working,
  shell-tunnel command layer instead of a SCPI tree, streamed responses,
  minimal USB488 capability set. Approval unlocks writing the implementation
  plan (added 2026-08-24, re: DiSlord/NanoVNA-D#98).
