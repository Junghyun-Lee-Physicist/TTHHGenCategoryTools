// -*- C++ -*-
// =============================================================================
// sortSplitExtend
// =============================================================================
// Turn an UNORDERED set of extend file ROOT files into a GLOBALLY (run, lumi, event)
// -SORTED set of fixed-size "part" ROOT files, plus a text index recording the
// (first, last) key of each part.  This lets any consumer (the validator here,
// or the analysis later) look up an event's Expanded_genTtbarId by:
//     1. reading the small index,
//     2. finding which part covers (lumi, event),
//     3. loading ONLY that part (a few tens of MB) and binary-searching it,
// instead of holding the whole multi-hundred-million-row extend file in memory.
//
// Why external sort:
//   The extend file files are NOT globally ordered (CRAB FileBased splitting plus
//   MiniAOD's own event ordering scatter a given lumisection across many files;
//   confirmed with scanOrder).  A single in-memory sort of ~236M rows would need
//   ~20 GB.  Instead we:
//     PASS 1 (partition+sort): stream the input, accumulate rows until a chunk
//             reaches --chunk-size, sort that chunk in memory, write it to a
//             temporary ROOT file.  Memory = one chunk.
//     PASS 2 (k-way merge): open all sorted chunks at once, repeatedly take the
//             globally smallest current row across chunks (a heap over chunk
//             heads), and stream the merged, fully-sorted output into part files
//             of --part-size rows each.  Memory = one row per chunk + one output
//             buffer.  This is what places each chunk's rows "in between" the
//             others to produce a single sorted order.
//
// Output:
//   <out-dir>/part00000.root, part00001.root, ...   (TTree "Events", same
//                                                      schema as the extend file)
//   <out-dir>/index.txt   one line per part:
//       partIndex  nRows  firstRun firstLumi firstEvent  lastRun lastLumi lastEvent
//
// Schema carried through (all extend file branches):
//   run/i  luminosityBlock/i  event/l  genTtbarId/I  Expanded_genTtbarId/I
//   nAddBJets/I  nAddBJetsMulti/I
//
// Usage:
//   sortSplitExtend --filelist extend_files.txt --out-dir sorted_TTToHadronic \
//       [--part-size 500000] [--chunk-size 10000000] [--tree Events] \
//       [--tmp-dir /tmp/ssX]
//
// Memory knobs:
//   --chunk-size  rows per in-memory sort chunk (default 10,000,000 ~ 320 MB)
//   --part-size   rows per output part           (default 500,000   ~ 16 MB)
// =============================================================================

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <queue>
#include <string>
#include <vector>

#include <TChain.h>
#include <TFile.h>
#include <TTree.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string filelist;
  std::string outDir;
  std::string tmpDir;
  std::string tree = "Events";
  Long64_t    partSize  = 500000;
  Long64_t    chunkSize = 10000000;
};

[[noreturn]] void usage(int code) {
  std::printf(
    "sortSplitExtend\n"
    "  --filelist PATH     text file, one extend file ROOT path per line\n"
    "  --out-dir DIR       output directory for partNNNNN.root + index.txt\n"
    "  --part-size N       rows per output part (default 500000)\n"
    "  --chunk-size N      rows per in-memory sort chunk (default 10000000)\n"
    "  --tree NAME         tree name (default Events)\n"
    "  --tmp-dir DIR       where to write sorted chunks (default <out-dir>/_tmp)\n"
    "  -h, --help          this help\n");
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
    if      (s == "--filelist")   a.filelist  = need(i, "--filelist");
    else if (s == "--out-dir")    a.outDir    = need(i, "--out-dir");
    else if (s == "--tmp-dir")    a.tmpDir    = need(i, "--tmp-dir");
    else if (s == "--tree")       a.tree      = need(i, "--tree");
    else if (s == "--part-size")  a.partSize  = std::stoll(need(i, "--part-size"));
    else if (s == "--chunk-size") a.chunkSize = std::stoll(need(i, "--chunk-size"));
    else if (s == "-h" || s == "--help") usage(0);
    else { std::fprintf(stderr, "ERROR: unknown arg '%s'\n", s.c_str()); usage(2); }
  }
  if (a.filelist.empty()) { std::fprintf(stderr, "ERROR: --filelist required\n"); usage(2); }
  if (a.outDir.empty())   { std::fprintf(stderr, "ERROR: --out-dir required\n");  usage(2); }
  if (a.tmpDir.empty())   a.tmpDir = a.outDir + "/_tmp";
  if (a.partSize  <= 0)   { std::fprintf(stderr, "ERROR: --part-size must be > 0\n");  std::exit(2); }
  if (a.chunkSize <= 0)   { std::fprintf(stderr, "ERROR: --chunk-size must be > 0\n"); std::exit(2); }
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

// One extend file row.  Comparable by (run, lumi, event).
struct Row {
  UInt_t    run;
  UInt_t    lumi;
  ULong64_t event;
  Int_t     genTtbarId;
  Int_t     expandedId;
  Int_t     nAddBJets;
  Int_t     nAddBJetsMulti;
};

inline bool keyLess(const Row& a, const Row& b) {
  if (a.run  != b.run)  return a.run  < b.run;
  if (a.lumi != b.lumi) return a.lumi < b.lumi;
  return a.event < b.event;
}

// Bind a tree's branches to a Row (read side).
void bindRead(TTree* t, Row& r) {
  t->SetBranchStatus("*", 0);
  for (const char* b : {"run", "luminosityBlock", "event",
                        "genTtbarId", "Expanded_genTtbarId",
                        "nAddBJets", "nAddBJetsMulti"})
    t->SetBranchStatus(b, 1);
  t->SetBranchAddress("run",                 &r.run);
  t->SetBranchAddress("luminosityBlock",     &r.lumi);
  t->SetBranchAddress("event",               &r.event);
  t->SetBranchAddress("genTtbarId",          &r.genTtbarId);
  t->SetBranchAddress("Expanded_genTtbarId", &r.expandedId);
  t->SetBranchAddress("nAddBJets",           &r.nAddBJets);
  t->SetBranchAddress("nAddBJetsMulti",      &r.nAddBJetsMulti);
}

// Create a tree + bind branches for writing a Row.
TTree* makeWriteTree(Row& r, const char* name = "Events") {
  TTree* t = new TTree(name, "sorted extend");
  t->Branch("run",                 &r.run,            "run/i");
  t->Branch("luminosityBlock",     &r.lumi,           "luminosityBlock/i");
  t->Branch("event",               &r.event,          "event/l");
  t->Branch("genTtbarId",          &r.genTtbarId,     "genTtbarId/I");
  t->Branch("Expanded_genTtbarId", &r.expandedId,     "Expanded_genTtbarId/I");
  t->Branch("nAddBJets",           &r.nAddBJets,      "nAddBJets/I");
  t->Branch("nAddBJetsMulti",      &r.nAddBJetsMulti, "nAddBJetsMulti/I");
  return t;
}

std::string chunkPath(const std::string& tmpDir, int idx) {
  char buf[32];
  std::snprintf(buf, sizeof(buf), "/chunk%05d.root", idx);
  return tmpDir + buf;
}

std::string partPath(const std::string& outDir, int idx) {
  char buf[32];
  std::snprintf(buf, sizeof(buf), "/part%05d.root", idx);
  return outDir + buf;
}

// Write a sorted in-memory chunk to a temporary ROOT file.
void writeChunk(const std::string& path, const std::string& tree, std::vector<Row>& rows) {
  TFile* f = TFile::Open(path.c_str(), "RECREATE");
  if (!f || f->IsZombie()) { std::fprintf(stderr, "ERROR: cannot create %s\n", path.c_str()); std::exit(4); }
  Row w;
  TTree* t = makeWriteTree(w, tree.c_str());
  for (const Row& r : rows) { w = r; t->Fill(); }
  t->Write("", TObject::kOverwrite);
  f->Close();
  delete f;
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::printf(">>> sortSplitExtend start\n");
  std::printf(">>>   filelist   = %s\n", args.filelist.c_str());
  std::printf(">>>   out-dir    = %s\n", args.outDir.c_str());
  std::printf(">>>   tmp-dir    = %s\n", args.tmpDir.c_str());
  std::printf(">>>   part-size  = %lld\n", args.partSize);
  std::printf(">>>   chunk-size = %lld\n", args.chunkSize);
  std::fflush(stdout);

  // mkdir out-dir and tmp-dir (via system; portable enough for Tier3 shells)
  std::string mk1 = "mkdir -p '" + args.outDir + "'";
  std::string mk2 = "mkdir -p '" + args.tmpDir + "'";
  if (std::system(mk1.c_str()) != 0 || std::system(mk2.c_str()) != 0) {
    std::fprintf(stderr, "ERROR: cannot create output/tmp directories\n");
    return 4;
  }

  const std::vector<std::string> files = readFilelist(args.filelist);
  if (files.empty()) { std::fprintf(stderr, "ERROR: filelist empty\n"); return 3; }

  // ---------------------------------------------------------------------------
  // PASS 1: partition into sorted chunks
  // ---------------------------------------------------------------------------
  std::printf(">>> PASS 1: partition + sort into chunks\n"); std::fflush(stdout);

  TChain in(args.tree.c_str());
  int added = 0;
  for (const auto& f : files) if (in.Add(f.c_str()) > 0) ++added;
  Row r;
  bindRead(&in, r);
  const Long64_t nTotal = in.GetEntries();
  std::printf(">>>   input files=%d, total rows=%lld\n", added, nTotal); std::fflush(stdout);

  std::vector<Row> buf;
  buf.reserve(static_cast<size_t>(args.chunkSize));
  int nChunks = 0;
  Long64_t seen = 0;

  auto flushChunk = [&]() {
    if (buf.empty()) return;
    std::sort(buf.begin(), buf.end(), keyLess);
    const std::string cp = chunkPath(args.tmpDir, nChunks);
    writeChunk(cp, args.tree, buf);
    std::printf(">>>   wrote chunk %d : %zu rows -> %s\n", nChunks, buf.size(), cp.c_str());
    std::fflush(stdout);
    ++nChunks;
    buf.clear();
  };

  for (Long64_t i = 0; i < nTotal; ++i) {
    in.GetEntry(i);
    buf.push_back(r);
    if ((Long64_t)buf.size() >= args.chunkSize) flushChunk();
    if ((++seen % 10000000) == 0) { std::printf(">>>   read %lld / %lld\n", seen, nTotal); std::fflush(stdout); }
  }
  flushChunk();
  std::printf(">>> PASS 1 done: %d sorted chunks\n", nChunks); std::fflush(stdout);

  if (nChunks == 0) { std::fprintf(stderr, "ERROR: no rows read\n"); return 3; }

  // ---------------------------------------------------------------------------
  // PASS 2: k-way merge chunks -> sorted parts + index
  // ---------------------------------------------------------------------------
  std::printf(">>> PASS 2: k-way merge -> parts\n"); std::fflush(stdout);

  // Open every chunk, bind a private Row to each.
  std::vector<TFile*> cf(nChunks, nullptr);
  std::vector<TTree*> ct(nChunks, nullptr);
  std::vector<Row>    head(nChunks);
  std::vector<Long64_t> pos(nChunks, 0), nent(nChunks, 0);
  for (int c = 0; c < nChunks; ++c) {
    cf[c] = TFile::Open(chunkPath(args.tmpDir, c).c_str());
    if (!cf[c] || cf[c]->IsZombie()) { std::fprintf(stderr, "ERROR: reopen chunk %d failed\n", c); return 4; }
    ct[c] = dynamic_cast<TTree*>(cf[c]->Get(args.tree.c_str()));
    if (!ct[c]) { std::fprintf(stderr, "ERROR: no tree in chunk %d\n", c); return 4; }
    bindRead(ct[c], head[c]);
    nent[c] = ct[c]->GetEntries();
  }

  // Min-heap over chunk heads, keyed by (run,lumi,event).
  struct HeapItem { Row row; int chunk; };
  auto cmp = [](const HeapItem& a, const HeapItem& b) { return keyLess(b.row, a.row); }; // min-heap
  std::priority_queue<HeapItem, std::vector<HeapItem>, decltype(cmp)> pq(cmp);

  auto pull = [&](int c) -> bool {
    if (pos[c] >= nent[c]) return false;
    ct[c]->GetEntry(pos[c]++);
    pq.push(HeapItem{head[c], c});
    return true;
  };
  for (int c = 0; c < nChunks; ++c) pull(c);

  // Output part files + index.
  std::ofstream index((args.outDir + "/index.txt").c_str());
  if (!index) { std::fprintf(stderr, "ERROR: cannot write index.txt\n"); return 4; }
  index << "# partIndex nRows firstRun firstLumi firstEvent lastRun lastLumi lastEvent\n";

  int partIdx = 0;
  Long64_t partRows = 0, mergedRows = 0;
  TFile* pf = nullptr;
  TTree* pt = nullptr;
  Row w;            // write-row for current part
  Row firstKey{}, lastKey{};

  auto openPart = [&]() {
    pf = TFile::Open(partPath(args.outDir, partIdx).c_str(), "RECREATE");
    if (!pf || pf->IsZombie()) { std::fprintf(stderr, "ERROR: cannot create part %d\n", partIdx); std::exit(4); }
    pt = makeWriteTree(w, args.tree.c_str());
    partRows = 0;
  };
  auto closePart = [&]() {
    if (!pf) return;
    pt->Write("", TObject::kOverwrite);
    pf->Close();
    delete pf; pf = nullptr; pt = nullptr;
    index << partIdx << " " << partRows << " "
          << firstKey.run << " " << firstKey.lumi << " " << firstKey.event << " "
          << lastKey.run  << " " << lastKey.lumi  << " " << lastKey.event  << "\n";
    index.flush();
    std::printf(">>>   wrote part %d : %lld rows  [%u:%u:%llu .. %u:%u:%llu]\n",
                partIdx, partRows,
                firstKey.run, firstKey.lumi, (unsigned long long)firstKey.event,
                lastKey.run,  lastKey.lumi,  (unsigned long long)lastKey.event);
    std::fflush(stdout);
    ++partIdx;
  };

  openPart();
  while (!pq.empty()) {
    HeapItem it = pq.top(); pq.pop();
    if (partRows == 0) firstKey = it.row;
    w = it.row;
    pt->Fill();
    lastKey = it.row;
    ++partRows; ++mergedRows;
    pull(it.chunk);                 // replace the head we just consumed
    if (partRows >= args.partSize) { closePart(); openPart(); }
    if ((mergedRows % 10000000) == 0) { std::printf(">>>   merged %lld / %lld\n", mergedRows, nTotal); std::fflush(stdout); }
  }
  if (partRows > 0) closePart();
  else if (pf) { pt->Write("", TObject::kOverwrite); pf->Close(); delete pf; }  // empty final part safety
  index.close();

  for (int c = 0; c < nChunks; ++c) { if (cf[c]) { cf[c]->Close(); delete cf[c]; } }

  std::printf(">>> PASS 2 done: merged %lld rows into %d parts\n", mergedRows, partIdx);

  // Sanity: merged count must equal input count.
  if (mergedRows != nTotal) {
    std::fprintf(stderr, ">>> WARNING: merged rows (%lld) != input rows (%lld)\n",
                 mergedRows, nTotal);
  }

  // Clean up temporary chunks.
  std::string rmtmp = "rm -f '" + args.tmpDir + "'/chunk*.root";
  std::system(rmtmp.c_str());
  std::printf(">>> removed temporary chunks in %s\n", args.tmpDir.c_str());

  std::printf(">>> done. parts + index in %s\n", args.outDir.c_str());
  std::fflush(stdout);
  return 0;
}
