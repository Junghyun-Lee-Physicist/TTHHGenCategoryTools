Validation/lookup2018/ -- 2018 UL per-sample ttbar-Id patch files (analyzer input)
===============================================================================
Purpose : one file per stitching sample, holding ONLY the tt+nb rows
          (Expanded_genTtbarId % 100 in {61,62,71,72}, i.e. nAddBJets >= 3),
          keyed by (run, luminosityBlock, event).  The analyzer loads one of
          these and overrides genTtbarId per event by key membership.
Audience: analysis users; anyone re-deriving the lookups.
Status  : produced 2026-07-28 from the 2018 UL ttbarId-extend output
          (CRAB campaign ttbarIdExtend_v2/2018, 7 tasks / 11,946 jobs, failed 0).
          Row counts are recorded in docs/06_validation_results.md.
Links   : ../tools/extractTtbarIdPatch.cc (producer tool),
          ../../docs/07_analyzer_integration.md (consumer contract).

NAMING: OLD convention on purpose -- file ttnb_<projectKey>.root, TTree "TtNb".
  The tool's default is the NEW convention (ttbarIdPatch_*/TtbarIdPatch, D12),
  so these were produced with an explicit --out-tree TtNb.  Reason: the current
  tempTTHH loader (ExpandedTtbarId) expects TtNb, and the 2017 files in
  ../lookup/ carry that tree name INSIDE the file -- so keeping one convention
  across eras avoids a per-era trap.  Getting it wrong fails SILENTLY (loader
  goes INACTIVE, analyzer uses the raw NanoAOD genTtbarId).
  Next cleanup: make the loader try TtbarIdPatch then fall back to TtNb --
  see docs/07_analyzer_integration.md section 4 and tempTTHH/docs/STATUS.md.

WHY THESE ARE COMMITTED: the analyzer runs at KNU, these are produced on
  lxplus, and they are small (~12 MB total).  Committing them is the transfer
  mechanism.  Same choice as the 2017 files in ../lookup/.

NAME MAPPING (Validation short name -> analyzer project key):
  tt4b              -> TT4b                ttbb_2L2Nu        -> TTbb_DiLep
  ttbb_Hadronic     -> TTbb_Hadronic       TTToHadronic      -> TTbar_Hadronic
  ttbb_SemiLeptonic -> TTbb_SemiLep        TTToSemiLeptonic  -> TTbar_SemiLep
                                           TTTo2L2Nu         -> TTbar_DiLep

Do not edit these files; re-derive with (from Validation/):
  ./bin/extractTtbarIdPatch \
      --filelist filelists/sidecar2018/filelist_<short>.txt \
      --out lookup2018/ttnb_<KEY>.root --out-tree TtNb --label <KEY>_2018
