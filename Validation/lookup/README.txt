Validation/lookup/ -- per-sample ttbar-Id patch files (analyzer-facing lookups)
===============================================================================
Purpose : one file per stitching sample, holding ONLY the tt+nb rows
          (Expanded_genTtbarId % 100 in {61,62,71,72}, i.e. nAddBJets >= 3),
          keyed by (run, luminosityBlock, event).  The analyzer loads one of
          these and overrides genTtbarId per event by key membership.
Audience: analysis users; anyone re-deriving the lookups.
Status  : DECIDED artifacts, produced 2026-06 from the validated UL17 sidecars.
          Row counts match docs/06_validation_results.md section "extract".
Links   : ../src/extractTtbarIdPatch.cc (producer tool),
          ../../docs/07_analyzer_integration.md (consumer contract).

NAMING NOTE (2026-07-05 rename):
  These seven files were produced BEFORE the tool rename and therefore follow
  the OLD convention:  file ttnb_<sample>.root, internal TTree name "TtNb".
  They are kept byte-identical because (a) the tree name is baked inside each
  file and (b) the current tempTTHH analyzer loader (ExpandedTtbarId class)
  expects exactly this convention.  Files produced from now on default to the
  NEW convention:  ttbarIdPatch_<sample>.root, TTree "TtbarIdPatch"
  (see docs/07_analyzer_integration.md for the coordinated analyzer change,
  status PROPOSED until applied on the analyzer side).

Do not edit these files; re-derive with:
  bin/extractTtbarIdPatch --filelist filelists/ttbarId-extend/filelist_<S>.txt \
      --out <name>.root --label <S>          # add --out-tree TtNb for the old convention
