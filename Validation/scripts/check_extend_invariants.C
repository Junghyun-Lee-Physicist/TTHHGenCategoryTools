// ============================================================================
// check_extend_invariants.C -- local sanity check of a ttbarIDExtend output
// ============================================================================
// Verifies the Expanded_genTtbarId encoding contract on a locally produced
// ttbarIDExtend file, BEFORE spending grid time. Pure ROOT/C++ on purpose:
// PyROOT is unusable in CMSSW_10_6_32_patch1 (ROOT 6.14 there is built against
// python2, so `import ROOT` under python3 dies with
//   ImportError: dynamic module does not define module export function
//                (PyInit_libPyROOT)
// observed 2026-07-27). A compiled-free ROOT macro works in every environment.
//
// Usage (from TTHHGenCategoryTools/Validation, or anywhere):
//   root -l -b -q 'scripts/check_extend_invariants.C("ttbarIDExtend_local2018_numEvent2000.root")'
//
// NOTE ON THE FILENAME: run_ttbarIdExtend_cfg.py uses VarParsing, which appends
// `_numEventN` to outputFile whenever maxEvents is set. A local test with
// maxEvents=2000 therefore writes ttbarIDExtend_local2018_numEvent2000.root,
// not ttbarIDExtend_local2018.root. (CRAB runs without maxEvents, so the grid
// output keeps the plain name that JobType.outputFiles expects.)
//
// Contract checked (canonical definition: docs/02_physics.md):
//   nAddBJets <= 2  ->  Expanded_genTtbarId == genTtbarId          (untouched)
//   nAddBJets == 3  ->  sub-code 61 or 62                          (tt+bbb)
//   nAddBJets >= 4  ->  sub-code 71 or 72                          (tt+4b)
//   for nAddBJets >= 3: prefix (>=100 digits) preserved, and the ORIGINAL
//                       sub-code must have been 53/54/55 (tt+bb bucket)
//   sub-code 56 must NEVER appear (non-existent code; v10 fatal bug, D4)
//   MC -> run == 1 everywhere
//
// Exit: prints PASS/FAIL per invariant and a final verdict line.
// ============================================================================

void check_extend_invariants(const char* fname) {
   TFile* f = TFile::Open(fname);
   if (!f || f->IsZombie()) {
      printf("FAIL: cannot open %s\n", fname);
      return;
   }
   TTree* t = (TTree*)f->Get("Events");
   if (!t) {
      printf("FAIL: no top-level 'Events' tree in %s\n", fname);
      return;
   }

   const char* need[7] = {"run", "luminosityBlock", "event", "genTtbarId",
                          "Expanded_genTtbarId", "nAddBJets", "nAddBJetsMulti"};
   bool branches_ok = true;
   for (int i = 0; i < 7; ++i) {
      if (!t->GetBranch(need[i])) {
         printf("  MISSING BRANCH: %s\n", need[i]);
         branches_ok = false;
      }
   }
   printf("entries : %lld\n", t->GetEntries());
   printf("CHECK0 branches            : %s\n", branches_ok ? "PASS" : "FAIL");
   if (!branches_ok) { printf("\nVERDICT: FAIL\n"); return; }

   UInt_t    run = 0, lumi = 0;
   ULong64_t event = 0;
   Int_t     gid = 0, xid = 0, nb = 0, nbm = 0;
   t->SetBranchAddress("run", &run);
   t->SetBranchAddress("luminosityBlock", &lumi);
   t->SetBranchAddress("event", &event);
   t->SetBranchAddress("genTtbarId", &gid);
   t->SetBranchAddress("Expanded_genTtbarId", &xid);
   t->SetBranchAddress("nAddBJets", &nb);
   t->SetBranchAddress("nAddBJetsMulti", &nbm);

   Long64_t n_le2_changed = 0, n_eq3_bad = 0, n_ge4_bad = 0, n_sub56 = 0;
   Long64_t n_prefix = 0, n_run_not1 = 0, n_orig_bad = 0;
   Long64_t n_ge3 = 0, n_61 = 0, n_62 = 0, n_71 = 0, n_72 = 0;

   const Long64_t N = t->GetEntries();
   for (Long64_t i = 0; i < N; ++i) {
      t->GetEntry(i);
      const int xs = ((xid % 100) + 100) % 100;
      const int gs = ((gid % 100) + 100) % 100;

      if (run != 1) ++n_run_not1;
      if (xs == 56) ++n_sub56;

      if (nb <= 2) {
         if (xid != gid) ++n_le2_changed;
      } else {
         ++n_ge3;
         if (gid / 100 != xid / 100)          ++n_prefix;
         if (gs != 53 && gs != 54 && gs != 55) ++n_orig_bad;
         if (nb == 3 && xs != 61 && xs != 62) ++n_eq3_bad;
         if (nb >= 4 && xs != 71 && xs != 72) ++n_ge4_bad;
         if (xs == 61) ++n_61;
         if (xs == 62) ++n_62;
         if (xs == 71) ++n_71;
         if (xs == 72) ++n_72;
      }
   }

   printf("\nscanned %lld events; nAddBJets>=3 : %lld", N, n_ge3);
   printf("   (61=%lld 62=%lld 71=%lld 72=%lld)\n", n_61, n_62, n_71, n_72);
   if (n_ge3 == 0)
      printf("  NOTE: no nAddBJets>=3 event in this sample slice -- the extension\n"
             "        branch was never exercised. Re-run with a larger maxEvents\n"
             "        (or use tt4b) to actually test it.\n");

   printf("\n");
   printf("  %s  le2_unchanged      violations=%lld\n", n_le2_changed ? "FAIL" : "PASS", n_le2_changed);
   printf("  %s  eq3_in_61_62       violations=%lld\n", n_eq3_bad     ? "FAIL" : "PASS", n_eq3_bad);
   printf("  %s  ge4_in_71_72       violations=%lld\n", n_ge4_bad     ? "FAIL" : "PASS", n_ge4_bad);
   printf("  %s  no_subcode_56      violations=%lld\n", n_sub56       ? "FAIL" : "PASS", n_sub56);
   printf("  %s  prefix_preserved   violations=%lld\n", n_prefix      ? "FAIL" : "PASS", n_prefix);
   printf("  %s  orig_was_53_54_55  violations=%lld\n", n_orig_bad    ? "FAIL" : "PASS", n_orig_bad);
   printf("  %s  run_is_1           violations=%lld\n", n_run_not1    ? "FAIL" : "PASS", n_run_not1);

   const bool all_ok = (n_le2_changed == 0 && n_eq3_bad == 0 && n_ge4_bad == 0 &&
                        n_sub56 == 0 && n_prefix == 0 && n_orig_bad == 0 &&
                        n_run_not1 == 0);
   printf("\nVERDICT: %s\n", all_ok ? "ALL INVARIANTS PASS"
                                    : "INVARIANT VIOLATION -- do not submit");
   f->Close();
}
