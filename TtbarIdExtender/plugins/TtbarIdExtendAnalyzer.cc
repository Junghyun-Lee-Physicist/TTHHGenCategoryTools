// -*- C++ -*-
//
// TtbarIdExtendAnalyzer
//
// Writes a small ROOT TTree ("Events") with one row per event holding:
//     run             (UInt_t)
//     luminosityBlock (UInt_t)
//     event           (ULong64_t)
//     genTtbarId      (Int_t)    -- standard CMSSW categorizeGenTtbar output
//     Expanded_genTtbarId          (Int_t)    -- ExtendedTtbarIdProducer output (genTtbarId with the
//                                               nAddBJets>=3 events reclassified to 61/62/71/72)
//     nAddBJets       (Int_t)    -- ExtendedTtbarIdProducer output (un-capped count, pt>20, |eta|<2.4)
//     nAddBJetsMulti  (Int_t)    -- ExtendedTtbarIdProducer output (of nAddBJets, how many host >=2 b-hadrons)
//
// Output: direct TFile (not TFileService)
// ------------------------------------------------
// An earlier iteration used edm::Service<TFileService>.  TFileService isolates each
// module's objects inside a TDirectory named after the module label, so the
// tree landed at "ttbarIdExtend/Events" instead of the top-level "Events".
// That breaks the friend-tree workflow: central NanoAOD has its tree at the
// top level ("Events"), and TTree::AddFriend expects the friend tree to be
// reachable as a plain "Events" too.  Forcing every downstream reader to
// know the "ttbarIdExtend/" prefix is fragile.
//
// We therefore open our OWN TFile directly and create the TTree at the
// file's top level.  The output is then a clean NanoAOD-like file whose
// "Events" tree can be friend-attached with no path gymnastics:
//
//     auto* fc = TFile::Open("central_nanoaod.root");
//     auto* tc = (TTree*)fc->Get("Events");
//     auto* fs = TFile::Open("ttbarIDExtend.root");
//     auto* ts = (TTree*)fs->Get("Events");   // <-- top level, no prefix
//     tc->AddFriend(ts, "extend");
//
// The branch type choices match the central NanoAODv9 schema exactly:
//   * run / luminosityBlock are UInt_t  (NanoAOD 'run/i', 'luminosityBlock/i')
//   * event is ULong64_t                (NanoAOD 'event/l')
//   * genTtbarId is Int_t               (NanoAOD ExtVar("int", ...))
// so byte-identity at the (run, lumi, event) join is guaranteed.
//
// Logging pattern:
//   * LogInfo at construction with all input tags + output file + tree name
//   * safeGetInt(...) wraps iEvent.get() in try/catch
//   * Optional per-event LogVerbatim controlled by an untracked `verbose` PSet
//
// References:
//   * NanoAODv9 branch schema:
//       https://cms-nanoaod-integration.web.cern.ch/integration/master-cmsswmaster/mc102X_doc.html
//   * categorizeGenTtbar canonical setup:
//       https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/ttbarCategorization_cff.py
//   * Why a direct TFile (not TFileService) for a friend-tree-ready output:
//       https://root.cern/manual/trees/#widening-a-tree-via-friends
//

#include <memory>
#include <string>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDGetToken.h"
#include "FWCore/Utilities/interface/Exception.h"
#include "FWCore/Utilities/interface/InputTag.h"

#include <TFile.h>
#include <TTree.h>

class TtbarIdExtendAnalyzer
    : public edm::one::EDAnalyzer<> {
 public:
  explicit TtbarIdExtendAnalyzer(const edm::ParameterSet&);
  ~TtbarIdExtendAnalyzer() override = default;

 private:
  void analyze(const edm::Event&, const edm::EventSetup&) override;
  void beginJob() override;
  void endJob() override;

  int safeGetInt(const edm::Event&,
                 const edm::EDGetTokenT<int>&,
                 const edm::InputTag&,
                 const char* fieldName,
                 int fallback = 0) const;

  // Input tags (kept for log messages on errors).
  const edm::InputTag tagGenTtbarId_, tagExpandedId_, tagNAddB_, tagNAddBMulti_;

  // Tokens.
  const edm::EDGetTokenT<int> tokGenTtbarId_;
  const edm::EDGetTokenT<int> tokExpandedId_;
  const edm::EDGetTokenT<int> tokNAddB_;
  const edm::EDGetTokenT<int> tokNAddBMulti_;

  // Output configuration.
  const std::string outputFile_;
  const std::string treeName_;
  const std::string treeTitle_;
  const bool        buildIndex_;
  const bool        verbosePerEvent_;

  // Per-row buffer (types match NanoAOD schema).
  UInt_t    b_run_;
  UInt_t    b_luminosityBlock_;
  ULong64_t b_event_;
  Int_t     b_genTtbarId_;
  Int_t     b_expandedId_;
  Int_t     b_nAddBJets_;
  Int_t     b_nAddBJetsMulti_;

  // We own these directly (no TFileService).
  TFile* file_ = nullptr;
  TTree* tree_ = nullptr;

  unsigned long long nFilled_ = 0;
  unsigned long long nMissingGenTtbar_   = 0;
  unsigned long long nMissingExpandedId_     = 0;
  unsigned long long nMissingNAddB_      = 0;
  unsigned long long nMissingNAddBMulti_ = 0;
};

TtbarIdExtendAnalyzer::TtbarIdExtendAnalyzer(const edm::ParameterSet& iConfig)
    : tagGenTtbarId_   (iConfig.getParameter<edm::InputTag>("genTtbarId")),
      tagExpandedId_       (iConfig.getParameter<edm::InputTag>("Expanded_genTtbarId")),
      tagNAddB_        (iConfig.getParameter<edm::InputTag>("nAddBJets")),
      tagNAddBMulti_   (iConfig.getParameter<edm::InputTag>("nAddBJetsMulti")),
      tokGenTtbarId_   (consumes<int>(tagGenTtbarId_)),
      tokExpandedId_       (consumes<int>(tagExpandedId_)),
      tokNAddB_        (consumes<int>(tagNAddB_)),
      tokNAddBMulti_   (consumes<int>(tagNAddBMulti_)),
      outputFile_      (iConfig.getParameter<std::string>("outputFile")),
      treeName_        (iConfig.getUntrackedParameter<std::string>("treeName",  "Events")),
      treeTitle_       (iConfig.getUntrackedParameter<std::string>("treeTitle", "ttbar HF categorization extend")),
      buildIndex_      (iConfig.getUntrackedParameter<bool>("buildIndex", true)),
      verbosePerEvent_ (iConfig.getUntrackedParameter<bool>("verbose",    false)) {
  // No usesResource("TFileService"); we manage our own TFile.

  edm::LogInfo("TtbarIdExtendAnalyzer")
      << "constructed:"
      << "  outputFile='" << outputFile_ << "'"
      << "  tree='"       << treeName_ << "'"
      << "  genTtbarId="  << tagGenTtbarId_.encode()
      << "  Expanded_genTtbarId="      << tagExpandedId_.encode()
      << "  nAddBJets="   << tagNAddB_.encode()
      << "  nAddBJetsMulti=" << tagNAddBMulti_.encode()
      << "  buildIndex="  << (buildIndex_ ? "yes" : "no")
      << "  verbose="     << (verbosePerEvent_ ? "yes" : "no");
}

void TtbarIdExtendAnalyzer::beginJob() {
  // Open our own file and create the tree at the TOP LEVEL of that file.
  file_ = TFile::Open(outputFile_.c_str(), "RECREATE");
  if (!file_ || file_->IsZombie()) {
    throw cms::Exception("FileOpenError")
        << "TtbarIdExtendAnalyzer could not open output file '"
        << outputFile_ << "' for writing.";
  }
  file_->cd();   // ensure the tree is attached to this file's top directory
  tree_ = new TTree(treeName_.c_str(), treeTitle_.c_str());
  tree_->SetDirectory(file_);

  // Branch names + types chosen so the extend can be friend-treed directly
  // against central NanoAOD's run / luminosityBlock / event.
  tree_->Branch("run",             &b_run_,             "run/i");              // UInt_t
  tree_->Branch("luminosityBlock", &b_luminosityBlock_, "luminosityBlock/i");  // UInt_t
  tree_->Branch("event",           &b_event_,           "event/l");            // ULong64_t
  tree_->Branch("genTtbarId",      &b_genTtbarId_,      "genTtbarId/I");       // Int_t
  tree_->Branch("Expanded_genTtbarId",   &b_expandedId_,   "Expanded_genTtbarId/I");           // Int_t
  tree_->Branch("nAddBJets",       &b_nAddBJets_,       "nAddBJets/I");        // Int_t
  tree_->Branch("nAddBJetsMulti",  &b_nAddBJetsMulti_,  "nAddBJetsMulti/I");   // Int_t

  edm::LogInfo("TtbarIdExtendAnalyzer")
      << "beginJob: opened '" << outputFile_ << "', created top-level TTree '"
      << treeName_ << "' with 7 branches "
      << "(run/luminosityBlock/event/genTtbarId/Expanded_genTtbarId/nAddBJets/nAddBJetsMulti)";
}

int TtbarIdExtendAnalyzer::safeGetInt(const edm::Event& iEvent,
                                        const edm::EDGetTokenT<int>& tok,
                                        const edm::InputTag& tag,
                                        const char* fieldName,
                                        int fallback) const {
  try {
    return iEvent.get(tok);
  } catch (const cms::Exception& e) {
    edm::LogError("TtbarIdExtendAnalyzer")
        << "Could not read input '" << fieldName
        << "' (InputTag=" << tag.encode() << "): " << e.what()
        << "  -- using fallback value " << fallback;
    return fallback;
  }
}

void TtbarIdExtendAnalyzer::analyze(const edm::Event& iEvent, const edm::EventSetup&) {
  b_run_             = iEvent.id().run();
  b_luminosityBlock_ = iEvent.luminosityBlock();
  b_event_           = iEvent.id().event();

  b_genTtbarId_     = safeGetInt(iEvent, tokGenTtbarId_, tagGenTtbarId_, "genTtbarId");
  b_expandedId_         = safeGetInt(iEvent, tokExpandedId_,     tagExpandedId_,     "Expanded_genTtbarId");
  b_nAddBJets_      = safeGetInt(iEvent, tokNAddB_,      tagNAddB_,      "nAddBJets");
  b_nAddBJetsMulti_ = safeGetInt(iEvent, tokNAddBMulti_, tagNAddBMulti_, "nAddBJetsMulti");

  if (!iEvent.getHandle(tokGenTtbarId_).isValid()) ++nMissingGenTtbar_;
  if (!iEvent.getHandle(tokExpandedId_).isValid())     ++nMissingExpandedId_;
  if (!iEvent.getHandle(tokNAddB_).isValid())      ++nMissingNAddB_;
  if (!iEvent.getHandle(tokNAddBMulti_).isValid()) ++nMissingNAddBMulti_;

  if (verbosePerEvent_) {
    edm::LogVerbatim("TtbarIdExtendAnalyzer")
        << "evt run=" << b_run_
        << " lumi="   << b_luminosityBlock_
        << " event="  << b_event_
        << "  genTtbarId="     << b_genTtbarId_
        << "  Expanded_genTtbarId="         << b_expandedId_
        << "  nAddBJets="      << b_nAddBJets_
        << "  nAddBJetsMulti=" << b_nAddBJetsMulti_;
  }

  tree_->Fill();
  ++nFilled_;
}

void TtbarIdExtendAnalyzer::endJob() {
  if (!file_ || !tree_) {
    edm::LogError("TtbarIdExtendAnalyzer")
        << "endJob: file or tree was never created!";
    return;
  }

  // Make sure we write into our file even if some later module touched gDirectory.
  file_->cd();

  if (buildIndex_) {
    // BuildIndex(major, minor): run as major, event as minor.  Unique within
    // a single MC sample.  Friend-tree readers can GetEntryWithIndex(run, event).
    const Long64_t nidx = tree_->BuildIndex("run", "event");
    edm::LogInfo("TtbarIdExtendAnalyzer")
        << "endJob: BuildIndex(run, event) -> " << nidx << " indexed entries";
  }

  // Write the tree exactly once.  Using kOverwrite ensures a single cycle
  // ("Events;1") rather than two ("Events;1" + "Events;2").  The earlier
  // sequence tree_->Write() followed by file_->Write() wrote the tree twice:
  // file_->Write() re-persists every object attached to the file, including
  // the tree, creating a duplicate cycle.  A duplicate cycle is not fatal
  // (TFile::Get returns the highest cycle), but it bloats the file and can
  // confuse downstream tools (hadd, friend trees, CRAB output validation).
  tree_->Write("", TObject::kOverwrite);
  file_->Close();          // close + delete the TFile object
  // After Close(), tree_ is owned/deleted by the file; null both to be safe.
  tree_ = nullptr;
  file_ = nullptr;

  edm::LogInfo("TtbarIdExtendAnalyzer")
      << "endJob summary:"
      << "  total rows="              << nFilled_
      << "  missing genTtbarId="      << nMissingGenTtbar_
      << "  missing Expanded_genTtbarId="          << nMissingExpandedId_
      << "  missing nAddBJets="       << nMissingNAddB_
      << "  missing nAddBJetsMulti="  << nMissingNAddBMulti_
      << "  (output written to '" << outputFile_ << "', tree at top level)";
}

DEFINE_FWK_MODULE(TtbarIdExtendAnalyzer);
