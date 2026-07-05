# =============================================================================
# TtbarIdHistCompare - Makefile
# =============================================================================
# Standalone build (no CMSSW / scram).  Requires only a ROOT installation with
# `root-config` on PATH (the same environment used to run the jobs).
#
#   make            # build all binaries into ./bin
#   make makeTtbarHist
#   make plotTtbarCompare
#   make clean
#
# Binaries:
#   bin/makeTtbarHist      - fill genTtbarId / Expanded_genTtbarId histograms from a filelist
#   bin/matchTtbarId       - per-event match (loads whole sidecar in memory; small samples)
#   bin/matchTtbarIdSorted - per-event match using sorted+split sidecar (memory-light; large ttbar)
#   bin/sortSplitExtend    - external-sort a ttbarId-extend file by (run,lumi,event) into part files + index
#   bin/extractTtbarIdPatch - extract tt+nb rows (Expanded%100 in 61/62/71/72) into the per-sample ttbar-Id patch file
#   bin/scanOrder          - diagnose per-file (run,lumi,event) ordering
#   bin/plotTtbarCompare   - overlay plot with per-bin ratio numbers, sidecar vs nano
# =============================================================================

# --- Compiler ----------------------------------------------------------------
CXX      ?= g++
CXXSTD   ?= -std=c++17
WARN     ?= -Wall -Wextra
OPT      ?= -O2
CXXFLAGS ?= $(CXXSTD) $(WARN) $(OPT)

# --- ROOT (via root-config) --------------------------------------------------
ROOTCONFIG := $(shell which root-config 2>/dev/null)
ifeq ($(ROOTCONFIG),)
  $(error root-config not found on PATH.  Set up your ROOT environment first \
          (the same setup you use to run the jobs), then re-run make.)
endif
ROOTCFLAGS := $(shell root-config --cflags)
ROOTLIBS   := $(shell root-config --libs)

# --- Layout ------------------------------------------------------------------
SRCDIR := src
BINDIR := bin

# Each .cc in src/ becomes a standalone executable in bin/.
SOURCES := $(wildcard $(SRCDIR)/*.cc)
BINARIES := $(patsubst $(SRCDIR)/%.cc,$(BINDIR)/%,$(SOURCES))

# --- Rules -------------------------------------------------------------------
.PHONY: all clean

all: $(BINARIES)
	@echo "[Makefile] built: $(BINARIES)"

# Pattern rule: bin/<name> from src/<name>.cc
$(BINDIR)/%: $(SRCDIR)/%.cc | $(BINDIR)
	@echo "[Makefile] compiling $< -> $@"
	$(CXX) $(CXXFLAGS) $(ROOTCFLAGS) $< -o $@ $(ROOTLIBS)

$(BINDIR):
	@mkdir -p $(BINDIR)

# Convenience targets so `make makeTtbarHist` works (maps to bin/makeTtbarHist).
makeTtbarHist:    $(BINDIR)/makeTtbarHist
plotTtbarCompare: $(BINDIR)/plotTtbarCompare
.PHONY: makeTtbarHist plotTtbarCompare

clean:
	@echo "[Makefile] cleaning"
	@rm -rf $(BINDIR)
