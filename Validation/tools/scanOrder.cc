// -*- C++ -*-
// =============================================================================
// scanOrder
// =============================================================================
// Diagnose whether the files in a filelist are laid out in (run, lumi, event)
// order, and how the (run, lumi) ranges of consecutive files relate.  The goal
// is to find out whether a given filelist (extend file from MiniAOD, or NanoAOD)
// is block-ordered by lumisection, so that matching could be done in lumi-range
// chunks instead of loading everything into memory.
//
// For each file it reports, reading the tree in stored order:
//   idx          position in the filelist
//   nEntries     number of events in the file
//   firstRLE     (run, lumi, event) of the first entry
//   lastRLE      (run, lumi, event) of the last entry
//   minLumi      smallest luminosityBlock seen in the file
//   maxLumi      largest luminosityBlock seen in the file
//   sortedInFile 1 if (run,lumi,event) is non-decreasing within the file, else 0
//
// Then it prints summary diagnostics across files:
//   * whether each file is internally sorted by (run,lumi,event)
//   * whether files are globally ordered (file i's maxLumi <= file i+1's minLumi)
//   * any lumi-range OVERLAP between files (which would break chunked matching)
//
// It does NOT build any big map; it streams each file and keeps only first/last
// /min/max per file, so memory is negligible regardless of sample size.
//
// Usage:
//   scanOrder --filelist filelist_TTToSemiLeptonic.txt [--tree Events]
//             [--max-files N] [--csv out.csv]
//
// Branch names assumed: run (UInt), luminosityBlock (UInt), event (ULong64).
// Override the tree name with --tree if needed (default Events).
// =============================================================================

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <TChain.h>
#include <TFile.h>
#include <TTree.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string filelist;
  std::string tree = "Events";
  std::string csv  = "";
  int         maxFiles = -1;
};

[[noreturn]] void usage(int code) {
  std::cout <<
    "scanOrder\n"
    "  --filelist PATH   text file, one ROOT path per line ('#' comments ok)\n"
    "  --tree NAME       tree name (default Events)\n"
    "  --max-files N     only scan the first N files (default: all)\n"
    "  --csv PATH        also write the per-file table as CSV\n"
    "  -h, --help        this help\n";
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
    if      (s == "--filelist")  a.filelist = need(i, "--filelist");
    else if (s == "--tree")      a.tree     = need(i, "--tree");
    else if (s == "--csv")       a.csv      = need(i, "--csv");
    else if (s == "--max-files") a.maxFiles = std::stoi(need(i, "--max-files"));
    else if (s == "-h" || s == "--help") usage(0);
    else { std::cerr << "ERROR: unknown arg '" << s << "'\n"; usage(2); }
  }
  if (a.filelist.empty()) { std::cerr << "ERROR: --filelist required\n"; usage(2); }
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

// One (run,lumi,event) triple, comparable in that priority order.
struct RLE {
  UInt_t    run;
  UInt_t    lumi;
  ULong64_t event;
  bool operator<=(const RLE& o) const {
    if (run  != o.run)  return run  < o.run;
    if (lumi != o.lumi) return lumi < o.lumi;
    return event <= o.event;
  }
};

struct FileInfo {
  int       idx;
  Long64_t  nEntries;
  RLE       first;
  RLE       last;
  UInt_t    minLumi;
  UInt_t    maxLumi;
  bool      sortedInFile;
  bool      opened;
};

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::cout << "[scanOrder] filelist = " << args.filelist << "\n";
  std::cout << "[scanOrder] tree     = " << args.tree << "\n";

  std::vector<std::string> files = readFilelist(args.filelist);
  if (files.empty()) { std::cerr << "ERROR: filelist empty\n"; return 3; }
  if (args.maxFiles >= 0 && (int)files.size() > args.maxFiles)
    files.resize(args.maxFiles);
  std::cout << "[scanOrder] files to scan = " << files.size() << "\n\n";

  std::vector<FileInfo> infos;
  infos.reserve(files.size());

  for (size_t fi = 0; fi < files.size(); ++fi) {
    FileInfo info{};
    info.idx = (int)fi;
    info.opened = false;

    TFile* f = TFile::Open(files[fi].c_str());
    if (!f || f->IsZombie()) {
      std::cerr << "[scanOrder] WARNING: cannot open file " << fi
                << " : " << files[fi] << "\n";
      infos.push_back(info);
      if (f) delete f;
      continue;
    }
    TTree* t = dynamic_cast<TTree*>(f->Get(args.tree.c_str()));
    if (!t) {
      std::cerr << "[scanOrder] WARNING: no tree '" << args.tree
                << "' in file " << fi << " : " << files[fi] << "\n";
      f->Close(); delete f;
      infos.push_back(info);
      continue;
    }

    UInt_t    run = 0, lumi = 0;
    ULong64_t evt = 0;
    t->SetBranchStatus("*", 0);
    for (const char* b : {"run", "luminosityBlock", "event"})
      t->SetBranchStatus(b, 1);
    t->SetBranchAddress("run",             &run);
    t->SetBranchAddress("luminosityBlock", &lumi);
    t->SetBranchAddress("event",           &evt);

    const Long64_t n = t->GetEntries();
    info.nEntries = n;
    info.opened   = true;
    info.sortedInFile = true;

    if (n > 0) {
      t->GetEntry(0);
      info.first  = RLE{run, lumi, evt};
      info.minLumi = lumi;
      info.maxLumi = lumi;
      RLE prev = info.first;

      for (Long64_t i = 0; i < n; ++i) {
        t->GetEntry(i);
        RLE cur{run, lumi, evt};
        if (lumi < info.minLumi) info.minLumi = lumi;
        if (lumi > info.maxLumi) info.maxLumi = lumi;
        if (i > 0 && !(prev <= cur)) info.sortedInFile = false;
        prev = cur;
      }
      info.last = prev;
    }

    f->Close();
    delete f;
    infos.push_back(info);

    std::cout << "[scanOrder] file " << fi << " / " << files.size()
              << "  entries=" << info.nEntries
              << "  lumi[" << info.minLumi << "," << info.maxLumi << "]"
              << "  sortedInFile=" << (info.sortedInFile ? 1 : 0) << "\n";
  }

  // ---- Per-file table ----
  std::cout << "\n===== per-file (run,lumi,event) table =====\n";
  std::printf("%4s %12s %22s %22s %10s %10s %6s\n",
              "idx", "nEntries", "first(run:lumi:event)",
              "last(run:lumi:event)", "minLumi", "maxLumi", "sorted");
  for (const auto& in : infos) {
    if (!in.opened) {
      std::printf("%4d %12s %22s %22s %10s %10s %6s\n",
                  in.idx, "(FAILED)", "-", "-", "-", "-", "-");
      continue;
    }
    char fbuf[64], lbuf[64];
    std::snprintf(fbuf, sizeof(fbuf), "%u:%u:%llu",
                  in.first.run, in.first.lumi, (unsigned long long)in.first.event);
    std::snprintf(lbuf, sizeof(lbuf), "%u:%u:%llu",
                  in.last.run, in.last.lumi, (unsigned long long)in.last.event);
    std::printf("%4d %12lld %22s %22s %10u %10u %6d\n",
                in.idx, in.nEntries, fbuf, lbuf,
                in.minLumi, in.maxLumi, in.sortedInFile ? 1 : 0);
  }

  // ---- Optional CSV ----
  if (!args.csv.empty()) {
    std::ofstream out(args.csv);
    if (!out) {
      std::cerr << "[scanOrder] WARNING: cannot write CSV " << args.csv << "\n";
    } else {
      out << "idx,nEntries,first_run,first_lumi,first_event,"
             "last_run,last_lumi,last_event,minLumi,maxLumi,sortedInFile,opened\n";
      for (const auto& in : infos) {
        out << in.idx << "," << in.nEntries << ","
            << in.first.run << "," << in.first.lumi << "," << in.first.event << ","
            << in.last.run << "," << in.last.lumi << "," << in.last.event << ","
            << in.minLumi << "," << in.maxLumi << ","
            << (in.sortedInFile ? 1 : 0) << "," << (in.opened ? 1 : 0) << "\n";
      }
      std::cout << "[scanOrder] wrote CSV " << args.csv << "\n";
    }
  }

  // ---- Cross-file diagnostics ----
  std::cout << "\n===== cross-file ordering diagnostics =====\n";

  int nUnsortedInFile = 0;
  for (const auto& in : infos)
    if (in.opened && in.nEntries > 0 && !in.sortedInFile) ++nUnsortedInFile;
  std::cout << "files not internally sorted by (run,lumi,event) : "
            << nUnsortedInFile << "\n";

  // Global ordering: does file i's last <= file (i+1)'s first ?
  int nOutOfOrder = 0;
  int nLumiOverlap = 0;
  const FileInfo* prev = nullptr;
  for (const auto& in : infos) {
    if (!in.opened || in.nEntries == 0) continue;
    if (prev) {
      if (!(prev->last <= in.first)) {
        ++nOutOfOrder;
        if (nOutOfOrder <= 20)
          std::cout << "  OUT-OF-ORDER between file " << prev->idx
                    << " (last lumi=" << prev->last.lumi << ") and file "
                    << in.idx << " (first lumi=" << in.first.lumi << ")\n";
      }
      // lumi-range overlap: prev.maxLumi >= in.minLumi means lumi ranges overlap
      if (prev->maxLumi >= in.minLumi) {
        ++nLumiOverlap;
        if (nLumiOverlap <= 20)
          std::cout << "  LUMI-OVERLAP: file " << prev->idx
                    << " maxLumi=" << prev->maxLumi << "  vs  file " << in.idx
                    << " minLumi=" << in.minLumi << "\n";
      }
    }
    prev = &in;
  }

  std::cout << "\n[scanOrder] SUMMARY for " << args.filelist << ":\n";
  std::cout << "  files scanned                 : " << infos.size() << "\n";
  std::cout << "  files not internally sorted   : " << nUnsortedInFile << "\n";
  std::cout << "  consecutive files out of order: " << nOutOfOrder << "\n";
  std::cout << "  consecutive files lumi-overlap: " << nLumiOverlap << "\n";

  if (nUnsortedInFile == 0 && nOutOfOrder == 0 && nLumiOverlap == 0) {
    std::cout << "  >>> Files ARE globally ordered by (run,lumi,event) with no "
                 "lumi overlap.\n"
                 "      Chunked / streaming matching by lumi range is feasible.\n";
  } else if (nLumiOverlap > 0) {
    std::cout << "  >>> Files have OVERLAPPING lumi ranges. A given lumisection "
                 "may be spread\n"
                 "      across multiple files, so simple per-file lumi chunking "
                 "is NOT safe.\n";
  } else {
    std::cout << "  >>> Files are not strictly ordered; see flags above.\n";
  }

  return 0;
}
