// -*- C++ -*-
//
// ExtendedTtbarIdProducer
//
// Reads the standard CMSSW genTtbarId produced by the upstream
// `categorizeGenTtbar` plugin (which is byte-identical to NanoAOD's value),
// independently counts the number of additional b-jets in strict acceptance,
// and emits:
//
//   * EDM product instance "expandedGenTtbarId" (NO underscore -- EDM forbids
//     underscores in product instance names; the extend analyzer writes this
//     value to the final TTree branch "Expanded_genTtbarId", where underscores
//     are allowed) -- same as the input `genTtbarId` for events with <=2
//                 additional b-jets.  For >=3 additional b-jets the sub-code
//                 (Z = id % 100) is REPLACED by 61/62 (exactly 3 add b-jets,
//                 tt+bbb) or 71/72 (>=4 add b-jets, tt+4b), preserving the
//                 leading prefix digits.  This is necessary because the
//                 standard GenTtbarCategorizer does NOT distinguish >=3 add
//                 b-jets: it maps all events with >=2 additional b-jets to
//                 53/54/55 (tt+bb), so the tt+bbb / tt+4b categories of the
//                 ttHH(bbbb) analysis cannot be obtained from genTtbarId alone.
//   * "nAddBJets"      -- our own un-capped count of additional b-jets
//                         (strict acceptance: pt > genJetPtMin, |eta| < genJetAbsEtaMax;
//                          a jet counts if it hosts additional b-hadrons and
//                          no b-hadron from the top decay)
//   * "nAddBJetsMulti" -- of nAddBJets, how many host >=2 b-hadrons (g->bb merged)
//
// We never touch the c-side or the prefix counters: the standard producer
// already gets those right.
//
// Author: JH (KNU)
//

#include <algorithm>
#include <cmath>
#include <memory>
#include <unordered_map>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDGetToken.h"
#include "FWCore/Utilities/interface/InputTag.h"

#include "DataFormats/Common/interface/View.h"
#include "DataFormats/JetReco/interface/GenJet.h"

namespace {

// Map (nAddBJets, nAddBJetsMulti) to the extended sub-code, applied when
// nAddBJets >= 3 (i.e. beyond the standard tt+bb of 2 additional b-jets):
//   3 add b-jets, no  multi-b-hadron jet -> 61  (tt+bbb)
//   3 add b-jets, >=1 multi-b-hadron jet -> 62  (tt+bbb, with a g->bb jet)
//  >=4 add b-jets, no  multi              -> 71  (tt+4b)
//  >=4 add b-jets, >=1 multi              -> 72  (tt+4b, with a g->bb jet)
constexpr int kExtendedSubCode(int nAddBJets, int nAddBJetsMulti) {
  if (nAddBJets == 3) return (nAddBJetsMulti == 0) ? 61 : 62;
  return                     (nAddBJetsMulti == 0) ? 71 : 72;
}

}  // namespace


class ExtendedTtbarIdProducer : public edm::global::EDProducer<> {
 public:
  explicit ExtendedTtbarIdProducer(const edm::ParameterSet&);
  ~ExtendedTtbarIdProducer() override = default;

  static void fillDescriptions(edm::ConfigurationDescriptions&);

 private:
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

  const double genJetPtMin_;
  const double genJetAbsEtaMax_;

  const edm::EDGetTokenT<int>                      tokGenTtbarId_;
  const edm::EDGetTokenT<edm::View<reco::GenJet>>  tokGenJets_;
  const edm::EDGetTokenT<std::vector<int>>         tokBJetIdx_;
  const edm::EDGetTokenT<std::vector<int>>         tokBFromTop_;
};

ExtendedTtbarIdProducer::ExtendedTtbarIdProducer(const edm::ParameterSet& iConfig)
    : genJetPtMin_     (iConfig.getParameter<double>     ("genJetPtMin")),
      genJetAbsEtaMax_ (iConfig.getParameter<double>     ("genJetAbsEtaMax")),
      tokGenTtbarId_   (consumes<int>                    (iConfig.getParameter<edm::InputTag>("genTtbarId"))),
      tokGenJets_      (consumes<edm::View<reco::GenJet>>(iConfig.getParameter<edm::InputTag>("genJets"))),
      tokBJetIdx_      (consumes<std::vector<int>>       (iConfig.getParameter<edm::InputTag>("genBHadJetIndex"))),
      tokBFromTop_     (consumes<std::vector<int>>       (iConfig.getParameter<edm::InputTag>("genBHadFromTopWeakDecay"))) {
  produces<int>("expandedGenTtbarId");
  produces<int>("nAddBJets");
  produces<int>("nAddBJetsMulti");
}

void ExtendedTtbarIdProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<double>("genJetPtMin",     20.0);
  desc.add<double>("genJetAbsEtaMax",  2.4);
  desc.add<edm::InputTag>("genTtbarId",       edm::InputTag("categorizeGenTtbar", "genTtbarId"));
  desc.add<edm::InputTag>("genJets",          edm::InputTag("slimmedGenJets"));
  desc.add<edm::InputTag>("genBHadJetIndex",          edm::InputTag("matchGenBHadron", "genBHadJetIndex"));
  desc.add<edm::InputTag>("genBHadFromTopWeakDecay",  edm::InputTag("matchGenBHadron", "genBHadFromTopWeakDecay"));
  descriptions.add("extendedTtbarId", desc);
}

void ExtendedTtbarIdProducer::produce(edm::StreamID,
                           edm::Event& iEvent,
                           const edm::EventSetup&) const {
  const int genTtbarId    = iEvent.get(tokGenTtbarId_);
  const auto& genJets     = iEvent.get(tokGenJets_);
  const auto& bHadJetIdx  = iEvent.get(tokBJetIdx_);
  const auto& bHadFromTop = iEvent.get(tokBFromTop_);

  // Strict acceptance mask
  std::vector<unsigned char> acc(genJets.size(), 0);
  for (std::size_t i = 0; i < genJets.size(); ++i) {
    const auto& j = genJets[i];
    acc[i] = (j.pt() >= genJetPtMin_ &&
              std::abs(j.eta()) <= genJetAbsEtaMax_) ? 1u : 0u;
  }
  auto inAcc = [&](int idx) {
    return idx >= 0 && static_cast<std::size_t>(idx) < acc.size() && acc[idx];
  };

  // For each accepted jet: (nTopHadrons, nAdditionalHadrons)
  std::unordered_map<int, std::pair<int,int>> perJet;
  perJet.reserve(bHadJetIdx.size());
  for (std::size_t i = 0; i < bHadJetIdx.size(); ++i) {
    const int jetIdx = bHadJetIdx[i];
    if (!inAcc(jetIdx)) continue;
    auto& [nTop, nAdd] = perJet[jetIdx];
    (bHadFromTop[i] == 1 ? nTop : nAdd) += 1;
  }

  int nAddBJets      = 0;
  int nAddBJetsMulti = 0;
  for (const auto& [jetIdx, counts] : perJet) {
    const auto& [nTop, nAdd] = counts;
    if (nAdd == 0 || nTop > 0) continue;
    ++nAddBJets;
    if (nAdd >= 2) ++nAddBJetsMulti;
  }

  // ----- Encode expandedId ----------------------------------------------------
  // The standard GenTtbarCategorizer does NOT produce sub-code 56: any event
  // with >=2 additional b-jets is mapped to 53/54/55 (tt+bb), independent of
  // whether there are 2, 3, 4, ... additional b-jets.  To separate tt+bbb
  // (exactly 3 additional b-jets) and tt+4b (>=4 additional b-jets) -- the
  // extra categories defined in the ttHH(bbbb) analysis -- we must use our own
  // nAddBJets count, NOT the standard sub-code.  Additional b-jet here means a
  // gen-jet with pt>20, |eta|<2.4 hosting only additional b-hadrons (none from
  // the top decay), matching the AN definition.
  //
  // Reclassification (only the sub-code Z = id % 100 is changed; the leading
  // digits, which encode b-jets-from-top etc., are preserved):
  //   nAddBJets == 3 : tt+bbb -> sub-code 61 (no multi) / 62 (>=1 multi jet)
  //   nAddBJets >= 4 : tt+4b  -> sub-code 71 (no multi) / 72 (>=1 multi jet)
  //   nAddBJets <= 2 : unchanged (keep the standard genTtbarId)
  // The multi split (61 vs 62, 71 vs 72) is finer than the AN, which only needs
  // tt+bbb and tt+4b; analyses can merge 61+62 -> tt+bbb and 71+72 -> tt+4b.
  int expandedId = genTtbarId;
  if (nAddBJets >= 3) {
    const int base   = (genTtbarId / 100) * 100;   // preserve leading digits
    const int newSub = kExtendedSubCode(nAddBJets, nAddBJetsMulti);
    expandedId = base + newSub;
  }

  iEvent.put(std::make_unique<int>(expandedId),          "expandedGenTtbarId");
  iEvent.put(std::make_unique<int>(nAddBJets),       "nAddBJets");
  iEvent.put(std::make_unique<int>(nAddBJetsMulti),  "nAddBJetsMulti");
}

DEFINE_FWK_MODULE(ExtendedTtbarIdProducer);
