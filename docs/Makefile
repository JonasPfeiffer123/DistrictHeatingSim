SPHINXOPTS    ?= -W --keep-going -n
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

.PHONY: help clean html livehtml linkcheck coverage

help:
    @$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

clean:
    @echo "Cleaning build directory..."
    @$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

html:
    @echo "Building HTML documentation..."
    @$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) -E -a
    @echo "HTML documentation generated in $(BUILDDIR)/html/"
    @echo "Open $(BUILDDIR)/html/index.html to view"

livehtml:
    @echo "Starting live documentation server..."
    sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)/html" --host 0.0.0.0 --port 8000 --open-browser

linkcheck:
    @echo "Checking external links..."
    @$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS)

coverage:
    @echo "Checking documentation coverage..."
    @$(SPHINXBUILD) -b coverage "$(SOURCEDIR)" "$(BUILDDIR)/coverage" $(SPHINXOPTS)
    @cat "$(BUILDDIR)/coverage/python.txt"

%: Makefile
    @$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)