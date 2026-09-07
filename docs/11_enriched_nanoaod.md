# 11 — Enriched NanoAOD (D17): 이론 · 레시피 · 검증 기록

> **목적**: MiniAODv2 를 입력으로 **중앙 생산과 동일한 NanoAOD 를 만들면서 확장 ttbar id 세 컬럼을 함께 넣는** 경로의 단일 참조 문서. 왜 그것이 "중앙과 동일"인지(이론), 정확히 어떤 명령인지(레시피), 무엇이 어디까지 증명됐는지(gate 와 증거), 그리고 그 과정에서 배운 검증 방법을 한 곳에 둔다.
> **대상 독자**: 이 경로로 샘플을 생산·검증하려는 사람; D17 을 DECIDED 로 올릴지 판단하는 사람.
> **상태**: 살아있는 문서. 마지막 갱신 **2026-09-07** — gate 1·2·3·5 **CLOSED**, gate 4 수치 확보(§3.4; 1 스레드 RSS **2,977 MB** 실측 → CRAB `maxMemoryMB` 는 제출 시 결정, §6). 검증은 HTCondor 배치(`TtbarIdExtender/condor/`)로 재현 가능.
> **관련**: 결정과 근거는 [04](04_decisions.md) D17 · D-DEP1 · D2, 인코딩 명세의 정본은 [02](02_physics.md) §3, 폐기됐던 첫 시도의 기록은 [10](10_enriched_nanoaod_archive.md), 비교 도구는 NtupleForge `script/compare_v9_v15.py`.

## 결론 먼저 (BLUF)

**되는 것이 실측으로 증명됐다.** 중앙 NanoAOD 생산에 쓰인 cmsDriver 원문을 DAS 에서 그대로 받아 `--customise` 하나만 덧붙이면, 출력은 **중앙과 이름·타입·값이 모두 같고 우리 컬럼 3 개만 더 있는** NanoAOD 가 된다. v9 에서 2000 event × 1666 branch = 3,332,000 개 값을 비트 단위로 비교해 **실질 불일치 0**. v15 에서도 같은 customise 가 그대로 동작하고(스키마 1903 + 3 = 1906, 타입 불일치 0), **2000 event 값 비교에서 정수 branch 불일치 0** — 다른 것은 재생산 자체의 성질인 세 부류(jet ghost-area 난수, HTXS float 잔차, NN 추론의 하드웨어 의존 마지막 비트; §3.3, §4.7)뿐이고, customise 를 뺀 중앙 cfg 를 같은 event 에 돌린 음성 대조군이 그 세 부류를 똑같이 재현했다.

**새 C++ 은 한 줄도 쓰지 않았다.** 추가된 것은 python 파일 하나(`TtbarIdExtender/python/ttbarIdTable_cff.py`, 71 줄)이고, 그것도 릴리스가 `genTtbarId` 를 branch 로 내보내는 방식을 그대로 베낀 것이다. 2026-08-31 의 D17 원문이 "FlatTable producer 를 새로 작성해야 한다" 고 적었던 것은 **비용 추정이 틀린 것**이었다 — 전제(table 컬럼을 붙이는 물건이 없다)는 맞았지만 해법이 이미 릴리스 안에 있었다.

71/72(tt+4b) 는 `TT4b` 2000 event 에서 51 건 확인됐고, **v9 와 v15 의 전이표가 글자 하나 다르지 않다**(§3.5). 처리율은 batch 노드에서 v15 1.26 ev/s, v9 6.12 ev/s — v15 NANO 가 4.9 배 비싸다(ParticleNetAK4 재계산). 부재 6 샘플 × 2 era 의 MiniAOD 는 3,525 파일 / 125.4M event 라 `FileBased` 1 파일/job 이면 3,525 job, task 당 최대 486 으로 D15 상한과 무관하다(§3.4).

남은 것은 결정과 생산이다: 컬럼 이름(§6), CRAB `maxMemoryMB`(1 스레드 RSS 2,977 MB — 1 코어 기본 2,000 MB 를 넘는다; cfg 는 그대로, §3.4·§6), 그리고 이 레시피를 CRAB 에 태우는 생산 글루.

---

## 1. 이론 — 무엇을 만들고, 왜 그것이 중앙과 같은가

### 1.1 만드는 것

인코딩의 정본은 [02](02_physics.md) §2–§3 이다. 여기서는 반복하지 않고, enriched 경로가 **그 명세를 실제로 만족함을 확인한 표**만 둔다 (v9, `TTbb_4f_TTToHadronic` 2000 event 중 `nAddBJets>=3` 인 6 개):

| entry | `genTtbarId` | `expandedGenTtbarId` | `%100` | nAddBJets | Multi |
|---:|---:|---:|:---:|:---:|:---:|
| 312 | 10254 | 10262 | 54 → **62** | 3 | 1 |
| 423 | 254 | 262 | 54 → **62** | 3 | 1 |
| 889 | 153 | 161 | 53 → **61** | 3 | 0 |
| 1456 | 253 | 261 | 53 → **61** | 3 | 0 |
| 1459 | 10153 | 10161 | 53 → **61** | 3 | 0 |
| 1631 | 10253 | 10261 | 53 → **61** | 3 | 0 |

02 §3 이 말하는 세 가지가 전부 보인다: 분기는 오직 `nAddBJets>=3`, 61/62 의 구분은 `nAddBJetsMulti`, prefix(100 자리 이상)는 보존(253 → 261). 그리고 **재분류는 총수를 보존한다** — 확장 후 census 가 53 = 166 · 61 = 4, 54 = 5 · 62 = 2 이므로 표준값 53 = 170 · 54 = 7 에서 정확히 4 개와 2 개만 옮겨간 것이다. 표준 categorizer 의 판정은 훼손되지 않는다.

`nAddBJets<=2` 인 1994 개는 `expandedGenTtbarId == genTtbarId` 다. 이것도 명세다(02 §3 첫 줄) — "확장이 안 됐다" 가 아니라 "확장 조건에 안 걸렸다" 이다.

### 1.2 왜 "중앙과 동일" 이라고 주장할 수 있나 — 다섯 가지 사실

"사설 생산인데 중앙과 같다" 는 주장은 다음 다섯 사실 위에 서 있고, 각각 실측이 뒷받침한다.

1. **같은 시퀀스를 돈다.** 중앙 생산의 cmsDriver 원문을 DAS config cache 에서 받아(§2.1) 글자 그대로 쓴다. `--step NANO`, `--era`, `--conditions`, `--eventcontent` 전부 동일. 우리가 손대는 것은 `--customise` 인자에 항목 하나를 **덧붙이는** 것뿐이다.
2. **`--customise` 는 중앙도 쓰는 정규 슬롯이다.** 중앙 생산 자체가 `Configuration/DataProcessing/Utils.addMonitoring` 을 그 슬롯에 걸고 있다. 우리 항목은 쉼표로 뒤에 붙는다. JMENano / BTVNano / PFNano 도 정확히 이 메커니즘으로 만들어진다 — 편법이 아니다.
3. **상위 모듈을 하나도 추가·제거·재설정하지 않는다.** `ExtendedTtbarIdProducer` 가 consume 하는 네 프로덕트는 전부 **중앙 시퀀스가 이미 만들고 있는 것**이다:

   | 입력 | 만드는 곳 |
   |---|---|
   | `categorizeGenTtbar:genTtbarId` | `ttbarCatMCProducers` (10_6) / `ttbarCatMCProducersTask` (15_0) |
   | `matchGenBHadron:genBHadJetIndex` | 같음 |
   | `matchGenBHadron:genBHadFromTopWeakDecay` | 같음 |
   | `slimmedGenJets` | MiniAOD 자체 |

   그래서 우리 customise 가 하는 일은 "이미 있는 프로덕트를 읽어 새 프로덕트를 만들고, 그것을 table 컬럼으로 내보내는" 것뿐이다. 기존 branch 의 값이 바뀔 경로가 **없다**. 스키마 비교에서 "중앙에만 있는 branch 0 개" 가 나오는 이유가 이것이다.
4. **실행 순서는 Task 가 데이터 의존성으로 정한다.** 우리 두 모듈을 `cms.Task` 로 묶어 `process.nanoAOD_step.associate()` 한다. Task 는 unscheduled 이므로 `extendedTtbarId` 가 `categorizeGenTtbar` 뒤에 도는 것은 시퀀스 순서를 손으로 맞춰서가 아니라 consume 관계로 보장된다. 10_6(Sequence 기반)과 15_0(Task 기반)에서 같은 코드가 도는 이유다.
5. **top-level branch 로 나오는 것은 릴리스의 관용구다.** `GlobalVariablesTableProducer` 에 `name`/`extension` 을 주지 않으면 `name=""` 이 되어 컬럼이 `Events` 의 top-level branch 가 된다. `genTtbarId`, `Flag_*`, `fixedGridRhoFastjet*` 이 모두 이 방식이다. 15_0_X 의 생성 cfi 는 이 두 값을 `extension=False`, `name=''` 로 **명시**해 준다 — 추론이 아니라 명시값이다.

### 1.3 v9 와 v15 는 무엇이 같고 무엇이 다른가

DAS config cache 로 확인한 중앙 레시피 (`TTbb_4f_TTToHadronic` UL17):

| | v9 | v15 |
|---|---|---|
| release | **CMSSW_10_6_26** | **CMSSW_15_0_18** |
| `--conditions` | `106X_mc2017_realistic_v9` | `150X_mc2017_realistic_v1` |
| `--era` | `Run2_2017,run2_nanoAOD_106Xv2` | **동일** |
| `--step` / `--eventcontent` | `NANO` / `NANOEDMAODSIM` | 동일 |
| `--customise` | `Configuration/DataProcessing/Utils.addMonitoring` | 동일 |
| 부모 MiniAOD | `RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1` | **동일** |
| config hash | `086c69c1b826c78c43be2aa70d7f23ab` | `f8c6f9a4395a3065a2aa683b1fdbf932` |

**era 와 부모 MiniAOD 가 완전히 같다.** 차이는 릴리스와 GT 둘뿐이고, 그래서 우리 customise 는 두 버전에서 **같은 파일**이다. 이것은 NtupleForge 캠페인이 별도로 확인한 사실 — CPV gen categorizer 가 v9·v15 에서 143,000 event × 61 branch 비트 동일 — 과 정합한다: gen 정보는 릴리스·GT 와 무관해야 하고, 실제로 그렇다.

같은 이유로 v15 smoke 의 **앞 10 event 의 `(genTtbarId, expanded, nAddBJets, Multi)` 가 v9 실행과 글자 하나 다르지 않았다.** MiniAOD 의 event 순서가 보존된다는 확인도 겸한다.

---

## 2. 레시피

### 2.1 중앙 cmsDriver 원문을 받는 법

이름만 알면 파일을 열지 않고 받는다. `release` 쿼리는 어느 CMSSW 로 생산됐는지, `config` 쿼리는 ReqMgr config cache 해시를 준다.

```bash
DS=/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM
dasgoclient -query="release dataset=$DS"            # -> CMSSW_10_6_26
dasgoclient -query="parent  dataset=$DS"            # -> ...MiniAODv2.../MINIAODSIM
HASH=$(dasgoclient -query="config dataset=$DS" -json \
       | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["config"][0]["ids"][0])')
PROXY="${X509_USER_PROXY:-/tmp/x509up_u$(id -u)}"
curl -sL --capath /etc/grid-security/certificates --cert "$PROXY" --key "$PROXY" \
  "https://cmsweb.cern.ch:8443/couchdb/reqmgr_config_cache/$HASH/configFile" -o central_cfg.py
head -5 central_cfg.py     # 5 행에 cmsDriver 원문
```

`release` 값은 DBS 가 injection 시점에 기록한 **메타데이터**다. 우리가 그 릴리스를 돌려 확인한 것이 아니라, 그 릴리스로 만들어진 **결과물**과 우리 결과물을 비교한 것이다(§3). 그것이 더 직접적인 증거다.

### 2.2 customise — 파일 하나, 두 릴리스

`TtbarIdExtender/python/ttbarIdTable_cff.py` (커밋 `a438485`). 요지:

```python
from PhysicsTools.NanoAOD.common_cff import ExtVar
from TTHHGenCategoryTools.TtbarIdExtender.extendedTtbarId_cfi import extendedTtbarId

try:    # CMSSW_15_0_X: fillDescriptions 로 생성된 cfi 를 clone (릴리스의 ttbarCategorization_cff 와 같은 방식)
    from PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi import globalVariablesTableProducer as _t
    _make_table = lambda v: _t.clone(variables=v)
except ImportError:   # CMSSW_10_6_X: 그 cfi 가 없다 -> 플러그인 이름으로 직접
    _make_table = lambda v: cms.EDProducer("GlobalVariablesTableProducer", variables=v)

ttbarIdExtendTable = _make_table(cms.PSet(
    expandedGenTtbarId = ExtVar(cms.InputTag("extendedTtbarId","expandedGenTtbarId"), "int", doc=...),
    nAddBJets          = ExtVar(cms.InputTag("extendedTtbarId","nAddBJets"),          "int", doc=...),
    nAddBJetsMulti     = ExtVar(cms.InputTag("extendedTtbarId","nAddBJetsMulti"),     "int", doc=...),
))

def customise(process):
    process.extendedTtbarId    = extendedTtbarId.clone()
    process.ttbarIdExtendTable = ttbarIdExtendTable.clone()
    process.nanoAOD_step.associate(cms.Task(process.extendedTtbarId, process.ttbarIdExtendTable))
    print("[ttbarIdTable_cff] table built via %s" % TABLE_STYLE)   # 어느 분기를 탔는지 로그에 남긴다
    return process
```

C++ 플러그인 `GlobalVariablesTableProducer` 는 두 릴리스에 똑같이 있다. 바뀐 것은 python 손잡이만이고, 그래서 `try/except ImportError` 하나로 갈린다. 실행 로그의 `[ttbarIdTable_cff] table built via ...` 줄이 어느 분기인지 알려준다 — 10_6 에서 `[10_6_X style]`, 15_0 에서 `[15_0_X style]` 이 실측됐다.

`ExtendedTtbarIdProducer` 는 무수정이다. `edm::global::EDProducer<>` + `fillDescriptions` 라는 현대 API 로 이미 쓰여 있어 15_0_18 에서 그대로 컴파일된다.

### 2.3 실행 — 릴리스별 영역

CMSSW 환경은 중첩되지 않는다. **영역마다 새 셸**이고, 영역을 넘나들 때 `$CMSSW_BASE` 는 쓰지 않는다(§5).

| 단계 | 컨테이너 | 영역 | 비고 |
|---|---|---|---|
| v9 enriched 생산 | `cmssw-el7` | `~/TTHHGenCategoryTools/CMSSW_10_6_32_patch1` | 정본 git 체크아웃이 여기 |
| v15 enriched 생산 | `cmssw-el8` (`SCRAM_ARCH=el8_amd64_gcc12`) | `~/TTHHGenCategoryTools_v15/CMSSW_15_0_18` | 같은 repo 를 clone |
| 비교·검증 | 어느 쪽이든 python3 + ROOT | NtupleForge `script/compare_v9_v15.py` 를 절대경로로 | v15 파일은 ROOT 6.32 로 쓰였으니 15_0 환경이 안전 |
| DAS / curl | 컨테이너 무관 | — | proxy 만 필요 |

**v9** (10_6_32_patch1):

```bash
cmsDriver.py nano --python_filename enriched_v9_cfg.py \
  --eventcontent NANOAODSIM --datatier NANOAODSIM \
  --conditions 106X_mc2017_realistic_v9 \
  --step NANO --era Run2_2017,run2_nanoAOD_106Xv2 \
  --customise Configuration/DataProcessing/Utils.addMonitoring,TTHHGenCategoryTools/TtbarIdExtender/ttbarIdTable_cff.customise \
  --filein file:/tmp/mini.root --fileout file:enriched_v9.root --no_exec --mc -n 2000
cmsRun enriched_v9_cfg.py
```

**v15** (15_0_18) — `--conditions` 만 바뀐다:

```bash
  --conditions 150X_mc2017_realistic_v1
```

두 가지 운영 규칙. ① **입력 MiniAOD 는 `xrdcp` 로 받아 `file:` 로 읽는다** — 캐시는 EOS `/eos/user/j/junghyun/ttHH/miniaod/` (lxplus `/tmp` 는 노드별이라 다음 로그인에 없다; [08](08_troubleshooting.md) T-28 이후 규칙). WAN 직독은 v9 에서 우연히 됐고 v15 에서 `exit=84` / `FileOpenError: Operation expired` 로 **18m53s 를 소모하고 죽었다**(CPU 3.4 s, 즉 전부 대기). MiniAOD 4.6 GB, `xrdcp` 3m9s. ② **grid proxy 를 job 전에 확인한다** — 위 실패의 1 차 원인은 전날 발급한 proxy 가 자정을 넘겨 만료된 것이었다 (`--valid 72:00`).

### 2.4 배치 실행 — `TtbarIdExtender/condor/`

§3 의 검증은 2026-09-07 부터 HTCondor 로 돈다: `submit.sh`(lxplus 호스트) 가 proxy·DAS·EOS 참조 파일을 확인하고 task 별 JDL 을 제출, `runTask.sh`(worker) 가 입력을 scratch 로 받아 cmsDriver/cmsRun → 비교 → 판정(`judge_compare.py`, `check_expanded.py`) → EOS `{enriched,json,logs}/<TAG>/` 로 결과를 남긴다. task 는 넷: `control_v15_200`(음성 대조군, 같은 노드에서 plain·ours), `timing_v15_2k`(처리율·gate 5), `tt4b_v9_2k`·`tt4b_v15_2k`(gate 3). v15 는 `MY.WantOS="el8"`, v9 는 el9 호스트에서 `cmssw-el7` 로 자기를 재실행한다. 사용법·판정 기준·CERN batch 주의사항은 그 디렉터리의 README 와 [08](08_troubleshooting.md) T-33~T-35.

---

## 3. Gate 와 증거

D17 을 DECIDED 로 올리는 데 필요한 조건을 gate 로 두고, 각각 무엇으로 증명됐는지 적는다.

| gate | 내용 | 상태 | 증거 |
|:---:|---|:---:|---|
| 1 | customise 로 컬럼이 top-level branch 로 나온다 | **CLOSED** 08-31 | §3.1 |
| 2 | 중앙 v9 와 이름·타입·**값**이 동일 | **CLOSED** 08-31 | §3.2 |
| 3 | 확장값 61/62/**71/72** 가 enriched 경로에서 옳다 | **CLOSED** 09-07 | §1.1 (61/62, TTbb), §3.5 (71/72, TT4b 2000 ev, v9 ≡ v15) |
| 4 | CRAB `units_per_job` 산정 (D15 상한) | 수치 확보 09-07 | §3.4 — `FileBased` 1 파일/job, 3,525 job / 16 task; RSS 2,977 MB(200 ev, 1 스레드) → `maxMemoryMB` 는 제출 시 결정 §6 |
| 5 | v15(15_0_18)에서 동일 절차 | **CLOSED** 09-07 | §3.3 — 2000 ev 정수 불일치 0, 차이는 세 부류만; 음성 대조군이 같은 부류를 재현 |

### 3.1 gate 1 — 컬럼이 나온다

v9, 10 event 스모크 → 2000 event. `expandedGenTtbarId` / `nAddBJets` / `nAddBJetsMulti` 세 개가 `Events` top-level 에 존재. 총 branch **1669**. 경고 3 종(`BTagSFProducer@ctor`, `HTXSRivetProducer@beginRun`, `GenWeightsTableProducer@beginRun`)은 전부 `%MSG-w` 이고 중앙 생산도 같은 시퀀스라 동일하게 난다.

### 3.2 gate 2 — 중앙 v9 와 동일

**스키마.** 중앙 파일 `653BA400-...` (같은 데이터셋, 우리 event 와 겹치지 않음) 과 이름·타입 비교:

| | branch |
|---|---:|
| 중앙 v9 | **1666** |
| 우리 | **1669** |
| 우리에만 | `expandedGenTtbarId`, `nAddBJets`, `nAddBJetsMulti` — 정확히 3 |
| 중앙에만 | **0** |
| 공통 1666 개 타입 불일치 | **0** |

1666 은 NtupleForge 인벤토리 스윕의 UL17 MC 값과 일치한다.

**값.** 짝은 lumi 추정이 아니라 **부모로 확정**했다: `dasgoclient -query="child file=<우리가 처리한 MiniAOD LFN>"` → v9 자식 2 개 중 `2C5102B9-...` 가 우리 2000 event 를 전부 포함(overlap 2000/2000), `653BA400-...` 는 0. 즉 **스키마 근거와 값 근거가 서로 다른 파일**이다.

```
compare_v9_v15.py --v9 central_2C5102B9.root --v15 enriched_v9.root --prefix "" --ftol 0
  compared  2000 event x 1666 branch = 3,332,000 values
  only in ours : expandedGenTtbarId, nAddBJets, nAddBJetsMulti     <- 음성 대조군 역할
  common events: 2000 / 2000
  실질 불일치  : 0      정수 branch 불일치 : 0
  NaN==NaN     : HTXS_Higgs_y 2000, PuppiMET_{pt,phi}JER{Up,Down} 각 5  (인공물, §4.4)
```

`--ftol 0` 은 비트 동일 요구다. 그리고 이 비교는 **CMSSW_10_6_26(중앙) 대 10_6_32_patch1(우리)** 이므로, 같은 cycle 의 patch 차이가 값에 미치는 영향이 **0** 임이 함께 증명됐다 — D2 의 pin 이 유효한 실측 근거다.

### 3.3 gate 5 — v15

15_0_18 에 repo 를 clone 해 `scram b` → **무수정 전부 빌드**. 200 event smoke, exit 0:

| | branch |
|---|---:|
| 중앙 v15 (`7546c9f8-...`, overlap 0) | **1903** |
| 우리 | **1906** |
| 우리에만 / 중앙에만 | 3 / **0** |
| 공통 1903 개 타입 불일치 | **0** |

`PFMET_pt` 와 `Rho_fixedGridRhoFastjetAll` 이 존재한다 — v9 라면 `MET_pt` / `fixedGridRhoFastjetAll` 이어야 하므로 출력이 진짜 v15 스키마임을 스스로 증명한다.

**값.** 비교 상대는 우리 MiniAOD 파일의 v15 자식 중 우리 event 를 담은 `e10ceebb-…`(overlap 200/200, 2000/2000). 파일 정체 (provenance):

```
입력 MiniAOD  /store/mc/RunIISummer20UL17MiniAODv2/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/MINIAODSIM/106X_mc2017_realistic_v9-v1/280000/04B35B8B-2D7E-DD4C-AA6A-FC6364606485.root
중앙 v15 값   /store/mc/RunIISummer20UL17NanoAODv15/.../NANOAODSIM/150X_mc2017_realistic_v1-v1/2550000/e10ceebb-116c-4a8f-a2b1-19b89b467713.root   (618,000 ev)
중앙 v15 스키마 .../2550000/7546c9f8-6992-46cc-8e88-c11a9f2aebd6.root   (overlap 0)
중앙 v9 값     /store/mc/RunIISummer20UL17NanoAODv9/.../NANOAODSIM/106X_mc2017_realistic_v9-v1/130000/2C5102B9-7027-3E4E-836C-06A981E74AF3.root
중앙 v9 스키마 .../130000/653BA400-3833-5F48-A42F-23B3F86AB049.root
```

세 번 비교했고 결과는 한 문장이다 — **정수 branch 는 어디서도 다르지 않고, float 차이는 세 부류에만 있다.**

| 비교 (`--ftol 0`) | 언제·어디서 | 불일치 event | 다른 branch |
|---|---|---:|---|
| ours 200 ev vs 중앙 | 09-03 lxplus | 3 / 200 | `FatJet_area` (2 ev), `HTXS_{Mjj,V_pt,dPhijj,ptHjj}` (1 ev) |
| ours 2000 ev vs 중앙 | 09-03 lxplus | 38 / 2000 | `FatJet_area` 17, `Jet_area` 15, `CorrT1METJet_area` 13, `SubJet_area` 6, `HTXS_*` 1 |
| ours 2000 ev vs 중앙 | 09-07 lxbatch | 40 / 2000 | 위 + `Tau_rawDeepTau2018v2p5VS{e,mu}`, `boostedTau_rawBoostedDeepTauRunIIv2p0VSjet` 각 1 |
| ours 200 ev vs ours 2000 ev (같은 노드) | 09-03 | **0** | — |
| ours 2000 ev (lxplus) vs ours 2000 ev (lxbatch) | 09-07 | 3 / 2000 | DeepTau 세 값만 |

세 부류의 정체는 §4.7. 요점만: `*_area` 는 FastJet ghost 난수로 **job 의 event 이력**을 따르고(같은 event 순서면 다른 노드라도 동일), HTXS 는 수학적 0 의 float 잔차(0 vs 3×10⁻⁵), DeepTau 는 NN 추론의 마지막 비트가 **CPU 종류**에 따라 달라 저장 정밀도(10-bit mantissa) 한 칸(2⁻¹¹~2⁻¹⁴)을 넘은 값만 보이는 것이다. 어느 것도 우리 customise 와 관계없다 — 그것을 증명하는 것이 음성 대조군이다.

**음성 대조군 (`control_v15_200`).** 우리 customise 를 **뺀** 중앙 cfg 로 같은 200 event 를 돌린 `plain` 과 비교:

- (a) plain vs 중앙: `FatJet_area` (1,3791,6)·(1,3791,72), `HTXS_*` (1,3791,12) — 09-03 에 **우리 출력**과 중앙 사이에서 본 것과 **같은 event, 같은 값** (+ DeepTau 1 값, batch 하드웨어). 즉 그 차이는 customise 가 아니라 재생산의 성질이다.
- (c) plain(lxbatch) vs ours smoke(lxplus): area·HTXS **일치**, DeepTau 1 값만 다름 → area/HTXS 는 event 이력, DeepTau 는 하드웨어라는 분리가 확정.
- (b) plain vs ours, **같은 노드·같은 job** (TAG `20260907_1128`, 연달아 280 s / 277 s, 둘 다 `%MSG-e` 0): `--zero` 로 **비트 동일**, v15 에만 있는 branch 는 우리 3 컬럼뿐 → **PASS**. 이것이 "customise 는 3 컬럼 외 아무것도 바꾸지 않는다" 의 직접 증거다. (a)·(c) 도 PASS — `control_v15_200` verdict **ALL PASS** (판정 기준은 `condor/README.md`, 세 부류는 §4.7).

### 3.4 처리율과 job 산정 (gate 4)

| 릴리스 | 샘플 | event | 노드 | event loop | init | **ev/s** (loop) |
|---|---|---:|---|---:|---:|---:|
| v15 15_0_18 | TTbb | 200 | lxplus (09-02) | — | — | 2.4 (시동 비중 큼, 참고만) |
| v15 15_0_18 | TTbb | 2000 | lxbatch Xeon Gold 5218 | 1,588 s | 41 s | **1.26** |
| v15 15_0_18 | TT4b | 2000 | lxbatch | ~2,050 s | — | ~1.0 |
| v9 10_6_32 | TT4b | 2000 | lxbatch (el7 컨테이너) | 327 s | 32 s | **6.12** |

v15 가 v9 의 **4.9 배** 비싸다. 원인은 로그에 있다: 15_0_X NANO 는 MiniAOD 에서 **ParticleNetAK4 를 재계산**한다 (`Updating process to run ParticleNetAK4`, discriminator 34 개, b tagging 을 위해 JEC 를 되돌렸다 다시 적용) — v9 에는 없던 작업이다. lxplus 의 2.4 ev/s 는 200 event 라 시동 비용이 섞인 값이고, 산정에는 batch 의 1.26 ev/s 를 쓴다(grid 노드도 그쪽에 가깝다).

**부재 6 샘플의 MiniAOD 부모** (DAS, 2026-09-07; `json/miniaod_parents_absent6.txt`):

| era | 샘플 | 파일 | event | 파일당 ev | 1 파일/job 소요 (1.26 ev/s) |
|---|---|---:|---:|---:|---:|
| 2017 | `TTHHto4b` | 199 | 9,934,000 | 49.9k | 11.0 h |
| 2017 | `tHW` | 436 | 14,964,000 | 34.3k | 7.6 h |
| 2017 | `TTZToBB` | 144 | 7,074,000 | 49.1k | 10.8 h |
| 2017 | `TTZHTo4b` / `_ext1` | 92 / 204 | 5,000,000 / 4,998,000 | 54.3k / 24.5k | 12.0 h / 5.4 h |
| 2017 | `TTZZTo4b` / `_ext1` | 111 / 203 | 4,832,000 / 5,000,000 | 43.5k / 24.6k | 9.6 h / 5.4 h |
| 2017 | `TT4b` | 185 | 9,502,000 | 51.4k | 11.3 h |
| 2018 | `TTHHto4b` | 365 | 9,598,000 | 26.3k | 5.8 h |
| 2018 | `tHW` | 486 | 14,973,000 | 30.8k | 6.8 h |
| 2018 | `TTZToBB` | 189 | 9,965,000 | 52.7k | 11.6 h |
| 2018 | `TTZHTo4b` / `_ext1` | 193 / 212 | 4,823,000 / 4,998,000 | 25.0k / 23.6k | 5.5 h / 5.2 h |
| 2018 | `TTZZTo4b` / `_ext1` | 109 / 209 | 4,934,000 / 4,996,000 | 45.3k / 23.9k | 10.0 h / 5.3 h |
| 2018 | `TT4b` | 188 | 9,844,000 | 52.4k | 11.5 h |
| | **합계** | **3,525** | **125,362,000** | | **≈ 27,600 core-h** |

산정: `FileBased`, **`units_per_job = 1`** → job 3,525 개 / 16 task, task 당 최대 486(2018 `tHW`) 으로 D15 상한 10,000 의 5 %. job 하나가 5–12 시간이라 CRAB 기본 한도(~22 h) 안이고, 대안으로 `splitting='Automatic'`(목표 480 분)도 무방하다. 슬롯 500–1,000 개면 벽시계 1–2 일 + 꼬리. 메모리는 아래 실측으로 정한다.

**메모리 (`control_v15_200`, TAG 20260907_1128, framework job report; `addMonitoring` 의 `SimpleMemoryCheck` 는 로그가 아니라 job report 에만 쓰므로 `cmsRun -j` 가 필요하다):**

| run (같은 노드, 연달아) | event | `PeakValueRss` | `PeakValueVsize` | `TotalJobCPU` | `AvgEventTime` | loop rate |
|---|---:|---:|---:|---:|---:|---:|
| plain (중앙 cfg) | 200 | **2,976.8 MB** | 4,475.6 MB | 259.5 s | 1.045 s | 0.91 ev/s |
| ours (customise) | 200 | **2,977.4 MB** | 4,463.8 MB | 261.4 s | 1.055 s | 0.90 ev/s |

우리 customise 의 비용은 메모리 **+0.6 MB**, CPU **+0.7 %** — 측정 잡음 수준이다. 비용은 전부 15_0_X NANO 자체(ParticleNetAK4 재계산)에 있다. 200 ev 의 loop rate(0.91)가 2000 ev(1.26)보다 낮은 것은 첫 event 의 일회성 비용(ONNX 모델 적재 등) 때문이고, 두 점을 `t = t₀ + N/r` 로 풀면 **정상 상태 r ≈ 1.32 ev/s, t₀ ≈ 68 s** 다 — 위 산정(1.26)은 그만큼 보수적이다.

**CRAB 에의 함의.** 1 스레드 RSS 가 **2,977 MB** 로 CRAB 1 코어 기본(2,000 MB)을 넘는다. 200 ev 의 피크는 파일 하나(25–55k ev)를 처리하는 job 의 **하한**이다(ROOT 출력 버퍼·힙 조각화로 더 자랄 수 있다 — 기울기는 `timing_v15_2k` 를 현행 스크립트(`cmsRun -j`)로 다시 돌려 2000 ev 의 RSS 로 잰다). **cfg 에는 손대지 않는다**: §2 의 규칙 1(중앙 cmsDriver 원문 그대로)이고, 우리가 받은 원문에는 스레드 옵션이 없다. 그러므로 1 차 안은 **`numCores = 1`, `maxMemoryMB ≈ 3,500`** 이고, 이것이 되는지는 CRAB 서버가 제출 시 판정한다(단일 코어 job 의 메모리 상한 — 2,500 MB 로 기억하지만 확인하지 않았다). 거부될 때만 `numCores = 2` + `--nThreads 2` 로 간다(그때는 2 스레드 확인 run 이 먼저다, §6). 중앙 job 이 몇 스레드로 돌았는지는 cmsDriver 줄이 아니라 ReqMgr 요청의 `Multicore` 에 있다(WMAgent 가 job 생성 시 `numberOfThreads` 를 주입한다) — §6 항목 1 의 curl 로 읽을 수 있고, `Memory` 값은 우리 요청량의 참고가 된다.

부수 관찰: MiniAOD 부모가 중앙 NanoAOD v9 보다 event 가 **많은** 데가 있다 — `tHW` 2017 14,964,000 vs 14,325,000, `TTZToBB` 2018 9,965,000 vs 9,842,000, `TTZZTo4b_ext1` 2018 4,996,000 vs 4,864,000. 중앙 v9 가 1–4 % 를 잃은 것이고, MiniAOD 에서 만드는 우리 enriched 는 그만큼 더 온전하다.

### 3.5 gate 3 — 71/72 (TT4b, 2000 event, v9 와 v15)

`TT4b_TuneCP5_13TeV_madgraph_pythia8` 2017 MiniAOD (`…/80000/DEAA93B6-5BD1-EE42-A545-6EC08733138D.root`, 27,000 ev 중 앞 2000) 을 v9(10_6_32_patch1)와 v15(15_0_18)로 각각 처리, `check_expanded.py` 가 [02](02_physics.md) §3 의 규칙을 event 마다 검사: **규칙 위반 0, 두 릴리스의 표가 동일.**

```
nAddBJets            0:180  1:677  2:741  3:351  4:48  5:3      (>=3: 402, >=4: 51)
genTtbarId%100 -> expanded%100
   0->0 170   41->41 5   42->42 2   43->43 1   44->44 1
  51->51 520   52->52 154
  53->53 528   53->61 268   53->71 43
  54->54 195   54->62  79   54->72  8
  55->55  22   55->62   4
extended: 61:268  62:83  71:43  72:8
```

읽는 법: 61 ← 53 (multi 0), 62 ← 54·55 (multi ≥1), 71 ← 53, 72 ← 54 — 정확히 규칙대로고, `55→62` 는 "중앙 55(두 추가 b-jet 모두 B hadron ≥2)에 세 번째 b-jet" 인 event 다. 71/72 는 TT4b 에서도 2.5 %(51/2000) 로 드물다. gen 레벨 분류가 릴리스·GT 와 무관하다는 §1.3 의 주장이 2000 event 실측으로 닫힌다.

cmsRun 의 `%MSG-e` 는 세 job 모두 `JetPtMismatch` 14 건 — `JetFlavourClustering:genJetAK8FlavourAssociation`(중앙 시퀀스; MiniAOD 의 `slimmedGenJetsAK8` constituent 가 잘린 것, [08](08_troubleshooting.md) T-1 부류)이고 우리 것이 아니다. worker 는 이 카테고리만 허용하고 다른 `%MSG-e` 가 나오면 FAIL 로 표시한다.

---

## 4. 검증 방법론 — 이 캠페인이 가르친 것

측정 자체보다 오래 남을 것은 **어떻게 재서 어떻게 믿었는가**다. 일곱 개.

### 4.1 개수가 아니라 값을 찍는다

gate 2 의 첫 실행은 `events with >=1 disagreement: 2000 (100.0000 %)` 였다. per-branch 는 5 개뿐이었지만 "5 개 branch 만 다르네" 로 넘어갔다면 그 5 개가 진짜 차이인지 인공물인지 모른 채 남았을 것이고, 반대로 100 % 만 보고 "릴리스 차이가 크다" 고 결론냈다면 마이그레이션을 세웠을 것이다. 값을 직접 찍어보니 전부 `nan` vs `nan` 이었다(§4.4). **집계는 어디를 볼지 알려줄 뿐이고 판정은 값이 한다.**

### 4.2 음성 대조군을 항상 포함시킨다

`--prefix ""` 로 전 branch 를 비교하면 "우리에만 있는 것" 이 정확히 우리 3 개로 나와야 한다. 이것은 도구가 **차이를 실제로 감지한다**는 증명이다. 불일치 0 이라는 결과는 이 대조군이 함께 있을 때만 의미가 있다 — 도구가 아무것도 못 보는 상태에서도 불일치는 0 이기 때문이다. NtupleForge 의 CPV 검증이 `only in v15: GenJet_nBHadrons, GenJet_nCHadrons` 로 같은 역할을 했던 것과 같은 원리다.

### 4.3 근거를 독립시킨다

스키마는 우리 event 와 **겹치지 않는** 중앙 파일과 비교했고(v9 `653BA400`, v15 `7546c9f8`), 값은 **겹치는** 파일과 비교했다(v9 `2C5102B9`, v15 `e10ceebb`). 우연히 그렇게 됐지만 결과적으로 두 주장이 서로 다른 데이터에 기대게 됐다. 앞으로도 의도적으로 이렇게 한다.

### 4.4 IEEE 754 의 `nan != nan`

`==` 비교와 `abs(x-y) <= tol` 비교는 양쪽이 NaN 이면 **둘 다** False 다. `HTXS_Higgs_y` 는 Higgs 가 없는 샘플에서 정의 불가라 양쪽 다 NaN 이고(`HTXSRivetProducer@beginRun` 경고가 그 신호), `PuppiMET_*JER*` 도 일부 event 에서 그렇다. `--ftol` 을 올려도 안 고쳐진다 — tolerance 문제가 아니다. 비교기는 이제 양쪽 NaN 을 agreement 로 처리하되 **branch 별 건수를 세어 출력**한다. 조용히 넘기지 않는 것이 조건이다. 기록: NtupleForge `docs/05_troubleshooting.md` A21.

부수 사실: 그 비교기의 float 판정은 **이름 기반**(`_pt`/`_eta`/`_phi`/`_mass`/`_energy` 로 끝나는 것만)이라 `PuppiMET_ptJERUp` 같은 것은 `--ftol` 과 무관하게 `==` 로 비교된다. 즉 대부분의 float 이 사실상 완전일치 비교다. byte-identity 검증에는 좋지만, 어디에 tolerance 가 걸리는지 착각하면 안 된다.

### 4.5 짝은 추정하지 않고 부모로 확정한다

v9 와 v15 의 NanoAOD 파일 경계는 서로 대응하지 않는다(NtupleForge `docs/08` 6.1). 그러나 우리가 **어느 MiniAOD 파일을 처리했는지는 확정**돼 있으므로 `dasgoclient -query="child file=<LFN>"` 이 그 파일의 NanoAOD 자식을 직접 준다. lumi 페어링(`pair_v9_v15.py`)은 두 중앙본을 비교할 때의 도구이고, 우리 산출물 대 중앙본에는 이쪽이 정확하다.

### 4.6 스키마는 xrootd 로, event loop 는 로컬에서

branch 이름·타입은 TTree 헤더만 읽으므로 xrootd 직독으로 몇 초다(2.2 GB 파일도). event 를 도는 것은 반드시 `/tmp` 복사 뒤에 한다 — §2.3 의 18 분 사고와, 비교기의 640k-event 인덱싱이 20m46s 에서 key 3 branch 만 읽도록 고쳐 수 분으로 줄어든 것이 같은 교훈이다.

### 4.7 "중앙과 동일" 은 비트 동일이 아니다 — 재생산의 세 부류와 그것을 분리하는 법

같은 릴리스·같은 cfg·같은 event 라도 두 job 의 출력은 세 곳에서 다를 수 있다 (§3.3 표):

| 부류 | 원인 | 따라가는 것 | 크기 |
|---|---|---|---|
| `Jet/FatJet/SubJet/CorrT1METJet_area` | FastJet active area 의 ghost 난수 | job 의 **event 이력** (몇 번째 event 인가) | ~1 % |
| `HTXS_{Mjj,V_pt,dPhijj,ptHjj}` | 수학적 0 을 float 로 계산한 잔차 | event 이력 | 0 vs 3×10⁻⁵ |
| `Tau_rawDeepTau*`, `boostedTau_rawBoostedDeepTau*` | NN 추론의 마지막 비트 (SIMD/FMA 경로) | **CPU 종류** (lxplus·중앙 vs lxbatch) | 저장 정밀도 한 칸 (2⁻¹¹~2⁻¹⁴) |

그래서 "동일" 의 판정 기준은 비교 상대에 따라 셋이어야 한다 (`condor/config.sh`): **같은 노드·같은 job 에서 만든 두 파일은 비트 동일**을 예외 없이 요구하고(음성 대조군 (b)), 다른 머신에서 만든 같은 event 는 NN 출력만 허용하고, 중앙처럼 다른 job 이력이면 세 부류 모두 허용한다. 정수 branch 와 우리 3 컬럼은 어느 경우에도 달라선 안 된다. 이 세 부류 밖의 불일치가 하나라도 나오면 그것은 설명해야 할 차이다.

이 분리를 배운 대가는 하루였다. 처음 대조군은 batch 의 plain 과 lxplus 의 ours 를 비교했고 DeepTau 한 값에서 "비트 동일" 이 깨졌다 — 하드웨어 변수를 대조군에 섞은 설계 실수였다([08](08_troubleshooting.md) T-35). 대조군은 **같은 job 에서 plain 과 ours 를 연달아** 돌려야 한다. 생산 함의도 하나 있다: grid 는 이기종이므로 enriched NanoAOD 의 NN 출력은 중앙과 이 수준에서 다를 수 있고, 그것은 물리적으로 무의미하다.

---

## 5. 환경 · 운영 메모

- **임시 파일은 lxplus `/tmp` 가 아니라 EOS 에.** `/tmp` 는 노드별이라 다음 로그인(다른 노드)에 없다 — 09-03 의 `central_ttbb_v15.root`, `mini_ttbb.root` 가 그렇게 사라졌다. 입력·중앙·출력·비교 결과는 `/eos/user/j/junghyun/ttHH/{miniaod,central,enriched,json,logs}/`.
- **CERN batch 는 바뀐다** — stdout 스트리밍 금지(2025-11), `set -u` 아래에서 CMS site 스크립트를 source 하면 `CVS_RSH: unbound variable` 로 즉사, `MY.WantOS` 는 el8/el9. [08](08_troubleshooting.md) T-33·T-34, `condor/README.md`.
- **git 원격 작업은 컨테이너 밖에서.** `cmssw-el7/el8` 안에서는 SSH agent 가 없어 `git pull/push` 가 `Permission denied (publickey)` 로 실패한다. 이 계정은 키 활성화 함수(`switch`)를 컨테이너 밖에서 실행해야 한다. clone 도 밖에서 한 뒤 빌드만 안에서.
- **`nohup` 은 컨테이너 종료를 못 넘긴다.** 컨테이너 안에서 `nohup ... &` 로 띄운 job 은 그 컨테이너를 `exit` 하면 함께 사라질 수 있다. 긴 job 은 셸을 유지하거나 condor 로.
- **`$CMSSW_BASE` 는 영역마다 다르다.** 14_2_1 에서 `cmsenv` 한 뒤 `$CMSSW_BASE/src/enriched_v15.root` 를 쓰면 15_0_18 의 파일을 못 찾는다. 영역을 넘는 경로는 절대경로.
- **15_0_X 의 평탄화 python 트리는 비어 있다.** `$CMSSW_RELEASE_BASE/python/PhysicsTools/NanoAOD/` 에 `__init__.py` 만 있고 실제 파일은 `src/PhysicsTools/NanoAOD/python/` 에 있다. import 는 정상 동작한다. 10_6 의 습관대로 `python/` 아래를 grep 해 "없다" 고 결론내면 [08](08_troubleshooting.md) 의 "한 번의 조회로 부재를 단정" 류 오류다(NtupleForge A19/A20 과 같은 계열).
- **ROOT 6.14 (10_6, python2) 의 PyROOT 함정.** `ROOT.TFile.Open(p).Get('Events')` 는 TFile 에 python 참조가 안 남아 GC 가 닫고, 이후 tree 접근이 segfault 다. `f = TFile.Open(p); t = f.Get(...)` 로 파일 객체를 잡아둔다. 14_2_1/15_0 의 최신 ROOT 는 넘어가 주므로 환경을 옮기면 갑자기 터진다.
- **`TTree::Scan(varexp, sel, opt, nentries, first)`** — 4 번째 인자는 **nentries** 다. `Scan(v, cut, '', 20)` 은 "20 개 보여줘" 가 아니라 "앞 20 entry 만 훑어라" 여서, cut 을 만족하는 event 가 뒤에 있으면 `0 selected entries` 라는 **거짓 음성**을 낸다.
- **python2 의 `ImportError: No module named X`** 는 마지막 컴포넌트 이름만 적는다. `A.B.C` 에서 A 가 없어도, C 가 없어도 다르게 보인다 — 어느 단계가 없는지는 따로 확인한다.

---

## 6. 남은 작업과 열린 결정

**작업**

1. **CRAB 메모리 (제출 시 결정)** — 실측 1 스레드 `PeakValueRss` **2,977 MB**(§3.4; 200 ev 라 하한). 순서: ① `timing_v15_2k` 를 현행 스크립트로 재실행해 2000 ev 의 RSS(성장 기울기)를 얻는다(코드 변경 없음, `./submit.sh -T timing_v15_2k`). ② 1 차 안 **`numCores = 1`, `maxMemoryMB = 3500`**(2000 ev RSS 를 보고 4,000 으로 올릴 수 있음) 으로 첫 task(`TT4b`)를 제출 — cfg 는 중앙 원문 그대로(스레드 옵션 없음), 검증한 것과 1:1. ③ 서버가 단일 코어 메모리 상한으로 거부하면 그때 `numCores = 2` + `--nThreads 2` + `maxMemoryMB = 4000` 으로 바꾸되, 먼저 `condor/` 에 2 스레드 task 를 추가해 같은 노드 2T plain vs 2T ours `--zero`, 2T ours vs 1T ours 2000 ev(`*_area` 만 예상 — ghost 난수가 프로세스 이력을 따르므로), 2T 의 RSS 를 확인한다. 참고로 중앙 요청의 스레드·메모리는 ReqMgr 에서 읽는다: `curl -sL --capath /etc/grid-security/certificates --cert $PROXY --key $PROXY "https://cmsweb.cern.ch/reqmgr2/data/request?outputdataset=$DS"` 의 `Multicore` / `Memory`. 결정은 D17 표에.
2. **생산 글루** — 이 cmsDriver cfg 를 CRAB 에 태우는 것. 두 갈래: NtupleForge `job_type: cmsrun`(D17 원안; registry·das_scan·preflight·submit/status/report 재사용) 또는 이미 MiniAOD 위에서 cmsRun 을 CRAB 으로 돌려 본 `TtbarIdExtender/crab/` 의 pset 교체. 선택은 NtupleForge `01_STATUS` A1.
3. **적용 순서** — `TT4b`(이미 검증 입력) → `TTHHto4b`(신호) → `TTZHTo4b`(+ext1), `TTZZTo4b`(+ext1), `tHW`, `TTZToBB`; 두 era. 파일 수·event 수는 §3.4 표.
4. **생산 후 검증** — 각 dataset 의 출력 event 합 = MiniAOD 부모 event 수(§3.4 표; 중앙 v9 수가 아니다), `check_expanded.py` 로 규칙, 중앙 v15 가 있는 샘플(TTbb 등)과의 값 비교는 §4.7 의 세 부류 기준.
5. **2018 레시피** — 지금까지의 검증은 전부 **2017** 이다(`Run2_2017`, `150X_mc2017_realistic_v1`). 2018 은 §2.1 절차로 중앙 `RunIISummer20UL18NanoAODv15` 의 cmsDriver 원문(era `Run2_2018,run2_nanoAOD_106Xv2`, 2018 GT)을 받아 옮기고, 2018 MiniAOD 파일 하나로 `control_v15_200` 형 같은-노드 대조군(plain vs ours `--zero`, plain vs 중앙 2018 v15 `ALLOW_REPRO`)을 한 번 돈다 — `condor/` 에 era 인자 하나면 된다. 물리는 같지만 GT·era 가 다르니 200 ev 로 확인하는 값어치가 있다.
6. **출력 목적지·크기·공개** — 125.4M ev × v15 MC ≈ 2.9 kB/ev ≈ **0.36 TB**. T3_CH_CERNBOX(EOS user) 로 받으려면 `eos quota` 를 먼저 보고(기본 1 TB 에 기존 사용량), 아니면 T2_KR_KNU 등 다른 storage. DBS `publication` 여부(NtupleForge 가 `das_scan` 으로 읽으려면 `phys03` 에 publish 하는 편이 맞다)와 출력 dataset 이름 규칙(`enrichedNanoAODv15_<KEY>_<era>`)을 D17 에 적는다.

**열린 결정 — 컬럼 이름.** NanoAOD 컬럼은 현재 `expandedGenTtbarId`(camelCase, EDM instance 이름과 동일, `genTtbarId` 와 같은 관용)이다. 그런데 sidecar TTree 와 analyzer 계약([07](07_analyzer_integration.md))은 `Expanded_genTtbarId` 다. 6 샘플은 enriched, ttbar 3 종은 sidecar 이므로 **analyzer 가 두 이름을 다 알아야 한다.** NanoAOD 관용으로는 camelCase 가 맞고(`Expanded_` 는 `Jet_` 처럼 컬렉션 prefix 로 읽힌다), 계약 통일로는 `Expanded_genTtbarId` 가 맞다. 어느 쪽이든 **결정 후 D17 에 기록**한다. 지금 기본값은 camelCase.

**D17 상태.** 원문의 DECIDED 조건 5 개 — ①(producer) ②(byte-identity) ③(확장값 61/62/71/72) ⑤(15_0_X) 충족, ④(CRAB 상한) 수치로 충족(3,525 job / 16 task, task 당 ≤ 486). DECIDED 로 올릴 근거가 갖춰졌다; 컬럼 이름 결정을 같은 항목에 적는다.
