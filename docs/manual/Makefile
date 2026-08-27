# Manual build. Step 1: menu map only. Run from this directory or the repo root via make -C docs/manual.
ROOT := $(abspath ..)/..
.PHONY: all menus console formats test
all: menus console formats
menus:
	cd $(ROOT) && python3 tools/manual/gen_menus.py
console:
	cd $(ROOT) && python3 tools/manual/gen_console.py
formats:
	cd $(ROOT) && python3 tools/manual/gen_formats.py
test:
	cd $(ROOT) && python3 -m unittest tests.test_manual_gen
