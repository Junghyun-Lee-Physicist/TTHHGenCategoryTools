// make_sidecar.C -- a synthetic ttbarId-extend ("sidecar") file for Validation/tests/test_extract_format2.sh
//   root -l -b -q 'make_sidecar.C("rows.tsv","out.root")'           (tree Events, the 7 extend branches)
//   root -l -b -q 'make_sidecar.C("rows.tsv","out.root","Events",1)' (without nAddBJetsMulti: a broken input)
// rows.tsv: one row per line, blank-separated: run lumi event genTtbarId Expanded_genTtbarId nAddBJets nAddBJetsMulti
// ('#' lines and empty lines are skipped). An empty TSV gives a tree with 0 entries.
#include <fstream>
#include <sstream>
#include <string>

#include <TFile.h>
#include <TTree.h>

void make_sidecar(const char* tsv, const char* out, const char* tree = "Events", int dropMulti = 0) {
  TFile f(out, "RECREATE");
  TTree t(tree, "synthetic ttbarId-extend rows (test_extract_format2.sh)");
  UInt_t run = 0, lumi = 0;
  ULong64_t event = 0;
  Int_t gen = 0, exp = 0, nadd = 0, nmulti = 0;
  t.Branch("run", &run, "run/i");
  t.Branch("luminosityBlock", &lumi, "luminosityBlock/i");
  t.Branch("event", &event, "event/l");
  t.Branch("genTtbarId", &gen, "genTtbarId/I");
  t.Branch("Expanded_genTtbarId", &exp, "Expanded_genTtbarId/I");
  t.Branch("nAddBJets", &nadd, "nAddBJets/I");
  if (!dropMulti) t.Branch("nAddBJetsMulti", &nmulti, "nAddBJetsMulti/I");
  std::ifstream in(tsv);
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream s(line);
    s >> run >> lumi >> event >> gen >> exp >> nadd >> nmulti;
    t.Fill();
  }
  t.Write();
  f.Close();
}
