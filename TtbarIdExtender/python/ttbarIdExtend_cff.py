# -*- coding: utf-8 -*-
# =============================================================================
# - ttbar HF categorization EXTEND (Approach 3)
# =============================================================================
# Approach 3 ("ttbarId-extend") runs ONLY the gen-level ttbar+HF categorization
# producers on MiniAODv2 and emits a small ROOT TTree ("ttbarIDExtend.root")
# containing one row per event:
#
#     run / luminosityBlock / event                   -- NanoAOD-style keys
#     genTtbarId                                      -- standard 5-digit id
#     Expanded_genTtbarId / nAddBJets / nAddBJetsMulti             -- ExtendedTtbarIdProducer outputs
#
# Output file handling:
#   The analyzer (TtbarIdExtendAnalyzer) now opens its OWN TFile and writes
#   the TTree at the file's TOP LEVEL, instead of going through TFileService
#   (which buried the tree under a "ttbarIdExtend/" TDirectory).  The output
#   "Events" tree is therefore directly friend-attachable to central NanoAOD.
#   Consequently:
#     * the analyzer takes an `outputFile` (tracked) parameter,
#     * NO process.TFileService is configured by addTtbarIdExtend anymore.
#
# Why Approach 3 supersedes Approach 2 (enriched NanoAOD): see
# docs/ARCHITECTURE.md section 12.  In short: gen-level only, release-cycle
# immune, ~32 B/event, friend-tree-ready.
#
# Standard producers we depend on (all in CMSSW PhysicsTools/NanoAOD):
#   * matchGenBHadron, matchGenCHadron     -- jet flavor matching at gen level
#   * categorizeGenTtbar                   -- emits the byte-identical
#                                             5-digit "genTtbarId"
# Our additional producer (this package):
#   * extendedTtbarId   -- reclassifies events with >=3 additional b-jets:
#                          nAddBJets==3 -> 61/62 (tt+bbb), >=4 -> 71/72 (tt+4b).
# Our analyzer:
#   * ttbarIdExtend (TtbarIdExtendAnalyzer) -- writes the top-level TTree.
# =============================================================================

import FWCore.ParameterSet.Config as cms

from PhysicsTools.NanoAOD.ttbarCategorization_cff import (
    matchGenBHadron,
    matchGenCHadron,
    categorizeGenTtbar,
)

from TTHHGenCategoryTools.TtbarIdExtender.extendedTtbarId_cfi import (
    extendedTtbarId as _extendedTtbarId_base,
)


# -----------------------------------------------------------------------------
# Module-level extender (importable for custom wiring).
# -----------------------------------------------------------------------------
extendedTtbarId = _extendedTtbarId_base.clone(
    genTtbarId              = cms.InputTag("categorizeGenTtbar", "genTtbarId"),
    genJets                 = cms.InputTag("slimmedGenJets"),
    genBHadJetIndex         = cms.InputTag("matchGenBHadron", "genBHadJetIndex"),
    genBHadFromTopWeakDecay = cms.InputTag("matchGenBHadron", "genBHadFromTopWeakDecay"),
)


# -----------------------------------------------------------------------------
# Our ttbarId-extend analyzer.  `outputFile` is a TRACKED string parameter -- the
# analyzer opens this file itself (no TFileService).
# -----------------------------------------------------------------------------
ttbarIdExtend = cms.EDAnalyzer(
    "TtbarIdExtendAnalyzer",
    genTtbarId      = cms.InputTag("categorizeGenTtbar", "genTtbarId"),
    Expanded_genTtbarId = cms.InputTag("extendedTtbarId",       "expandedGenTtbarId"),
    nAddBJets       = cms.InputTag("extendedTtbarId",       "nAddBJets"),
    nAddBJetsMulti  = cms.InputTag("extendedTtbarId",       "nAddBJetsMulti"),
    outputFile      = cms.string("ttbarIDExtend.root"),
    treeName        = cms.untracked.string("Events"),
    treeTitle       = cms.untracked.string("ttbar HF categorization ttbarId-extend"),
    buildIndex      = cms.untracked.bool(True),
    verbose         = cms.untracked.bool(False),
)


# -----------------------------------------------------------------------------
# Sequence (analyzer is path-terminal).
# -----------------------------------------------------------------------------
ttbarIdExtendSequence = cms.Sequence(
    matchGenBHadron
  * matchGenCHadron
  * categorizeGenTtbar
  * extendedTtbarId
  * ttbarIdExtend
)


# -----------------------------------------------------------------------------
# One-shot customizer: attach the ttbarId-extend pipeline to a process.
# -----------------------------------------------------------------------------
def addTtbarIdExtend(process, outputFile="ttbarIDExtend.root", verbose=False):
    """Attach the full ttbar-Id ttbarId-extend pipeline to `process`.

    This function:
      1. Adds matchGenBHadron / matchGenCHadron / categorizeGenTtbar / extendedTtbarId
         / ttbarIdExtend as `process` attributes (if not already present).
      2. Adds a single Path that runs them in dependency order.
      3. Sets the analyzer's `outputFile` parameter.

    NO TFileService is configured -- the analyzer owns its TFile and
    writes the tree at the file's top level (friend-tree-ready).

    Call this from a minimal cfg that has done nothing more than build a
    `cms.Process(...)` and configure `process.source` / `process.maxEvents`.

    Diagnostic prints (stdout) report the configuration so any future
    regression is easy to localize from the first ~30 lines of the cmsRun log.
    """
    print("[TTHHGenCategoryTools.TtbarIdExtender] addTtbarIdExtend(process) start")
    print("[TTHHGenCategoryTools.TtbarIdExtender]   output file = %s" % outputFile)
    print("[TTHHGenCategoryTools.TtbarIdExtender]   verbose     = %s" % verbose)

    # 1) Attach the standard producers (fresh clones).
    from PhysicsTools.NanoAOD.ttbarCategorization_cff import (
        matchGenBHadron as _mGB,
        matchGenCHadron as _mGC,
        categorizeGenTtbar as _cgt,
    )
    if hasattr(process, "matchGenBHadron"):
        print("[TTHHGenCategoryTools.TtbarIdExtender]   matchGenBHadron already on process; keeping existing")
    else:
        process.matchGenBHadron = _mGB.clone()

    if hasattr(process, "matchGenCHadron"):
        print("[TTHHGenCategoryTools.TtbarIdExtender]   matchGenCHadron already on process; keeping existing")
    else:
        process.matchGenCHadron = _mGC.clone()

    if hasattr(process, "categorizeGenTtbar"):
        print("[TTHHGenCategoryTools.TtbarIdExtender]   categorizeGenTtbar already on process; keeping existing")
    else:
        process.categorizeGenTtbar = _cgt.clone()

    # 2) Attach OUR extender, with explicit InputTags (10_6_X does not
    #    auto-convert tuples to cms.InputTag; see docs/ARCHITECTURE.md S10).
    from TTHHGenCategoryTools.TtbarIdExtender.extendedTtbarId_cfi import (
        extendedTtbarId as _ext,
    )
    if hasattr(process, "extendedTtbarId"):
        print("[TTHHGenCategoryTools.TtbarIdExtender]   extendedTtbarId already on process -- replacing")
    process.extendedTtbarId = _ext.clone(
        genTtbarId              = cms.InputTag("categorizeGenTtbar", "genTtbarId"),
        genJets                 = cms.InputTag("slimmedGenJets"),
        genBHadJetIndex         = cms.InputTag("matchGenBHadron", "genBHadJetIndex"),
        genBHadFromTopWeakDecay = cms.InputTag("matchGenBHadron", "genBHadFromTopWeakDecay"),
    )

    # 3) Attach the ttbarId-extend analyzer, passing the output filename.
    if hasattr(process, "ttbarIdExtend"):
        print("[TTHHGenCategoryTools.TtbarIdExtender]   ttbarIdExtend already on process -- replacing")
    process.ttbarIdExtend = cms.EDAnalyzer(
        "TtbarIdExtendAnalyzer",
        genTtbarId      = cms.InputTag("categorizeGenTtbar", "genTtbarId"),
        Expanded_genTtbarId = cms.InputTag("extendedTtbarId",       "expandedGenTtbarId"),
        nAddBJets       = cms.InputTag("extendedTtbarId",       "nAddBJets"),
        nAddBJetsMulti  = cms.InputTag("extendedTtbarId",       "nAddBJetsMulti"),
        outputFile      = cms.string(outputFile),
        treeName        = cms.untracked.string("Events"),
        treeTitle       = cms.untracked.string("ttbar HF categorization ttbarId-extend"),
        buildIndex      = cms.untracked.bool(True),
        verbose         = cms.untracked.bool(bool(verbose)),
    )

    # 4) Build the Path.  Producers first (dependency order), analyzer last.
    process.ttbarIdExtendPath = cms.Path(
        process.matchGenBHadron
      * process.matchGenCHadron
      * process.categorizeGenTtbar
      * process.extendedTtbarId
      * process.ttbarIdExtend
    )

    # 5) No TFileService.  The analyzer opens its own TFile.
    #    If a stray TFileService is present from an earlier workflow we leave
    #    it untouched; it simply won't be used by this analyzer.

    # 6) Build/extend the schedule.  cms.Process ALWAYS has a `schedule`
    #    attribute, default None, so test `is not None` (hasattr is always
    #    True and `x not in None` raises TypeError).
    existing_schedule = getattr(process, "schedule", None)
    if existing_schedule is not None:
        if process.ttbarIdExtendPath not in existing_schedule:
            existing_schedule.append(process.ttbarIdExtendPath)
            print("[TTHHGenCategoryTools.TtbarIdExtender]   appended ttbarIdExtendPath to existing schedule")
        else:
            print("[TTHHGenCategoryTools.TtbarIdExtender]   ttbarIdExtendPath already in schedule; no change")
    else:
        process.schedule = cms.Schedule(process.ttbarIdExtendPath)
        print("[TTHHGenCategoryTools.TtbarIdExtender]   created new schedule with ttbarIdExtendPath")

    print("[TTHHGenCategoryTools.TtbarIdExtender] addTtbarIdExtend(process) done; "
          "top-level TTree will be written to '%s' with branches "
          "run/luminosityBlock/event/genTtbarId/Expanded_genTtbarId/nAddBJets/nAddBJetsMulti" % outputFile)
    return process
