// -*- C++ -*-
// =============================================================================
// matchTtbarIdSorted
// =============================================================================
// Memory-light validation of a extend file against central NanoAOD, using the
// sorted+split extend file produced by sortSplitExtend (parts + index.txt).
//
// The original matchTtbarId loads the ENTIRE extend file into a hash map (~20 GB
// for a 236M-row ttbar sample), which does not fit on Tier3 workers.  This tool
// avoids that: it keeps only ONE part (a few tens of MB) resident at a time.
//
// How it works:
//   * read index.txt -> per-part (firstKey, lastKey) over (run, lumi, event);
//   * loop over the (unordered) NanoAOD Events; for each nano event compute its
//     key (run, lumi, event), find which part's [firstKey, lastKey] range covers
//     it (binary search over parts, since parts are globally ordered and their
//     ranges are non-overlapping by construction), load that part if not already
//     cached, and binary-search the key within the part;
//   * compare genTtbarId (must be byte-identical) and validate the extended
//     Expanded_genTtbarId (v10 model: only nAddBJets>=3 events are reclassified
//     to 61/62/71/72, the rest satisfy Expanded_genTtbarId == genTtbarId).
//
// Memory: one part resident (~16 MB at 500k rows) + the index (tiny).  nano need
// NOT be sorted; if nano jumps between lumi regions the current part is reloaded,
// which costs I/O but never grows memory.  (If nano has any lumi locality, the
// single-part cache already captures most of the benefit.)
//
// Extended-id validation (v10), over matched events, against the extend file's own
// genTtbarId (the reference the extension was derived from):
//   * sub-code in {61,62,71,72}  <=>  nAddBJets >= 3   (both directions)
//   * reclassified rows preserve the prefix: Expanded/100 == genTtbarId/100
//   * conservation: #(nAddBJets>=3) == #(61)+#(62)+#(71)+#(72)
//   * nAddBJets <= 2  =>  Expanded_genTtbarId == genTtbarId  (unchanged)
//
// Usage:
//   matchTtbarIdSorted --sorted-dir sorted_TTToHadronic
//       --nano-filelist nano_TTToHadronic.txt [--out match.root] [--label NAME]
//       [--tree-nano Events] [--dump-mismatches N]
//
// Exit codes: 0 ok; 5 nothing matched; 6 genTtbarId disagreement; 9 nano run!=1;
//             8 extended-id consistency failed.
// =============================================================================

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include <TChain.h>
#include <TFile.h>
#include <TH1.h>
#include <TTree.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string sortedDir;
  std::string nanoFilelist;
  std::string out;
  std::string label = "sample";
  std::string treeNano = "Events";
  int         dumpN = 0;
};

[[noreturn]] void usage(int code) {
  std::printf(
    "matchTtbarIdSorted\n"
    "  --sorted-dir DIR        directory from sortSplitExtend (partNNNNN.root + index.txt)\n"
    "  --nano-filelist PATH    text file, one central NanoAOD path per line\n"
    "  --out PATH              optional ROOT file with matched-event histograms\n"
    "  --label NAME            label for messages/histogram titles\n"
    "  --tree-nano NAME        nano tree name (default Events)\n"
    "  --dump-mismatches N     print up to N genTtbarId mismatches\n"
    "  -h, --help              this help\n");
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
    if      (s == "--sorted-dir")     a.sortedDir    = need(i, "--sorted-dir");
    else if (s == "--nano-filelist")  a.nanoFilelist = need(i, "--nano-filelist");
    else if (s == "--out")            a.out          = need(i, "--out");
    else if (s == "--label")          a.label        = need(i, "--label");
    else if (s == "--tree-nano")      a.treeNano     = need(i, "--tree-nano");
    else if (s == "--dump-mismatches")a.dumpN        = std::stoi(need(i, "--dump-mismatches"));
    else if (s == "-h" || s == "--help") usage(0);
    else { std::fprintf(stderr, "ERROR: unknown arg '%s'\n", s.c_str()); usage(2); }
  }
  if (a.sortedDir.empty())    { std::fprintf(stderr, "ERROR: --sorted-dir required\n"); usage(2); }
  if (a.nanoFilelist.empty()) { std::fprintf(stderr, "ERROR: --nano-filelist required\n"); usage(2); }
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

// 128-bit-ish key as a struct, compared (run, lumi, event).
struct Key {
  UInt_t    run;
  UInt_t    lumi;
  ULong64_t event;
};
inline bool keyLess(const Key& a, const Key& b) {
  if (a.run  != b.run)  return a.run  < b.run;
  if (a.lumi != b.lumi) return a.lumi < b.lumi;
  return a.event < b.event;
}
inline bool keyEq(const Key& a, const Key& b) {
  return a.run == b.run && a.lumi == b.lumi && a.event == b.event;
}

// One part's index entry.
struct PartInfo {
  int      idx;
  Long64_t nRows;
  Key      first;
  Key      last;
};

struct Row {
  Key   key;
  Int_t genTtbarId;
  Int_t expandedId;
  Int_t nAddBJets;
  Int_t nAddBJetsMulti;
};

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::printf("[matchSorted] start\n");
  std::printf("[matchSorted]   sorted-dir    = %s\n", args.sortedDir.c_str());
  std::printf("[matchSorted]   nano-filelist = %s\n", args.nanoFilelist.c_str());
  std::printf("[matchSorted]   label         = %s\n", args.label.c_str());
  std::fflush(stdout);

  // ---- read index ----
  std::vector<PartInfo> parts;
  {
    std::ifstream idx((args.sortedDir + "/index.txt").c_str());
    if (!idx) { std::fprintf(stderr, "ERROR: cannot open %s/index.txt\n", args.sortedDir.c_str()); return 3; }
    std::string line;
    while (std::getline(idx, line)) {
      if (line.empty() || line[0] == '#') continue;
      std::istringstream ss(line);
      PartInfo p{};
      if (!(ss >> p.idx >> p.nRows
               >> p.first.run >> p.first.lumi >> p.first.event
               >> p.last.run  >> p.last.lumi  >> p.last.event)) continue;
      parts.push_back(p);
    }
  }
  if (parts.empty()) { std::fprintf(stderr, "ERROR: index.txt has no parts\n"); return 3; }
  std::printf("[matchSorted]   parts in index = %zu\n", parts.size());
  std::fflush(stdout);

  // ---- nano chain ----
  const auto nanoFiles = readFilelist(args.nanoFilelist);
  if (nanoFiles.empty()) { std::fprintf(stderr, "ERROR: nano filelist empty\n"); return 3; }
  TChain nano(args.treeNano.c_str());
  for (const auto& f : nanoFiles) nano.Add(f.c_str());
  UInt_t nRun = 0, nLumi = 0; ULong64_t nEvt = 0; Int_t nGtb = 0;
  nano.SetBranchStatus("*", 0);
  for (const char* b : {"run", "luminosityBlock", "event", "genTtbarId"})
    nano.SetBranchStatus(b, 1);
  nano.SetBranchAddress("run",             &nRun);
  nano.SetBranchAddress("luminosityBlock", &nLumi);
  nano.SetBranchAddress("event",           &nEvt);
  nano.SetBranchAddress("genTtbarId",      &nGtb);
  const Long64_t nN = nano.GetEntries();
  std::printf("[matchSorted]   nano entries = %lld\n", nN); std::fflush(stdout);

  // ---- optional output histograms ----
  TFile* outF = nullptr;
  TH1* h_nano = nullptr; TH1* h_side = nullptr; TH1* h_exp = nullptr;
  if (!args.out.empty()) {
    outF = TFile::Open(args.out.c_str(), "RECREATE");
    h_nano = new TH1D("h_genTtbarId_sub",          (args.label + " nano genTtbarId%100").c_str(), 100, 0, 100);
    h_side = new TH1D("h_extend_genTtbarId_sub",  (args.label + " extend file genTtbarId%100").c_str(), 100, 0, 100);
    h_exp  = new TH1D("h_extend_Expanded_sub",    (args.label + " extend file Expanded%100").c_str(), 100, 0, 100);
    h_nano->SetDirectory(outF); h_side->SetDirectory(outF); h_exp->SetDirectory(outF);
  }

  // ---- part cache (one resident part) ----
  int cachedPart = -1;
  std::vector<Row> cache;   // sorted by key

  auto loadPart = [&](int pidx) {
    const PartInfo& p = parts[pidx];
    char buf[32]; std::snprintf(buf, sizeof(buf), "/part%05d.root", p.idx);
    const std::string path = args.sortedDir + buf;
    TFile* f = TFile::Open(path.c_str());
    if (!f || f->IsZombie()) { std::fprintf(stderr, "ERROR: cannot open %s\n", path.c_str()); std::exit(4); }
    TTree* t = dynamic_cast<TTree*>(f->Get(args.treeNano.c_str()));
    if (!t) { std::fprintf(stderr, "ERROR: no tree in %s\n", path.c_str()); std::exit(4); }
    Row r;
    t->SetBranchStatus("*", 0);
    for (const char* b : {"run", "luminosityBlock", "event",
                          "genTtbarId", "Expanded_genTtbarId",
                          "nAddBJets", "nAddBJetsMulti"})
      t->SetBranchStatus(b, 1);
    t->SetBranchAddress("run",                 &r.key.run);
    t->SetBranchAddress("luminosityBlock",     &r.key.lumi);
    t->SetBranchAddress("event",               &r.key.event);
    t->SetBranchAddress("genTtbarId",          &r.genTtbarId);
    t->SetBranchAddress("Expanded_genTtbarId", &r.expandedId);
    t->SetBranchAddress("nAddBJets",           &r.nAddBJets);
    t->SetBranchAddress("nAddBJetsMulti",      &r.nAddBJetsMulti);
    const Long64_t n = t->GetEntries();
    cache.clear(); cache.reserve(static_cast<size_t>(n));
    for (Long64_t i = 0; i < n; ++i) { t->GetEntry(i); cache.push_back(r); }
    f->Close(); delete f;
    cachedPart = pidx;
    // parts are globally sorted, so each part is already sorted; assert-lite:
    // (we trust sortSplitExtend; no re-sort to keep it light)
  };

  // find which part covers key k: parts are ordered and ranges non-overlapping,
  // so the covering part is the last one whose first <= k.
  auto findPart = [&](const Key& k) -> int {
    // binary search for last part with first <= k
    int lo = 0, hi = (int)parts.size() - 1, ans = -1;
    while (lo <= hi) {
      int mid = (lo + hi) / 2;
      if (!keyLess(k, parts[mid].first)) { ans = mid; lo = mid + 1; } // parts[mid].first <= k
      else hi = mid - 1;
    }
    if (ans < 0) return -1;
    // k must be within [first,last] of that part
    if (keyLess(parts[ans].last, k)) return -1;  // k beyond this part's last -> gap (not present)
    return ans;
  };

  // ---- main loop ----
  Long64_t matched = 0, unmatched = 0, agree = 0, disagree = 0;
  int dumped = 0;
  std::map<int, Long64_t> disagreeBySub;

  // extended-id validation accumulators
  Long64_t nGe3 = 0;            // extend file nAddBJets >= 3 among matched
  Long64_t nExtended = 0;       // extend file Expanded sub in {61,62,71,72}
  Long64_t nExtNotGe3 = 0;      // extended sub but nAddBJets < 3 (must be 0)
  Long64_t nGe3NotExt = 0;      // nAddBJets>=3 but sub not extended (must be 0)
  Long64_t nPrefixBad = 0;      // reclassified but prefix changed (must be 0)
  Long64_t nLe2Changed = 0;     // nAddBJets<=2 but Expanded != genTtbarId (must be 0)

  auto isExt = [](int sub){ return sub==61||sub==62||sub==71||sub==72; };

  for (Long64_t i = 0; i < nN; ++i) {
    nano.GetEntry(i);
    if (nRun != 1) {
      std::fprintf(stderr,
        "[matchSorted] ERROR: nano run = %u != 1 at entry %lld. This tooling "
        "assumes MC (run==1); aborting with exit code 9.\n", nRun, i);
      return 9;
    }
    const Key k{nRun, nLumi, nEvt};
    int pidx = findPart(k);
    if (pidx < 0) { ++unmatched; continue; }
    if (pidx != cachedPart) loadPart(pidx);

    // binary search within cached part
    auto it = std::lower_bound(cache.begin(), cache.end(), k,
                               [](const Row& r, const Key& key){ return keyLess(r.key, key); });
    if (it == cache.end() || !keyEq(it->key, k)) { ++unmatched; continue; }

    ++matched;
    const Row& sr = *it;
    if (sr.genTtbarId == nGtb) ++agree;
    else {
      ++disagree; disagreeBySub[nGtb % 100]++;
      if (dumped < args.dumpN) {
        std::printf("[matchSorted] MISMATCH (run,lumi,event)=(%u,%u,%llu) nano=%d extend file=%d\n",
                    nRun, nLumi, (unsigned long long)nEvt, nGtb, sr.genTtbarId);
        ++dumped;
      }
    }

    // extended-id checks (reference = extend file genTtbarId)
    const int gsub = ((sr.genTtbarId % 100) + 100) % 100;
    const int esub = ((sr.expandedId % 100) + 100) % 100;
    const bool ge3 = (sr.nAddBJets >= 3);
    if (ge3) ++nGe3;
    if (isExt(esub)) ++nExtended;
    if (isExt(esub) && !ge3) ++nExtNotGe3;
    if (ge3 && !isExt(esub)) ++nGe3NotExt;
    if (isExt(esub) && (sr.expandedId / 100 != sr.genTtbarId / 100)) ++nPrefixBad;
    if (!ge3 && sr.expandedId != sr.genTtbarId) ++nLe2Changed;
    (void)gsub;

    if (h_nano) {
      h_nano->Fill(nGtb % 100);
      h_side->Fill(sr.genTtbarId % 100);
      h_exp->Fill(sr.expandedId % 100);
    }
    if ((i % 20000000) == 0 && i > 0) { std::printf("[matchSorted]   nano scanned %lld / %lld\n", i, nN); std::fflush(stdout); }
  }

  if (outF) {
    outF->cd();
    if (h_nano) h_nano->Write();
    if (h_side) h_side->Write();
    if (h_exp)  h_exp->Write();
    outF->Close(); delete outF;
    std::printf("[matchSorted] wrote histograms to %s\n", args.out.c_str());
  }

  // ---- summary ----
  std::printf("[matchSorted] ===== summary (%s) =====\n", args.label.c_str());
  std::printf("[matchSorted]   nano entries : %lld\n", nN);
  std::printf("[matchSorted]   matched      : %lld\n", matched);
  std::printf("[matchSorted]   unmatched    : %lld  (nano events not in extend file; expected if extend file is a subset)\n", unmatched);
  std::printf("[matchSorted]   agree        : %lld\n", agree);
  std::printf("[matchSorted]   disagree     : %lld\n", disagree);
  if (!disagreeBySub.empty()) {
    std::printf("[matchSorted]   disagreements by nano sub-code:\n");
    for (const auto& kv : disagreeBySub)
      std::printf("[matchSorted]       sub-code %d : %lld\n", kv.first, kv.second);
  }

  std::printf("[matchSorted] ----- extended-id (Expanded_genTtbarId) validation -----\n");
  std::printf("[matchSorted]   nAddBJets>=3 (matched)        : %lld\n", nGe3);
  std::printf("[matchSorted]   Expanded sub in {61,62,71,72} : %lld\n", nExtended);
  std::printf("[matchSorted]   conservation (must be equal)  : %lld vs %lld\n", nGe3, nExtended);
  std::printf("[matchSorted]   extended-but-nAddBJets<3 (=0) : %lld\n", nExtNotGe3);
  std::printf("[matchSorted]   nAddBJets>=3-but-not-ext (=0) : %lld\n", nGe3NotExt);
  std::printf("[matchSorted]   prefix changed on reclass (=0): %lld\n", nPrefixBad);
  std::printf("[matchSorted]   nAddBJets<=2 changed (=0)     : %lld\n", nLe2Changed);

  bool extOk = (nGe3 == nExtended) && nExtNotGe3 == 0 && nGe3NotExt == 0
               && nPrefixBad == 0 && nLe2Changed == 0;
  if (extOk)
    std::printf("[matchSorted]   >>> extended-id consistent (v10 model).\n");
  else
    std::printf("[matchSorted]   >>> extended-id INCONSISTENT (see nonzero lines above).\n");

  if (matched == 0) { std::printf("[matchSorted] >>> NO events matched.\n"); return 5; }
  if (disagree != 0) { std::printf("[matchSorted] >>> genTtbarId DISAGREEMENT.\n"); return 6; }
  if (!extOk) { std::printf("[matchSorted] >>> extended-id check FAILED.\n"); return 8; }
  std::printf("[matchSorted] >>> ALL %lld matched events agree on genTtbarId and Expanded_genTtbarId is consistent.\n", matched);
  return 0;
}
