import FWCore.ParameterSet.Config as cms

extendedTtbarId = cms.EDProducer(
    "ExtendedTtbarIdProducer",
    # Strict acceptance for the additional-b-jet counting that drives the
    # tt+bbb / tt+4b extension (nAddBJets == 3 -> 61/62, >= 4 -> 71/72).
    # These match the standard categorizer's main cuts and the ttHH AN
    # additional-b-jet definition (pt > 20 GeV, |eta| < 2.4).
    genJetPtMin              = cms.double(20.0),
    genJetAbsEtaMax          = cms.double(2.4),

    # Inputs.  Defaults match the canonical NanoAOD ttbarCategorization_cff
    # module names (matchGenBHadron, categorizeGenTtbar).  Note that the
    # standard categorizer's output IS named "genTtbarId", so the InputTag
    # carries an explicit second arg.
    genTtbarId               = cms.InputTag("categorizeGenTtbar", "genTtbarId"),
    genJets                  = cms.InputTag("slimmedGenJets"),
    genBHadJetIndex          = cms.InputTag("matchGenBHadron", "genBHadJetIndex"),
    genBHadFromTopWeakDecay  = cms.InputTag("matchGenBHadron", "genBHadFromTopWeakDecay"),
)
