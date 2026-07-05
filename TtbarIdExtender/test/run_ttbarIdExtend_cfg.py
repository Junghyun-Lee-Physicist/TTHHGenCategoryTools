# -*- coding: utf-8 -*-
# =============================================================================
# - run_ttbarIdExtend_cfg.py
# =============================================================================
# Minimal cmsRun configuration that:
#   * Reads a MiniAODv2 input file (one or many)
#   * Runs matchGenBHadron, matchGenCHadron, categorizeGenTtbar,
#     ExtendedTtbarIdProducer, TtbarIdExtendAnalyzer  -- in that order
#   * Writes a ROOT TTree to `ttbarIDExtend.root` (configurable) containing
#     (run, luminosityBlock, event, genTtbarId, Expanded_genTtbarId, nAddBJets,
#      nAddBJetsMulti) with one row per event
#
# Usage:
#   cmsRun run_ttbarIdExtend_cfg.py
#       inputFiles=<miniaodv2 path>  (or comma-separated list)
#       outputFile=ttbarIDExtend.root      (default)
#       maxEvents=-1                 (-1 = all events)
#       verbose=False                (per-event log spam if True)
#
# Why this cfg is hand-written (the enriched approach used cmsDriver):
#   * We do NOT run the NANO step.  The NANO step is what made the
#     hand-written approach fragile in an earlier iteration (era modifiers, customizer
#     chains, AK8 ParticleNet recalculation, ...).  Skipping NANO removes
#     all of those failure modes.
#   * Everything we need is gen-level: slimmedGenJets,
#     slimmedGenJetsFlavourInfos, prunedGenParticles -- all present
#     in any MiniAODv2 file by definition.
#   * No GlobalTag is required (gen-level only; no detector geometry, no
#     alignment, no calibrations).
#   * No EventSetup / GeometryRecoDB / MagneticField loads required.
#   * No external CMSSW customizers required.
#
# This minimal-cfg design is what makes the ttbarId-extend robust across release patches:
# we depend only on the SC-stable gen-level producer interfaces, which
# have not changed between CMSSW 10_2 and 14_X.
#
# References:
#   * ROOT TFile / TTree (the analyzer writes its own file):
#       https://root.cern/manual/trees/
#   * categorizeGenTtbar canonical setup:
#       https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/ttbarCategorization_cff.py
#   * Repository docs: ../../docs/05_architecture.md -- ttbarId-extend design
# =============================================================================

from __future__ import print_function

import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

# ---- VarParsing CLI ---------------------------------------------------------
opts = VarParsing("analysis")
opts.register("verbose", False,
              VarParsing.multiplicity.singleton, VarParsing.varType.bool,
              "Per-event LogVerbatim from the ttbarId-extend analyzer (default False)")
opts.outputFile = "ttbarIDExtend.root"
opts.maxEvents  = -1
# Default input: leave empty.  Two ways input gets set:
#   * interactive:  pass inputFiles=<miniaodv2_path> on the cmsRun command line
#   * CRAB:         CRAB injects the per-job input files at grid-run time;
#                   at submit-time it imports this cfg ONCE with NO inputFiles
#                   to validate structure, so we must NOT hard-fail here.
opts.parseArguments()

# Do not raise on empty input: CRAB's submit-time import has no inputFiles yet.
# If a human runs cmsRun interactively without inputFiles, PoolSource will stop
# with an empty-fileNames error, which is a clear enough message.
if not opts.inputFiles:
    print("[run_ttbarIdExtend_cfg] WARNING: no inputFiles given.  This is normal for "
          "CRAB submit-time import (CRAB injects files per job).  For an "
          "interactive run, pass inputFiles=<miniaodv2_path>.")

print("[run_ttbarIdExtend_cfg] ttbarId-extend configuration")
print("[run_ttbarIdExtend_cfg]   inputFiles = %s" % (list(opts.inputFiles) or "(empty; CRAB will inject)"))
print("[run_ttbarIdExtend_cfg]   outputFile = %s" % opts.outputFile)
print("[run_ttbarIdExtend_cfg]   maxEvents  = %d" % opts.maxEvents)
print("[run_ttbarIdExtend_cfg]   verbose    = %s" % opts.verbose)


# ---- Process ----------------------------------------------------------------
# Era modifier not strictly required for gen-level only, but kept for
# consistency with downstream NanoAOD friend-tree workflows (any 2017
# friend-tree consumer expects Run2_2017 / run2_nanoAOD_106Xv2 to have
# been applied somewhere upstream).
from Configuration.StandardSequences.Eras import eras
process = cms.Process("TTBARIDEXTEND", eras.Run2_2017, eras.run2_nanoAOD_106Xv2)


# ---- Services ---------------------------------------------------------------
# MessageLogger does NOT auto-attach in CMSSW_10_6_X; we must load it
# explicitly (a CMSSW_10_6_X requirement).
process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = 1000

# Register our analyzer's category so its LogInfo and LogVerbatim messages
# are not silenced by the default MessageLogger config.
_cat = cms.untracked.PSet(limit = cms.untracked.int32(1000000))
if hasattr(process.MessageLogger, "categories"):
    # MessageLogger.categories is a vstring in 10_6_X; we have to append
    # (setattr alone is not enough).
    if "TtbarIdExtendAnalyzer" not in process.MessageLogger.categories:
        process.MessageLogger.categories.append("TtbarIdExtendAnalyzer")
setattr(process.MessageLogger, "TtbarIdExtendAnalyzer", _cat)


# ---- Input source -----------------------------------------------------------
process.source = cms.Source(
    "PoolSource",
    fileNames = cms.untracked.vstring(opts.inputFiles),
    secondaryFileNames = cms.untracked.vstring(),
)
process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32(opts.maxEvents))


# ---- The ttbarId-extend pipeline ---------------------------------------------------
# addTtbarIdExtend(process, outputFile=..., verbose=...) attaches all the
# producers, the analyzer (which opens its own TFile), and the Path/Schedule.
from TTHHGenCategoryTools.TtbarIdExtender.ttbarIdExtend_cff import addTtbarIdExtend
addTtbarIdExtend(process, outputFile=opts.outputFile, verbose=opts.verbose)


# ---- (Optional) Print the schedule for debugging ----------------------------
# This is purely informational.  The cms.Schedule / Path introspection API
# (.label(), .moduleNames()) is not guaranteed stable across releases, so we
# guard it: a print failure must never abort the actual job.
try:
    print("[run_ttbarIdExtend_cfg] schedule built; paths:")
    for p in process.schedule:
        try:
            label = p.label()
        except Exception:
            label = str(p)
        print("[run_ttbarIdExtend_cfg]   path: %s" % label)
except Exception as _e:
    print("[run_ttbarIdExtend_cfg] (schedule introspection skipped: %s)" % _e)
print("[run_ttbarIdExtend_cfg] cmsRun will now process up to %d events"
      % opts.maxEvents)
