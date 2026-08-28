# NanoVNA guides
Copy the GUIDES folder to the SD card root. On the device:
SD CARD -> LOAD -> GUIDE. Wheel or tap left/right = page,
push or tap the header = back.
## Writing your own (.md or .txt)
- First line `# Title`; `---` on its own line = page break
- Keep lines under 60 characters and pages under 27 rows;
  the device clips, it does not wrap or scroll
- `## Heading`, **bold** / *emphasis*, `code`, [text](url)
- Tables: | a | b | rows, second row |---|--:| sets alignment
- Ω ° µ are drawn; other non-ASCII shows as ?
- Check on a PC: python3 tools/manual/guide.py check FILE
- Preview: python3 tools/manual/guide.py render FILE --target H4
