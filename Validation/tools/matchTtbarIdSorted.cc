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
#include <ctime>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include <TFile.h>
#include <TH1.h>
#include <TTree.h>
#include <TSystem.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string sortedDir;
  std::string nanoFilelist;
  std::string out;
  std::string label = "sample";
  std::string treeNano = "Events";
  int         dumpN = 0;
  bool allowMissing = false;   // --allow-missing-files (T-21)
  std::string json;            // --json PATH: machine-readable counters
};

[[noreturn]] void usage(int code) {
  std::printf(
    "matchTtbarIdSorted\n"
    "  --sorted-dir DIR        directory from sortSplitExtend (partNNNNN.root + index.txt)\n"
    "  --nano-filelist PATH    text file, one central NanoAOD path per line\n"
    "  --out PATH              optional ROOT file with matched-event histograms\n"
    "  --json PATH             write counters as JSON (for aggregation across\n"
    "                          condor chunks; see scripts/aggregate_validation.py)\n"
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
    else if (s == "--json")           a.json         = need(i, "--json");
    else if (s == "--allow-missing-files") a.allowMissing = true;
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

// Verify every nano file opens (WITH RETRIES) and return total entries; abort
// otherwise. Same rationale as matchTtbarId (docs/08 T-21): TChain::Add() does
// not open the file, so unreachable files silently shrink the sample while
// `unmatched` can only get SMALLER -- a false pass. The 2026-07-27 case was a
// TRANSIENT AAA failure (the same files opened fine minutes later in the same
// environment), so retry is the right response, backed by a hard assertion.
// ---------------------------------------------------------------------------
// Every TTree/TChain read must be checked.
//
// WHY (2026-07-28, TTToSemiLeptonic 2018): GetEntry() returns bytes read, or
// <=0 on failure. Unchecked, a failed read leaves the branch buffers holding
// the PREVIOUS event -- so the loop silently processes a duplicate. It still
// "matches", still "agrees", and the counters look perfect. In that run ~1.87%
// of nano entries failed to read and ~1.74% of tt+nb events went missing, while
// every correctness counter reported clean. This is the single most dangerous
// failure mode in this tooling: it produces a confident wrong answer.
// Exit 10 = read failure.
// ---------------------------------------------------------------------------
static inline void checkRead(Int_t nbytes, Long64_t entry, const char* tag) {
  if (nbytes > 0) return;
  std::fprintf(stderr,
    "\nFATAL: %s GetEntry(%lld) returned %d (<=0) -- the read FAILED.\n"
    "  Continuing would reuse the previous event's values and silently\n"
    "  fabricate a duplicate. Aborting. Exit 10.\n", tag, entry, (int)nbytes);
  std::exit(10);
}

// ---------------------------------------------------------------------------
// Retry policy for nano opens (2026-07-29).
//
// The failures we are defending against are XRootD OPEN timeouts, not data
// corruption: stderr showed "TNetXNGFile::Open: [ERROR] Operation expired".
// Opening /store/... through cms-xrd-global is a multi-step handshake
// (redirector lookup -> hosting site answers -> connect to that site -> open),
// and under concurrency (20-49 jobs on one dataset) that handshake can exceed
// the client's connection window. Site/redirector state changes second to
// second, so a backed-off retry almost always succeeds.
//
// HOW LONG TO RETRY -- measured, not guessed (2026-07-29 cluster 13293958).
// The 10 jobs that survived finished 07:25-07:39 UTC; the 10 that died failed
// 07:44-08:05 UTC. So the bad window was open for AT LEAST 21 minutes: a job
// that retried for a couple of minutes would have died anyway. Budget is
// therefore ~25 min of retrying per open (10 attempts, backoff 10/20/40/80/160
// then capped at 300 s). The job flavour is "workday" (8 h) and the work itself
// is ~1.5-2 h, so this is affordable; losing the chunk is not.
//
// The pre-flight open-check gets a SHORT budget instead (kPrecheckAttempts):
// it is a fail-fast sanity check on ~20 files and must not sit for hours. The
// real endurance belongs on the read path.
// ---------------------------------------------------------------------------
constexpr int kOpenAttempts     = 10;    // attempts per file open (read path)
constexpr int kOpenBudgetS      = 1800;  // total seconds spent retrying one open
constexpr int kOpenBackoffCapS  = 300;   // single sleep is never longer than this
constexpr int kPrecheckAttempts = 3;     // pre-flight only
constexpr int kPrecheckBudgetS  = 120;
constexpr int kReadAttempts     = 3;     // reopen+reseek rounds for a failed GetEntry

TFile* openWithRetry(const std::string& path, const char* why,
                     int maxAttempts = kOpenAttempts,
                     int budgetSeconds = kOpenBudgetS) {
  const std::time_t t0 = std::time(nullptr);
  int wait = 10;
  for (int attempt = 1; attempt <= maxAttempts; ++attempt) {
    if (attempt > 1) {
      const long elapsed = static_cast<long>(std::time(nullptr) - t0);
      if (elapsed >= budgetSeconds) {
        std::printf(">>> nano %s GIVING UP after %lds (budget %ds)  %s\n",
                    why, elapsed, budgetSeconds, path.c_str());
        std::fflush(stdout);
        break;
      }
      std::printf(">>> nano %s retry %d/%d in %ds (elapsed %lds)  %s\n",
                  why, attempt, maxAttempts, wait, elapsed, path.c_str());
      std::fflush(stdout);
      gSystem->Sleep(1000 * wait);
      wait = std::min(wait * 2, kOpenBackoffCapS);
    }
    TFile* fh = TFile::Open(path.c_str());
    if (fh && !fh->IsZombie()) {
      if (attempt > 1) {
        std::printf(">>> nano %s RECOVERED on attempt %d after %lds  %s\n",
                    why, attempt,
                    static_cast<long>(std::time(nullptr) - t0), path.c_str());
        std::fflush(stdout);
      }
      return fh;
    }
    if (fh) delete fh;
  }
  return nullptr;
}

long long assertAllFilesOpen(const std::vector<std::string>& files,
                             const std::string& treeName, bool allowMissing,
                             int maxAttempts = kPrecheckAttempts) {
  std::vector<std::string> bad;
  long long total = 0;
  for (const auto& f : files) {
    bool ok = false;
    TFile* fh = openWithRetry(f, "open-check", maxAttempts, kPrecheckBudgetS);
    if (fh) {
      auto* t = dynamic_cast<TTree*>(fh->Get(treeName.c_str()));
      if (t) { total += t->GetEntries(); ok = true; }
      delete fh;
    }
    if (!ok) bad.push_back(f);
  }
  // Individual retries are printed by openWithRetry as they happen.
  std::printf(">>> nano open-check %d/%d files OK, total entries = %lld\n",
              (int)(files.size() - bad.size()), (int)files.size(), total);
  if (!bad.empty()) {
    std::fprintf(stderr, "\n%s: %d of %d nano file(s) unreadable after %d attempts:\n",
                 allowMissing ? "WARNING" : "FATAL",
                 (int)bad.size(), (int)files.size(), maxAttempts);
    int shown = 0;
    for (const auto& b : bad) {
      if (shown++ >= 10) { std::fprintf(stderr, "        ... and %d more\n",
                                        (int)bad.size() - 10); break; }
      std::fprintf(stderr, "        %s\n", b.c_str());
    }
    if (!allowMissing) {
      std::fprintf(stderr,
        "\n  A partial nano list still prints 'unmatched 0' -- a false pass.\n"
        "  Transient AAA failures are normal; the retries above already covered\n"
        "  short blips, so just re-run. Aborting with exit 4.\n"
        "  --allow-missing-files gives an INDICATIVE result only.\n");
      std::exit(4);
    }
  }
  return total;
}

// The pre-check total is the contract: the loop must have read exactly that
// many entries, or a file changed/died between the check and the read.
void assertReadComplete(long long got, long long expected, const char* tag) {
  if (got == expected) return;
  std::fprintf(stderr,
    "\nFATAL: %s loop read %lld entries but the open-check counted %lld "
    "(difference %lld).\n  A file became unreadable or changed between check and "
    "read; this run would cover only part of the sample. Re-run. Exit 4.\n",
    tag, got, expected, expected - got);
  std::exit(4);
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

  // ---- nano files ----
  //
  // WHY NOT TChain (2026-07-29, TTToSemiLeptonic 2018).
  // TChain::Add() opens nothing; the file is opened LAZILY inside the event
  // loop, at the moment the entry index crosses a file boundary -- and that
  // open has NO retry. 10 of 20 chunks died exactly there: every FATAL entry
  // number was an exact multiple of 2000 (i.e. a file boundary, never mid-file)
  // and stderr carried "TNetXNGFile::Open: [ERROR] Operation expired".
  // assertAllFilesOpen() below does retry -- but it guards a code path that
  // reads no physics data, so the protection sat in the wrong place, and it
  // also meant every file was opened TWICE (once to check, once to read),
  // doubling this job's load on the redirector.
  //
  // Opening each file explicitly puts the retry ON the read path and removes
  // the second open. The pre-check is kept because it is the independent
  // expected-entry count that makes a short read detectable (docs/08 T-21).
  const auto nanoFiles = readFilelist(args.nanoFilelist);
  if (nanoFiles.empty()) { std::fprintf(stderr, "ERROR: nano filelist empty\n"); return 3; }
  const long long expNano =
      assertAllFilesOpen(nanoFiles, args.treeNano, args.allowMissing);
  UInt_t nRun = 0, nLumi = 0; ULong64_t nEvt = 0; Int_t nGtb = 0;
  const Long64_t nN = expNano;
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
  // Memory resident = ONE part. Row is 32 B (Key 16 + 4 Int_t), part is 500k
  // rows -> 16 MB, independent of sample size. That is the whole point of this
  // tool: the in-memory variant would need ~15-38 GB for TTToSemiLeptonic.
  //
  // partLoads counts how often the cache had to be refilled. It is the direct
  // measure of whether the nano traversal order thrashes the cache:
  //   partLoads ~= number of parts        -> a clean monotone sweep (ideal)
  //   partLoads >> number of parts        -> thrashing; each miss is a 16 MB
  //                                          read, so this dominates runtime
  // Reported in the summary and in --json so it is a number, not a guess.
  Long64_t partLoads = 0;
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
    for (Long64_t i = 0; i < n; ++i) {
      checkRead(t->GetEntry(i), i, "sorted part");
      cache.push_back(r);
    }
    f->Close(); delete f;
    cachedPart = pidx;
    ++partLoads;
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

  std::map<int, Long64_t> expSubCount;   // Expanded sub-code -> n (61/62/71/72)
  std::map<int, Long64_t> origSubOfExt;  // nano sub-code of reclassified events

  auto isExt = [](int sub){ return sub==61||sub==62||sub==71||sub==72; };

  // ---- nano traversal: one file at a time, every open retried -------------
  // gEntry is the GLOBAL nano entry index, i.e. exactly what the old TChain
  // reported, so FATAL messages stay comparable with pre-2026-07-29 logs.
  Long64_t gEntry = 0;        // entries iterated
  Long64_t readTimeEntries = 0;   // sum of GetEntries() seen at read-time open
  int      skippedFiles = 0;      // only reachable with --allow-missing-files

  for (size_t fi = 0; fi < nanoFiles.size(); ++fi) {
    const std::string& path = nanoFiles[fi];
    TFile* fh = openWithRetry(path, "open");
    if (!fh) {
      if (args.allowMissing) {
        std::fprintf(stderr, "WARNING: skipping unreadable nano file (%d attempts): %s\n",
                     kOpenAttempts, path.c_str());
        ++skippedFiles;
        continue;
      }
      std::fprintf(stderr,
        "\nFATAL: nano file unreadable after %d attempts: %s\n"
        "  A partial nano list still prints 'unmatched 0' -- a false pass.\n"
        "  Exit 4.\n", kOpenAttempts, path.c_str());
      return 4;
    }
    TTree* t = dynamic_cast<TTree*>(fh->Get(args.treeNano.c_str()));
    if (!t) {
      std::fprintf(stderr, "\nFATAL: no tree '%s' in %s. Exit 4.\n",
                   args.treeNano.c_str(), path.c_str());
      return 4;
    }

    // Branch binding must be redone after every (re)open.
    auto bind = [&](TTree* tt) {
      tt->SetBranchStatus("*", 0);
      for (const char* b : {"run", "luminosityBlock", "event", "genTtbarId"})
        tt->SetBranchStatus(b, 1);
      tt->SetBranchAddress("run",             &nRun);
      tt->SetBranchAddress("luminosityBlock", &nLumi);
      tt->SetBranchAddress("event",           &nEvt);
      tt->SetBranchAddress("genTtbarId",      &nGtb);
    };
    bind(t);

    const Long64_t nF = t->GetEntries();
    readTimeEntries += nF;

    for (Long64_t j = 0; j < nF; ++j, ++gEntry) {
      const Long64_t i = gEntry;   // keep the original message/progress semantics

      // A mid-file read failure is the same transient AAA problem as a failed
      // open, so give it the same treatment: drop the handle, reopen (itself
      // retried), rebind, re-seek to the SAME local entry. checkRead() -- exit 10
      // -- remains the last resort. It must never be reached by simply ignoring
      // a bad return value: that fabricates a duplicate event (docs/08 T-23 (8)).
      Int_t nb = t->GetEntry(j);
      for (int attempt = 2; nb <= 0 && attempt <= kReadAttempts; ++attempt) {
        std::fprintf(stderr,
          ">>> nano read failed at entry %lld (local %lld) -- reopening %s "
          "(round %d/%d)\n", gEntry, j, path.c_str(), attempt, kReadAttempts);
        std::fflush(stderr);
        fh->Close(); delete fh;
        fh = openWithRetry(path, "reopen");
        if (!fh) break;
        t = dynamic_cast<TTree*>(fh->Get(args.treeNano.c_str()));
        if (!t) break;
        if (t->GetEntries() != nF) {
          std::fprintf(stderr,
            "\nFATAL: %s changed size across reopen (%lld -> %lld). Exit 4.\n",
            path.c_str(), nF, t->GetEntries());
          return 4;
        }
        bind(t);
        nb = t->GetEntry(j);
      }
      checkRead(nb, gEntry, "nano");

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
      if (isExt(esub)) { ++nExtended; ++expSubCount[esub];
                         ++origSubOfExt[((nGtb % 100) + 100) % 100]; }
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
    }   // ---- entries in this nano file ----
    fh->Close(); delete fh;
  }     // ---- nano files ----

  // Short read = partial sample = false pass. Same contract the chain-length
  // assertion used to enforce, now measured on what was actually read.
  if (!args.allowMissing) assertReadComplete(gEntry, expNano, "nano");
  else if (skippedFiles)
    std::printf("[matchSorted]   WARNING: %d nano file(s) skipped "
                "(--allow-missing-files): INDICATIVE result only\n", skippedFiles);

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
  std::printf("[matchSorted]   nano entries : %lld  (open-check %lld)\n",
              gEntry, (long long)expNano);
  std::printf("[matchSorted]   matched      : %lld\n", matched);
  std::printf("[matchSorted]   unmatched    : %lld  (nano events not in extend file; expected if extend file is a subset)\n", unmatched);
  std::printf("[matchSorted]   agree        : %lld\n", agree);
  std::printf("[matchSorted]   disagree     : %lld\n", disagree);
  std::printf("[matchSorted]   part loads   : %lld  (parts in index = %d;"
              " ~equal = clean sweep, >> = cache thrashing)\n",
              partLoads, (int)parts.size());
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

  // ---- machine-readable counters (--json) --------------------------------
  // Written BEFORE the exit-code branches so a FAILING chunk still reports its
  // numbers -- the aggregator needs the bad chunk's counters to tell you WHICH
  // chunk broke and by how much. Emitted with plain fprintf (no JSON library in
  // this standalone build); keys are flat and stable.
  if (!args.json.empty()) {
    FILE* jf = std::fopen(args.json.c_str(), "w");
    if (!jf) {
      std::fprintf(stderr, "ERROR: cannot write --json %s\n", args.json.c_str());
      return 3;                       // do not silently lose the counters
    }
    const bool extOkNow = (nGe3 == nExtended) && nExtNotGe3 == 0 && nGe3NotExt == 0
                          && nPrefixBad == 0 && nLe2Changed == 0;
    std::fprintf(jf, "{\n");
    std::fprintf(jf, "  \"tool\": \"matchTtbarIdSorted\",\n");
    std::fprintf(jf, "  \"label\": \"%s\",\n", args.label.c_str());
    std::fprintf(jf, "  \"sorted_dir\": \"%s\",\n", args.sortedDir.c_str());
    std::fprintf(jf, "  \"nano_filelist\": \"%s\",\n", args.nanoFilelist.c_str());
    std::fprintf(jf, "  \"nano_files\": %d,\n", (int)nanoFiles.size());
    std::fprintf(jf, "  \"parts_in_index\": %d,\n", (int)parts.size());
    std::fprintf(jf, "  \"part_loads\": %lld,\n", (long long)partLoads);
    // Three independent counts, all of which must agree (the aggregator checks
    // this and the C++ side aborts with exit 4 above if they do not):
    //   nano_entries           entries the loop actually READ (gEntry)
    //   nano_entries_postloop  sum of GetEntries() seen when each file was
    //                          opened FOR READING -- a second, later
    //                          measurement than the pre-flight one
    //   nano_entries_opencheck the pre-flight open-check total
    // Before 2026-07-29 the postloop value came from re-querying the TChain and
    // was the symptom that exposed the silent-duplicate bug (docs/08 T-23 (8)).
    std::fprintf(jf, "  \"nano_entries\": %lld,\n", (long long)gEntry);
    std::fprintf(jf, "  \"nano_entries_postloop\": %lld,\n",
                 (long long)readTimeEntries);
    std::fprintf(jf, "  \"nano_entries_opencheck\": %lld,\n", (long long)expNano);
    std::fprintf(jf, "  \"matched\": %lld,\n",   (long long)matched);
    std::fprintf(jf, "  \"unmatched\": %lld,\n", (long long)unmatched);
    std::fprintf(jf, "  \"agree\": %lld,\n",     (long long)agree);
    std::fprintf(jf, "  \"disagree\": %lld,\n",  (long long)disagree);
    std::fprintf(jf, "  \"nAddBJets_ge3\": %lld,\n", (long long)nGe3);
    std::fprintf(jf, "  \"expanded_sub_in_set\": %lld,\n", (long long)nExtended);
    std::fprintf(jf, "  \"viol_ext_but_lt3\": %lld,\n",  (long long)nExtNotGe3);
    std::fprintf(jf, "  \"viol_ge3_not_ext\": %lld,\n",  (long long)nGe3NotExt);
    std::fprintf(jf, "  \"viol_prefix_changed\": %lld,\n", (long long)nPrefixBad);
    std::fprintf(jf, "  \"viol_le2_changed\": %lld,\n",  (long long)nLe2Changed);
    std::fprintf(jf, "  \"ext_consistent\": %s,\n", extOkNow ? "true" : "false");
    auto dumpMap = [&](const char* key, const std::map<int, Long64_t>& m2) {
      std::fprintf(jf, "  \"%s\": {", key);
      bool first = true;
      for (const auto& kv : m2) {
        std::fprintf(jf, "%s\"%d\": %lld", first ? "" : ", ", kv.first,
                     (long long)kv.second);
        first = false;
      }
      std::fprintf(jf, "},\n");
    };
    dumpMap("expanded_sub_counts", expSubCount);
    dumpMap("orig_sub_of_reclassified", origSubOfExt);
    dumpMap("disagree_by_nano_sub", disagreeBySub);
    // exit_code is what THIS chunk would return; the aggregator re-derives the
    // sample-level verdict from the summed counters, not from these codes.
    int wouldExit = 0;
    if (matched == 0)        wouldExit = 5;
    else if (disagree != 0)  wouldExit = 6;
    else if (!extOkNow)      wouldExit = 8;
    std::fprintf(jf, "  \"exit_code\": %d\n", wouldExit);
    std::fprintf(jf, "}\n");
    std::fclose(jf);
    std::printf("[matchSorted] wrote counters JSON -> %s\n", args.json.c_str());
  }

  if (matched == 0) { std::printf("[matchSorted] >>> NO events matched.\n"); return 5; }
  if (disagree != 0) { std::printf("[matchSorted] >>> genTtbarId DISAGREEMENT.\n"); return 6; }
  if (!extOk) { std::printf("[matchSorted] >>> extended-id check FAILED.\n"); return 8; }
  std::printf("[matchSorted] >>> ALL %lld matched events agree on genTtbarId and Expanded_genTtbarId is consistent.\n", matched);
  return 0;
}
