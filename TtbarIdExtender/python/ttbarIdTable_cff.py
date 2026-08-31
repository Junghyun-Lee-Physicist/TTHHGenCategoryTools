"""Put the extended ttbar id into the NanoAOD Events table.

Mirrors the release's own PhysicsTools/NanoAOD/ttbarCategorization_cff.py, which
exposes genTtbarId as a top-level branch. Leaving name/extension unset keeps
name="" so the columns land at top level, exactly as genTtbarId and Flag_* do.

Nothing upstream is touched. ExtendedTtbarIdProducer consumes only products the
central sequence already makes:

    categorizeGenTtbar:genTtbarId            ttbarCatMCProducers(Task)
    matchGenBHadron:genBHadJetIndex          ttbarCatMCProducers(Task)
    matchGenBHadron:genBHadFromTopWeakDecay  ttbarCatMCProducers(Task)
    slimmedGenJets                           MiniAOD

Those four names are IDENTICAL in CMSSW_10_6_X and CMSSW_15_0_X -- checked
2026-08-31 against both releases' ttbarCategorization_cff.py. That is what
licenses the claim "identical to central plus three extra columns".

ONE release difference: how the table module is built. The C++ plugin
GlobalVariablesTableProducer is the same in both; only the python handle moved.
15_0_X ships a fillDescriptions-generated cfi and clones it, 10_6_X has no such
cfi so the module is constructed by plugin name. Supporting both keeps ONE file
for BOTH release areas, which matters because v9 and v15 are produced and
compared in parallel.
"""
import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import ExtVar
from TTHHGenCategoryTools.TtbarIdExtender.extendedTtbarId_cfi import extendedTtbarId

try:                                   # CMSSW_15_0_X and later
    from PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi import (
        globalVariablesTableProducer as _globalTable)
    def _make_table(variables):
        return _globalTable.clone(variables=variables)
    TABLE_STYLE = "globalVariablesTableProducer_cfi.clone  [15_0_X style]"
except ImportError:                    # CMSSW_10_6_X
    def _make_table(variables):
        return cms.EDProducer("GlobalVariablesTableProducer", variables=variables)
    TABLE_STYLE = 'cms.EDProducer("GlobalVariablesTableProducer")  [10_6_X style]'

ttbarIdExtendTable = _make_table(cms.PSet(
    expandedGenTtbarId = ExtVar(
        cms.InputTag("extendedTtbarId", "expandedGenTtbarId"), "int",
        doc="expanded ttbar categorization: standard genTtbarId plus the "
            "tt+bbb (61/62) and tt+4b (71/72) sub-codes"),
    nAddBJets = ExtVar(
        cms.InputTag("extendedTtbarId", "nAddBJets"), "int",
        doc="additional b jets (pt>20, |eta|<2.4) not from top weak decay"),
    nAddBJetsMulti = ExtVar(
        cms.InputTag("extendedTtbarId", "nAddBJetsMulti"), "int",
        doc="additional b jets containing >=2 b hadrons"),
))


def customise(process):
    """cmsDriver --customise entry point.

    Task ordering is by data dependency, so extendedTtbarId always runs after
    categorizeGenTtbar no matter how the release organises its sequences
    (10_6_X: ttbarCatMCProducers Sequence; 15_0_X: ttbarCatMCProducersTask).
    """
    process.extendedTtbarId    = extendedTtbarId.clone()
    process.ttbarIdExtendTable = ttbarIdExtendTable.clone()
    if not hasattr(process, "nanoAOD_step"):
        raise RuntimeError(
            "ttbarIdTable_cff.customise: no nanoAOD_step in the process -- "
            "this customise is meant for a cmsDriver '--step NANO' job")
    process.nanoAOD_step.associate(
        cms.Task(process.extendedTtbarId, process.ttbarIdExtendTable))
    print("[ttbarIdTable_cff] table built via %s" % TABLE_STYLE)
    return process
