// -*- C++ -*-
// =============================================================================
// - compareExtendToCentral.cc
// =============================================================================
// Verifies that the extend file's `genTtbarId` is byte-identical to the
// central NanoAODv9's `genTtbarId` for every (run, lumi, event) tuple
// the two files share.  Also tabulates the extended Expanded_genTtbarId / nAddBJets /
// nAddBJetsMulti distributions emitted by our ExtendedTtbarIdProducer.
//
// Why this comparator exists separately previously's
// `compareEnrichedToCentral`:
//   * The enriched-approach comparator hash-joined enriched and central on (run, lumi,
//     event) and compared 1665 common branches one by one.  That was the
//     right thing for Approach 2 where we re-emitted the entire NanoAOD.
//   * The extend file holds only 4 ints per row -- there is no
//     "common branch" set to enumerate.  We just need to check that
//     extend file.genTtbarId  ==  central.genTtbarId  for matched events.
//   * Tabulating Expanded_genTtbarId%100 confirms that the nAddBJets>=3 -> 61/62/71/72 split
//     fires for enough events to be meaningful.
//
// Usage:
//   compareExtendToCentral
//       --extend  ttbarIDExtend.root
//       --central  root://.../NanoAODv9/.../<file>.root
//       [--max-events 1000000]
//       [--tree-extend Events]   (default: Events)
//       [--tree-central Events]   (default: Events)
//       [--dump-mismatches 20]    (default: 0 = no per-event dump)
//
// Exit code 0 if every matched event has extend file.genTtbarId ==
// central.genTtbarId; non-zero otherwise.
// =============================================================================

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include <TBranch.h>
#include <TFile.h>
#include <TLeaf.h>
#include <TTree.h>
#include <RtypesCore.h>

// ---- CLI ---------------------------------------------------------------
struct Args {
  std::string extendPath;
  std::string centralPath;
  std::string treeExtend = "Events";
  std::string treeCentral = "Events";
  Long64_t    maxEvents   = 1000000;
  int         dumpN       = 0;
};

static Args parseArgs(int argc, char** argv) {
  Args a;
  auto needArg = [&](int& i, const char* opt) {
    if (i + 1 >= argc) { std::cerr << "ERROR: " << opt << " needs a value\n"; std::exit(2); }
    return std::string(argv[++i]);
  };
  for (int i = 1; i < argc; ++i) {
    std::string s = argv[i];
    if      (s == "--extend" || s == "--sidecar")   a.extendPath = needArg(i, s.c_str());
    else if (s == "--central")          a.centralPath = needArg(i, "--central");
    else if (s == "--tree-extend" || s == "--tree-sidecar") a.treeExtend = needArg(i, s.c_str());
    else if (s == "--tree-central")     a.treeCentral = needArg(i, "--tree-central");
    else if (s == "--max-events")       a.maxEvents   = std::stoll(needArg(i, "--max-events"));
    else if (s == "--dump-mismatches")  a.dumpN       = std::stoi(needArg(i, "--dump-mismatches"));
    else if (s == "-h" || s == "--help") {
      std::cout
        << "compareExtendToCentral\n"
        << "  --extend PATH               extend file ROOT file (this package's output)\n"
        << "  --central PATH              central NanoAODv9 file (xrootd or local)\n"
        << "  --tree-extend NAME          tree name in the extend file (default Events)\n"
        << "  --tree-central NAME         tree name in central (default Events)\n"
        << "  --max-events N              cap on central events scanned (default 1,000,000)\n"
        << "  --dump-mismatches N         print up to N mismatched (run,lumi,event,extend file,central) tuples\n"
        << "  -h, --help                  this help\n";
      std::exit(0);
    } else {
      std::cerr << "ERROR: unknown argument '" << s << "'\n";
      std::exit(2);
    }
  }
  if (a.extendPath.empty() || a.centralPath.empty()) {
    std::cerr << "ERROR: --extend and --central are both required\n";
    std::exit(2);
  }
  return a;
}

// ---- Event key ---------------------------------------------------------
struct Key {
  UInt_t     run;
  UInt_t     lumi;
  ULong64_t  event;
  bool operator==(const Key& o) const noexcept {
    return run == o.run && lumi == o.lumi && event == o.event;
  }
};
struct KeyHash {
  std::size_t operator()(const Key& k) const noexcept {
    return std::hash<uint64_t>{}(
      (static_cast<uint64_t>(k.run)  * 1469598103934665603ULL) ^
      (static_cast<uint64_t>(k.lumi) * 1099511628211ULL) ^
       static_cast<uint64_t>(k.event));
  }
};

// One row of extend file payload.
struct ExtendRow {
  Int_t genTtbarId;
  Int_t expandedId;
  Int_t nAddBJets;
  Int_t nAddBJetsMulti;
};

// ---- Helpers ---------------------------------------------------------------
static std::unique_ptr<TFile> openTFile(const std::string& path, const char* label) {
  std::unique_ptr<TFile> f(TFile::Open(path.c_str()));
  if (!f || f->IsZombie()) {
    std::cerr << "ERROR: cannot open " << label << " file: " << path << "\n";
    std::exit(3);
  }
  return f;
}

static TTree* getTree(TFile* f, const std::string& name, const char* label) {
  auto* t = dynamic_cast<TTree*>(f->Get(name.c_str()));
  if (!t) {
    std::cerr << "ERROR: tree '" << name << "' not found in " << label << " file\n";
    std::exit(4);
  }
  return t;
}

// ---- Main ----------------------------------------------------------------
int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::cout << "[compare] compareExtendToCentral starting\n";
  std::cout << "[compare]   argv:";
  for (int i = 0; i < argc; ++i) std::cout << " " << argv[i];
  std::cout << "\n";
  std::cout << "[compare]   extend  = " << args.extendPath << "\n";
  std::cout << "[compare]   central = " << args.centralPath << "\n";
  std::cout << "[compare]   tree    = " << args.treeExtend << "\n";
  std::cout << "[compare]   tree-central = " << args.treeCentral << "\n";
  std::cout << "[compare]   max-events   = " << args.maxEvents   << "\n";
  std::cout << "[compare]   dump-mismatches = " << args.dumpN    << "\n";

  // ---- Open files ----
  auto fS = openTFile(args.extendPath, "extend file");
  auto fC = openTFile(args.centralPath, "central");
  auto* tS = getTree(fS.get(), args.treeExtend, "extend file");
  auto* tC = getTree(fC.get(), args.treeCentral, "central");
  std::cout << "[open] extend file entries = " << tS->GetEntries() << "\n";
  std::cout << "[open] central entries = " << tC->GetEntries() << "\n";

  // ---- Read extend file into an in-memory hash map ----
  // Branch types matched to the analyzer's output schema:
  //   run/i = UInt_t, luminosityBlock/i = UInt_t, event/l = ULong64_t,
  //   genTtbarId/I = Int_t, Expanded_genTtbarId/I = Int_t, nAddBJets/I = Int_t,
  //   nAddBJetsMulti/I = Int_t.
  UInt_t    sRun, sLumi;
  ULong64_t sEvt;
  Int_t     sGtb, sTbb, sNa, sNam;
  tS->SetBranchStatus("*", 0);
  for (const char* b : {"run","luminosityBlock","event",
                        "genTtbarId","Expanded_genTtbarId","nAddBJets","nAddBJetsMulti"})
    tS->SetBranchStatus(b, 1);
  tS->SetBranchAddress("run",             &sRun);
  tS->SetBranchAddress("luminosityBlock", &sLumi);
  tS->SetBranchAddress("event",           &sEvt);
  tS->SetBranchAddress("genTtbarId",      &sGtb);
  tS->SetBranchAddress("Expanded_genTtbarId",          &sTbb);
  tS->SetBranchAddress("nAddBJets",       &sNa);
  tS->SetBranchAddress("nAddBJetsMulti",  &sNam);

  std::unordered_map<Key, ExtendRow, KeyHash> idx;
  idx.reserve(static_cast<size_t>(tS->GetEntries()));
  const Long64_t nS = tS->GetEntries();
  for (Long64_t i = 0; i < nS; ++i) {
    tS->GetEntry(i);
    idx[Key{sRun, sLumi, sEvt}] = ExtendRow{sGtb, sTbb, sNa, sNam};
  }
  std::cout << "[join]  built extend file index : " << idx.size() << " entries\n";

  // ---- Iterate over central; for each matched key compare genTtbarId ----
  // The central NanoAODv9 schema uses the same run/i, luminosityBlock/i,
  // event/l, genTtbarId/I (see WorkBookNanoAOD).
  UInt_t    cRun, cLumi;
  ULong64_t cEvt;
  Int_t     cGtb;
  tC->SetBranchStatus("*", 0);
  for (const char* b : {"run","luminosityBlock","event","genTtbarId"})
    tC->SetBranchStatus(b, 1);
  tC->SetBranchAddress("run",             &cRun);
  tC->SetBranchAddress("luminosityBlock", &cLumi);
  tC->SetBranchAddress("event",           &cEvt);
  tC->SetBranchAddress("genTtbarId",      &cGtb);

  Long64_t matched = 0, unmatched = 0, agree = 0, disagree = 0, dumped = 0;
  std::map<int, uint64_t> distCentralSubcode;      // central.genTtbarId % 100
  std::map<int, uint64_t> distExtendSubcode;      // extend file.Expanded_genTtbarId % 100
  std::map<int, uint64_t> distExtendGenSubcode;   // extend file.genTtbarId % 100  -- byte-identity tabulation
  std::vector<int> mismatchDump;  // optional

  const Long64_t nC = std::min<Long64_t>(args.maxEvents, tC->GetEntries());
  std::cout << "[loop]  scanning " << nC << " central events...\n";
  for (Long64_t i = 0; i < nC; ++i) {
    tC->GetEntry(i);
    auto it = idx.find(Key{cRun, cLumi, cEvt});
    if (it == idx.end()) { ++unmatched; continue; }
    ++matched;
    const ExtendRow& sr = it->second;
    // Byte-identity check
    if (sr.genTtbarId == cGtb) ++agree;
    else {
      ++disagree;
      if (dumped < args.dumpN) {
        std::cout << "[diff]  run=" << cRun << " lumi=" << cLumi
                  << " event=" << cEvt
                  << "   extend file.genTtbarId=" << sr.genTtbarId
                  << "   central.genTtbarId=" << cGtb << "\n";
        ++dumped;
      }
    }
    distCentralSubcode[cGtb       % 100]++;
    distExtendSubcode[sr.expandedId  % 100]++;
    distExtendGenSubcode[sr.genTtbarId % 100]++;
  }

  // ---- Report --------------------------------------------------------------
  std::cout << "[loop]  matched   : " << matched   << "\n";
  std::cout << "[loop]  unmatched : " << unmatched << "  (central events not present in extend file -- expected if extend file processed a subset of the central's parent MiniAODs)\n";
  std::cout << "[byte]  genTtbarId byte-identity check (target: agree == matched):\n";
  std::cout << "[byte]    agree    = " << agree    << "\n";
  std::cout << "[byte]    disagree = " << disagree << "\n";
  if (matched > 0 && disagree == 0) {
    std::cout << "[byte]  >>> ALL matched events have extend file.genTtbarId == central.genTtbarId (1:1).\n";
  } else if (matched > 0) {
    std::cout << "[byte]  >>> BYTE-IDENTITY FAILED on " << disagree
              << " event(s).  See [diff] lines above (raise --dump-mismatches if needed).\n";
  } else {
    std::cout << "[byte]  >>> NO matched events; cannot evaluate byte-identity.\n";
  }

  std::cout << "[Expanded_genTtbarId] central genTtbarId%100 distribution (matched events only):\n";
  uint64_t cSum = 0;
  for (const auto& kv : distCentralSubcode) cSum += kv.second;
  for (const auto& kv : distCentralSubcode) {
    std::cout << "         sub-code " << std::setw(3) << kv.first
              << " : " << std::setw(8) << kv.second;
    if (cSum > 0) std::cout << "  (" << std::fixed << std::setprecision(2)
                            << (100.0 * kv.second / cSum) << "%)";
    std::cout << "\n";
  }
  std::cout << "         total           : " << cSum << "\n";

  std::cout << "[Expanded_genTtbarId] extend file genTtbarId%100 distribution (should match central exactly):\n";
  uint64_t sgSum = 0;
  for (const auto& kv : distExtendGenSubcode) sgSum += kv.second;
  for (const auto& kv : distExtendGenSubcode) {
    std::cout << "         sub-code " << std::setw(3) << kv.first
              << " : " << std::setw(8) << kv.second;
    if (sgSum > 0) std::cout << "  (" << std::fixed << std::setprecision(2)
                             << (100.0 * kv.second / sgSum) << "%)";
    std::cout << "\n";
  }
  std::cout << "         total           : " << sgSum << "\n";

  std::cout << "[Expanded_genTtbarId] extend file Expanded_genTtbarId%100 distribution  (expected: identical to central except that some 53/54/55 events move to 61/62/71/72 when nAddBJets>=3):\n";
  uint64_t tSum = 0;
  for (const auto& kv : distExtendSubcode) tSum += kv.second;
  for (const auto& kv : distExtendSubcode) {
    const bool newSub = (kv.first == 61 || kv.first == 62 || kv.first == 71 || kv.first == 72);
    std::cout << "         sub-code " << std::setw(3) << kv.first
              << " : " << std::setw(8) << kv.second;
    if (tSum > 0) std::cout << "  (" << std::fixed << std::setprecision(2)
                            << (100.0 * kv.second / tSum) << "%)";
    if (newSub) std::cout << "   <-- new sub-code from ExtendedTtbarIdProducer";
    std::cout << "\n";
  }
  std::cout << "         total           : " << tSum << "\n";

  // ---- Sub-code invariance (v10 logic) ----
  // The extension reclassifies events with >= 3 additional b-jets out of the
  // standard tt+bb bucket (53/54/55) into 61/62 (tt+bbb) or 71/72 (tt+4b).
  // (The standard GenTtbarCategorizer never produces sub-code 56; that value
  // belongs to a different scheme and is irrelevant here.)  Therefore:
  //   (a) total matched counts must be equal;
  //   (b) every sub-code that is NOT a split source (53/54/55) and NOT a split
  //       target (61/62/71/72) must be identical between central and extend file
  //       -- i.e. 0, 41-45, 51, 52 unchanged;
  //   (c) the standard tt+bb bucket is conserved:
  //         central(53+54+55) == extend file(53+54+55) + extend file(61+62+71+72);
  //   (d) 61/62/71/72 appear ONLY in the extend file (central has none).
  bool invarianceOk = true;

  auto isTtbb    = [](int s){ return s == 53 || s == 54 || s == 55; };
  auto isExtended = [](int s){ return s == 61 || s == 62 || s == 71 || s == 72; };

  uint64_t cAll = 0, sAll = 0;
  for (const auto& kv : distCentralSubcode) cAll += kv.second;
  for (const auto& kv : distExtendSubcode) sAll += kv.second;

  // (a) total
  if (cAll != sAll) {
    std::cout << "[ok?]  total counts differ: central=" << cAll
              << " extend file=" << sAll
              << "  (should not happen if both were built from the same matched set)\n";
    invarianceOk = false;
  }

  // (b) non-split, non-target sub-codes must match exactly
  std::set<int> allSub;
  for (const auto& kv : distCentralSubcode) allSub.insert(kv.first);
  for (const auto& kv : distExtendSubcode) allSub.insert(kv.first);
  for (int s : allSub) {
    if (isTtbb(s) || isExtended(s)) continue;   // handled by (c)/(d)
    uint64_t c = distCentralSubcode.count(s) ? distCentralSubcode[s] : 0;
    uint64_t t = distExtendSubcode.count(s) ? distExtendSubcode[s] : 0;
    if (c != t) {
      std::cout << "[ok?]  sub-code " << s << " differs: central=" << c
                << " extend file=" << t
                << "  (unchanged sub-codes must be identical)\n";
      invarianceOk = false;
    }
  }

  // (c) tt+bb bucket conservation
  uint64_t cTtbb = 0, sTtbb = 0, sExtended = 0;
  for (const auto& kv : distCentralSubcode) if (isTtbb(kv.first))     cTtbb     += kv.second;
  for (const auto& kv : distExtendSubcode) {
    if (isTtbb(kv.first))     sTtbb     += kv.second;
    if (isExtended(kv.first)) sExtended += kv.second;
  }
  if (cTtbb != sTtbb + sExtended) {
    std::cout << "[ok?]  tt+bb conservation broken: central(53+54+55)=" << cTtbb
              << "  extend file(53+54+55)=" << sTtbb
              << "  extend file(61+62+71+72)=" << sExtended
              << "  (central tt+bb must equal extend file tt+bb + extended)\n";
    invarianceOk = false;
  } else {
    std::cout << "[info]  tt+bb conservation OK: central(53+54+55)=" << cTtbb
              << " = extend file(53+54+55)=" << sTtbb
              << " + extended(61+62+71+72)=" << sExtended << "\n";
  }

  // (d) extended sub-codes must not appear in central
  uint64_t cExtended = 0;
  for (const auto& kv : distCentralSubcode) if (isExtended(kv.first)) cExtended += kv.second;
  if (cExtended != 0) {
    std::cout << "[ok?]  central has extended sub-codes (61/62/71/72)=" << cExtended
              << "  (these should only ever appear in the extend file)\n";
    invarianceOk = false;
  }

  if (matched > 0 && invarianceOk) {
    std::cout << "[ok]    sub-code invariance OK: only 61/62/71/72 are new, drawn\n"
                 "        entirely from the standard tt+bb (53/54/55) bucket, with\n"
                 "        all other categories identical to central.\n";
  } else if (matched > 0) {
    std::cout << "[fail]  sub-code invariance check FAILED -- see [ok?] lines above.\n";
  }

  // Exit code = 0 iff matched > 0 and disagree == 0 and invarianceOk.
  if (matched == 0)       return 5;
  if (disagree != 0)      return 6;
  if (!invarianceOk)      return 7;
  return 0;
}
