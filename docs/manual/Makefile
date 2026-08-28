# Manual build. Run via `make -C docs/manual <target>`.
#   all      regenerate the generated chapters (menus, console, formats) and the rendered screens
#   html/pdf build dist/NanoVNA-manual.{html,pdf} with tools/manual/build.py (pandoc; PDF needs xelatex)
#   status   list what is still missing ([describe], samples, verify-on-hardware markers)
ROOT := $(abspath ..)/..
.PHONY: all menus console formats html pdf dist status test
all: menus console formats screens
dist: html pdf
html:
	cd $(ROOT) && python3 tools/manual/build.py --html
pdf:
	cd $(ROOT) && python3 tools/manual/build.py --pdf
status:
	cd $(ROOT) && python3 tools/manual/status.py
menus:
	cd $(ROOT) && python3 tools/manual/gen_menus.py
console:
	cd $(ROOT) && python3 tools/manual/gen_console.py
formats:
	cd $(ROOT) && python3 tools/manual/gen_formats.py
screens:
	cd $(ROOT) && python3 tools/manual/gen_screens.py
test:
	cd $(ROOT) && python3 -m unittest tests.test_manual_gen tests.test_screen_render
