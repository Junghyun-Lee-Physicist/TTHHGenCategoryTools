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
//   extractTtbarIdPatch --filelist filelists/sidecar/filelist_tt4b.txt
//       --out ttbarIdPatch_tt4b.root [--tree Events] [--out-tree TtbarIdPatch] [--label tt4b]
//
// Naming compatibility: until 2026-07-05 this tool was `extractTtNb`, writing
// `ttnb_<sample>.root` with tree `TtNb`.  Logic is unchanged; the old file/tree
// convention can still be produced with `--out ttnb_X.root --out-tree TtNb`.
// The analyzer-side loader contract is in docs/07_analyzer_integration.md.
//
// Exit codes: 0 ok; 2 bad args; 3 empty/missing filelist;
//             7 selection inconsistency (sub-code vs nAddBJets disagree).
//
// -----------------------------------------------------------------------------
// FORMAT 2 (2026-11-05, TTHHAnalyzer STEP 45): the key holds the NanoAOD dataset
// -----------------------------------------------------------------------------
// Why: in 2022 / 2022EE the main and ext1 NanoAOD datasets of a ttbar sample use
//   the same (run, luminosityBlock, event) for DIFFERENT events (350,885 shared
//   keys over six samples; TTHHAnalyzer docs/claude-remote/daily/lxplus/files/
//   2026-11-04_dup_scan/main_ext_overlap.tsv). With the key (run, lumi, event)
//   an ext1 event can take a main event's category. And the 2022-23 lookups are
//   extracted from several CRAB outputs per NanoAOD dataset: MiniAODv4 (main,
//   ext1) and, for version A, MiniAODv3 for the events whose v4 parent is gone.
//
// Usage (repeat --input; no --filelist):
//   extractTtbarIdPatch --input <NanoAOD dataset>=<filelist>[:<priority>] [--input ...]
//       --out ttnb_<sample>.root --out-tree TtNb --label <sample>_<era>_<version>
//       [--expect <NanoAOD dataset>=<entries> ...] [--replace] [--tree Events]
//       [--on-conflict stop|report]
//   <NanoAOD dataset> = /<primary>/<processed>/NANOAODSIM, the dataset whose
//   events the CRAB output of <filelist> describes (a MiniAODv3 output of the
//   main production belongs to the main NanoAOD dataset). <priority> = the
//   digits after the last ':' (0-999999, default 0); a filelist whose own name
//   ends in ':<digits>' is refused when the name without them is no file.
//   --expect: the entries summed over the inputs of that dataset must be
//   exactly <entries> (the CRAB outputs' event counts: v4 = the dataset's
//   events, v3 = the events of its masked lumis), else exit 6.
//   --replace: an existing --out is replaced, on success only; without it an
//   existing --out is refused (exit 4).
// Rules:
//   - EVERY row is compared with every other row of its key in its dataset,
//     whatever its category, whichever input is held or streamed, and also two
//     rows of one key inside ONE input: a different genTtbarId or
//     Expanded_genTtbarId is a conflict -> exit 8, nothing written
//     (--on-conflict report counts them instead and ends with RESULT WARN;
//     never the default, a diagnosis). Equal rows of one key inside one input
//     are kept once (counted).
//   - Between two inputs of one dataset the row of the LOWER priority number is
//     kept (MiniAODv4 = 0 over MiniAODv3 = 1); equal numbers keep the earlier
//     --input. The same key in two datasets is two keys: both rows are kept.
//   - Every input must have entries (0 entries: exit 6), and no sidecar file
//     may be in two inputs or twice in one (compared by normalized path: '..',
//     '//' and symlinks of a local file, the door of a URL dropped; exit 2).
// Output (format 2): the same tree name and branches as format 1 plus
//   datasetIdx/I; TNamed nano_datasets (every dataset given, sorted by name, one
//   per line -- also one with no tt+nb row; datasetIdx = the line number from
//   0); TNamed lookup_format = "tthh-ttnb/2"; TNamed sources (per input: its
//   dataset, priority, filelist, files, entries, rows superseded by a lower
//   number, tt+nb rows written; the entries per dataset and their --expect).
//   Rows sorted by (datasetIdx, run, lumi, event), each key once. The file is
//   written as <out>.tmp.<pid> and renamed to <out> only when everything passed:
//   a failure leaves no file and no half-written one.
// Memory and passes: per dataset, the inputs other than its largest are held in
//   memory (32 bytes per row, every row); the largest is streamed through a
//   Bloom filter of its keys (12 bits per row): if a key may repeat in it, it is
//   read a second time and the rows of those keys are compared exactly. The log
//   says how much memory and whether a second pass ran.
// Format-2 exit codes, each with a last line 'RESULT FAIL ... (exit N)':
//   0 ok (or RESULT WARN with --on-conflict report); 2 bad args, or one sidecar
//   file twice; 3 a filelist missing or empty; 4 the output exists (no
//   --replace) or cannot be written; 5 an input file that cannot be opened,
//   lacks the tree or a branch, or an entry that cannot be read; 6 the entries
//   (an input with 0, a dataset's sum not its --expect); 7 selection
//   inconsistency (as format 1); 8 a conflict.
// The lines: "[extractTtbarIdPatch] ..." with progress (i / N, elapsed, ETA)
//   and the last line "RESULT OK|WARN|FAIL extractTtbarIdPatch format 2 ...".
// Format 1 (--filelist) is unchanged, byte for byte (Validation/tests/
//   test_extract_format2.sh compares it with the tool before format 2).
// The analyzer side: TTHHAnalyzer include/ExpandedTtbarId.h, this repo's
//   docs/07_analyzer_integration.md section 5.
// =============================================================================

#include <algorithm>
#include <chrono>
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include <sys/stat.h>
#include <unistd.h>

#include <TChain.h>
#include <TFile.h>
#include <TNamed.h>
#include <TTree.h>
#include <RtypesCore.h>

namespace {

// [format 2] one --input: the CRAB output (filelist) of the events of one NanoAOD dataset
struct InputSpec {
  std::string dataset, filelist;
  int priority = 0;
  int order    = 0;                   // its place on the command line
  // filled while running
  int ds = -1, rank = -1;
  std::vector<std::string> files;
  long long entries = 0, superseded = 0, written = 0;
};

struct Args {
  std::string filelist;
  std::string out;
  std::string tree    = "Events";
  std::string outTree = "TtbarIdPatch";
  std::string label   = "sample";
  std::vector<InputSpec> inputs;      // [format 2] --input
  bool conflictReport = false;        // [format 2] --on-conflict report
  bool conflictGiven  = false;
  std::vector<std::pair<std::string, long long>> expects;   // [format 2] --expect <dataset>=<entries>
  bool replace = false;               // [format 2] --replace
};

[[noreturn]] void usage(int code) {
  std::printf(
    "extractTtbarIdPatch\n"
    "  --filelist PATH    extend file filelist (one ROOT path per line): format 1, key (run, lumi, event)\n"
    "  --input DS=FILELIST[:PRIORITY]\n"
    "                     format 2 (repeat it; no --filelist): the extend files of NanoAOD dataset DS\n"
    "                     (/<primary>/<processed>/NANOAODSIM); key (datasetIdx, run, lumi, event). Within a\n"
    "                     dataset a key in two inputs keeps the LOWER PRIORITY (default 0; MiniAODv4 0, v3 1)\n"
    "  --expect DS=N      format 2 (repeat it): the entries of dataset DS's inputs must add up to N (exit 6)\n"
    "  --replace          format 2: replace an existing --out (on success only); without it: exit 4\n"
    "  --on-conflict stop|report\n"
    "                     format 2: two rows of one key in one dataset disagree on genTtbarId /\n"
    "                     Expanded_genTtbarId -> stop (default, exit 8) or count them (RESULT WARN)\n"
    "  --out PATH         output ROOT file (small tt+nb lookup)\n"
    "  --tree NAME        input tree name  (default Events)\n"
    "  --out-tree NAME    output tree name (default TtbarIdPatch; use TtNb for the pre-rename convention)\n"
    "  --label NAME       label for messages\n"
    "  -h, --help         this help\n");
  std::exit(code);
}

// [format 2] a usage error of a format-2 command line (one with --input): the ERROR line and the last line
//   'RESULT FAIL ... (exit 2)'. Format 1 keeps its messages as they were.
[[noreturn]] void argFail2(const std::string& msg) {
  std::fprintf(stderr, "ERROR: %s\n", msg.c_str());
  std::fflush(stderr);
  std::printf("RESULT FAIL extractTtbarIdPatch format 2: %s (exit 2)\n", msg.c_str());
  std::fflush(stdout);
  std::exit(2);
}

bool fileExists(const std::string& p) {
  struct stat st;
  return ::stat(p.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

// [format 2] /<primary>/<processed>/NANOAODSIM: three non-empty parts (the analyzer's datasetOfPath gives this form)
bool isNanoDataset(const std::string& s) {
  const std::string tier = "/NANOAODSIM";
  if (s.size() <= tier.size() || s[0] != '/' || s.compare(s.size() - tier.size(), tier.size(), tier) != 0) return false;
  int parts = 0;
  std::size_t p = 1;
  while (p <= s.size()) {
    std::size_t q = s.find('/', p);
    if (q == std::string::npos) q = s.size();
    if (q == p) return false;
    ++parts;
    p = q + 1;
  }
  return parts == 3;
}

// [format 2] DS=FILELIST[:PRIORITY] (the priority: the digits after the last ':')
void parseInput(const std::string& spec, InputSpec& in) {
  const std::size_t eq = spec.find('=');
  if (eq == std::string::npos || eq == 0 || eq + 1 >= spec.size())
    argFail2("--input '" + spec + "': not <NanoAOD dataset>=<filelist>[:<priority>]");
  in.dataset = spec.substr(0, eq);
  std::string rest = spec.substr(eq + 1);
  const std::size_t c = rest.rfind(':');
  if (c != std::string::npos && c + 1 < rest.size() &&
      rest.find_first_not_of("0123456789", c + 1) == std::string::npos) {
    const std::string num = rest.substr(c + 1);
    if (num.size() > 6) argFail2("--input '" + spec + "': priority '" + num + "' is too large");
    // a filelist whose own name ends in ':<digits>' would be read as another file with a priority: refuse it
    if (!fileExists(rest.substr(0, c)) && fileExists(rest))
      argFail2("--input '" + spec + "': the filelist name ends in ':" + num + "', which --input reads as the "
               "priority, and '" + rest.substr(0, c) + "' is no file -- rename the filelist");
    in.priority = std::atoi(num.c_str());
    rest = rest.substr(0, c);
  }
  in.filelist = rest;
  if (in.filelist.empty()) argFail2("--input '" + spec + "': no filelist");
  if (!isNanoDataset(in.dataset))
    argFail2("--input '" + spec + "': '" + in.dataset + "' is not a NanoAOD dataset /<primary>/<processed>/NANOAODSIM");
}

// [format 2] DS=N
void parseExpect(const std::string& spec, Args& a) {
  const std::size_t eq = spec.rfind('=');
  const std::string ds = eq == std::string::npos ? spec : spec.substr(0, eq);
  const std::string num = eq == std::string::npos ? std::string() : spec.substr(eq + 1);
  if (!isNanoDataset(ds) || num.empty() || num.size() > 18 || num.find_first_not_of("0123456789") != std::string::npos)
    argFail2("--expect '" + spec + "': not <NanoAOD dataset>=<entries>");
  for (const auto& e : a.expects)
    if (e.first == ds) argFail2("--expect: " + ds + " is given twice");
  a.expects.push_back(std::make_pair(ds, std::atoll(num.c_str())));
}

Args parseArgs(int argc, char** argv) {
  Args a;
  bool f2 = false;   // a format-2 command line (--input anywhere): its failures end with a RESULT FAIL line
  for (int i = 1; i < argc; ++i)
    if (std::string(argv[i]) == "--input") f2 = true;
  auto need = [&](int& i, const char* o) {
    if (i + 1 >= argc) {
      if (f2) argFail2(std::string(o) + " needs a value");
      std::fprintf(stderr, "ERROR: %s needs a value\n", o); std::exit(2);
    }
    return std::string(argv[++i]);
  };
  for (int i = 1; i < argc; ++i) {
    std::string s = argv[i];
    if      (s == "--filelist") a.filelist = need(i, "--filelist");
    else if (s == "--out")      a.out      = need(i, "--out");
    else if (s == "--tree")     a.tree     = need(i, "--tree");
    else if (s == "--out-tree") a.outTree  = need(i, "--out-tree");
    else if (s == "--label")    a.label    = need(i, "--label");
    else if (s == "--input") {
      InputSpec in;
      parseInput(need(i, "--input"), in);
      in.order = static_cast<int>(a.inputs.size());
      a.inputs.push_back(in);
    }
    else if (s == "--on-conflict") {
      const std::string v = need(i, "--on-conflict");
      if (v != "stop" && v != "report") {
        if (f2) argFail2("--on-conflict '" + v + "': stop or report");
        std::fprintf(stderr, "ERROR: --on-conflict '%s': stop or report\n", v.c_str());
        std::exit(2);
      }
      a.conflictReport = (v == "report");
      a.conflictGiven  = true;
    }
    else if (s == "--expect") {
      const std::string v = need(i, "--expect");
      if (!f2) { std::fprintf(stderr, "ERROR: --expect is for --input (format 2)\n"); std::exit(2); }
      parseExpect(v, a);
    }
    else if (s == "--replace") {
      if (!f2) { std::fprintf(stderr, "ERROR: --replace is for --input (format 2)\n"); std::exit(2); }
      a.replace = true;
    }
    else if (s == "-h" || s == "--help") usage(0);
    else {
      if (f2) argFail2("unknown arg '" + s + "'");
      std::fprintf(stderr, "ERROR: unknown arg '%s'\n", s.c_str()); usage(2);
    }
  }
  if (!a.filelist.empty() && !a.inputs.empty()) argFail2("--filelist (format 1) and --input (format 2) do not mix");
  if (a.filelist.empty() && a.inputs.empty()) {
    std::fprintf(stderr, "ERROR: --filelist (format 1) or --input (format 2) required\n");
    usage(2);
  }
  if (a.conflictGiven && a.inputs.empty()) {
    std::fprintf(stderr, "ERROR: --on-conflict is for --input (format 2)\n");
    std::exit(2);
  }
  for (const auto& e : a.expects) {
    bool named = false;
    for (const auto& in : a.inputs) named = named || in.dataset == e.first;
    if (!named) argFail2("--expect " + e.first + ": no --input names this dataset");
  }
  if (a.out.empty()) {
    if (f2) argFail2("--out required");
    std::fprintf(stderr, "ERROR: --out required\n"); usage(2);
  }
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

// =============================================================================
// format 1: --filelist (the tool as it was before format 2; keep it byte for byte)
// =============================================================================
int runFormat1(const Args& args) {
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

// =============================================================================
// format 2: --input (the key holds the NanoAOD dataset)
// =============================================================================
const char* kFormat2 = "tthh-ttnb/2";

// a format-2 failure: main prints 'RESULT FAIL ... <why> (exit <code>)' and returns the code; nothing is written
struct Stop { int code; std::string why; };
[[noreturn]] void stop2(int code, const std::string& why) { throw Stop{code, why}; }

// [format 2] the filelist of an input (exit 3 when it cannot be read or is empty)
std::vector<std::string> readFilelist2(const std::string& path, const std::string& what) {
  std::ifstream in(path);
  if (!in) {
    std::fprintf(stderr, "ERROR: %s: cannot open the filelist %s\n", what.c_str(), path.c_str());
    stop2(3, what + ": cannot open the filelist " + path);
  }
  std::vector<std::string> files;
  std::string line;
  while (std::getline(in, line)) {
    auto a = line.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) continue;
    auto b = line.find_last_not_of(" \t\r\n");
    std::string p = line.substr(a, b - a + 1);
    if (p.empty() || p[0] == '#') continue;
    files.push_back(p);
  }
  if (files.empty()) {
    std::fprintf(stderr, "ERROR: %s: the filelist %s is empty\n", what.c_str(), path.c_str());
    stop2(3, what + ": the filelist " + path + " is empty");
  }
  return files;
}

// [format 2] a sidecar file's path for the same-file check: a URL loses its door (root://host//path -> /path: one
//   file through two doors is one file), a local file that exists is resolved (realpath: symlinks, '..', '//'), else
//   the path is made absolute; then '//', '.' and '..' are resolved by name
std::string normalizedPath(const std::string& given) {
  std::string s = given;
  const std::size_t sch = s.find("://");
  if (sch != std::string::npos) {
    const std::size_t q = s.find('/', sch + 3);
    s = (q == std::string::npos) ? std::string("/") : s.substr(q);
    const std::size_t opt = s.find('?');
    if (opt != std::string::npos) s = s.substr(0, opt);
  } else {
    char buf[PATH_MAX];
    if (::realpath(s.c_str(), buf) != nullptr) return std::string(buf);
    if (s.empty() || s[0] != '/') {
      char cwd[PATH_MAX];
      if (::getcwd(cwd, sizeof cwd) != nullptr) s = std::string(cwd) + "/" + s;
    }
  }
  std::vector<std::string> parts;
  std::size_t p = 0;
  while (p <= s.size()) {
    std::size_t q = s.find('/', p);
    if (q == std::string::npos) q = s.size();
    const std::string part = s.substr(p, q - p);
    if (part == "..") {
      if (!parts.empty()) parts.pop_back();
    } else if (!part.empty() && part != ".") {
      parts.push_back(part);
    }
    p = q + 1;
  }
  std::string out;
  for (const auto& x : parts) out += "/" + x;
  return out.empty() ? std::string("/") : out;
}

// one sidecar row held in memory (the inputs of a dataset other than its largest): 32 bytes
struct MemRow {
  std::uint64_t event;
  std::uint32_t run, lumi;
  std::int32_t  gen, exp;
  std::int16_t  nadd, nmulti;
  std::uint16_t rank;        // the input's rank in its dataset (0 = lowest priority number, then the earliest --input)
  std::uint16_t input;       // the index of the --input
};

// one output row (tt+nb)
struct OutRow {
  std::int32_t  ds;
  std::uint32_t run, lumi;
  std::uint64_t event;
  std::int32_t  gen, exp, nadd, nmulti;
  std::int32_t  rank, input;
};

// a key, and a row of the second pass over the streamed input (the keys that may repeat in it)
struct Key3 {
  std::uint32_t run, lumi;
  std::uint64_t event;
};
struct OccRow {
  Key3 k;
  std::int32_t gen, exp, nadd, nmulti;
  std::uint64_t seq;         // the row's place in the input
};

bool keyLess(std::uint32_t r1, std::uint32_t l1, std::uint64_t e1, std::uint32_t r2, std::uint32_t l2, std::uint64_t e2) {
  if (r1 != r2) return r1 < r2;
  if (l1 != l2) return l1 < l2;
  return e1 < e2;
}
bool key3Less(const Key3& a, const Key3& b) { return keyLess(a.run, a.lumi, a.event, b.run, b.lumi, b.event); }
bool key3Eq(const Key3& a, const Key3& b) { return a.run == b.run && a.lumi == b.lumi && a.event == b.event; }

// a Bloom filter over the keys of the streamed input: 12 bits per row, 8 probes (about 0.3 % false positives).
//   testAndSet(): true when the key may have been seen before in this input -- it then gets the exact check
class KeyBloom {
 public:
  explicit KeyBloom(long long n) {
    std::uint64_t bits = static_cast<std::uint64_t>(n > 0 ? n : 1) * 12;
    if (bits < 4096) bits = 4096;
    _words.assign(static_cast<std::size_t>((bits + 63) / 64), 0);
    _nbits = static_cast<std::uint64_t>(_words.size()) * 64;
  }
  bool testAndSet(std::uint32_t run, std::uint32_t lumi, std::uint64_t event) {
    const std::uint64_t h1 = mix(event ^ mix((static_cast<std::uint64_t>(run) << 32) | lumi));
    const std::uint64_t h2 = mix(h1 ^ 0x9e3779b97f4a7c15ULL) | 1ULL;
    bool all = true;
    for (std::uint64_t i = 0; i < 8; ++i) {
      const std::uint64_t b = (h1 + i * h2) % _nbits;
      std::uint64_t& w = _words[static_cast<std::size_t>(b >> 6)];
      const std::uint64_t m = 1ULL << (b & 63);
      if (!(w & m)) {
        all = false;
        w |= m;
      }
    }
    return all;
  }
  static double megabytesFor(long long n) {
    const double bits = static_cast<double>(n > 0 ? n : 1) * 12.0;
    return (bits < 4096 ? 4096 : bits) / 8.0 / 1048576.0;
  }

 private:
  static std::uint64_t mix(std::uint64_t x) {   // splitmix64
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
  }
  std::vector<std::uint64_t> _words;
  std::uint64_t _nbits = 0;
};

class Format2 {
 public:
  explicit Format2(Args& a) : _a(a), _t0(std::chrono::steady_clock::now()) {}
  ~Format2() {
    if (!_tmpPath.empty()) std::remove(_tmpPath.c_str());   // a failure leaves no temporary file
  }
  int run();

 private:
  // the sidecar of one input, opened file by file
  struct Reader {
    std::unique_ptr<TChain> chain;
    UInt_t    run = 0, lumi = 0;
    ULong64_t event = 0;
    Int_t     gen = 0, exp = 0, nadd = 0, nmulti = 0;
  };

  void openInput_(InputSpec& in, Reader& r);
  void readRow_(Reader& r, const InputSpec& in, Long64_t i);
  void count_(int exp, int nadd);
  void progress_(bool force);
  void conflict_(const InputSpec& d1, const InputSpec& d2, std::uint32_t run, std::uint32_t lumi, std::uint64_t event,
                 int gen1, int exp1, int gen2, int exp2);
  void keep_(int ds, const InputSpec& in, std::uint32_t run, std::uint32_t lumi, std::uint64_t event, int gen, int exp,
             int nadd, int nmulti);
  void dataset_(int d);
  void repeats_(int d, InputSpec& in, std::vector<Key3>& cand);
  void prepareOutput_();
  double elapsed_() const {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - _t0).count();
  }

  Args& _a;
  std::chrono::steady_clock::time_point _t0;
  std::vector<std::string> _datasets;   // sorted: the index = datasetIdx
  std::vector<long long> _dsEntries;    // per dataset: the entries of its inputs
  std::vector<OutRow> _out;
  std::string _outPath, _outOpts, _tmpPath;
  long long _total = 0, _scanned = 0, _nextReport = 20000000;
  long long _nSel = 0, _nGe3 = 0, _nMismatch = 0;     // every row read (first pass), as format 1
  long long _nShared = 0, _nConflicts = 0, _nOtherCounts = 0, _nDupOut = 0, _nRepeatWithin = 0, _nSecondPass = 0;
  int _conflictsShown = 0;
};

void Format2::openInput_(InputSpec& in, Reader& r) {
  r.chain.reset(new TChain(_a.tree.c_str()));
  for (const auto& f : in.files)
    if (r.chain->Add(f.c_str(), 0) <= 0) {   // nentries 0: the file is opened and its tree read now
      std::fprintf(stderr, "ERROR: --input %s: the file %s cannot be opened or has no tree '%s'\n",
                   in.filelist.c_str(), f.c_str(), _a.tree.c_str());
      stop2(5, "--input " + in.filelist + ": the file " + f + " cannot be opened or has no tree '" + _a.tree + "'");
    }
  in.entries = r.chain->GetEntries();
  if (in.entries <= 0) return;
  r.chain->LoadTree(0);
  TChain& c = *r.chain;
  c.SetBranchStatus("*", 0);
  const char* names[] = {"run", "luminosityBlock", "event", "genTtbarId", "Expanded_genTtbarId", "nAddBJets",
                         "nAddBJetsMulti"};
  for (const char* b : names) {
    if (!c.GetBranch(b)) {
      std::fprintf(stderr, "ERROR: --input %s: no branch %s in the tree '%s'\n", in.filelist.c_str(), b,
                   _a.tree.c_str());
      stop2(5, "--input " + in.filelist + ": no branch " + b + " in the tree '" + _a.tree + "'");
    }
    c.SetBranchStatus(b, 1);
  }
  const int rc[] = {c.SetBranchAddress("run", &r.run), c.SetBranchAddress("luminosityBlock", &r.lumi),
                    c.SetBranchAddress("event", &r.event), c.SetBranchAddress("genTtbarId", &r.gen),
                    c.SetBranchAddress("Expanded_genTtbarId", &r.exp), c.SetBranchAddress("nAddBJets", &r.nadd),
                    c.SetBranchAddress("nAddBJetsMulti", &r.nmulti)};
  for (std::size_t k = 0; k < sizeof(rc) / sizeof(rc[0]); ++k)
    if (rc[k] < 0) {
      std::fprintf(stderr, "ERROR: --input %s: the branch %s is not of the type the extend file has "
                   "(run/i luminosityBlock/i event/l genTtbarId/I Expanded_genTtbarId/I nAddBJets/I nAddBJetsMulti/I; "
                   "SetBranchAddress %d)\n", in.filelist.c_str(), names[k], rc[k]);
      stop2(5, "--input " + in.filelist + ": the branch " + names[k] + " is not of the extend file's type");
    }
}

void Format2::readRow_(Reader& r, const InputSpec& in, Long64_t i) {
  if (r.chain->GetEntry(i) <= 0) {
    std::fprintf(stderr, "ERROR: --input %s: entry %lld cannot be read\n", in.filelist.c_str(), (long long)i);
    stop2(5, "--input " + in.filelist + ": entry " + std::to_string((long long)i) + " cannot be read");
  }
  ++_scanned;
  progress_(false);
}

void Format2::count_(int exp, int nadd) {
  const int esub = ((exp % 100) + 100) % 100;
  const bool selBySub = isTtNbSub(esub);
  const bool selByCnt = (nadd >= 3);
  if (selBySub != selByCnt) ++_nMismatch;   // must stay 0
  if (selByCnt) ++_nGe3;
  if (selBySub) ++_nSel;
}

void Format2::progress_(bool force) {
  if (!force && _scanned < _nextReport) return;
  while (_nextReport <= _scanned) _nextReport += 20000000;
  const double t = elapsed_();
  const double frac = _total > 0 ? static_cast<double>(_scanned) / static_cast<double>(_total) : 1.0;
  const double eta = (frac > 0 && frac < 1) ? t * (1.0 - frac) / frac : 0.0;
  std::printf("[extractTtbarIdPatch]   scanned %lld / %lld (%.1f %%), elapsed %.0f s, ETA %.0f s\n", _scanned, _total,
              100.0 * frac, t, eta);
  std::fflush(stdout);
}

void Format2::conflict_(const InputSpec& d1, const InputSpec& d2, std::uint32_t run, std::uint32_t lumi,
                        std::uint64_t event, int gen1, int exp1, int gen2, int exp2) {
  ++_nConflicts;
  const bool same = (d1.order == d2.order);
  if (_conflictsShown < 20) {
    ++_conflictsShown;
    std::printf("[extractTtbarIdPatch]   CONFLICT dataset %s, key (run %u, lumi %u, event %llu)%s: %s (priority %d) "
                "genTtbarId %d Expanded_genTtbarId %d; %s (priority %d) genTtbarId %d Expanded_genTtbarId %d\n",
                d1.dataset.c_str(), run, lumi, (unsigned long long)event, same ? " twice in one input" : "",
                d1.filelist.c_str(), d1.priority, gen1, exp1, d2.filelist.c_str(), d2.priority, gen2, exp2);
    std::fflush(stdout);
  }
  if (!_a.conflictReport)
    stop2(8, std::string("two rows of one key of one NanoAOD dataset") + (same ? " (in one input)" : "") +
             " disagree on genTtbarId or Expanded_genTtbarId (the CONFLICT line above) -- nothing written; "
             "--on-conflict report counts every conflict instead");
}

void Format2::keep_(int ds, const InputSpec& in, std::uint32_t run, std::uint32_t lumi, std::uint64_t event, int gen,
                    int exp, int nadd, int nmulti) {
  if (!isTtNbSub(((exp % 100) + 100) % 100)) return;
  OutRow o;
  o.ds = ds; o.run = run; o.lumi = lumi; o.event = event; o.gen = gen; o.exp = exp; o.nadd = nadd; o.nmulti = nmulti;
  o.rank = in.rank; o.input = in.order;
  _out.push_back(o);
}

// the keys of the streamed input that may repeat in it (the Bloom filter): read it again and compare their rows
void Format2::repeats_(int d, InputSpec& in, std::vector<Key3>& cand) {
  std::sort(cand.begin(), cand.end(), key3Less);
  cand.erase(std::unique(cand.begin(), cand.end(), key3Eq), cand.end());
  ++_nSecondPass;
  _total += in.entries;
  std::printf("[extractTtbarIdPatch] dataset [%d]: %zu key(s) may repeat in %s (Bloom filter): reading it again to "
              "compare their rows exactly\n", d, cand.size(), in.filelist.c_str());
  std::fflush(stdout);
  std::vector<OccRow> occ;
  Reader r;
  openInput_(in, r);
  for (Long64_t i = 0; i < in.entries; ++i) {
    readRow_(r, in, i);
    const Key3 k{r.run, r.lumi, r.event};
    const auto it = std::lower_bound(cand.begin(), cand.end(), k, key3Less);
    if (it == cand.end() || !key3Eq(*it, k)) continue;
    OccRow o;
    o.k = k; o.gen = r.gen; o.exp = r.exp; o.nadd = r.nadd; o.nmulti = r.nmulti;
    o.seq = static_cast<std::uint64_t>(i);
    occ.push_back(o);
  }
  std::sort(occ.begin(), occ.end(), [](const OccRow& x, const OccRow& y) {
    if (!key3Eq(x.k, y.k)) return key3Less(x.k, y.k);
    return x.seq < y.seq;
  });
  long long rep = 0;
  for (std::size_t i = 0; i < occ.size();) {
    std::size_t j = i + 1;
    while (j < occ.size() && key3Eq(occ[j].k, occ[i].k)) {
      const OccRow& a = occ[i];
      const OccRow& b = occ[j];
      if (a.gen != b.gen || a.exp != b.exp)
        conflict_(in, in, a.k.run, a.k.lumi, a.k.event, a.gen, a.exp, b.gen, b.exp);
      else if (a.nadd != b.nadd || a.nmulti != b.nmulti)
        ++_nOtherCounts;
      ++rep;
      ++j;
    }
    i = j;
  }
  _nRepeatWithin += rep;
  std::printf("[extractTtbarIdPatch] dataset [%d]: %lld repeated row(s) of a key in %s, all compared (%zu candidate "
              "key(s), the rest Bloom false positives)\n", d, rep, in.filelist.c_str(), cand.size());
  std::fflush(stdout);
}

// one NanoAOD dataset: its inputs by rank; all but the largest in memory, the largest streamed
void Format2::dataset_(int d) {
  std::vector<InputSpec*> ins;
  for (auto& in : _a.inputs)
    if (in.ds == d) ins.push_back(&in);
  std::sort(ins.begin(), ins.end(), [](const InputSpec* x, const InputSpec* y) {
    return x->priority != y->priority ? x->priority < y->priority : x->order < y->order;
  });
  for (std::size_t k = 0; k < ins.size(); ++k) ins[k]->rank = static_cast<int>(k);
  std::size_t L = 0;   // the largest input (ties: the lowest rank)
  for (std::size_t k = 1; k < ins.size(); ++k)
    if (ins[k]->entries > ins[L]->entries) L = k;
  long long held = 0;
  for (std::size_t k = 0; k < ins.size(); ++k)
    if (k != L) held += ins[k]->entries;
  std::printf("[extractTtbarIdPatch] dataset [%d] %s: %zu input(s)", d, _datasets[d].c_str(), ins.size());
  if (ins.size() > 1)
    std::printf("; held in memory: %lld rows of %zu input(s) (~%.1f MB)", held, ins.size() - 1,
                held * static_cast<double>(sizeof(MemRow)) / 1048576.0);
  std::printf("; streamed: %s (%lld entries, Bloom filter ~%.1f MB)\n", ins[L]->filelist.c_str(), ins[L]->entries,
              KeyBloom::megabytesFor(ins[L]->entries));
  std::fflush(stdout);

  // ---- the inputs held in memory (every row: a key in two inputs, or twice in one, is compared whatever its category)
  std::vector<MemRow> mem;
  mem.reserve(static_cast<std::size_t>(held));
  for (std::size_t k = 0; k < ins.size(); ++k) {
    if (k == L) continue;
    InputSpec& in = *ins[k];
    Reader r;
    openInput_(in, r);
    for (Long64_t i = 0; i < in.entries; ++i) {
      readRow_(r, in, i);
      count_(r.exp, r.nadd);
      if (r.nadd < -32768 || r.nadd > 32767 || r.nmulti < -32768 || r.nmulti > 32767) {
        std::fprintf(stderr, "ERROR: --input %s: entry %lld has nAddBJets %d / nAddBJetsMulti %d outside 16 bits\n",
                     in.filelist.c_str(), (long long)i, r.nadd, r.nmulti);
        stop2(5, "--input " + in.filelist + ": nAddBJets / nAddBJetsMulti outside 16 bits");
      }
      MemRow m;
      m.event = r.event; m.run = r.run; m.lumi = r.lumi; m.gen = r.gen; m.exp = r.exp;
      m.nadd = static_cast<std::int16_t>(r.nadd); m.nmulti = static_cast<std::int16_t>(r.nmulti);
      m.rank = static_cast<std::uint16_t>(in.rank); m.input = static_cast<std::uint16_t>(in.order);
      mem.push_back(m);
    }
  }
  std::sort(mem.begin(), mem.end(), [](const MemRow& x, const MemRow& y) {
    if (x.run != y.run || x.lumi != y.lumi || x.event != y.event) return keyLess(x.run, x.lumi, x.event, y.run, y.lumi, y.event);
    return x.rank < y.rank;
  });
  // one row per key: the lowest rank; every other row of the key (another input, or the same one) must agree
  std::size_t w = 0;
  long long shared = 0;
  for (std::size_t i = 0; i < mem.size();) {
    std::size_t j = i + 1;
    bool two = false;
    while (j < mem.size() && mem[j].run == mem[i].run && mem[j].lumi == mem[i].lumi && mem[j].event == mem[i].event) {
      const MemRow& a = mem[i];
      const MemRow& b = mem[j];
      if (a.gen != b.gen || a.exp != b.exp)
        conflict_(_a.inputs[a.input], _a.inputs[b.input], a.run, a.lumi, a.event, a.gen, a.exp, b.gen, b.exp);
      else if (a.nadd != b.nadd || a.nmulti != b.nmulti)
        ++_nOtherCounts;
      if (a.input == b.input) ++_nRepeatWithin;
      else two = true;
      if (b.rank != a.rank) ++_a.inputs[b.input].superseded;
      ++j;
    }
    if (two) ++shared;
    mem[w++] = mem[i];
    i = j;
  }
  mem.resize(w);
  std::unordered_set<std::uint64_t> lumis;
  for (const MemRow& m : mem) lumis.insert((static_cast<std::uint64_t>(m.run) << 32) | m.lumi);
  std::vector<unsigned char> taken(mem.size(), 0);   // 1: the streamed input's row replaced this one (lower number)

  // ---- the largest input, streamed: every row against the held rows of its key; its own repeats via the Bloom filter
  {
    InputSpec& in = *ins[L];
    Reader r;
    openInput_(in, r);
    KeyBloom bloom(in.entries);
    std::vector<Key3> cand;
    for (Long64_t i = 0; i < in.entries; ++i) {
      readRow_(r, in, i);
      count_(r.exp, r.nadd);
      if (bloom.testAndSet(r.run, r.lumi, r.event)) cand.push_back(Key3{r.run, r.lumi, r.event});
      if (!mem.empty() && lumis.count((static_cast<std::uint64_t>(r.run) << 32) | r.lumi)) {
        const auto it = std::lower_bound(mem.begin(), mem.end(), r, [](const MemRow& m, const Reader& x) {
          return keyLess(m.run, m.lumi, m.event, x.run, x.lumi, x.event);
        });
        if (it != mem.end() && it->run == r.run && it->lumi == r.lumi && it->event == r.event) {
          ++shared;
          if (it->gen != r.gen || it->exp != r.exp)
            conflict_(_a.inputs[it->input], in, r.run, r.lumi, r.event, it->gen, it->exp, r.gen, r.exp);
          else if (it->nadd != r.nadd || it->nmulti != r.nmulti)
            ++_nOtherCounts;
          if (in.rank < it->rank) {          // the streamed input has the lower number: its row is kept
            ++_a.inputs[it->input].superseded;
            taken[it - mem.begin()] = 1;
            keep_(d, in, r.run, r.lumi, r.event, r.gen, r.exp, r.nadd, r.nmulti);
          } else {
            ++in.superseded;
          }
          continue;
        }
      }
      keep_(d, in, r.run, r.lumi, r.event, r.gen, r.exp, r.nadd, r.nmulti);
    }
    if (!cand.empty()) repeats_(d, in, cand);
  }
  for (std::size_t k = 0; k < mem.size(); ++k)
    if (!taken[k]) {
      const MemRow& m = mem[k];
      keep_(d, _a.inputs[m.input], m.run, m.lumi, m.event, m.gen, m.exp, m.nadd, m.nmulti);
    }
  _nShared += shared;
  std::printf("[extractTtbarIdPatch] dataset [%d] done: %lld key(s) in two or more of its inputs (rows of a lower "
              "priority number kept); elapsed %.0f s\n", d, shared, elapsed_());
  std::fflush(stdout);
}

// the output: --out (a local path; ROOT options after '?' kept), refused when it exists unless --replace; written as
//   <out>.tmp.<pid> (probed now, so an unwritable directory stops before the inputs are read) and renamed at the end
void Format2::prepareOutput_() {
  const std::size_t q = _a.out.find('?');
  _outPath = (q == std::string::npos) ? _a.out : _a.out.substr(0, q);
  _outOpts = (q == std::string::npos) ? std::string() : _a.out.substr(q);
  if (_outPath.empty() || _outPath.find("://") != std::string::npos)
    stop2(2, "--out " + _a.out + ": format 2 writes a local file (write it locally, then copy it)");
  struct stat st;
  if (::stat(_outPath.c_str(), &st) == 0) {
    if (!S_ISREG(st.st_mode)) stop2(4, "--out " + _outPath + " exists and is not a file");
    if (!_a.replace)
      stop2(4, "--out " + _outPath + " exists: --replace to replace it (the new file replaces it only on success)");
  }
  _tmpPath = _outPath + ".tmp." + std::to_string(static_cast<long long>(::getpid()));
  {
    std::ofstream probe(_tmpPath.c_str(), std::ios::binary | std::ios::trunc);
    if (!probe) {
      const std::string why = std::strerror(errno);
      _tmpPath.clear();
      stop2(4, "cannot write the temporary file next to --out " + _outPath + " (" + why + ")");
    }
  }
  std::remove(_tmpPath.c_str());
}

int Format2::run() {
  std::printf("[extractTtbarIdPatch] start: format 2 (%s), key (datasetIdx, run, luminosityBlock, event)\n", kFormat2);
  std::printf("[extractTtbarIdPatch]   out         = %s (tree '%s')%s\n", _a.out.c_str(), _a.outTree.c_str(),
              _a.replace ? ", --replace" : "");
  std::printf("[extractTtbarIdPatch]   label       = %s\n", _a.label.c_str());
  std::printf("[extractTtbarIdPatch]   on conflict = %s\n", _a.conflictReport ? "report (count, keep the lower number)"
                                                                               : "stop (exit 8)");
  std::fflush(stdout);
  prepareOutput_();
  for (const auto& in : _a.inputs)
    if (std::find(_datasets.begin(), _datasets.end(), in.dataset) == _datasets.end()) _datasets.push_back(in.dataset);
  std::sort(_datasets.begin(), _datasets.end());
  for (auto& in : _a.inputs)
    in.ds = static_cast<int>(std::find(_datasets.begin(), _datasets.end(), in.dataset) - _datasets.begin());
  // the filelists, and no sidecar file twice (in two inputs or in one), by normalized path
  {
    std::map<std::string, std::pair<int, std::string>> seen;
    for (auto& in : _a.inputs) {
      in.files = readFilelist2(in.filelist, "--input " + in.dataset + "=" + in.filelist);
      for (const auto& f : in.files) {
        const std::string n = normalizedPath(f);
        const auto it = seen.find(n);
        if (it != seen.end()) {
          const InputSpec& o = _a.inputs[it->second.first];
          const std::string where = (o.order == in.order) ? "twice in --input " + in.filelist
                                                          : "in --input " + o.filelist + " and --input " + in.filelist;
          std::fprintf(stderr, "ERROR: the sidecar file %s is %s (as '%s' and '%s')\n", n.c_str(), where.c_str(),
                       it->second.second.c_str(), f.c_str());
          stop2(2, "the sidecar file " + n + " is " + where + ": every event once");
        }
        seen[n] = std::make_pair(in.order, f);
      }
    }
  }
  // the sizes: every file of every input is opened once here (a file that cannot be read stops now)
  for (auto& in : _a.inputs) {
    Reader r;
    openInput_(in, r);
    _total += in.entries;
  }
  _dsEntries.assign(_datasets.size(), 0);
  for (const auto& in : _a.inputs) _dsEntries[in.ds] += in.entries;
  std::printf("[extractTtbarIdPatch]   %zu NanoAOD dataset(s) (datasetIdx = the line in nano_datasets), %zu input(s), "
              "%lld entries in all:\n", _datasets.size(), _a.inputs.size(), _total);
  std::vector<std::string> bad;
  for (std::size_t d = 0; d < _datasets.size(); ++d) {
    long long want = -1;
    for (const auto& e : _a.expects)
      if (e.first == _datasets[d]) want = e.second;
    std::printf("[extractTtbarIdPatch]   [%zu] %s: %lld entries", d, _datasets[d].c_str(), _dsEntries[d]);
    if (want >= 0) std::printf(", --expect %lld: %s", want, want == _dsEntries[d] ? "OK" : "DIFFERENT");
    std::printf("\n");
    if (want >= 0 && want != _dsEntries[d])
      bad.push_back("dataset " + _datasets[d] + " has " + std::to_string(_dsEntries[d]) + " entries, --expect " +
                    std::to_string(want));
    for (const auto& in : _a.inputs)
      if (in.ds == static_cast<int>(d)) {
        std::printf("[extractTtbarIdPatch]        priority %d  %s: %zu file(s), %lld entries%s\n", in.priority,
                    in.filelist.c_str(), in.files.size(), in.entries, in.entries == 0 ? "  <- NO ENTRY" : "");
        if (in.entries == 0) bad.push_back("--input " + in.dataset + "=" + in.filelist + " has 0 entries");
      }
  }
  std::fflush(stdout);
  if (!bad.empty()) {
    for (const auto& b : bad) std::fprintf(stderr, "ERROR: %s\n", b.c_str());
    stop2(6, bad[0] + (bad.size() > 1 ? " (and " + std::to_string(bad.size() - 1) + " more)" : std::string()) +
             " -- every input must have entries, every --expect must hold");
  }

  for (std::size_t d = 0; d < _datasets.size(); ++d) dataset_(static_cast<int>(d));
  progress_(true);

  // ---- every key once per dataset, sorted (stable: within one input the first row read is kept) -----------------
  std::stable_sort(_out.begin(), _out.end(), [](const OutRow& x, const OutRow& y) {
    if (x.ds != y.ds) return x.ds < y.ds;
    if (x.run != y.run || x.lumi != y.lumi || x.event != y.event) return keyLess(x.run, x.lumi, x.event, y.run, y.lumi, y.event);
    return x.rank < y.rank;
  });
  std::size_t w = 0;
  for (std::size_t i = 0; i < _out.size(); ++i) {
    if (w > 0) {
      const OutRow& p = _out[w - 1];
      const OutRow& c = _out[i];
      if (p.ds == c.ds && p.run == c.run && p.lumi == c.lumi && p.event == c.event) {   // one key twice in one input
        if (p.gen != c.gen || p.exp != c.exp) {   // compared already (and counted, --on-conflict report)
          if (!_a.conflictReport)
            stop2(8, "internal: an unchecked conflict at the end (a tool error -- report it)");
        } else {
          ++_nDupOut;
        }
        continue;
      }
    }
    _out[w++] = _out[i];
  }
  _out.resize(w);
  for (const OutRow& o : _out) ++_a.inputs[o.input].written;

  // ---- report ----------------------------------------------------------------------------------------------
  long long n61 = 0, n62 = 0, n71 = 0, n72 = 0;
  std::vector<long long> perDs(_datasets.size(), 0);
  std::map<int, long long> fromSub;
  for (const OutRow& o : _out) {
    const int esub = ((o.exp % 100) + 100) % 100;
    if      (esub == 61) ++n61;
    else if (esub == 62) ++n62;
    else if (esub == 71) ++n71;
    else if (esub == 72) ++n72;
    ++perDs[o.ds];
    fromSub[((o.gen % 100) + 100) % 100]++;
  }
  std::printf("[extractTtbarIdPatch] ===== summary (%s, format 2) =====\n", _a.label.c_str());
  std::printf("[extractTtbarIdPatch]   input entries                  : %lld\n", _total);
  std::printf("[extractTtbarIdPatch]   tt+nb rows read (all inputs)   : %lld\n", _nSel);
  std::printf("[extractTtbarIdPatch]   nAddBJets>=3 (cross-check)     : %lld\n", _nGe3);
  std::printf("[extractTtbarIdPatch]   keys in two or more inputs of one dataset : %lld; repeated rows of a key in one "
              "input: %lld (second passes: %lld); other nAddBJets / nAddBJetsMulti, same category: %lld; conflicts: "
              "%lld\n", _nShared, _nRepeatWithin, _nSecondPass, _nOtherCounts, _nConflicts);
  if (_nRepeatWithin)
    std::printf("[extractTtbarIdPatch]   WARN: %lld repeated row(s) of a key inside one input (equal ones kept once; "
                "tt+nb rows dropped as repeats: %lld)\n", _nRepeatWithin, _nDupOut);
  std::printf("[extractTtbarIdPatch]   tt+nb rows written             : %zu\n", _out.size());
  for (std::size_t d = 0; d < _datasets.size(); ++d)
    std::printf("[extractTtbarIdPatch]     [%zu] %lld  %s\n", d, perDs[d], _datasets[d].c_str());
  std::printf("[extractTtbarIdPatch]   tt+bbb (61+62) : %lld   tt+4b (71+72) : %lld\n", n61 + n62, n71 + n72);
  std::printf("[extractTtbarIdPatch]     61 : %lld   62 (multi) : %lld   71 : %lld   72 (multi) : %lld\n",
              n61, n62, n71, n72);
  std::printf("[extractTtbarIdPatch]   written rows by genTtbarId sub-code (expect 53/54/55):\n");
  for (const auto& kv : fromSub)
    std::printf("[extractTtbarIdPatch]       from sub-code %d : %lld\n", kv.first, kv.second);
  for (const auto& in : _a.inputs)
    std::printf("[extractTtbarIdPatch]   input [%d] priority %d %s: %lld entries, %lld row(s) superseded by a lower "
                "number, %lld tt+nb row(s) written\n", in.ds, in.priority, in.filelist.c_str(), in.entries,
                in.superseded, in.written);
  if (_nMismatch != 0 || _nSel != _nGe3) {
    std::printf("[extractTtbarIdPatch]   >>> ERROR: sub-code-vs-nAddBJets selection disagreed on %lld rows (tt+nb %lld, "
                "nAddBJets>=3 %lld) -- nothing written\n", _nMismatch, _nSel, _nGe3);
    std::fflush(stdout);
    stop2(7, "selection inconsistency: Expanded_genTtbarId % 100 in {61,62,71,72} and nAddBJets >= 3 disagree on " +
             std::to_string(_nMismatch) + " row(s)");
  }
  std::printf("[extractTtbarIdPatch]   >>> OK: selection consistent (sub in {61,62,71,72} <=> nAddBJets>=3).\n");
  std::fflush(stdout);

  // ---- the file: <out>.tmp.<pid>, renamed to <out> when written without error ----------------------------------
  std::string dsText, sources, dsLine;
  for (std::size_t d = 0; d < _datasets.size(); ++d) {
    dsText += (d ? "\n" : "") + _datasets[d];
    long long want = -1;
    for (const auto& e : _a.expects)
      if (e.first == _datasets[d]) want = e.second;
    dsLine += (d ? ", " : "") + std::string("[") + std::to_string(d) + "] " + std::to_string(_dsEntries[d]) +
              (want >= 0 ? " (--expect " + std::to_string(want) + ")" : std::string(" (no --expect)"));
  }
  sources = std::string("# extractTtbarIdPatch --input (") + kFormat2 + "): the inputs of each NanoAOD dataset. Within a "
            "dataset a key in two inputs keeps the row of the lower priority number (then the earlier --input); every "
            "row of a key is compared, also inside one input; on a genTtbarId / Expanded_genTtbarId conflict: " +
            (_a.conflictReport ? "report" : "stop") + "\n"
            "datasetIdx\tdataset\tpriority\tfilelist\tfiles\tentries\trows_superseded\tttnb_rows_written\n";
  for (const auto& in : _a.inputs)
    sources += std::to_string(in.ds) + "\t" + in.dataset + "\t" + std::to_string(in.priority) + "\t" + in.filelist +
               "\t" + std::to_string(in.files.size()) + "\t" + std::to_string(in.entries) + "\t" +
               std::to_string(in.superseded) + "\t" + std::to_string(in.written) + "\n";
  sources += "# entries per dataset: " + dsLine + "\n";
  sources += "# keys in two or more inputs of one dataset " + std::to_string(_nShared) + ", repeated rows of a key in "
             "one input " + std::to_string(_nRepeatWithin) + ", conflicts " + std::to_string(_nConflicts);

  TFile* outF = TFile::Open((_tmpPath + _outOpts).c_str(), "RECREATE");
  if (!outF || outF->IsZombie()) {
    std::fprintf(stderr, "ERROR: cannot create %s\n", _tmpPath.c_str());
    delete outF;
    stop2(4, "cannot create the temporary output " + _tmpPath);
  }
  UInt_t    oRun = 0, oLumi = 0;
  ULong64_t oEvent = 0;
  Int_t     oGen = 0, oExp = 0, oNAdd = 0, oNAddMulti = 0, oDs = 0;
  TTree* out = new TTree(_a.outTree.c_str(),
                         "tt+nb (Expanded sub in {61,62,71,72}) lookup, key (datasetIdx, run, luminosityBlock, event)");
  out->Branch("run",                 &oRun,        "run/i");
  out->Branch("luminosityBlock",     &oLumi,       "luminosityBlock/i");
  out->Branch("event",               &oEvent,      "event/l");
  out->Branch("genTtbarId",          &oGen,        "genTtbarId/I");
  out->Branch("Expanded_genTtbarId", &oExp,        "Expanded_genTtbarId/I");
  out->Branch("nAddBJets",           &oNAdd,       "nAddBJets/I");
  out->Branch("nAddBJetsMulti",      &oNAddMulti,  "nAddBJetsMulti/I");
  out->Branch("datasetIdx",          &oDs,         "datasetIdx/I");
  for (const OutRow& o : _out) {
    oRun = o.run; oLumi = o.lumi; oEvent = o.event; oGen = o.gen; oExp = o.exp; oNAdd = o.nadd;
    oNAddMulti = o.nmulti; oDs = o.ds;
    out->Fill();
  }
  out->Write("", TObject::kOverwrite);
  TNamed("lookup_format", kFormat2).Write();
  TNamed("nano_datasets", dsText.c_str()).Write();
  TNamed("sources", sources.c_str()).Write();
  const bool bad1 = outF->TestBit(TFile::kWriteError);
  outF->Close();
  const bool bad2 = outF->TestBit(TFile::kWriteError);
  delete outF;
  if (bad1 || bad2) stop2(4, "a write error on the temporary output " + _tmpPath);
  if (std::rename(_tmpPath.c_str(), _outPath.c_str()) != 0) {
    const std::string why = std::strerror(errno);
    stop2(4, "cannot rename " + _tmpPath + " to " + _outPath + " (" + why + ")");
  }
  _tmpPath.clear();   // renamed: nothing to remove
  std::printf("[extractTtbarIdPatch] wrote %zu tt+nb rows to %s (tree '%s', %s, %zu dataset(s) in nano_datasets)\n",
              _out.size(), _outPath.c_str(), _a.outTree.c_str(), kFormat2, _datasets.size());
  std::printf("RESULT %s extractTtbarIdPatch format 2: %zu rows, %zu dataset(s), %zu input(s), %lld entries, %lld shared "
              "key(s), %lld repeated row(s) in one input, %lld conflict(s)%s; %.0f s\n", _nConflicts ? "WARN" : "OK",
              _out.size(), _datasets.size(), _a.inputs.size(), _total, _nShared, _nRepeatWithin, _nConflicts,
              _nConflicts ? " (--on-conflict report: the lower number's row kept)" : "", elapsed_());
  std::fflush(stdout);
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  Args args = parseArgs(argc, argv);
  if (args.inputs.empty()) return runFormat1(args);
  try {
    Format2 f(args);
    return f.run();
  } catch (const Stop& s) {
    std::fflush(nullptr);
    std::printf("RESULT FAIL extractTtbarIdPatch format 2: %s (exit %d)\n", s.why.c_str(), s.code);
    std::fflush(stdout);
    return s.code;
  }
}
