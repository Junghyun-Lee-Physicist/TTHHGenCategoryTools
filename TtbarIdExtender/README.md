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
#   실측: 7 tasks / 20,953 jobs (MiniAOD 파일 수 합계, units_per_job=1) / 약 32 GB /
#         outLFN <out_lfn_base>/2018

# ── (5) 상태 — 정렬된 표 한 장 (컬럼 설명은 §2.3)
python3 crab/submit_ttbarIdExtend.py --era 2018 --report
```

> **MiniAOD 와 NanoAOD 의 event 수는 다르다** (실측: TTbar_Hadronic 343,248,000 vs
> 334,206,000 = 2.6% 차이; 2017 에서도 확인된 현상, 버그 아님). 따라서
> **extend 생산 완결성은 MiniAOD nevents 로, ntuple/prescan 완결성은 NanoAOD nevents 로**
> 판단한다. 섞으면 job 이 누락된 것처럼 보인다. `matchTtbarId` 의 `unmatched 0` 기준은
> extend ⊇ nano 이므로 그대로 유효하다.

> **`units_per_job: 1` 은 2017 과의 동일 조건을 위한 선택이다** (`site_config.yaml`).
> 실측상 job 하나가 3분(CPU eff 30%, waste 61%)이라 CRAB 이 splitting 개선을 권고한다.
> 물리 결과와는 무관하니, 완료가 너무 느리면 큰 3샘플만 `units_per_job: 10`(datasets.yaml
> 의 항목별 override)으로 재제출하는 선택지가 있다 — 그 경우 EOS 의 해당 디렉토리를
> 먼저 지워야 한다(위 timestamp 중복 경고).

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
