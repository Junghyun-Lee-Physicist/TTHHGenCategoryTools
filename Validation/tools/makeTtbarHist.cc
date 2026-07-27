// -*- C++ -*-
// =============================================================================
// makeTtbarHist
// =============================================================================
// Fills histograms of the ttbar+HF categorization id from a list of ROOT
// files (a "filelist": one file path per line, '#' comments allowed).
//
// Two input flavours, selected by --mode:
//   --mode nano     : reads only 'genTtbarId'      (central NanoAOD / forgedNtuple)
//   --mode extend file  : reads 'genTtbarId' AND 'Expanded_genTtbarId' AND 'nAddBJets' AND
//                     'nAddBJetsMulti'              (the ttbar-Id extend file output)
//
// Histograms written (TH1):
//   h_genTtbarId        full 5-digit id           (wide range)
//   h_genTtbarId_sub    sub-code = genTtbarId%100 (0..99)   <-- the physics one
//   (extend file mode also:)
//   h_Expanded            full Expanded_genTtbarId
//   h_Expanded_sub        Expanded_genTtbarId % 100              (0..99, shows 61/62/71/72)
//   h_nAddBJets         0..15
//   h_nAddBJetsMulti    0..15
//
// We do NOT use run/luminosityBlock/event: the comparison is a distribution
// (count or shape) comparison over the whole process, so per-event matching
// is unnecessary.  If extend file and nano were run over the same event set, the
// h_genTtbarId* histograms must be bin-by-bin identical.
//
// Usage:
//   makeTtbarHist --filelist filelist_TTToSemiLeptonic.txt
//                 --mode nano --out hist_nano_TTToSemiLeptonic.root
//                 [--tree Events] [--max-events -1] [--label TTToSemiLeptonic]
//
// The output file holds the histograms at top level so plotTtbarCompare can
// read them directly.
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
#include <TH1.h>
#include <RtypesCore.h>

namespace {

struct Args {
  std::string filelist;
  std::string mode;            // "nano" or "extend"
  std::string out;
  std::string tree  = "Events";
  std::string label = "";
  Long64_t    maxEvents = -1;  // -1 = all
};

[[noreturn]] void usage(int code) {
  std::cout <<
    "makeTtbarHist\n"
    "  --filelist PATH     text file, one ROOT file path per line ('#' comments ok)\n"
    "  --mode MODE         'nano' (genTtbarId only) or 'extend' (also Expanded_genTtbarId/nAddBJets)\n"
    "  --out PATH          output ROOT file for the histograms\n"
    "  --tree NAME         tree name (default 'Events')\n"
    "  --label NAME        label stored in histogram titles (default: derived from --out)\n"
    "  --max-events N      cap events read across the whole chain (default -1 = all)\n"
    "  -h, --help          this help\n";
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
    if      (s == "--filelist")   a.filelist  = need(i, "--filelist");
    else if (s == "--mode")       a.mode      = need(i, "--mode");
    else if (s == "--out")        a.out       = need(i, "--out");
    else if (s == "--tree")       a.tree      = need(i, "--tree");
    else if (s == "--label")      a.label     = need(i, "--label");
    else if (s == "--max-events") a.maxEvents = std::stoll(need(i, "--max-events"));
    else if (s == "-h" || s == "--help") usage(0);
    else { std::cerr << "ERROR: unknown arg '" << s << "'\n"; usage(2); }
  }
  if (a.filelist.empty() || a.out.empty() || a.mode.empty()) {
    std::cerr << "ERROR: --filelist, --mode and --out are required\n";
    usage(2);
  }
  if (a.mode == "sidecar") a.mode = "extend";   // back-compat: pre-rename mode name
  if (a.mode != "nano" && a.mode != "extend") {
    std::cerr << "ERROR: --mode must be 'nano' or 'extend' (got '" << a.mode << "')\n";
    std::exit(2);
  }
  if (a.label.empty()) {
    // derive from out filename: strip dir and extension
    std::string b = a.out;
    auto slash = b.find_last_of('/');
    if (slash != std::string::npos) b = b.substr(slash + 1);
    auto dot = b.find_last_of('.');
    if (dot != std::string::npos) b = b.substr(0, dot);
    a.label = b;
  }
  return a;
}

std::vector<std::string> readFilelist(const std::string& path) {
  std::vector<std::string> files;
  std::ifstream in(path);
  if (!in) { std::cerr << "ERROR: cannot open filelist " << path << "\n"; std::exit(3); }
  std::string line;
  while (std::getline(in, line)) {
    // trim leading/trailing whitespace
    auto a = line.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) continue;
    auto b = line.find_last_not_of(" \t\r\n");
    std::string p = line.substr(a, b - a + 1);
    if (p.empty() || p[0] == '#') continue;
    files.push_back(p);
  }
  return files;
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);

  std::cout << "[makeTtbarHist] starting\n";
  std::cout << "[makeTtbarHist]   filelist  = " << args.filelist << "\n";
  std::cout << "[makeTtbarHist]   mode      = " << args.mode << "\n";
  std::cout << "[makeTtbarHist]   out       = " << args.out << "\n";
  std::cout << "[makeTtbarHist]   tree      = " << args.tree << "\n";
  std::cout << "[makeTtbarHist]   label     = " << args.label << "\n";
  std::cout << "[makeTtbarHist]   maxEvents = " << args.maxEvents << "\n";

  const std::vector<std::string> files = readFilelist(args.filelist);
  if (files.empty()) { std::cerr << "ERROR: filelist is empty\n"; return 3; }
  std::cout << "[makeTtbarHist]   files in list = " << files.size() << "\n";

  TChain chain(args.tree.c_str());
  int added = 0;
  for (const auto& f : files) {
    if (chain.Add(f.c_str()) > 0) ++added;
  }
  std::cout << "[makeTtbarHist]   files added to chain = " << added << "\n";
  const Long64_t nEntries = chain.GetEntries();
  std::cout << "[makeTtbarHist]   total entries = " << nEntries << "\n";
  if (nEntries == 0) {
    std::cerr << "ERROR: chain has 0 entries (wrong --tree name? empty files?)\n";
    return 4;
  }

  const bool isExtend = (args.mode == "extend");

  // Branch buffers.
  Int_t genTtbarId = 0, expandedId = 0, nAddBJets = 0, nAddBJetsMulti = 0;

  chain.SetBranchStatus("*", 0);
  chain.SetBranchStatus("genTtbarId", 1);
  chain.SetBranchAddress("genTtbarId", &genTtbarId);
  if (isExtend) {
    for (const char* b : {"Expanded_genTtbarId", "nAddBJets", "nAddBJetsMulti"})
      chain.SetBranchStatus(b, 1);
    chain.SetBranchAddress("Expanded_genTtbarId",         &expandedId);
    chain.SetBranchAddress("nAddBJets",      &nAddBJets);
    chain.SetBranchAddress("nAddBJetsMulti", &nAddBJetsMulti);
  }

  // Histograms.  The full id can be large (e.g. 10153); we use a wide axis.
  // The sub-code (id % 100) is the physically interesting 0..99 axis.
  TH1::SetDefaultSumw2(true);
  auto* h_full = new TH1D("h_genTtbarId",
      (args.label + ";genTtbarId;events").c_str(), 60000, 0, 60000);
  auto* h_sub  = new TH1D("h_genTtbarId_sub",
      (args.label + ";genTtbarId % 100;events").c_str(), 100, 0, 100);

  TH1D *h_tfull = nullptr, *h_tsub = nullptr, *h_na = nullptr, *h_nam = nullptr;
  if (isExtend) {
    h_tfull = new TH1D("h_Expanded",
        (args.label + ";Expanded_genTtbarId;events").c_str(), 60000, 0, 60000);
    h_tsub  = new TH1D("h_Expanded_sub",
        (args.label + ";Expanded_genTtbarId % 100;events").c_str(), 100, 0, 100);
    h_na    = new TH1D("h_nAddBJets",
        (args.label + ";nAddBJets;events").c_str(), 16, 0, 16);
    h_nam   = new TH1D("h_nAddBJetsMulti",
        (args.label + ";nAddBJetsMulti;events").c_str(), 16, 0, 16);
  }

  const Long64_t nLoop = (args.maxEvents < 0)
      ? nEntries : std::min<Long64_t>(args.maxEvents, nEntries);

  for (Long64_t i = 0; i < nLoop; ++i) {
    chain.GetEntry(i);
    h_full->Fill(genTtbarId);
    h_sub->Fill(genTtbarId % 100);
    if (isExtend) {
      h_tfull->Fill(expandedId);
      h_tsub->Fill(expandedId % 100);
      h_na->Fill(nAddBJets);
      h_nam->Fill(nAddBJetsMulti);
    }
    if ((i % 1000000) == 0 && i > 0)
      std::cout << "[makeTtbarHist]   processed " << i << " / " << nLoop << "\n";
  }

  std::cout << "[makeTtbarHist] done looping; "
            << "h_genTtbarId entries=" << (Long64_t)h_full->GetEntries() << "\n";

  TFile fout(args.out.c_str(), "RECREATE");
  if (fout.IsZombie()) { std::cerr << "ERROR: cannot open out " << args.out << "\n"; return 5; }
  fout.cd();
  h_full->Write();
  h_sub->Write();
  if (isExtend) { h_tfull->Write(); h_tsub->Write(); h_na->Write(); h_nam->Write(); }
  fout.Close();

  std::cout << "[makeTtbarHist] wrote " << args.out << "\n";
  return 0;
}
