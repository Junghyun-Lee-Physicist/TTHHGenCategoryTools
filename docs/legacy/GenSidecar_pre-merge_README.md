# ExtendedTtbarId / NanoExtension

ttHH(bbbb) 분석을 위한 **ttbar + heavy-flavour 분류(categorization)** 도구입니다.
중앙 NanoAODv9 의 `genTtbarId` 를 MiniAODv2 에서 그대로 재현하면서, 표준 도구가
구분하지 못하는 **tt+bbb (추가 b-jet 정확히 3개)** 와 **tt+4b (4개 이상)** 를
추가로 분리해 냅니다.

이 결과는 작은 ROOT TTree("sidecar")로 출력되며, 한 행에
`(run, luminosityBlock, event, genTtbarId, Expanded_genTtbarId, nAddBJets, nAddBJetsMulti)`
를 담습니다. 분석 단계에서 이 sidecar 를 `(run, lumi, event)` 로 NanoAOD 에 붙여
ttbar stitching 과 카테고리 가중치 계산에 사용합니다.

---

## 0. 왜 이 패키지가 필요한가 (핵심 배경)

표준 CMSSW `GenTtbarCategorizer` (NanoAOD 의 `genTtbarId` 를 만드는 도구) 는
**추가 b-jet 이 2개 이상이면 개수와 무관하게 모두 53/54/55 (tt+bb) 로 묶습니다.**
즉 `genTtbarId` 만으로는 추가 b-jet 이 3개인지 4개인지 알 수 없습니다.

그런데 ttHH(bbbb) 분석(AN2022_122)은 tt+bbb(=3), tt+4b(>=4)를 별도 카테고리로
씁니다. 이 둘을 가르려면 추가 b-jet **개수**가 필요하므로, 우리가 직접 세어
(`nAddBJets`) `genTtbarId` 위에 얹어 줍니다. 그 결과가 `Expanded_genTtbarId` 입니다.

> **주의 — sub-code 56 에 대한 흔한 오해**: 표준 `genTtbarId` 에는 sub-code 56 이
> 존재하지 않습니다. 56 은 GenHFHadronMatcher TWiki 의 *다른* 분류 스킴(Example 2)에서
> "pseudo-additional b jet" 을 뜻하는 값으로, `genTtbarId` 와 무관합니다.
> (v9 이전 코드가 이 둘을 혼동해 split 이 작동하지 않았습니다. v10 에서 수정.)

---

## 1. 빠른 시작 — sidecar 하나 만들고 중앙 NanoAOD 와 대조

```bash
# 1. EL7 Singularity 컨테이너 진입 후 CMSSW 설정
cmssw-el7
cd CMSSW_10_6_32_patch1/src
cmsenv

# 2. 패키지 압축 해제 후 빌드
tar xzf ExtendedTtbarId_NanoExtension_v10.tar.gz   # ExtendedTtbarId/NanoExtension/ 생성
scram b -j8

# 3. MiniAODv2 파일 하나로 sidecar 생산
cmsRun ExtendedTtbarId/NanoExtension/test/run_sidecar_cfg.py \
    inputFiles=<miniaod.root> outputFile=sidecar.root maxEvents=100
# NB: VarParsing 이 파일명에 _numEventN 접미사를 붙이므로 실제 출력은
#     sidecar_numEvent100.root 입니다. 4단계에서 그 정확한 이름을 쓰세요.

# 3.1 실제 예시
cmsRun ExtendedTtbarId/NanoExtension/test/run_sidecar_cfg.py \
    inputFiles=root://xrootd-cms.infn.it///store/mc/RunIISummer20UL17MiniAODv2/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/MINIAODSIM/106X_mc2017_realistic_v9-v1/280000/215122BB-6A38-C24C-9589-11A9A1AC97BA.root outputFile=sidecar.root maxEvents=1000

# 4. genTtbarId 가 중앙 NanoAODv9 와 byte-identical 한지 검증
#    sidecar TTree 는 최상위에 있으므로 tree-path 접두사가 필요 없습니다.
compareSidecarToCentral \
    --sidecar sidecar_numEvent100.root \
    --central <central_nanoaodv9.root>

# 4.1 실제 예시
compareSidecarToCentral \
    --sidecar sidecar_numEvent1000.root \
    --central root://xrootd-cms.infn.it///store/mc/RunIISummer20UL17NanoAODv9/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/130000/1DD1BB46-D65F-B148-965E-8DB20A33BE8C.root
```

`compareSidecarToCentral` 은 두 파일을 `(run, lumi, event)` 로 매칭해 `genTtbarId` 가
완전히 일치하는지 확인하고, `Expanded_genTtbarId % 100` 분포를 표로 보여줍니다.

---

## 2. branch 의미

| branch | 타입 | 의미 |
|---|---|---|
| `run`, `luminosityBlock`, `event` | UInt/UInt/ULong64 | 이벤트 식별자 (NanoAOD 와 매칭용) |
| `genTtbarId` | Int | 표준 CMSSW 값. 중앙 NanoAOD 와 byte-identical |
| `Expanded_genTtbarId` | Int | 추가 b-jet <= 2 면 `genTtbarId` 와 동일. >= 3 이면 sub-code 가 **61/62**(정확히 3개, tt+bbb) 또는 **71/72**(4개 이상, tt+4b)로 재분류됨 |
| `nAddBJets` | Int | 우리가 센 추가 b-jet 개수 (acceptance: pT > 20 GeV, \|eta\| < 2.4, top decay 에서 안 온 b-hadron 보유 jet) |
| `nAddBJetsMulti` | Int | 그중 b-hadron 을 2개 이상 가진 jet 수 (g->bb 병합) |

`Expanded_genTtbarId` 의 sub-code (`% 100`) 인코딩:

| sub-code | 카테고리 | 조건 |
|---:|---|---|
| 0 | tt+LF | 추가 b/c jet 없음 |
| 41-45 | tt+cc | 추가 c jet >= 1 |
| 51 | tt+b | 추가 b-jet 1개, b-hadron 1개 |
| 52 | tt+2b | 추가 b-jet 1개, b-hadron >= 2개 |
| 53/54/55 | tt+bb | 추가 b-jet 2개 |
| **61/62** | **tt+bbb** | **추가 b-jet 정확히 3개** (62 는 multi jet 포함) |
| **71/72** | **tt+4b** | **추가 b-jet 4개 이상** (72 는 multi jet 포함) |

`genTtbarId` 의 앞자리(100/1000/10000 자리)는 그대로 보존되고 sub-code 만 확장됩니다.
AN 은 tt+bbb / tt+4b 만 구분하므로 분석에서는 61+62 -> tt+bbb, 71+72 -> tt+4b 로
합치면 됩니다 (multi 구분 61 vs 62 등은 g->bb 연구용 추가 정보).

> **내부 구현 메모**: 최종 ROOT branch 이름은 `Expanded_genTtbarId` (언더스코어 OK)
> 이지만, 그 중간 단계인 CMSSW EDM product 의 instance name 은 언더스코어를 쓸 수
> 없어 `expandedGenTtbarId` (camelCase) 로 둡니다. producer 가 `expandedGenTtbarId`
> 로 생산하고, sidecar analyzer 가 이를 받아 TTree branch `Expanded_genTtbarId` 로
> 기록합니다. 분석에서 읽을 branch 이름은 `Expanded_genTtbarId` 입니다.

---

## 3. CRAB 으로 전체 샘플 생산

ttbar stitching 에 필요한 7개 ttbar 샘플(inclusive 3 + ttbb 4FS 3 + tt4b 1)의
sidecar 를 CRAB 으로 일괄 생산합니다. 대상 목록은 `crab/datasets.yaml` 에 있습니다.

### 3.1 한 세션마다 한 번씩 설정

```bash
cmssw-el7
cd CMSSW_10_6_32_patch1/src && cmsenv
source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init -voms cms -valid 192:00
```

### 3.2 저장 위치 설정 (최초 1회)

`crab/site_config.yaml` 을 열어 `out_lfn_base` 의 placeholder
(`__YOUR_CERN_USERNAME__`)를 본인 CERN username 으로 바꿉니다.

### 3.3 MiniAODv2 parent 확인 (최초 1회 권장)

`datasets.yaml` 의 MiniAODv2 데이터셋 명은 DAS 로 확인된 값입니다(`verified: true`).
나중에 샘플을 추가하면 `crab/resolve_parents.sh` 로 정확한 parent(특히 -v1/-v2 접미사)를
확인할 수 있습니다:

```bash
bash crab/resolve_parents.sh   # 각 NanoAODv9 child 의 진짜 MiniAODv2 parent 출력
```

### 3.4 제출

```bash
# 환경 점검
python3 crab/preflight.py

# 제출 계획만 미리보기 (실제 제출 안 함)
python3 crab/submit_sidecar.py --dry-run

# 스모크 테스트: 한 샘플만, 파일 5개만
python3 crab/submit_sidecar.py --process TT4b --max-files 5

# 전체 enabled 샘플 제출
python3 crab/submit_sidecar.py
```

### 3.5 진행 상황 확인 / 실패 job 재제출 (일괄)

`submit_sidecar.py` 가 status / resubmit 일괄 실행도 지원합니다 (datasets.yaml 의
모든 선택 샘플에 대해 한 번에):

```bash
# 모든 샘플의 crab status 한꺼번에
python3 crab/submit_sidecar.py --status

# 모든 샘플의 실패 job 한꺼번에 resubmit
python3 crab/submit_sidecar.py --resubmit

# 특정 샘플만
python3 crab/submit_sidecar.py --resubmit --process TTbar_Hadronic,TTbb_Hadronic
```

`--status` / `--resubmit` 은 새 task 를 제출하지 않고, 기존 `crab_*` 프로젝트
디렉토리에 대해 `crab status` / `crab resubmit` 을 실행합니다. `--process`, `--era`
필터를 함께 쓸 수 있습니다.

---

## 4. 정확한 `cmsRun` 명령 (sidecar 하나)

```bash
cmsRun ExtendedTtbarId/NanoExtension/test/run_sidecar_cfg.py \
    inputFiles=file:<miniaodv2.root> \
    outputFile=sidecar.root \
    maxEvents=-1
```

`run_sidecar_cfg.py` 는 gen-level producer 만 돌립니다
(`matchGenBHadron` -> `categorizeGenTtbar` -> `extendedTtbarId`).
무거운 NanoAOD 재구성을 하지 않으므로 가볍고 빠릅니다. 출력은 최상위 `Events` TTree
하나이며 위 7개 branch 만 담습니다.

---

## 5. 패키지 구조

```
ExtendedTtbarId/NanoExtension/
+-- plugins/
|   +-- ExtendedTtbarIdProducer.cc    <- 핵심 producer. genTtbarId + nAddBJets 로
|   |                                    Expanded_genTtbarId 생성 (61/62/71/72)
|   +-- TtbarIdSidecarAnalyzer.cc     <- sidecar TTree (Events) 작성
|   `-- BuildFile.xml
+-- python/
|   +-- extendedTtbarId_cfi.py        <- producer cfi (cms.EDProducer)
|   +-- ttbarIdSidecar_cff.py         <- sidecar 시퀀스 (gen producer 체인)
|   `-- __init__.py
+-- test/
|   `-- run_sidecar_cfg.py            <- sidecar 생산 cmsRun cfg
+-- bin/
|   +-- compareSidecarToCentral.cc    <- sidecar vs 중앙 NanoAOD 검증
|   `-- BuildFile.xml
+-- crab/
|   +-- datasets.yaml                 <- ttbar stitching 7개 샘플 카탈로그
|   +-- site_config.yaml              <- 저장 위치 등 사용자 설정
|   +-- submit_sidecar.py             <- CRAB 제출 / --status / --resubmit
|   +-- resolve_parents.sh            <- DAS 로 MiniAODv2 parent 확인
|   +-- preflight.py                  <- 제출 전 환경 점검
|   +-- status.py                     <- crab_* 프로젝트 일괄 status
|   `-- __init__.py
+-- docs/
|   `-- ARCHITECTURE.md               <- 설계 원리 / 개발 이력 / 검증 결과
`-- README.md
```

---

## 6. 분석 단계에서 sidecar 사용하기

sidecar 는 NanoAOD 와 별개 파일이므로, 분석에서 `(run, lumi, event)` 로 매칭해
`Expanded_genTtbarId` 를 읽습니다. `event` branch 는 양쪽 모두 `ULong64_t` 라
형변환이 필요 없습니다.

```cpp
// ROOT friend-tree 예시
nano->AddFriend(sidecar);
nano->BuildIndex("run", "event");   // lumi 까지 쓰려면 합성키 필요 (docs 참고)
// 이후 nano->Draw("Expanded_genTtbarId") 가능
```

(MC 의 event 번호는 lumisection 안에서만 유일하므로, 엄밀한 매칭에는
`(run, luminosityBlock, event)` 3-key 가 필요합니다. 자세한 내용은
`docs/ARCHITECTURE.md` 참고.)

---

## 6b. ttbar 분류와 stitching (Expanded_genTtbarId 활용)

ttHH(bbbb) 분석은 tt+jets 를 추가 b-jet 개수로 7개 카테고리로 나눕니다
(추가 b-jet = gen-jet, pT > 20 GeV, |eta| < 2.4, top decay 에서 안 온 b-hadron 보유):

| 카테고리 | 정의 | 라벨 출처 |
|---|---|---|
| tt+LF | 추가 b/c jet 없음 | `genTtbarId` sub-code 0 |
| tt+cc | 추가 c jet >= 1 | `genTtbarId` 41-45 |
| tt+b | 추가 b-jet 1개, b-hadron 1개 | `genTtbarId` 51 |
| tt+2b | 추가 b-jet 1개, b-hadron >= 2 | `genTtbarId` 52 |
| tt+bb | 추가 b-jet 2개 | `genTtbarId` 53/54/55 |
| **tt+bbb** | **추가 b-jet 정확히 3개** | **`Expanded_genTtbarId` 61/62** |
| **tt+4b** | **추가 b-jet 4개 이상** | **`Expanded_genTtbarId` 71/72** |

앞 5개는 NanoAOD 의 `genTtbarId` 로 바로 결정됩니다. 마지막 두 개
(tt+bbb, tt+4b)는 `genTtbarId` 로는 불가능(53/54/55 안에 2/3/4개가 섞여 있음)하고
sidecar 의 `Expanded_genTtbarId` 가 필요합니다. 그래서 tt+bbb/tt+4b 카테고리에
참여하는 **모든 ttbar 샘플**에 sidecar 가 필요합니다.

**stitching 결정 (본 분석):** tt+bbb 와 tt+4b 는 dedicated **tt4b** LO 샘플로
모델링합니다 (AN option 1). 나머지는 기존 샘플 그대로 (tt+cc/LF 는 tt inclusive,
tt+b/2b/bb 는 TTbb 4FS). DNN 노드에서 tt+bbb + tt+4b -> **tt+nb**,
tt+b + tt+2b + tt+bb -> **tt+mb** 로 병합합니다.

**keep / reject (analyzer 단계에서 `Expanded_genTtbarId` 로 수행):**

```
# tt4b 샘플:        Expanded_genTtbarId%100 in {61,62,71,72} 이면 keep, 아니면 reject
# 그 외 ttbar 샘플:  Expanded_genTtbarId%100 in {61,62,71,72} 이면 reject, 아니면 keep
```

`Expanded_genTtbarId % 100` 은 완전하고 서로소인 분할(모든 이벤트가 정확히 하나의
카테고리)이며, 같은 물리 이벤트는 어느 샘플에 있든 같은 값을 받습니다(같은 producer,
같은 입력). 따라서 tt+nb / tt+mb 경계(`nAddBJets == 3`)가 모든 stitching 샘플에서
일관됩니다 — double-count 도 gap 도 없습니다.

현재 ntuplizer(`modules/ttbarCategorizer.py`)는 `genTtbarId` 로 5개 카테고리만
만듭니다(tt+bb = 53/54/55 는 아직 nAddBJets >= 2 를 통째로 포함). tt+bbb / tt+4b 분리와
위 keep/reject 는 sidecar 의 `Expanded_genTtbarId` 를 읽는 analyzer 단계에서
수행합니다. 자세한 내용은 `docs/ARCHITECTURE.md` §15.3.

---

## 7. (선택) 이벤트별 verbose 로깅

`run_sidecar_cfg.py` 에서 `process.ttbarIdSidecar.verbose = cms.untracked.bool(True)`
로 켜면, analyzer 가 이벤트마다
`(run, lumi, event, genTtbarId, Expanded_genTtbarId, nAddBJets, nAddBJetsMulti)`
한 줄을 `edm::LogVerbatim` 으로 출력합니다. `Expanded_genTtbarId` 가 `genTtbarId` 와
다른 드문 이벤트를 디버깅할 때 유용합니다.

---

## 8. 참고 자료

* ttHH(bbbb) AN: AN2022_122 (tt+jets 7-category 정의는 §3.1-3.2)
* GenHFHadronMatcher TWiki: 표준 `genTtbarId` 인코딩 (Example 1)
* CMSSW: `TopQuarkAnalysis/TopTools` (`GenTtbarCategorizer`),
  `PhysicsTools/JetMCAlgos` (`matchGenBHadron`)

---

## 9. 버전 이력

| 버전 | 내용 |
|---|---|
| v9 | CRAB 제출 버그 수정(sidecar cfg 의 `outputFile=` 처리, JobType.outputFiles 선언), per-job 메모리 2000MB, 비-ASCII 제거 |
| **v10** | **(1) 핵심 수정: split 조건이 존재하지 않는 sub-code 56 에 걸려 있어 tt+bbb/tt+4b 가 전혀 생성되지 않던 버그를 `nAddBJets` 기준으로 수정 (==3 -> 61/62, >=4 -> 71/72). (2) 패키지/모듈 rename: `TtbbStudies` -> `ExtendedTtbarId`, plugin `TtbbExtender` -> `ExtendedTtbarIdProducer`, cfi `ttbbExtender` -> `extendedTtbarId`. (3) branch `ttbbId` -> `Expanded_genTtbarId`. (4) stitching 문서(6b) 추가, CRAB 일괄 resubmit/status 옵션 추가, 안 쓰는 Approach-2(enriched NanoAOD) 파일 제거. 자세한 내용은 `docs/ARCHITECTURE.md` §15.** |

