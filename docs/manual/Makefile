# Manual build. Step 1: menu map only. Run from this directory or the repo root via make -C docs/manual.
ROOT := $(abspath ..)/..
.PHONY: menus test
menus:
	cd $(ROOT) && python3 tools/manual/gen_menus.py
test:
	cd $(ROOT) && python3 -m unittest tests.test_manual_gen
