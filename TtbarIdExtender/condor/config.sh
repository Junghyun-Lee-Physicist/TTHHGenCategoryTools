# =============================================================================
#  config.sh -- settings for the enriched-NanoAOD validation batch (D17 gates 3/4/5)
#  -----------------------------------------------------------------------------
#  Sourced by submit.sh (lxplus host) and runTask.sh (worker). Edit here only.
#  Everything the jobs read or write lives under TTHH_EOS (docs/11 section 2.3):
#      $TTHH_EOS/miniaod/   MiniAODv2 inputs   (cache: fetched from the grid once)
#      $TTHH_EOS/central/   central NanoAOD used as the comparison reference
#      $TTHH_EOS/enriched/  cmsRun outputs      (<TAG>/ per submission)
#      $TTHH_EOS/json/      compare_v9_v15.py --json results (<TAG>/)
#      $TTHH_EOS/logs/      full worker logs, cmsRun logs, generated cfgs (<TAG>/)
# =============================================================================

TTHH_EOS="/eos/user/j/junghyun/ttHH"
EOS_XRD="root://eosuser.cern.ch"            # xrootd door for /eos/user
GRID_XRD="root://cms-xrd-global.cern.ch/"   # for /store/... LFNs

# CMSSW areas (AFS; both already built with `scram b`). The worker does cmsenv
# there and comes back to its scratch directory -- nothing is written to AFS.
V9_AREA="/afs/cern.ch/user/j/junghyun/TTHHGenCategoryTools/CMSSW_10_6_32_patch1"        # slc7 -> el7
V15_AREA="/afs/cern.ch/user/j/junghyun/TTHHGenCategoryTools_v15/CMSSW_15_0_18"          # el8_amd64_gcc12

# The comparator (NtupleForge). Absolute path on purpose -- $CMSSW_BASE is a
# different area on the worker (TTHH docs/08 T-29).
NF_COMPARE="/afs/cern.ch/user/j/junghyun/CMSSW_14_2_1/src/NtupleForge/script/compare_v9_v15.py"

# --- cmsDriver pieces (docs/11 section 2.3) ---------------------------------
ERA="Run2_2017,run2_nanoAOD_106Xv2"
CONDITIONS_V9="106X_mc2017_realistic_v9"
CONDITIONS_V15="150X_mc2017_realistic_v1"
CUSTOMISE_CENTRAL="Configuration/DataProcessing/Utils.addMonitoring"
CUSTOMISE_OURS="TTHHGenCategoryTools/TtbarIdExtender/ttbarIdTable_cff.customise"
OUR_COLUMNS="expandedGenTtbarId,nAddBJets,nAddBJetsMulti"

# --- disagreement classes judge_compare.py may accept (docs/11 section 4; docs/08 T-35) ---
#   _area$              FastJet ghost-area RNG: follows the job's event history, not the code
#   ^HTXS_              float residual of a mathematically-zero Rivet quantity (0 vs 3e-5)
#   raw(Boosted)?DeepTau  NN inference differs in the last bit between CPU types; visible
#                       only where it straddles a storage-precision step (10-bit mantissa)
# Same cfg + same events + same node must be bit-identical (--zero); nothing is allowed there.
ALLOW_REPRO='(_area$|^HTXS_|raw(Boosted)?DeepTau)'   # vs a file produced elsewhere (central, other node)
ALLOW_XMACHINE='raw(Boosted)?DeepTau'                # same cfg + same events, different machine
# cmsRun %MSG-e categories the central NANO sequence itself emits (docs/08 T-1):
# JetFlavourClustering on MiniAOD gen jets whose constituents were pruned. Any
# other error category fails the produce step even when cmsRun exits 0.
ALLOW_MSGE='JetPtMismatch|MissingJetConstituent'

# --- inputs ------------------------------------------------------------------
# TTbb (2017): the MiniAOD file processed so far, and the central v15 file whose
# events contain ours (docs/11 section 3.3, e10ceebb = value reference).
TTBB_MINIAOD_LFN="/store/mc/RunIISummer20UL17MiniAODv2/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/MINIAODSIM/106X_mc2017_realistic_v9-v1/280000/04B35B8B-2D7E-DD4C-AA6A-FC6364606485.root"
TTBB_CENTRAL_V15_LFN="/store/mc/RunIISummer20UL17NanoAODv15/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/NANOAODSIM/150X_mc2017_realistic_v1-v1/2550000/e10ceebb-116c-4a8f-a2b1-19b89b467713.root"
TTBB_CENTRAL_V15_NAME="central_ttbb_v15_e10ceebb.root"     # name under $TTHH_EOS/central/
# Our existing outputs (lxplus runs of 2026-09-02), copied to $TTHH_EOS/enriched/
OURS_V15_SMOKE="enriched_v15_smoke.root"    # 200 ev, reference for the negative control
OURS_V15_2K="enriched_v15_2k.root"          # 2000 ev, reference for machine-independence

# TT4b (2017) for gate 3 (71/72 need nAddBJets >= 4). The MiniAOD file is
# resolved from DAS by submit.sh (parent of the v9 dataset; smallest file with
# enough events) unless TT4B_MINIAOD_LFN is set here.
TT4B_NANO_V9_DS="/TT4b_TuneCP5_13TeV_madgraph_pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v2/NANOAODSIM"
TT4B_MINIAOD_LFN=""

# --- event counts ------------------------------------------------------------
N_CONTROL=200      # negative control: same 200 events as OURS_V15_SMOKE
N_TIMING=2000      # gate 4 throughput (and gate 5 at 2000 events)
N_TT4B=2000        # gate 3

# --- which tasks a plain ./submit.sh runs (override with -T "a b") -------------
TASKS_DEFAULT="control_v15_200 timing_v15_2k tt4b_v9_2k tt4b_v15_2k"

# --- HTCondor ----------------------------------------------------------------
# v15 tasks: MY.WantOS=el8 and a native cmsenv (the pattern TopCPVGenCategorizer/
# condor uses for CMSSW_14_2_1). The v9 task needs slc7: it is submitted to the
# native el9 host and runTask.sh re-executes itself inside cmssw-el7 -- the same
# wrapper used interactively on lxplus.
WANTOS_V15="el8"
WANTOS_V9="el9"
REQUEST_CPUS=1
REQUEST_MEMORY="4 GB"       # 15_0_X NANO re-runs ParticleNetAK4
REQUEST_DISK="12 GB"        # MiniAOD 4.6 GB + central 2.1 GB + outputs
JOB_FLAVOUR="workday"       # 8 h; a task takes ~20-60 min
SUBMIT_ROOT="submissions"
PROXY_MIN_HOURS=8
