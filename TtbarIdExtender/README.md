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

## 2. 대량 생산 (CRAB) — 4단계 강제 순서

```bash
# 세션마다 1회
cmssw-el7
cd CMSSW_10_6_32_patch1/src && cmsenv
source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init -voms cms -valid 192:00
cd TTHHGenCategoryTools/TtbarIdExtender

# 최초 1회: crab/site_config.yaml 의 __YOUR_CERN_USERNAME__ 을 본인 계정으로.
# 샘플 추가 시: parent(-v1/-v2 접미사) 를 DAS 로 확인
bash crab/resolve_parents.sh

# (1) 환경 점검 → (2) 계획 미리보기 → (3) 스모크 → (4) 본제출
python3 crab/preflight.py
python3 crab/submit_ttbarIdExtend.py --dry-run
python3 crab/submit_ttbarIdExtend.py --process TT4b --max-files 5
python3 crab/submit_ttbarIdExtend.py

# 진행 확인 / 실패 재제출 (일괄; --process/--era 필터 병용 가능)
python3 crab/submit_ttbarIdExtend.py --status
python3 crab/submit_ttbarIdExtend.py --resubmit
python3 crab/submit_ttbarIdExtend.py --resubmit --process TTbar_Hadronic,TTbb_Hadronic
```

- 대상 샘플 정의: `crab/datasets.yaml` (2017 UL stitching 7종; `enabled` 플래그로 선택).
- 출력: `site_config.yaml`의 `out_lfn_base` 아래 (기존 production: T3_KR_KNU `/store/user/<user>/ExtendedTtbarId/sidecar/...` — 신규 제출은 `site_config.yaml`의 새 LFN `/store/user/<user>/TTHHGenCategoryTools/ttbarIdExtend/...`).
- **v11 이전에 제출한 `crab_*` 프로젝트의 `--status/--resubmit`은 구 체크아웃에서** 실행할 것 — 프로젝트가 구 pset 경로를 기억한다 ([../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-13).

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
