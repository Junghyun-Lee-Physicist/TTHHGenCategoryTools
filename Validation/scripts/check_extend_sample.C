// ============================================================================
// check_extend_sample.C -- whole-sample check of one ttbarIDExtend production
// ============================================================================
// The all-rows version of check_extend_invariants.C (same contract, same
// verdict line), for the outputs of one CRAB task. Used by
// TtbarIdExtender/crab/extend_manager.py after every job of the task finished.
// Pure ROOT/C++ on purpose (PyROOT is unusable in CMSSW_10_6_32_patch1).
//
// Usage:
//   root -l -b -q 'check_extend_sample.C("files_TTbb_DiLep_2016.txt")'
// The file list has one ROOT file per line (EOS FUSE path or root:// URL);
// empty lines and lines starting with '#' are skipped.
//
// Files are opened one at a time, so a bad file is named, not hidden in a
// chain. Every GetEntry() return value is checked (docs/03 v13.32: an
// unchecked GetEntry was the most dangerous bug found in this project).
// Branch types follow the producer: run UInt_t, the ids and counts Int_t.
//
// Contract checked (canonical definition: docs/02_physics.md):
//   nAddBJets <= 2  ->  Expanded_genTtbarId == genTtbarId
//   nAddBJets == 3  ->  sub-code 61 or 62          nAddBJets >= 4 -> 71 or 72
//   nAddBJets >= 3  ->  prefix (>=100 digits) kept, original sub-code 53/54/55
//   sub-code 56 never appears;  MC -> run == 1
//
// Output (parsed by extend_manager.py -- keep the formats):
//   progress lines  "  progress <k>/<n> files, <entries> entries, <s> s, ETA <s> s"
//   one line        "SAMPLE files=.. bad_open=.. no_tree=.. bad_branch=.. read_errors=..
//                    empty_files=.. entries=.. ge3=.. c61=.. c62=.. c71=.. c72=.."
//   final line      "VERDICT: ALL INVARIANTS PASS" or "VERDICT: FAIL (...)"
// ============================================================================
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#include "TFile.h"
#include "TTree.h"
#include "TStopwatch.h"

void check_extend_sample(const char* filelist) {
   std::ifstream in(filelist);
   if (!in) {
      printf("FAIL: cannot read file list %s\nVERDICT: FAIL (no file list)\n", filelist);
      fflush(stdout);
      return;
   }
   std::vector<std::string> files;
   std::string line;
   while (std::getline(in, line)) {
      if (line.empty() || line[0] == '#') continue;
      files.push_back(line);
   }
   const Long64_t nf = (Long64_t)files.size();
   printf("check_extend_sample: %lld files from %s\n", nf, filelist);
   fflush(stdout);
   if (nf == 0) {
      printf("VERDICT: FAIL (empty file list)\n");
      fflush(stdout);
      return;
   }

   Long64_t entries = 0, bad_open = 0, no_tree = 0, bad_branch = 0, read_err = 0, empty_files = 0;
   Long64_t n_le2_changed = 0, n_eq3_bad = 0, n_ge4_bad = 0, n_sub56 = 0;
   Long64_t n_prefix = 0, n_run_not1 = 0, n_orig_bad = 0;
   Long64_t n_ge3 = 0, n_61 = 0, n_62 = 0, n_71 = 0, n_72 = 0;

   const Long64_t step = (nf >= 10) ? nf / 10 : 1;
   TStopwatch sw;
   sw.Start();
   // progress line every ~10% of the files (and after the last one), also after unreadable files
   auto progress = [&](Long64_t k) {
      if ((k + 1) % step == 0 || k + 1 == nf) {
         const double el = sw.RealTime();
         sw.Continue();
         const double eta = (k + 1 < nf) ? el / (double)(k + 1) * (double)(nf - k - 1) : 0.0;
         printf("  progress %lld/%lld files, %lld entries, %.0f s, ETA %.0f s\n", k + 1, nf, entries, el, eta);
         fflush(stdout);
      }
   };
   for (Long64_t k = 0; k < nf; ++k) {
      const char* fname = files[k].c_str();
      TFile* f = TFile::Open(fname);
      if (!f || f->IsZombie()) {
         ++bad_open;
         printf("  BAD_OPEN %s\n", fname);
         fflush(stdout);
         delete f;
         progress(k);
         continue;
      }
      TTree* t = (TTree*)f->Get("Events");
      if (!t) {
         ++no_tree;
         printf("  NO_TREE %s\n", fname);
         fflush(stdout);
         f->Close();
         delete f;
         progress(k);
         continue;
      }
      const char* need[4] = {"run", "genTtbarId", "Expanded_genTtbarId", "nAddBJets"};
      bool ok = true;
      for (int i = 0; i < 4; ++i) {
         if (!t->GetBranch(need[i])) {
            printf("  MISSING_BRANCH %s in %s\n", need[i], fname);
            ok = false;
         }
      }
      if (!ok) {
         ++bad_branch;
         fflush(stdout);
         f->Close();
         delete f;
         progress(k);
         continue;
      }
      UInt_t run = 0;
      Int_t gid = 0, xid = 0, nb = 0;
      t->SetBranchStatus("*", 0);
      for (int i = 0; i < 4; ++i) t->SetBranchStatus(need[i], 1);
      t->SetBranchAddress("run", &run);
      t->SetBranchAddress("genTtbarId", &gid);
      t->SetBranchAddress("Expanded_genTtbarId", &xid);
      t->SetBranchAddress("nAddBJets", &nb);

      const Long64_t N = t->GetEntries();
      if (N == 0) {
         ++empty_files;
         printf("  EMPTY %s\n", fname);
         fflush(stdout);
      }
      Long64_t file_err = 0;
      for (Long64_t i = 0; i < N; ++i) {
         if (t->GetEntry(i) <= 0) {
            ++file_err;
            continue;
         }
         const int xs = ((xid % 100) + 100) % 100;
         const int gs = ((gid % 100) + 100) % 100;
         if (run != 1) ++n_run_not1;
         if (xs == 56) ++n_sub56;
         if (nb <= 2) {
            if (xid != gid) ++n_le2_changed;
         } else {
            ++n_ge3;
            if (gid / 100 != xid / 100) ++n_prefix;
            if (gs != 53 && gs != 54 && gs != 55) ++n_orig_bad;
            if (nb == 3 && xs != 61 && xs != 62) ++n_eq3_bad;
            if (nb >= 4 && xs != 71 && xs != 72) ++n_ge4_bad;
            if (xs == 61) ++n_61;
            if (xs == 62) ++n_62;
            if (xs == 71) ++n_71;
            if (xs == 72) ++n_72;
         }
      }
      if (file_err) {
         printf("  READ_ERRORS %lld in %s\n", file_err, fname);
         fflush(stdout);
      }
      read_err += file_err;
      entries += N;
      f->Close();
      delete f;
      progress(k);
   }

   printf("SAMPLE files=%lld bad_open=%lld no_tree=%lld bad_branch=%lld read_errors=%lld empty_files=%lld "
          "entries=%lld ge3=%lld c61=%lld c62=%lld c71=%lld c72=%lld\n",
          nf, bad_open, no_tree, bad_branch, read_err, empty_files, entries, n_ge3, n_61, n_62, n_71, n_72);
   printf("  %s  le2_unchanged      violations=%lld\n", n_le2_changed ? "FAIL" : "PASS", n_le2_changed);
   printf("  %s  eq3_in_61_62       violations=%lld\n", n_eq3_bad ? "FAIL" : "PASS", n_eq3_bad);
   printf("  %s  ge4_in_71_72       violations=%lld\n", n_ge4_bad ? "FAIL" : "PASS", n_ge4_bad);
   printf("  %s  no_subcode_56      violations=%lld\n", n_sub56 ? "FAIL" : "PASS", n_sub56);
   printf("  %s  prefix_preserved   violations=%lld\n", n_prefix ? "FAIL" : "PASS", n_prefix);
   printf("  %s  orig_was_53_54_55  violations=%lld\n", n_orig_bad ? "FAIL" : "PASS", n_orig_bad);
   printf("  %s  run_is_1           violations=%lld\n", n_run_not1 ? "FAIL" : "PASS", n_run_not1);
   const bool io_ok = (bad_open == 0 && no_tree == 0 && bad_branch == 0 && read_err == 0);
   const bool inv_ok = (n_le2_changed == 0 && n_eq3_bad == 0 && n_ge4_bad == 0 && n_sub56 == 0 &&
                        n_prefix == 0 && n_orig_bad == 0 && n_run_not1 == 0);
   if (io_ok && inv_ok)
      printf("VERDICT: ALL INVARIANTS PASS\n");
   else if (!io_ok)
      printf("VERDICT: FAIL (unreadable input: bad_open=%lld no_tree=%lld bad_branch=%lld read_errors=%lld)\n",
             bad_open, no_tree, bad_branch, read_err);
   else
      printf("VERDICT: FAIL (invariant violation -- do not use this production)\n");
   fflush(stdout);
}
