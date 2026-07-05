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

# (2) 계획 미리보기: 무엇이 몇 job 제출될지 (실제 제출 안 함)
python3 crab/submit_ttbarIdExtend.py --dry-run

# (3) 스모크 테스트: tt4b 한 샘플, 파일 5개만 먼저 (grid 왕복 확인)
python3 crab/submit_ttbarIdExtend.py --process TT4b --max-files 5

# (4) 본제출: enabled=true 인 전 샘플
python3 crab/submit_ttbarIdExtend.py
```

특정 샘플/era만 제출하려면 `--process TT4b,TTbb_Hadronic` 또는 `--era 2017` 필터를 붙인다.

### 2.3 진행 확인 / 재제출 / kill

```bash
python3 crab/submit_ttbarIdExtend.py --status                          # 전 태스크 상태
python3 crab/submit_ttbarIdExtend.py --resubmit                        # 실패 job 일괄 재제출
python3 crab/submit_ttbarIdExtend.py --resubmit --process TTbar_Hadronic,TTbb_Hadronic

# 실행 중/대기 중 job 죽이기 (crab kill). 파괴적이라 확인 프롬프트가 뜬다.
python3 crab/submit_ttbarIdExtend.py --kill                            # 전 태스크 kill (y/N 확인)
python3 crab/submit_ttbarIdExtend.py --kill --process TT4b            # 한 샘플만
python3 crab/submit_ttbarIdExtend.py --kill --process TT4b --yes      # 확인 없이 (스크립트용)
```

`--status`/`--resubmit`/`--kill`은 셋 중 하나만 쓸 수 있다(동시 지정 시 에러). 셋 다 새 task를 제출하지 않고 기존 `crab_projects/crab_*` 프로젝트에 대해서만 동작하며, `--process`/`--era` 필터를 존중한다. `--kill`은 job만 죽일 뿐 프로젝트 디렉토리를 지우지 않는다 — 같은 이름으로 다시 제출하려면 `rm -rf crab_projects/crab_<req>` 후 `request_name_tag`를 bump하거나 프로젝트를 지운다.

### 2.4 생산 후 → filelist 만들기 → 검증

CRAB 출력이 `out_lfn_base` 아래에 쌓이면, 그 위치를 `Validation/filelists/make_filelists_miniAOD.py`의 `SAMPLE_DIR`로 지정해 filelist를 생성하고([../Validation/README.md](../Validation/README.md) §0), §1의 검증 워크플로로 넘어간다.

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
