// -*- C++ -*-
// =============================================================================
// extractTtbarIdPatch  (renamed from extractTtNb, 2026-07-05; logic unchanged)
// =============================================================================
// Build the small "tt+nb lookup" that the analysis actually consumes.
//
// Rationale:
//   The analyzer only needs the extend file for events whose Expanded_genTtbarId
//   differs from genTtbarId, i.e. the reclassified tt+nb events (sub-code in
//   {61,62,71,72}, equivalently nAddBJets >= 3).  Every other event satisfies
//   Expanded_genTtbarId == genTtbarId, a value the analyzer already has from
//   NanoAOD; for those, no lookup is needed.
//
//   Those tt+nb events are rare in the inclusive ttbar samples (tens of
//   thousands out of hundreds of millions) and a manageable ~1.9M in the
//   dedicated tt4b sample.  So instead of carrying the whole multi-hundred-
//   million-row extend file around, we extract ONLY the tt+nb rows into a tiny
//   ROOT TTree.  The analyzer loads this into a (run,lumi,event)->Expanded map
//   (a few MB at most) and, for each event, looks up membership:
//       in map  -> tt+nb, use the stored Expanded_genTtbarId (61/62/71/72)
//       not in  -> use genTtbarId unchanged
//   No genTtbarId sub-code gating is needed, so the "boundary" (b-hadron vs
//   b-jet counting) subtlety never enters: membership alone decides.
//
// Input:  a extend file filelist (the SAME filelist used for validation), one ROOT
//         path per line.  Reads the extend file branches:
//             run/i luminosityBlock/i event/l genTtbarId/I
//             Expanded_genTtbarId/I nAddBJets/I nAddBJetsMulti/I
// Output: a small ROOT file with TTree "TtbarIdPatch" holding only the tt+nb rows,
//         same schema, plus a printed breakdown that should match the
//         matchTtbarId validation log (tt+bbb 61+62, tt+4b 71+72, etc.).
//
// Selection: Expanded_genTtbarId % 100 in {61, 62, 71, 72}.
//   (Equivalently nAddBJets >= 3; both are cross-checked and must agree.)
//
// Usage:
//   extractTtbarIdPatch --filelist filelists/extend file/filelist_tt4b.txt \
//       --out ttbarIdPatch_tt4b.root [--tree Events] [--out-tree TtbarIdPatch] [--label tt4b]
//
// Naming compatibility: until 2026-07-05 this tool was `extractTtNb`, writing
// `ttnb_<sample>.root` with tree `TtNb`.  Logic is unchanged; the old file/tree
// convention can still be produced with `--out ttnb_X.root --out-tree TtNb`.
// The analyzer-side loader contract is in docs/07_analyzer_integration.md.
//
// Exit codes: 0 ok; 2 bad args; 3 empty/missing filelist;
//             7 selection inconsistency (sub-code vs nAddBJets disagree).
// =============================================================================

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#include <TChain.h>
#include <TFile.h>
#include <TTree.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string filelist;
  std::string out;
  std::string tree    = "Events";
  std::string outTree = "TtbarIdPatch";
  std::string label   = "sample";
};

[[noreturn]] void usage(int code) {
  std::printf(
    "extractTtbarIdPatch\n"
    "  --filelist PATH    extend file filelist (one ROOT path per line)\n"
    "  --out PATH         output ROOT file (small tt+nb lookup)\n"
    "  --tree NAME        input tree name  (default Events)\n"
    "  --out-tree NAME    output tree name (default TtbarIdPatch; use TtNb for the pre-rename convention)\n"
    "  --label NAME       label for messages\n"
    "  -h, --help         this help\n");
  std::exit(code);
}

Args parseArgs(int argc, char** argv) {
  Args a;
  auto need = [&](int& i, const char* o) {
    if (i + 1 >= argc) { std::fprintf(stderr, "ERROR: %s needs a value\n", o); std::exit(2); }
    return std::string(argv[++i]);
  };
  for (int i = 1; i < argc; ++i) {
    std::string s = argv[i];
    if      (s == "--filelist") a.filelist = need(i, "--filelist");
    else if (s == "--out")      a.out      = need(i, "--out");
    else if (s == "--tree")     a.tree     = need(i, "--tree");
    else if (s == "--out-tree") a.outTree  = need(i, "--out-tree");
    else if (s == "--label")    a.label    = need(i, "--label");
    else if (s == "-h" || s == "--help") usage(0);
    else { std::fprintf(stderr, "ERROR: unknown arg '%s'\n", s.c_str()); usage(2); }
  }
  if (a.filelist.empty()) { std::fprintf(stderr, "ERROR: --filelist required\n"); usage(2); }
  if (a.out.empty())      { std::fprintf(stderr, "ERROR: --out required\n");      usage(2); }
  return a;
}

std::vector<std::string> readFilelist(const std::string& path) {
  std::vector<std::string> files;
  std::ifstream in(path);
  if (!in) { std::fprintf(stderr, "ERROR: cannot open filelist %s\n", path.c_str()); std::exit(3); }
  std::string line;
  while (std::getline(in, line)) {
    auto a = line.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) continue;
    auto b = line.find_last_not_of(" \t\r\n");
    std::string p = line.substr(a, b - a + 1);
    if (p.empty() || p[0] == '#') continue;
    files.push_back(p);
  }
  return files;
}

inline bool isTtNbSub(int sub) {
  return sub == 61 || sub == 62 || sub == 71 || sub == 72;
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::printf("[extractTtbarIdPatch] start\n");
  std::printf("[extractTtbarIdPatch]   filelist = %s\n", args.filelist.c_str());
  std::printf("[extractTtbarIdPatch]   out      = %s\n", args.out.c_str());
  std::printf("[extractTtbarIdPatch]   label    = %s\n", args.label.c_str());
  std::fflush(stdout);

  const auto files = readFilelist(args.filelist);
  if (files.empty()) { std::fprintf(stderr, "ERROR: filelist empty\n"); return 3; }

  TChain in(args.tree.c_str());
  int added = 0;
  for (const auto& f : files) if (in.Add(f.c_str()) > 0) ++added;

  UInt_t    run = 0, lumi = 0;
  ULong64_t event = 0;
  Int_t     genTtbarId = 0, expandedId = 0, nAddBJets = 0, nAddBJetsMulti = 0;
  in.SetBranchStatus("*", 0);
  for (const char* b : {"run", "luminosityBlock", "event",
                        "genTtbarId", "Expanded_genTtbarId",
                        "nAddBJets", "nAddBJetsMulti"})
    in.SetBranchStatus(b, 1);
  in.SetBranchAddress("run",                 &run);
  in.SetBranchAddress("luminosityBlock",     &lumi);
  in.SetBranchAddress("event",               &event);
  in.SetBranchAddress("genTtbarId",          &genTtbarId);
  in.SetBranchAddress("Expanded_genTtbarId", &expandedId);
  in.SetBranchAddress("nAddBJets",           &nAddBJets);
  in.SetBranchAddress("nAddBJetsMulti",      &nAddBJetsMulti);

  const Long64_t nIn = in.GetEntries();
  std::printf("[extractTtbarIdPatch]   input files=%d, entries=%lld\n", added, nIn);
  std::fflush(stdout);

  // Output: small tt+nb lookup tree (same schema).
  TFile* outF = TFile::Open(args.out.c_str(), "RECREATE");
  if (!outF || outF->IsZombie()) { std::fprintf(stderr, "ERROR: cannot create %s\n", args.out.c_str()); return 4; }
  UInt_t    oRun = 0, oLumi = 0;
  ULong64_t oEvent = 0;
  Int_t     oGen = 0, oExp = 0, oNAdd = 0, oNAddMulti = 0;
  TTree* out = new TTree(args.outTree.c_str(), "tt+nb (Expanded sub in {61,62,71,72}) lookup");
  out->Branch("run",                 &oRun,        "run/i");
  out->Branch("luminosityBlock",     &oLumi,       "luminosityBlock/i");
  out->Branch("event",               &oEvent,      "event/l");
  out->Branch("genTtbarId",          &oGen,        "genTtbarId/I");
  out->Branch("Expanded_genTtbarId", &oExp,        "Expanded_genTtbarId/I");
  out->Branch("nAddBJets",           &oNAdd,       "nAddBJets/I");
  out->Branch("nAddBJetsMulti",      &oNAddMulti,  "nAddBJetsMulti/I");

  // Counters that mirror the matchTtbarId validation log.
  Long64_t nSel = 0;          // selected tt+nb rows
  Long64_t n61 = 0, n62 = 0, n71 = 0, n72 = 0;
  Long64_t nGe3 = 0;          // nAddBJets >= 3 (cross-check)
  Long64_t nMismatch = 0;     // sub in {61,62,71,72} XOR nAddBJets>=3
  std::map<int, Long64_t> fromSub;   // genTtbarId sub-code of selected rows

  for (Long64_t i = 0; i < nIn; ++i) {
    in.GetEntry(i);
    const int esub = ((expandedId % 100) + 100) % 100;
    const bool selBySub = isTtNbSub(esub);
    const bool selByCnt = (nAddBJets >= 3);
    if (selBySub != selByCnt) ++nMismatch;   // must stay 0
    if (selByCnt) ++nGe3;
    if (!selBySub) {
      if ((i % 20000000) == 0 && i > 0) { std::printf("[extractTtbarIdPatch]   scanned %lld / %lld\n", i, nIn); std::fflush(stdout); }
      continue;
    }

    oRun = run; oLumi = lumi; oEvent = event;
    oGen = genTtbarId; oExp = expandedId; oNAdd = nAddBJets; oNAddMulti = nAddBJetsMulti;
    out->Fill();
    ++nSel;
    if      (esub == 61) ++n61;
    else if (esub == 62) ++n62;
    else if (esub == 71) ++n71;
    else if (esub == 72) ++n72;
    fromSub[((genTtbarId % 100) + 100) % 100]++;

    if ((i % 20000000) == 0 && i > 0) { std::printf("[extractTtbarIdPatch]   scanned %lld / %lld\n", i, nIn); std::fflush(stdout); }
  }

  out->Write("", TObject::kOverwrite);
  outF->Close();
  delete outF;

  // ---- report (compare these to the matchTtbarId log) ----
  std::printf("[extractTtbarIdPatch] ===== summary (%s) =====\n", args.label.c_str());
  std::printf("[extractTtbarIdPatch]   input entries                 : %lld\n", nIn);
  std::printf("[extractTtbarIdPatch]   selected tt+nb rows (written)  : %lld\n", nSel);
  std::printf("[extractTtbarIdPatch]   nAddBJets>=3 (cross-check)     : %lld\n", nGe3);
  std::printf("[extractTtbarIdPatch]   tt+bbb (61+62) : %lld   tt+4b (71+72) : %lld\n",
              n61 + n62, n71 + n72);
  std::printf("[extractTtbarIdPatch]     61 : %lld   62 (multi) : %lld   71 : %lld   72 (multi) : %lld\n",
              n61, n62, n71, n72);
  std::printf("[extractTtbarIdPatch]   selected rows by genTtbarId sub-code (expect 53/54/55):\n");
  for (const auto& kv : fromSub)
    std::printf("[extractTtbarIdPatch]       from sub-code %d : %lld\n", kv.first, kv.second);

  bool ok = true;
  if (nMismatch != 0) {
    std::printf("[extractTtbarIdPatch]   >>> ERROR: sub-code-vs-nAddBJets selection disagreed on %lld rows\n", nMismatch);
    ok = false;
  }
  if (nSel != nGe3) {
    std::printf("[extractTtbarIdPatch]   >>> ERROR: selected (%lld) != nAddBJets>=3 (%lld)\n", nSel, nGe3);
    ok = false;
  }
  if (ok)
    std::printf("[extractTtbarIdPatch]   >>> OK: selection consistent (sub in {61,62,71,72} <=> nAddBJets>=3).\n");

  std::printf("[extractTtbarIdPatch] wrote %lld tt+nb rows to %s (tree '%s')\n",
              nSel, args.out.c_str(), args.outTree.c_str());
  std::fflush(stdout);

  return ok ? 0 : 7;
}
