// make_sidecar.C -- a synthetic ttbarId-extend ("sidecar") file for Validation/tests/test_extract_format2.sh
//   root -l -b -q 'make_sidecar.C("rows.tsv","out.root")'           (tree Events, the 7 extend branches)
//   root -l -b -q 'make_sidecar.C("rows.tsv","out.root","Events",1)' (without nAddBJetsMulti: a broken input)
// rows.tsv: one row per line, blank-separated: run lumi event genTtbarId Expanded_genTtbarId nAddBJets nAddBJetsMulti
// ('#' lines and empty lines are skipped). An empty TSV gives a tree with 0 entries.
// [STEP 46] fp (the 5th argument; Validation/tests/test_extract_format3.sh): 1 = the four fingerprint branches of the
//   CRAB sidecar, Generator_x1/F Generator_x2/F Generator_id1/I Generator_id2/I, from four more columns per row
//   (x1 x2 id1 id2; x read with strtof: decimal or hex float); 2 = only Generator_x1 (a broken input); 0 = none.
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>

#include <TFile.h>
#include <TTree.h>

void make_sidecar(const char* tsv, const char* out, const char* tree = "Events", int dropMulti = 0, int fp = 0) {
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
  Float_t x1 = 0, x2 = 0;
  Int_t id1 = 0, id2 = 0;
  if (fp >= 1) t.Branch("Generator_x1", &x1, "Generator_x1/F");
  if (fp == 1) {
    t.Branch("Generator_x2", &x2, "Generator_x2/F");
    t.Branch("Generator_id1", &id1, "Generator_id1/I");
    t.Branch("Generator_id2", &id2, "Generator_id2/I");
  }
  std::ifstream in(tsv);
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream s(line);
    s >> run >> lumi >> event >> gen >> exp >> nadd >> nmulti;
    if (fp >= 1) {
      std::string a, b;
      s >> a >> b >> id1 >> id2;
      x1 = std::strtof(a.c_str(), nullptr);
      x2 = std::strtof(b.c_str(), nullptr);
    }
    t.Fill();
  }
  t.Write();
  f.Close();
}
