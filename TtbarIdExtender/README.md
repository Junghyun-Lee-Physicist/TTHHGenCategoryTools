# TtbarIdExtender — ttbarId 확장(gen-level) 생산 패키지 (지역 README)

> **목적**: 이 디렉토리에서 ttbarId-extend 파일을 **만들고**(로컬/CRAB) **스팟체크**하는 실행 명령 모음.
> **대상 독자**: ttbarId-extend 파일을 생산·재생산하는 사람. 개념·설계는 저장소 문서로 — 인코딩 [../docs/02_physics.md](../docs/02_physics.md), 구조 [../docs/05_architecture.md](../docs/05_architecture.md), 문제 발생 시 [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md).
> **상태**: DECIDED 워크플로 (v10 확립). rename 이력: 패키지 `NanoExtension`→`GenSidecar`(v11)→`TtbarIdExtender`(v12), 출력 `sidecar.root`→`ttbarIDExtend.root`(v12). **lxplus 첫 빌드는 확인됨(v12): plugin 라이브러리 컴파일 성공, `Validation/`은 `tools/`로 옮겨 scram 간섭 제거** ([../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-15).
> **환경**: CMSSW_10_6_32_patch1 (lxplus에서 `cmssw-el7` 컨테이너 필수) — [../docs/09_environment.md](../docs/09_environment.md).

산출물 스키마 한 줄: top-level `Events` TTree = `run/i, luminosityBlock/i, event/l, genTtbarId/I, Expanded_genTtbarId/I, nAddBJets/I, nAddBJetsMulti/I` (event당 ~32 B).

## 1. 빠른 시작 — ttbarId-extend 하나 만들고 중앙 NanoAOD와 대조

```bash
# 1. EL7 컨테이너 진입 후 CMSSW 릴리스 생성 + 저장소 clone
cmssw-el7                                  # lxplus(EL9)에서 SLC7 컨테이너 진입 (필수)
cmsrel CMSSW_10_6_32_patch1
cd CMSSW_10_6_32_patch1/src && cmsenv
git clone https://github.com/Junghyun-Lee-Physicist/TTHHGenCategoryTools.git
#   (tar 배포본을 쓸 경우: tar xzf TTHHGenCategoryTools_v12.tar.gz)

# 2. 빌드
scram b -j8

# 3. MiniAODv2 파일 하나로 ttbarId-extend 생산
cmsRun TTHHGenCategoryTools/TtbarIdExtender/test/run_ttbarIdExtend_cfg.py \
    inputFiles=<miniaod.root> outputFile=ttbarIDExtend.root maxEvents=100
# NB: VarParsing 이 파일명에 _numEventN 접미사를 붙이므로 실제 출력은
#     ttbarIDExtend_numEvent100.root 입니다. 4단계에서 그 정확한 이름을 쓰세요.

# 3.1 실제 예시 (UL17 TTbb_4f)
cmsRun TTHHGenCategoryTools/TtbarIdExtender/test/run_ttbarIdExtend_cfg.py \
    inputFiles=root://xrootd-cms.infn.it///store/mc/RunIISummer20UL17MiniAODv2/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/MINIAODSIM/106X_mc2017_realistic_v9-v1/280000/215122BB-6A38-C24C-9589-11A9A1AC97BA.root outputFile=ttbarIDExtend.root maxEvents=1000

# 4. genTtbarId 가 중앙 NanoAODv9 와 byte-identical 한지 스팟체크
#    (ttbarId-extend TTree 는 최상위라 tree-path 접두사 불필요)
compareExtendToCentral \
    --extend ttbarIDExtend_numEvent1000.root \
    --central root://xrootd-cms.infn.it///store/mc/RunIISummer20UL17NanoAODv9/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/130000/1DD1BB46-D65F-B148-965E-8DB20A33BE8C.root
```

`compareExtendToCentral`은 두 파일을 `(run, lumi, event)`로 매칭해 `genTtbarId` 완전 일치를 확인하고(불일치·미매치 시 non-zero exit), `Expanded_genTtbarId % 100` 분포와 tt+bb 보존식을 표로 보여준다. 참고: 위 스팟체크는 ttbarId-extend 쪽 event가 central 파일에 다 있어야 의미가 있다 — 임의 파일 쌍이면 unmatched가 크게 나올 수 있으며, 전량 검증은 `../Validation`의 filelist 기반 도구로 한다.

## 2. 대량 생산 (CRAB) — 2017 UL 7샘플 전량 제출

7개 stitching 샘플의 MiniAODv2를 전부 훑어 ttbarId-extend 파일을 grid에서 생산한다. **로컬 run(§1)이 성공한 뒤에** 하는 단계다.

### 2.0 최초 1회 설정 (제출 전 반드시)

`crab/site_config.yaml`을 열어 **본인 계정으로 두 줄만** 고친다:

```yaml
storage_site:    "T3_CH_CERNBOX"                              # lxplus 개인 EOS(/eos/user/)로 출력
out_lfn_base:    "/store/user/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2"   # /store/user/<본인계정>/...
```

`T3_CH_CERNBOX` + `/store/user/<user>/...` 조합이면 CRAB이 lxplus **개인 EOS**(`/eos/user/<첫글자>/<user>/...`, `root://eosuser.cern.ch/`)로 출력을 보낸다 — CERN 계정이면 별도 활성화 없이 쓸 수 있다. 홈 T2/T3(예: `T3_KR_KNU`)로 보내려면 그걸 `storage_site`에 넣는다.

> **주의**: `T2_CH_CERN`은 개인 EOS가 **아니다** — `/store/user/`가 CMS 실험 EOS(`/eos/cms/store/user/`)로 매핑되며 별도 CMS-EOS 쓰기 활성화가 필요하다. 안 되어 있으면 제출이 `SUBMITREFUSED` / `HTTP 403 MAKE_PARENT`로 거부된다([../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-17).

제출 전에 목적지 쓰기 권한을 미리 확인하면 SUBMITREFUSED를 피할 수 있다:
```bash
crab checkwrite --site=T3_CH_CERNBOX --lfn=/store/user/junghyun
```

대상 샘플은 `crab/datasets.yaml`에 정의돼 있다 (era `2017` 아래 7종: `TT4b`, `TTbar_SemiLep`, `TTbar_Hadronic`, `TTbar_DiLep`, `TTbb_SemiLep`, `TTbb_Hadronic`, `TTbb_DiLep`; 각 `enabled: true/false`로 선택). MiniAODv2 parent 경로(`-v1`/`-v2` 접미사)가 grid에서 정확한지 확인하려면 (grid proxy 필요):

```bash
voms-proxy-init -voms cms
bash crab/resolve_parents.sh   # 각 샘플의 DAS parent 를 출력 → datasets.yaml 의 dataset: 에 반영
```

### 2.1 세션마다 1회 — 환경 + proxy

```bash
cmssw-el7                                            # lxplus(EL9) → SLC7 컨테이너 (필수)
cd CMSSW_10_6_32_patch1/src && cmsenv
source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init -voms cms -valid 192:00              # 8일짜리 proxy
cd TTHHGenCategoryTools/TtbarIdExtender
```

### 2.2 제출 — 강제 순서 (preflight → dry-run → 스모크 → 본제출)

```bash
# (1) 환경 점검: cmsenv/proxy/pset/plugin lib 존재 확인
python3 crab/preflight.py

# (2) era/dataset 점검 (읽기 전용, --dry-run 보다 강함) — 2026-07-26 신설
python3 crab/submit_ttbarIdExtend.py --era 2017 --preflight --check-das

# (3) 계획 미리보기: 무엇이 제출될지 (실제 제출 안 함)
python3 crab/submit_ttbarIdExtend.py --era 2017 --dry-run

# (4) 스모크 테스트: **가장 작은 샘플을 통째로** (아래 경고 참조)
python3 crab/submit_ttbarIdExtend.py --era 2017 --process TTbb_DiLep

# (5) 본제출: enabled=true 인 전 샘플
python3 crab/submit_ttbarIdExtend.py --era 2017
```

특정 샘플/era만 제출하려면 `--process TT4b,TTbb_Hadronic` 또는 `--era 2017` 필터를 붙인다.

> **⚠️ `--max-files N` 로 스모크하지 말 것** (DECIDED 2026-07-27). 그 옵션은
> `Data.totalUnits=N` 을 걸어 **완결될 수 없는 부분 task** 를 만든다: 103 files 중
> 5개만 도는 task 가 `--status` 에 `done 5/5 = 100%` 로 보이지만 실제 커버리지는 5% 이고,
> 나머지를 처리하려면 같은 dataset 을 **또** 제출해야 해서 같은 LFN 아래 CRAB timestamp
> 디렉토리가 둘로 갈린다 → `make_filelists_miniAOD.py` 가 둘 다 주워 3-key 중복이 되고
> `matchTtbarId` 가 **exit 7** 로 죽는다. **가장 작은 dataset(`TTbb_DiLep`)을 그대로**
> 던지는 것이 올바른 스모크다.
> 이미 부분 task 를 던졌다면: `--kill --yes` → project dir 삭제 → **EOS 의 해당 timestamp
> 디렉토리 삭제**까지 한 뒤 재제출한다. (`Validation/filelists/make_filelists_miniAOD.py`
> 에 timestamp 중복 FATAL 가드가 있어 놓쳐도 filelist 단계에서 잡힌다.)

#### `--preflight` 가 보는 것

환경(cmsenv / CRABClient / proxy 잔여시간) · pset 존재·compile·**`year` 옵션 유무** ·
site_config(`out_lfn_base` placeholder, `/store/` 접두) · era 별 dataset 상태
(MINIAODSIM/NANOAODSIM 경로 문법, **campaign 문자열에 era 키 포함 여부**,
MiniAOD↔Nano primary 일치, `enabled`/`verified` 조합, 기존 CRAB project dir).
`--check-das` 를 붙이면 모든 MiniAOD/Nano 경로를 DAS 로 조회해 **잘못된 `-vN` 접미사를
제출 전에** 잡는다. 로그: `crab/preflight_extend_<eras>_<timestamp>.log`, FAIL 시 exit 1.

---

### 2.2b 다른 연도(예: 2018 UL) 제출 — 실제 재현 순서 (2026-07-27 실행 기록)

`datasets.yaml` 은 era 별 블록 구조이고 pset 은 `year=` 를 받으므로, 연도 추가는
**부모 확정 → 잠금 해제 → preflight → 제출** 네 단계다.

```bash
# ── (0) 로컬 검증부터: 2018 MiniAOD 한 파일로 물리량이 맞는지 먼저 확인
NANO=/TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM
MINI=$(dasgoclient -query "parent dataset=$NANO" | grep MINIAODSIM | head -1)
MINIFILE=$(dasgoclient -query "file dataset=$MINI" | head -1)
cmsRun test/run_ttbarIdExtend_cfg.py year=2018 \
    inputFiles=root://cms-xrd-global.cern.ch/${MINIFILE} \
    maxEvents=20000 outputFile=ttbarIDExtend_local2018.root
#   확인: 'era modifier = Run2_2018 + run2_nanoAOD_106Xv2',
#         endJob summary 의 missing 전부 0.
#   불변조건 검증은 ROOT 매크로로 (10_6_X 의 PyROOT 는 python2 빌드라 python3 에서 죽는다):
root -l -b -q "$CMSSW_BASE/src/TTHHGenCategoryTools/Validation/scripts/check_extend_invariants.C(\"ttbarIDExtend_local2018_numEvent20000.root\")"
#   -> VERDICT: ALL INVARIANTS PASS  (실측: nAddBJets>=3 이 63 event, 61=34 62=23 71=6 72=0)
#   NB: VarParsing 이 maxEvents 지정 시 파일명에 _numEventN 을 붙인다.

# ── (1) MiniAODv2 부모를 DAS 로 확정 (추측 금지)
bash crab/resolve_parents.sh 2018 2>&1 | tee crab/resolve_parents_2018_$(date +%Y%m%d_%H%M).log
#   출력의 'PARENT (from DAS)' 7개를 datasets.yaml 의 2018 블록 dataset: 에 붙여넣고
#   해당 항목만 verified: true / enabled: true 로 바꾼다.
#   실측 주의: TTbar_SemiLep 은 MiniAOD -v2 / Nano -v1 로 **비대칭**이었다.

# ── (2) preflight → (3) dry-run → (4) 본제출 (파일 쪼개기 없이)
python3 crab/submit_ttbarIdExtend.py --era 2018 --preflight --check-das
python3 crab/submit_ttbarIdExtend.py --era 2018 --dry-run
python3 crab/submit_ttbarIdExtend.py --era 2018 \
    2>&1 | tee crab/submit_2018_full_$(date +%Y%m%d_%H%M).log
#   실측(2026-07-27): client 는 7 tasks / 20,953 jobs 제출 성공을 보고했으나
#   TTbar_SemiLep 은 서버가 SUBMITREFUSED 로 거부했다 (10,010 jobs > CRAB 상한 10,000).
#   -> 실제로 돈 것은 6 tasks / 10,943 jobs. 원인·복구는 docs/08_troubleshooting.md T-19.
#   조치: site_config 의 units_per_job 을 1 -> 10, max_memory_mb 2000 -> 2500 으로 올리고
#   2018 전량을 처음부터 재제출했다 (절차 = 아래 2.2c, 근거 = units_per_job 절).
#   --preflight --check-das 가 이제 task 당 job 수를 미리 계산해 상한 초과면 FAIL 시킨다.
#   재제출 후: 7 tasks / 2,097 jobs (20,953 -> 10배 감소).
#         outLFN <out_lfn_base>/2018

# ── (5) 상태 — 정렬된 표 한 장 (컬럼 설명은 §2.3)
python3 crab/submit_ttbarIdExtend.py --era 2018 --report
```

> **MiniAOD 와 NanoAOD 의 event 수는 다르다** (실측: TTbar_Hadronic 343,248,000 vs
> 334,206,000 = 2.6% 차이; 2017 에서도 확인된 현상, 버그 아님). 따라서
> **extend 생산 완결성은 MiniAOD nevents 로, ntuple/prescan 완결성은 NanoAOD nevents 로**
> 판단한다. 섞으면 job 이 누락된 것처럼 보인다. `matchTtbarId` 의 `unmatched 0` 기준은
> extend ⊇ nano 이므로 그대로 유효하다.

#### `units_per_job` — 물리에 무관한 순수 운영 knob (단, **내릴 때만 위험**)

> ### 🚫 절대 규칙: task 당 job 10,000 개를 넘기지 마라
>
> `njobs = ceil(nfiles / units_per_job)` 이고 **CRAB 은 task 당 job 10,000 개를 초과하면
> 거부한다.** 그런데 그 거부가 **제출 시점이 아니라 서버 측에서** 일어나서 **조용하다**:
>
> - `crab submit` 은 **성공을 반환**하고 submitter 는 `submitted : N` 을 찍는다
> - 서버가 나중에 `SUBMITREFUSED` + `The splitting on your task generated N jobs.
>   The maximum number of jobs in each task is 10000` 로 세워 둔다
> - `jobsPerStatus` 가 비어 `--report` 행이 **전부 0** → "아직 안 시작"과 구분 불가
> - **`--resubmit` 으로 못 고친다** (scheduler 에 도달한 task 의 FAILED job 만 재큐)
>
> → **샘플 하나가 아무것도 만들지 않는데 며칠 모를 수 있다.** 2026-07-27 에 2018
> `TTbar_SemiLep`(MiniAOD 10,010 파일, 당시 upj=1 → 10,010 jobs)로 실제로 하루를 잃었다.
> **총합은 정상으로 보인다 — 상한은 per-task 다.**
>
> **그래서:**
> - **올리는 건 항상 안전**하다(job 수가 줄고, 물리에 무관하며, 위쪽 제약은 walltime 1440분뿐 —
>   upj=10 이 ~11분/job 이라 ~130배 여유).
> - **내리기 전에는 반드시** 아래를 돌려 per-task job 수를 확인한다. 상한 초과면 **FAIL** 하고
>   필요한 값을 알려 준다:
>   ```bash
>   python3 crab/submit_ttbarIdExtend.py --era <ERA> --preflight --check-das
>   ```
> - 이 규칙의 정본은 [`../docs/04_decisions.md`](../docs/04_decisions.md) **D15**,
>   사고 기록은 [`../docs/08_troubleshooting.md`](../docs/08_troubleshooting.md) **T-19**.
>   경고는 `crab/site_config.yaml`·`crab/datasets.yaml`·`crab/submit_ttbarIdExtend.py`
>   (`cfg.Data.unitsPerJob` 대입 지점) 세 곳에 박혀 있다 — 지우지 마라.

**파일을 job 에 어떻게 묶든 결과는 같다.** 각 job 은
`(run, luminosityBlock, event, ...)` 행을 쓰고, 소비자(`matchTtbarId` /
`matchTtbarIdSorted`)는 **filelist 전체에 대해 3-key map 하나**를 만든다 — 어느 행이 어느
파일에서 왔는지는 보지 않는다. 그래서 `units_per_job` 은 **오직 운영 효율의 문제**다.

`site_config.yaml` 의 기본값 `1` 은 원래 "2017 과 동일 조건"을 위한 선택이었지만, 실측상
나쁜 설정이다 — job 하나가 2~3분인데 그중 ~90초가 CMSSW 시작/stage-in 이라 CRAB 이 매 task 마다
`average jobs CPU efficiency is less than 50%` 를 경고한다(2026-07-27 실측 CPU eff 20~45%,
waste 50~58%).

2018 `TTbar_SemiLep` 실측 기준 (파일당 ~47.6k event ≈ 55초 작업 + ~90초 시작):

| `units_per_job` | jobs | job 당 시간 | 시작 오버헤드 비중 | |
|---|---|---|---|---|
| 1 | 10,010 | ~2.4분 | ~63% | ❌ **CRAB 상한 10,000 초과 → SUBMITREFUSED** |
| 2 | 5,005 | ~3.3분 | ~45% | 최소 수정 |
| **10** | **1,001** | **~10.7분** | **~14%** | ✅ **채택** |
| 20 | 501 | ~19.8분 | ~7% | 가능 (walltime 상한 1440분과 무관하게 여유) |

참고로 이 7샘플의 **MiniAOD/NanoAOD 파일 수 비는 ~22.5** (`TTbar_SemiLep` 은 10,010/391 = 25.6)
이므로, MiniAOD 10개는 여전히 NanoAOD 파일 1개분 event 보다 적다. 덤으로 출력 파일이
10,010 → 1,001 개로 줄어 뒤의 `sortSplitExtend`/`matchTtbarIdSorted` 가 눈에 띄게 싸진다.

**2026-07-27 결정: `site_config.yaml` 의 캠페인 기본값을 `1` → `10` 으로 올리고, 2018 전량을
처음부터 재제출한다.** `TTbar_SemiLep` 하나만 고치고 나머지 6개를 upj=1 로 남기면 캠페인이
혼합 설정이 되고 비효율도 그대로 남는데, 마침 재제출 결정이 났으므로 전체를 통일했다.
`max_memory_mb` 도 2000 → **2500** (관측 피크 1731 MB 대비 헤드룸 13% → 44%).

| | 이전 | 이후 |
|---|---|---|
| `units_per_job` | 1 | **10** |
| 2018 총 job 수 | 20,953 (SemiLep 이 상한 초과) | **2,097** (10배 감소) |
| `max_memory_mb` | 2000 | **2500** |

> ⚠️ **이 값을 바꾸려면 반드시 전량 재생산이다.** kill → **EOS 산출물 삭제** → project dir 삭제
> → 재제출. EOS 를 안 지우면 같은 LFN 아래 CRAB timestamp 디렉토리가 둘 생겨 3-key 중복 →
> `matchTtbarId` **exit 7** 이 된다. 그리고 **kill 이 완전히 끝난 뒤에** EOS 를 지워야 한다 —
> 늦게 stage-out 되는 job 하나가 지운 디렉토리를 되살리면 정확히 그 사고가 난다.
> 절차는 §2.2c.
>
> **끝난 캠페인을 효율 때문에 다시 돌리지는 마라.** 산출물은 packing 과 무관하게 동일하다.
> 2017 캠페인은 upj=1 로 완료됐고 **그대로 유효하다** — 재생산 대상이 아니다.

---

### 2.2c 한 연도를 처음부터 다시 제출 (전량 재생산) — 순서가 중요하다

`units_per_job`·`max_memory_mb` 같은 splitting/자원 설정을 바꿨을 때의 절차다. 2026-07-27 에
2018 전량에 대해 실제로 이 순서로 수행했다.

**순서를 지켜야 하는 이유**: kill 이 완전히 끝나기 **전에** EOS 를 지우면, 뒤늦게 stage-out 하는
job 이 지운 디렉토리를 되살린다. 그러면 새 제출의 timestamp 디렉토리와 **둘이 공존**하고,
`make_filelists_miniAOD.py` 가 둘 다 주워 3-key 중복 → `matchTtbarId` **exit 7** 이다.

```bash
# ── 0) 세션 준비 ─────────────────────────────────────────────────────────────
cmssw-el7
cd ~/TTHHGenCategoryTools/CMSSW_10_6_32_patch1/src && cmsenv
source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init -voms cms -valid 192:00
cd TTHHGenCategoryTools/TtbarIdExtender
git pull                     # 새 site_config(upj 10 / mem 2500) + preflight job-count 체크

export EXT=/eos/user/j/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2018

# ── 1) 죽인다 (era 2018 전체) ────────────────────────────────────────────────
python3 crab/submit_ttbarIdExtend.py --era 2018 --kill --yes \
    2>&1 | tee crab/kill_2018_$(date +%Y%m%d_%H%M).log
#   이미 COMPLETED 인 task 는 "no jobs to kill" 류로 실패해도 정상이다.

# ── 2) 진짜로 다 죽었는지 확인 — run/idle/transf 가 전부 0 이 될 때까지 반복 ──
python3 crab/submit_ttbarIdExtend.py --era 2018 --report
#   ↑ run·idle·transf 열이 하나라도 0 이 아니면 2~3분 뒤 다시. 여기서 서두르면 안 된다.

# ── 3) EOS 산출물 삭제 (2)가 깨끗해진 뒤에만!) ───────────────────────────────
ls "$EXT"                                  # 지울 대상 눈으로 확인
du -sh "$EXT"
rm -rf "$EXT"                              # 2018 만 지운다 — 상위 ttbarIdExtend_v2 는 건드리지 않음
ls /eos/user/j/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/   # 2018 이 없어야 한다

# ── 4) CRAB project dir 삭제 (안 지우면 submit 이 skip 한다) ─────────────────
rm -rf crab_projects/crab_*_2018_extend
ls crab_projects/ | grep 2018 || echo "clean"

# ── 5) preflight — 새 job 수가 상한 아래인지 여기서 확인된다 ────────────────
python3 crab/submit_ttbarIdExtend.py --era 2018 --preflight --check-das \
    2>&1 | tee crab/preflight_2018_redo_$(date +%Y%m%d_%H%M).log
#   기대: 7샘플 모두 job count PASS, 최대가 TTbar_SemiLep 의 1,001 jobs.
#         "existing CRAB project" 항목도 전부 없음(=4단계가 됐다는 뜻).

# ── 6) 재제출 ───────────────────────────────────────────────────────────────
python3 crab/submit_ttbarIdExtend.py --era 2018 \
    2>&1 | tee crab/submit_2018_redo_$(date +%Y%m%d_%H%M).log
#   기대: submitted : 7

# ── 7) 몇 분 뒤 — SUBMITREFUSED 가 없는지 반드시 확인 ───────────────────────
python3 crab/submit_ttbarIdExtend.py --era 2018 --report
#   DEAD TASK 블록이 안 나와야 한다. 나오면 T-19 로.
```

**재제출 후 기대 job 수** (`units_per_job: 10`, MiniAOD 파일 수 ÷ 10):

| sample | MiniAOD files | jobs |
|---|---|---|
| TTbar_SemiLep | 10,010 | 1,001 |
| TTbar_Hadronic | 7,195 | 720 |
| TTbar_DiLep | 3,069 | 307 |
| TTbb_SemiLep | 219 | 22 |
| TT4b | 188 | 19 |
| TTbb_Hadronic | 169 | 17 |
| TTbb_DiLep | 103 | 11 |
| **합계** | **20,953** | **2,097** |

### 2.3 진행 확인 / 재제출 / kill

**상태를 보는 세 가지 방법** — 용도가 다르다:

```bash
# (a) --report : 한 장으로 보는 정렬된 표 (2026-07-27 신설). 평소엔 이걸 쓴다.
#     NtupleForge 의 submit_crab.py --report 와 컬럼·집계 규칙이 100% 동일하다.
python3 crab/submit_ttbarIdExtend.py --report
python3 crab/submit_ttbarIdExtend.py --era 2018 --report \
    2>&1 | tee crab/report_2018_$(date +%Y%m%d_%H%M).log

# (b) crab/status.py : datasets.yaml 을 안 보고 workArea 를 '스캔'해서 찾는다.
#     entry 를 enabled:false 로 바꿨거나 request_name_tag 를 bump 한 뒤에도 찾아낸다.
python3 crab/status.py --filter _2018_extend

# (c) --status : crab status 원본 출력 전량. 특정 task 를 깊게 파볼 때만.
python3 crab/submit_ttbarIdExtend.py --status --process TTbar_Hadronic

python3 crab/submit_ttbarIdExtend.py --resubmit                        # 실패 job 일괄 재제출
python3 crab/submit_ttbarIdExtend.py --resubmit --process TTbar_Hadronic,TTbb_Hadronic

# 실행 중/대기 중 job 죽이기 (crab kill). 파괴적이라 확인 프롬프트가 뜬다.
python3 crab/submit_ttbarIdExtend.py --kill                            # 전 태스크 kill (y/N 확인)
python3 crab/submit_ttbarIdExtend.py --kill --process TT4b            # 한 샘플만
python3 crab/submit_ttbarIdExtend.py --kill --process TT4b --yes      # 확인 없이 (스크립트용)
```

`--report` 출력 예시 (job 상태 버킷):

```
sample            done     run    idle  transf    fail   other   total
----------------------------------------------------------------------
TTbar_SemiLep     3100     420    1800     260      37      12    5629
...
TOTAL             7653     808    3605     515      57      16   12654
```

- `transf`(transferring) 가 **독립 컬럼**인 이유: `units_per_job: 1` 이라 job 이 ~21k 개이고,
  상당수가 T3_CH_CERNBOX 로 stage-out 하는 동안 이 상태에 오래 머문다.
  (2026-07-27 전의 `crab/status.py` 는 이걸 안 찍으면서 `tot` 에는 포함시켜서
  **done+run+idle+fail ≠ tot** 였다 — 이제 두 도구 모두 모든 job 이 찍히는 컬럼에 들어간다.)
- `other` = `unsubmitted`/`cooloff`/`held`/`killed`/`toRetry` 등. 코드가 모르는 상태가 섞이면
  **`[WARN] unknown CRAB job state(s)`** 로 알려 준다 — 조용히 삼키지 않는다.
- ⚠️ `--max-files` 로 만든 부분 task 는 `done 5/5` 처럼 **100% 로 보인다**. 커버리지가 아니라
  제출한 unit 기준이기 때문 — 그래서 `--max-files` 를 금지했다(§2.2).

#### `--resubmit` 출력 읽는 법 (2026-07-27 정정)

CRAB 의 resubmit 은 **세 가지 결과가 두 개의 오해되는 라벨로 뭉개졌었다.** 이제 결과별로
분류하고, 맨 끝에 breakdown 을 찍는다:

| 출력 | 뜻 | 조치 |
|---|---|---|
| `[resubmit SENT]` | 서버가 요청을 받았다 — **실제로 재제출된 유일한 경우** | 몇 분 뒤 `--report` |
| `[resubmit -- NOTHING TO DO]`<br>(`Found no jobs to resubmit`) | **실패한 job 이 없다 = 좋은 소식.** 에러가 아니다 | 없음 |
| `[resubmit REFUSED]`<br>(`has not been submitted to the Grid scheduler yet` / `Status information is unavailable`) | CRAB 이 거부 → **아무것도 재큐되지 않았다** | 몇 분 뒤 다시 `--resubmit` |
| `[resubmit UNCLEAR]` | CRAB 출력에 아는 표식이 없다 | `--report` 로 직접 확인 |
| `[skip] no project dir` | 여기 `crab_projects/` 에 그 프로젝트가 없다 (다른 체크아웃에서 제출한 2017 등) | 정상. 그 체크아웃에서 실행 ([T-13](../docs/08_troubleshooting.md)) |

**왜 중요한가**: `REFUSED` 는 예전에 `[resubmit ok]` 로 찍히고 `resubmitted : N` 에도
**포함**됐다. 즉 아무 일도 안 일어났는데 "재제출됨"으로 보였다. 반대로 `NOTHING TO DO` 는
`[resubmit FAILED]` 로 찍혀서 문제처럼 보였다. 지금은 요약이 이렇게 나온다:

```
  resubmitted : 2
  resubmit outcome breakdown:
    sent       2   request accepted by the server -- ACTUALLY RESUBMITTED
    nothing    4   no failed jobs -> nothing to do (GOOD, not an error)
    refused    1   CRAB declined ... -> NOTHING was requeued; run again later
    noproj     7   no crab_* project dir here ...
  NOTE: 'refused' tasks were NOT resubmitted. Re-run --resubmit for them in a few minutes.
```

`--status`/`--report`/`--resubmit`/`--kill`은 **넷 중 하나만** 쓸 수 있다(동시 지정 시 에러).
넷 다 새 task를 제출하지 않고 기존 `crab_projects/crab_*` 프로젝트에 대해서만 동작하며,
`--process`/`--era` 필터를 존중한다. `--kill`은 job만 죽일 뿐 프로젝트 디렉토리를 지우지
않는다 — 같은 이름으로 다시 제출하려면 `rm -rf crab_projects/crab_<req>` 후
`request_name_tag`를 bump하거나 프로젝트를 지운다.

### 2.4 생산 후 → filelist 만들기 → 검증

CRAB 출력이 `out_lfn_base` 아래에 쌓이면 그 위치를 `Validation/filelists/make_filelists_miniAOD.py`에
**2번째 인자로** 넘겨 filelist를 생성하고([../Validation/README.md](../Validation/README.md) §0·§0.1),
§1의 검증 워크플로로 넘어간다. 스크립트 상단의 상수는 `SAMPLE_DIR` 하나가 아니라
**`SAMPLE_DIR_BY_ERA` (era별 기본값)** 이고, 1번째 인자가 era 다:

```bash
cd ../Validation/filelists
python3 make_filelists_miniAOD.py 2018 /eos/user/j/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2018
#   -> sidecar2018/ (era 를 생략하면 2017 + sidecar/ — 2017 목록을 덮어쓰니 주의)
```

**주의사항**
- **`crab-setup.sh`를 먼저 source**해야 한다(세션당 1회) — 안 하면 `ModuleNotFoundError: No module named 'CRABClient'`.
- 제출은 `TtbarIdExtender/` 등 어느 디렉토리에서 실행해도 된다(psetName은 절대경로로 해결됨, v12.2). 제출이 실패하면 빈 `crab_projects/crab_*` 껍데기가 남아 재제출을 막으니, 재시도 전 `rm -rf crab_projects/crab_*_2017_extend`로 지운다([../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-16).
- 출력 LFN: `site_config.yaml`의 `out_lfn_base` 아래. 2026-06 기존 production은 구 경로 `/store/user/<user>/ExtendedTtbarId/sidecar/...`에 있고(rename이 데이터를 안 옮김), 신규 제출은 위에서 설정한 새 경로로 간다.
- **v11 이전에 제출한 `crab_*` 프로젝트의 `--status`/`--resubmit`은 그 당시 체크아웃에서** 실행할 것 — CRAB 프로젝트 디렉토리가 제출 당시의 pset 경로를 기억한다 ([../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-13).
- 같은 샘플을 재제출해 `requestName`이 충돌하면 `site_config.yaml`의 `request_name_tag`를 bump.

## 3. 디렉토리 안내

| 경로 | 내용 |
|---|---|
| `plugins/` | `ExtendedTtbarIdProducer.cc`(물리 로직), `TtbarIdExtendAnalyzer.cc`(TTree 작성) |
| `python/` | `extendedTtbarId_cfi.py`(파라미터), `ttbarIdExtend_cff.py`(`addTtbarIdExtend` 원샷 부착) |
| `test/run_ttbarIdExtend_cfg.py` | 최소 cfg (NANO step 없음, GlobalTag 불필요) |
| `bin/` | `compareExtendToCentral.cc` (스팟체크 비교기; scram이 PATH에 올림) |
| `crab/` | 위 §2의 제출 인프라 |
| `archive/enriched_nanoaod/` | 폐기된 Approach 2 cfg — **실행하지 말 것**, 정체는 [../docs/10_enriched_nanoaod_archive.md](../docs/10_enriched_nanoaod_archive.md) |

생산이 끝나면: 전량 검증·analyzer용 patch 추출은 [`../Validation/README.md`](../Validation/README.md)로.
