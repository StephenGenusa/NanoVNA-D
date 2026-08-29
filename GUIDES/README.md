# NanoVNA guides
Copy this GUIDES folder to the SD card root. On the device:
SD CARD -> LOAD -> GUIDE. Wheel or tap left/right = page,
push or tap the header = back.

Files are grouped by prefix: ant- antennas, pota-/sota- field
operating, choke-, coax-, cal-, ref- tables and formulas,
dev- the instrument itself, prop- propagation.

## Writing your own (.md or .txt)
- First line `# Title`; `---` on its own line = page break
- Keep lines under 60 characters and pages under 27 rows;
  the device clips, it does not wrap or scroll
- `## Heading`, **bold** / *emphasis*, `code`, [text](url)
- Tables: | a | b | rows, second row |---|--:| sets alignment
- Ω ° µ are drawn; other non-ASCII shows as ?
- Check on a PC: python3 tools/manual/guide.py check FILE
- Preview: python3 tools/manual/guide.py render FILE --target H4
---
## Sources
- The NanoVNA-D fork manual, docs/manual/ (device guides are
  generated from the firmware source)
- ARRL Antenna Book for Radio Communications (coax loss
  Vol 3 Table 23.4; radial voltages Vol 1 Fig 3.27)
- N6LF (R. Severns) QEX 3/2009 and 3-4/2012, QST 3/2010:
  radials
- K9YC (J. Brown) "RFI, Ferrites, and Common Mode Chokes"
  and the 2018 Choke Cookbook: k9yc.com/publish.htm
- G3TXQ choke charts: karinya.net/g3txq/chokes/
- Fair-Rite Products catalog (14th ed.) and material data
  sheets: fair-rite.com; Palomar Engineers mix-selection table
- Parks on the Air rules and guides: docs.pota.app;
  SOTA General Rules: sota.org.uk
- "Portable HF Vertical Antennas", S. Genusa 2026 (the
  portvert reference, with its claims ledger)
