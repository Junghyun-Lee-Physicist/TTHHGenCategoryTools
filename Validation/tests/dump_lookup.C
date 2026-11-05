// dump_lookup.C -- a tt+nb lookup as text, for Validation/tests/test_extract_format2.sh
//   root -l -b -q 'dump_lookup.C("ttnb_X.root","TtNb")'
// Lines: NAMED <name> (then its text, one LINE per line, then END) for lookup_format, nano_datasets, sources;
//   TREE <name> <entries>; LEAF <name> <type> per leaf; ROW <datasetIdx or -1> run lumi event genTtbarId
//   Expanded_genTtbarId nAddBJets nAddBJetsMulti per entry, in the file's order; [STEP 46] a tree with Generator_x1
//   (format 3) adds Generator_x1 Generator_x2 (%.9g: exact for a float) Generator_id1 Generator_id2 to each ROW.
#include <cstdio>
#include <string>

#include <TFile.h>
#include <TLeaf.h>
#include <TNamed.h>
#include <TObjArray.h>
#include <TTree.h>

void dump_lookup(const char* file, const char* tree = "TtNb") {
  TFile f(file, "READ");
  if (f.IsZombie()) { std::printf("DUMPFAIL cannot open %s\n", file); return; }
  const char* names[] = {"lookup_format", "nano_datasets", "sources"};
  for (const char* n : names) {
    TNamed* o = dynamic_cast<TNamed*>(f.Get(n));
    if (!o) { std::printf("NONAMED %s\n", n); continue; }
    std::printf("NAMED %s\n", n);
    std::string s = o->GetTitle(), cur;
    for (char c : s) {
      if (c == '\n') { std::printf("LINE %s\n", cur.c_str()); cur.clear(); }
      else cur += c;
    }
    if (!cur.empty()) std::printf("LINE %s\n", cur.c_str());
    std::printf("END\n");
  }
  TTree* t = dynamic_cast<TTree*>(f.Get(tree));
  if (!t) { std::printf("DUMPFAIL no tree %s\n", tree); return; }
  std::printf("TREE %s %lld\n", tree, t->GetEntries());
  TObjArray* leaves = t->GetListOfLeaves();
  for (int i = 0; i < leaves->GetEntries(); ++i) {
    TLeaf* l = static_cast<TLeaf*>(leaves->At(i));
    std::printf("LEAF %s %s\n", l->GetName(), l->GetTypeName());
  }
  UInt_t run = 0, lumi = 0;
  ULong64_t event = 0;
  Int_t gen = 0, exp = 0, nadd = 0, nmulti = 0, ds = -1;
  t->SetBranchAddress("run", &run);
  t->SetBranchAddress("luminosityBlock", &lumi);
  t->SetBranchAddress("event", &event);
  t->SetBranchAddress("genTtbarId", &gen);
  t->SetBranchAddress("Expanded_genTtbarId", &exp);
  t->SetBranchAddress("nAddBJets", &nadd);
  t->SetBranchAddress("nAddBJetsMulti", &nmulti);
  const bool hasDs = t->GetBranch("datasetIdx") != nullptr;
  if (hasDs) t->SetBranchAddress("datasetIdx", &ds);
  Float_t x1 = 0, x2 = 0;
  Int_t id1 = 0, id2 = 0;
  const bool hasFp = t->GetBranch("Generator_x1") != nullptr;   // [STEP 46] format 3
  if (hasFp) {
    t->SetBranchAddress("Generator_x1", &x1);
    t->SetBranchAddress("Generator_x2", &x2);
    t->SetBranchAddress("Generator_id1", &id1);
    t->SetBranchAddress("Generator_id2", &id2);
  }
  for (Long64_t i = 0; i < t->GetEntries(); ++i) {
    t->GetEntry(i);
    if (hasFp)
      std::printf("ROW %d %u %u %llu %d %d %d %d %.9g %.9g %d %d\n", hasDs ? ds : -1, run, lumi, (unsigned long long)event,
                  gen, exp, nadd, nmulti, static_cast<double>(x1), static_cast<double>(x2), id1, id2);
    else
      std::printf("ROW %d %u %u %llu %d %d %d %d\n", hasDs ? ds : -1, run, lumi, (unsigned long long)event, gen, exp,
                  nadd, nmulti);
  }
}
