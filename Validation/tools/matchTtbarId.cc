// -*- C++ -*-
// =============================================================================
// matchTtbarId
// =============================================================================
// Per-event 1:1 comparison of genTtbarId between a extend file source (MiniAOD-
// derived, this analysis) and a nano source (central NanoAOD / forgedNtuple),
// matched on the (run, lumi, event) key.  This is the strict check: for every
// nano event, look up the same (run, lumi, event) in the extend file and verify the
// genTtbarId is identical.  Events present in the extend file but absent from nano
// (e.g. the ~few % of MiniAOD events that a NanoAOD production dropped) are
// simply never looked up, so the event-count mismatch between MiniAOD and
// NanoAOD does not pollute the comparison.
//
// KEY = (run, lumi, event).  In a large MC sample the event number is only
// unique within a lumisection, so event numbers get reused across different
// lumisections; (run, event) alone collides (observed ~4% collisions in a
// 355M-event sample).  Including luminosityBlock makes the key well-defined.
// While loading the extend file we insert every (run, lumi, event) into a hash
// map and ABORT with a nonzero exit code if a duplicate key is found
// (printing both conflicting genTtbarId values).  A genuine duplicate of the
// full 3-key must never happen; surfacing it as an error lets you grep the
// condor logs for it.
//
// Memory note: one map entry per extend file event.  For ~350M events this is
// ~11 GB; request a worker with >= 12 GB (matching the analyzer's footprint).
//
// Extended-id (Expanded_genTtbarId) validation -- v10 model.  The v10 producer reclassifies
// on nAddBJets (NOT on the non-existent sub-code 56): an event is moved out of
// the standard tt+bb bucket only when it has >= 3 additional b-jets, into
// 61/62 (tt+bbb, nAddBJets==3) or 71/72 (tt+4b, nAddBJets>=4), with the leading
// prefix digits preserved.  Since the extend file carries nAddBJets / nAddBJetsMulti
// directly, we check the producer's encoding rule head-on, per matched event:
//   (a) Expanded_genTtbarId sub-code in {61,62,71,72}  <=>  nAddBJets >= 3      (iff, both ways)
//   (b) reclassified events preserve the prefix: Expanded_genTtbarId/100 == genTtbarId/100
//   (c) exact mapping: nAddBJets==3 -> 61/62, >=4 -> 71/72, by nAddBJetsMulti
//   (d) nAddBJets <= 2  =>  Expanded_genTtbarId == genTtbarId  (byte-identical, unchanged)
// (The earlier "only sub-code 56 may split" invariant was the v9 model and is
// obsolete -- the official GenTtbarCategorizer never emits 56.)
//
// Output (optional, --out): histograms filled ONLY over matched events:
//   h_genTtbarId_sub      nano genTtbarId % 100   (matched events)
//   h_extend_genTtbarId_sub  extend file genTtbarId % 100 (matched events)
//   h_extend_Expanded_sub  extend file Expanded_genTtbarId % 100    (matched events)
// Because these cover exactly the matched (= nano) event set, plotTtbarCompare
// on them gives ratio = 1.0 without needing --normalize.
//
// Usage:
//   matchTtbarId
//       --extend-filelist filelist_<P>_extend.txt
//       --nano-filelist    filelist_<P>_nano.txt
//       [--out match_<P>.root]
//       [--tree-extend Events] [--tree-nano Events]
//       [--label <P>] [--dump-mismatches 20]
//
// Exit codes:
//   0  success, every matched event agrees and Expanded_genTtbarId is consistent
//   5  no events matched
//   6  one or more matched events disagree on genTtbarId
//   7  duplicate (run, lumi, event) key found in extend file  (the "must not happen" case)
//   8  extended-id (Expanded_genTtbarId) consistency check failed
//   9  run != 1 encountered (this tooling assumes MC; run is always 1)
// =============================================================================

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include <TChain.h>
#include <TFile.h>
#include <TH1.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string extendFilelist;
  std::string nanoFilelist;
  std::string out;
  std::string treeExtend = "Events";
  std::string treeNano    = "Events";
  std::string label       = "";
  int         dumpN       = 20;
};

[[noreturn]] void usage(int code) {
  std::cout <<
    "matchTtbarId\n"
    "  --extend-filelist PATH   filelist of extend file ROOT files (one path/line)\n"
    "  --nano-filelist PATH      filelist of nano ROOT files (one path/line)\n"
    "  --out PATH                optional ROOT file of matched-event histograms\n"
    "  --tree-extend NAME       extend file tree name (default Events)\n"
    "  --tree-nano NAME          nano tree name (default Events)\n"
    "  --label NAME              label for histogram titles (default from --out)\n"
    "  --dump-mismatches N       print up to N disagreeing events (default 20)\n"
    "  -h, --help                this help\n";
  std::exit(code);
}

Args parseArgs(int argc, char** argv) {
  Args a;
  auto need = [&](int& i, const char* o) {
    if (i + 1 >= argc) { std::cerr << "ERROR: " << o << " needs a value\n"; std::exit(2); }
    return std::string(argv[++i]);
  };
  for (int i = 1; i < argc; ++i) {
    std::string s = argv[i];
    if      (s == "--extend-filelist" || s == "--sidecar-filelist") a.extendFilelist = need(i, s.c_str());
    else if (s == "--nano-filelist")    a.nanoFilelist    = need(i, s.c_str());
    else if (s == "--out")              a.out             = need(i, s.c_str());
    else if (s == "--tree-extend" || s == "--tree-sidecar")     a.treeExtend     = need(i, s.c_str());
    else if (s == "--tree-nano")        a.treeNano        = need(i, s.c_str());
    else if (s == "--label")            a.label           = need(i, s.c_str());
    else if (s == "--dump-mismatches")  a.dumpN           = std::stoi(need(i, s.c_str()));
    else if (s == "-h" || s == "--help") usage(0);
    else { std::cerr << "ERROR: unknown arg '" << s << "'\n"; usage(2); }
  }
  if (a.extendFilelist.empty() || a.nanoFilelist.empty()) {
    std::cerr << "ERROR: --extend-filelist and --nano-filelist are required\n";
    usage(2);
  }
  if (a.label.empty()) {
    if (!a.out.empty()) {
      std::string b = a.out;
      auto slash = b.find_last_of('/');
      if (slash != std::string::npos) b = b.substr(slash + 1);
      auto dot = b.find_last_of('.');
      if (dot != std::string::npos) b = b.substr(0, dot);
      a.label = b;
    } else {
      a.label = "matchTtbarId";
    }
  }
  return a;
}

std::vector<std::string> readFilelist(const std::string& path) {
  std::vector<std::string> files;
  std::ifstream in(path);
  if (!in) { std::cerr << "ERROR: cannot open filelist " << path << "\n"; std::exit(3); }
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

// (run, lumi, event) key.  In a large MC sample the event number is only
// unique within a lumisection, so event numbers are reused across different
// lumisections; (run, event) alone is therefore NOT unique and collides.
// Including the luminosityBlock makes the key well-defined.
struct Key {
  UInt_t    run;
  UInt_t    lumi;
  ULong64_t event;
  bool operator==(const Key& o) const noexcept {
    return run == o.run && lumi == o.lumi && event == o.event;
  }
};
struct KeyHash {
  std::size_t operator()(const Key& k) const noexcept {
    // FNV-style mix of the three fields.
    uint64_t h = 1469598103934665603ULL;
    h = (h ^ static_cast<uint64_t>(k.run))   * 1099511628211ULL;
    h = (h ^ static_cast<uint64_t>(k.lumi))  * 1099511628211ULL;
    h = (h ^ static_cast<uint64_t>(k.event)) * 1099511628211ULL;
    return std::hash<uint64_t>{}(h);
  }
};

struct Row {
  Int_t genTtbarId;
  Int_t expandedId;
  Int_t nAddBJets;
  Int_t nAddBJetsMulti;
};

TChain* makeChain(const std::string& treeName,
                  const std::vector<std::string>& files,
                  const char* tag) {
  auto* ch = new TChain(treeName.c_str());
  int added = 0;
  for (const auto& f : files) if (ch->Add(f.c_str()) > 0) ++added;
  std::cout << "[matchTtbarId] " << tag << ": files in list = " << files.size()
            << ", added to chain = " << added
            << ", entries = " << ch->GetEntries() << "\n";
  if (added != (int)files.size()) {
    std::cout << "[matchTtbarId] " << tag
              << ": WARNING - some files were not added (see above).\n";
  }
  return ch;
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::cout << "[matchTtbarId] starting\n";
  std::cout << "[matchTtbarId]   extend file-filelist = " << args.extendFilelist << "\n";
  std::cout << "[matchTtbarId]   nano-filelist    = " << args.nanoFilelist << "\n";
  std::cout << "[matchTtbarId]   out              = " << (args.out.empty() ? "(none)" : args.out) << "\n";
  std::cout << "[matchTtbarId]   tree-extend file     = " << args.treeExtend << "\n";
  std::cout << "[matchTtbarId]   tree-nano        = " << args.treeNano << "\n";
  std::cout << "[matchTtbarId]   label            = " << args.label << "\n";

  const auto extendFiles = readFilelist(args.extendFilelist);
  const auto nanoFiles    = readFilelist(args.nanoFilelist);
  if (extendFiles.empty()) { std::cerr << "ERROR: extend file filelist empty\n"; return 3; }
  if (nanoFiles.empty())    { std::cerr << "ERROR: nano filelist empty\n";    return 3; }

  // ---- Load extend file into a (run,lumi,event) -> Row map, detecting duplicates ----
  TChain* sChain = makeChain(args.treeExtend, extendFiles, "extend");
  UInt_t    sRun = 0, sLumi = 0;
  ULong64_t sEvt = 0;
  Int_t     sGtb = 0, sTbb = 0, sNAdd = 0, sNAddMulti = 0;
  sChain->SetBranchStatus("*", 0);
  for (const char* b : {"run", "luminosityBlock", "event",
                        "genTtbarId", "Expanded_genTtbarId", "nAddBJets", "nAddBJetsMulti"})
    sChain->SetBranchStatus(b, 1);
  sChain->SetBranchAddress("run",             &sRun);
  sChain->SetBranchAddress("luminosityBlock", &sLumi);
  sChain->SetBranchAddress("event",           &sEvt);
  sChain->SetBranchAddress("genTtbarId",      &sGtb);
  sChain->SetBranchAddress("Expanded_genTtbarId",          &sTbb);
  sChain->SetBranchAddress("nAddBJets",       &sNAdd);
  sChain->SetBranchAddress("nAddBJetsMulti",  &sNAddMulti);

  std::unordered_map<Key, Row, KeyHash> idx;
  const Long64_t nS = sChain->GetEntries();
  idx.reserve(static_cast<size_t>(nS) * 2);

  Long64_t nDup = 0;
  int dupDumped = 0;
  for (Long64_t i = 0; i < nS; ++i) {
    sChain->GetEntry(i);
    if (sRun != 1) {
      std::cerr << "[matchTtbarId] FATAL: extend file run=" << sRun
                << " != 1 at entry " << i
                << ".  This tooling assumes MC (run is always 1). "
                   "Aborting with exit code 9.\n";
      delete sChain;
      return 9;
    }
    Key k{sRun, sLumi, sEvt};
    Row r{sGtb, sTbb, sNAdd, sNAddMulti};
    auto res = idx.emplace(k, r);
    if (!res.second) {
      ++nDup;
      if (dupDumped < args.dumpN) {
        const Row& prev = res.first->second;
        std::cerr << "[matchTtbarId] DUPLICATE (run,lumi,event)=(" << sRun << ","
                  << sLumi << "," << sEvt << ")"
                  << "  existing genTtbarId=" << prev.genTtbarId
                  << "  |  new genTtbarId=" << sGtb << "\n";
        ++dupDumped;
      }
    }
    if ((i % 20000000) == 0 && i > 0)
      std::cout << "[matchTtbarId]   extend file loaded " << i << " / " << nS << "\n";
  }
  std::cout << "[matchTtbarId] extend file map built: " << idx.size()
            << " unique (run,lumi,event) keys";
  if (nDup > 0) std::cout << "  (+ " << nDup << " DUPLICATES)";
  std::cout << "\n";

  if (nDup > 0) {
    std::cerr << "[matchTtbarId] FATAL: " << nDup
              << " duplicate (run,lumi,event) key(s) in extend file. "
                 "(run,lumi,event) must be unique for the lookup to be well-defined. "
                 "Aborting with exit code 7 so this is visible in the condor logs.\n";
    delete sChain;
    return 7;
  }

  // ---- Optional histograms over matched events ----
  TH1::SetDefaultSumw2(true);
  TH1D *h_nano = nullptr, *h_side = nullptr, *h_ttbb = nullptr;
  TFile* fout = nullptr;
  if (!args.out.empty()) {
    fout = TFile::Open(args.out.c_str(), "RECREATE");
    if (!fout || fout->IsZombie()) {
      std::cerr << "ERROR: cannot open --out " << args.out << "\n";
      delete sChain;
      return 5;
    }
    fout->cd();
    h_nano = new TH1D("h_genTtbarId_sub",
        (args.label + " (matched);genTtbarId % 100;events").c_str(), 100, 0, 100);
    h_side = new TH1D("h_extend_genTtbarId_sub",
        (args.label + " extend file (matched);genTtbarId % 100;events").c_str(), 100, 0, 100);
    h_ttbb = new TH1D("h_extend_Expanded_sub",
        (args.label + " extend file Expanded_genTtbarId (matched);Expanded_genTtbarId % 100;events").c_str(), 100, 0, 100);
    h_nano->SetDirectory(fout);
    h_side->SetDirectory(fout);
    h_ttbb->SetDirectory(fout);
  }

  // ---- Iterate nano, look up each (run,lumi,event) in the extend file map ----
  TChain* nChain = makeChain(args.treeNano, nanoFiles, "nano");
  UInt_t    nRun = 0, nLumi = 0;
  ULong64_t nEvt = 0;
  Int_t     nGtb = 0;
  nChain->SetBranchStatus("*", 0);
  for (const char* b : {"run", "luminosityBlock", "event", "genTtbarId"})
    nChain->SetBranchStatus(b, 1);
  nChain->SetBranchAddress("run",             &nRun);
  nChain->SetBranchAddress("luminosityBlock", &nLumi);
  nChain->SetBranchAddress("event",           &nEvt);
  nChain->SetBranchAddress("genTtbarId",      &nGtb);

  Long64_t matched = 0, unmatched = 0, agree = 0, disagree = 0;
  int misDumped = 0;
  std::map<int, Long64_t> disagreeBySub;

  // Extended-id (Expanded_genTtbarId) validation -- v10 model (nAddBJets-driven).
  // We read nAddBJets / nAddBJetsMulti from the extend file, so we check the
  // producer's encoding rule directly (not the obsolete sub-code-56 model):
  //   reclassified (Expanded_genTtbarId sub-code in {61,62,71,72})  <=>  nAddBJets >= 3
  Long64_t nExt        = 0;   // Expanded_genTtbarId sub-code in {61,62,71,72}
  Long64_t nAddGe3     = 0;   // nAddBJets >= 3
  Long64_t nExtNoAdd   = 0;   // ext sub-code but nAddBJets < 3        (must be 0)
  Long64_t nAddNoExt   = 0;   // nAddBJets >= 3 but no ext sub-code    (must be 0)
  Long64_t nPrefixBad  = 0;   // Expanded_genTtbarId/100 != genTtbarId/100          (must be 0)
  Long64_t nMapBad     = 0;   // (nAddBJets,Multi) -> sub-code wrong   (must be 0)
  Long64_t nLowChanged = 0;   // nAddBJets <= 2 but Expanded_genTtbarId changed     (must be 0)
  std::map<int, Long64_t> ttbbSubAll;     // Expanded_genTtbarId%100 distribution (matched events)
  std::map<int, Long64_t> origSubOfExt;   // nano sub-code of reclassified events

  const Long64_t nN = nChain->GetEntries();
  for (Long64_t i = 0; i < nN; ++i) {
    nChain->GetEntry(i);
    if (nRun != 1) {
      std::cerr << "[matchTtbarId] FATAL: nano run=" << nRun
                << " != 1 at entry " << i
                << ".  This tooling assumes MC (run is always 1). "
                   "Aborting with exit code 9.\n";
      delete sChain;
      delete nChain;
      return 9;
    }
    auto it = idx.find(Key{nRun, nLumi, nEvt});
    if (it == idx.end()) { ++unmatched; continue; }
    ++matched;
    const Row& sr = it->second;
    if (sr.genTtbarId == nGtb) {
      ++agree;
    } else {
      ++disagree;
      disagreeBySub[nGtb % 100]++;
      if (misDumped < args.dumpN) {
        std::cout << "[matchTtbarId] MISMATCH (run,lumi,event)=(" << nRun << ","
                  << nLumi << "," << nEvt << ")  nano genTtbarId=" << nGtb
                  << "  extend file genTtbarId=" << sr.genTtbarId << "\n";
        ++misDumped;
      }
    }

    // ---- extended-id consistency (v10): check the producer rule directly
    //      using the extend file's own nAddBJets / nAddBJetsMulti.  The 1:1 check
    //      above guarantees sr.genTtbarId == nGtb, so sr.genTtbarId is the
    //      pre-extension reference. ----
    const int  tbSub  = sr.expandedId % 100;
    const bool isExt  = (tbSub == 61 || tbSub == 62 || tbSub == 71 || tbSub == 72);
    const bool addGe3 = (sr.nAddBJets >= 3);
    ttbbSubAll[tbSub]++;
    if (isExt)  ++nExt;
    if (addGe3) ++nAddGe3;
    if (isExt && !addGe3) ++nExtNoAdd;   // reclassified without >=3 add b-jets
    if (addGe3 && !isExt) ++nAddNoExt;   // >=3 add b-jets but never reclassified
    if (isExt) {
      origSubOfExt[sr.genTtbarId % 100]++;                       // expect 53/54/55
      if (sr.expandedId / 100 != sr.genTtbarId / 100) ++nPrefixBad;  // prefix must survive
      const int want = (sr.nAddBJets == 3)
                         ? (sr.nAddBJetsMulti == 0 ? 61 : 62)
                         : (sr.nAddBJetsMulti == 0 ? 71 : 72);   // == kExtendedSubCode
      if (tbSub != want) ++nMapBad;
    } else {
      if (sr.expandedId != sr.genTtbarId) ++nLowChanged;             // unchanged case
    }

    if (h_nano) {
      h_nano->Fill(nGtb % 100);
      h_side->Fill(sr.genTtbarId % 100);
      h_ttbb->Fill(sr.expandedId % 100);
    }
    if ((i % 20000000) == 0 && i > 0)
      std::cout << "[matchTtbarId]   nano scanned " << i << " / " << nN << "\n";
  }

  if (fout) {
    fout->cd();
    h_nano->Write();
    h_side->Write();
    h_ttbb->Write();
    fout->Close();
    std::cout << "[matchTtbarId] wrote matched-event histograms to " << args.out << "\n";
  }

  // ---- Report ----
  std::cout << "[matchTtbarId] ===== summary (" << args.label << ") =====\n";
  std::cout << "[matchTtbarId]   nano entries        : " << nN << "\n";
  std::cout << "[matchTtbarId]   extend file unique keys : " << idx.size() << "\n";
  std::cout << "[matchTtbarId]   matched             : " << matched << "\n";
  std::cout << "[matchTtbarId]   unmatched (nano-only): " << unmatched << "\n";
  std::cout << "[matchTtbarId]   agree               : " << agree << "\n";
  std::cout << "[matchTtbarId]   disagree            : " << disagree << "\n";
  if (!disagreeBySub.empty()) {
    std::cout << "[matchTtbarId]   disagreements by nano sub-code:\n";
    for (const auto& kv : disagreeBySub)
      std::cout << "[matchTtbarId]       sub-code " << kv.first << " : " << kv.second << "\n";
  }

  // ---- Extended-id (Expanded_genTtbarId) validation, v10 (nAddBJets-driven) ----
  auto cnt = [](const std::map<int, Long64_t>& m, int k) -> Long64_t {
    auto it = m.find(k);
    return (it == m.end()) ? 0 : it->second;
  };
  std::cout << "[matchTtbarId] ----- extended-id (Expanded_genTtbarId) validation [v10] -----\n";
  std::cout << "[matchTtbarId]   matched events with nAddBJets >= 3       : " << nAddGe3 << "\n";
  std::cout << "[matchTtbarId]   matched events with ext sub-code (61/62/71/72): " << nExt << "\n";
  std::cout << "[matchTtbarId]   tt+bbb (61+62) : " << (cnt(ttbbSubAll, 61) + cnt(ttbbSubAll, 62))
            << "   tt+4b (71+72) : "                << (cnt(ttbbSubAll, 71) + cnt(ttbbSubAll, 72))
            << "\n";
  std::cout << "[matchTtbarId]     of which multi (g->bb merged): 62 : " << cnt(ttbbSubAll, 62)
            << "   72 : " << cnt(ttbbSubAll, 72) << "\n";
  std::cout << "[matchTtbarId]   nano sub-code of reclassified events (expect 53/54/55):\n";
  for (const auto& kv : origSubOfExt)
    std::cout << "[matchTtbarId]       from sub-code " << kv.first << " : " << kv.second << "\n";
  std::cout << "[matchTtbarId]   --- invariant violations (every count must be 0) ---\n";
  std::cout << "[matchTtbarId]   ext sub-code but nAddBJets < 3           : " << nExtNoAdd  << "\n";
  std::cout << "[matchTtbarId]   nAddBJets >= 3 but not reclassified      : " << nAddNoExt  << "\n";
  std::cout << "[matchTtbarId]   reclassified with changed prefix         : " << nPrefixBad << "\n";
  std::cout << "[matchTtbarId]   (nAddBJets,Multi) -> sub-code mismatch    : " << nMapBad    << "\n";
  std::cout << "[matchTtbarId]   nAddBJets <= 2 but Expanded_genTtbarId != genTtbarId  : " << nLowChanged << "\n";

  const bool extOk = (nExtNoAdd == 0 && nAddNoExt == 0 &&
                      nPrefixBad == 0 && nMapBad == 0 && nLowChanged == 0);
  if (extOk)
    std::cout << "[matchTtbarId]   >>> extended-id consistent [v10]: Expanded_genTtbarId sub-code is in "
                 "{61,62,71,72} iff nAddBJets>=3, prefix preserved, mapping exact.\n";
  else
    std::cout << "[matchTtbarId]   >>> extended-id INCONSISTENT (see the nonzero counts above).\n";

  delete sChain;
  delete nChain;

  if (matched == 0) {
    std::cout << "[matchTtbarId] >>> NO events matched (check run/event branches "
                 "and that the two filelists are the same process).\n";
    return 5;
  }
  if (disagree != 0) {
    std::cout << "[matchTtbarId] >>> " << disagree
              << " matched event(s) DISAGREE on genTtbarId.\n";
    return 6;
  }
  if (!extOk) {
    std::cout << "[matchTtbarId] >>> extended-id (Expanded_genTtbarId) consistency check FAILED "
                 "(see above).\n";
    return 8;
  }
  std::cout << "[matchTtbarId] >>> ALL " << matched
            << " matched events have extend file.genTtbarId == nano.genTtbarId (1:1), "
               "and Expanded_genTtbarId is consistent.\n";
  if (unmatched > 0) {
    std::cout << "[matchTtbarId] (note: " << unmatched
              << " nano events had no extend file match; if nonzero, the extend file "
                 "did not cover all nano events for this process.)\n";
  }
  return 0;
}
