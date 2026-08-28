# Manual build. Run via `make -C docs/manual <target>`.
#   all      regenerate the generated chapters (menus, console, formats), the rendered screens and the guides pack
#   guides   regenerate docs/manual/guides from guides-src and the code tables
#   html/pdf build dist/NanoVNA-manual.{html,pdf} with tools/manual/build.py (pandoc; PDF needs xelatex)
#   status   list what is still missing ([describe], samples, verify-on-hardware markers)
ROOT := $(abspath ..)/..
.PHONY: all menus console formats screens guides html pdf dist status test
all: menus console formats screens guides
dist: html pdf guides
	cd $(ROOT)/docs/manual && mkdir -p dist && rm -rf dist/GUIDES dist/NanoVNA-guides.zip && cp -r guides dist/GUIDES && (cd dist && zip -qr NanoVNA-guides.zip GUIDES && rm -r GUIDES)
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
guides:
	cd $(ROOT) && python3 tools/manual/guide.py pack
test:
	cd $(ROOT) && python3 -m unittest tests.test_manual_gen tests.test_screen_render tests.test_guides
