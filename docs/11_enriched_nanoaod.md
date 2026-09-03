# 11 — Enriched NanoAOD (D17): 이론 · 레시피 · 검증 기록

> **목적**: MiniAODv2 를 입력으로 **중앙 생산과 동일한 NanoAOD 를 만들면서 확장 ttbar id 세 컬럼을 함께 넣는** 경로의 단일 참조 문서. 왜 그것이 "중앙과 동일"인지(이론), 정확히 어떤 명령인지(레시피), 무엇이 어디까지 증명됐는지(gate 와 증거), 그리고 그 과정에서 배운 검증 방법을 한 곳에 둔다.
> **대상 독자**: 이 경로로 샘플을 생산·검증하려는 사람; D17 을 DECIDED 로 올릴지 판단하는 사람.
> **상태**: 살아있는 문서. 마지막 갱신 **2026-09-02** — gate 1·2 CLOSED, gate 5 스키마 통과·값 비교 대기, gate 3·4 미착수.
> **관련**: 결정과 근거는 [04](04_decisions.md) D17 · D-DEP1 · D2, 인코딩 명세의 정본은 [02](02_physics.md) §3, 폐기됐던 첫 시도의 기록은 [10](10_enriched_nanoaod_archive.md), 비교 도구는 NtupleForge `script/compare_v9_v15.py`.

## 결론 먼저 (BLUF)

**되는 것이 실측으로 증명됐다.** 중앙 NanoAOD 생산에 쓰인 cmsDriver 원문을 DAS 에서 그대로 받아 `--customise` 하나만 덧붙이면, 출력은 **중앙과 이름·타입·값이 모두 같고 우리 컬럼 3 개만 더 있는** NanoAOD 가 된다. v9 에서 2000 event × 1666 branch = 3,332,000 개 값을 비트 단위로 비교해 **실질 불일치 0**. v15 에서도 같은 customise 가 그대로 동작하고(스키마 1903 + 3 = 1906, 타입 불일치 0), 값 비교만 남았다.

**새 C++ 은 한 줄도 쓰지 않았다.** 추가된 것은 python 파일 하나(`TtbarIdExtender/python/ttbarIdTable_cff.py`, 71 줄)이고, 그것도 릴리스가 `genTtbarId` 를 branch 로 내보내는 방식을 그대로 베낀 것이다. 2026-08-31 의 D17 원문이 "FlatTable producer 를 새로 작성해야 한다" 고 적었던 것은 **비용 추정이 틀린 것**이었다 — 전제(table 컬럼을 붙이는 물건이 없다)는 맞았지만 해법이 이미 릴리스 안에 있었다.

남은 것은 세 가지다. ① 71/72(tt+4b) 는 `TTbb` 2000 event 에 `nAddBJets>=4` 가 없어 아직 못 봤다 — `TT4b` 에서 본다. ② v15 값 비교. ③ CRAB `units_per_job` 산정 — v15 NANO 는 v9 보다 CPU 가 훨씬 비싸다.

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

두 가지 운영 규칙. ① **입력 MiniAOD 는 `/tmp` 로 `xrdcp` 한 뒤 `file:` 로 읽는다.** WAN 직독은 v9 에서 우연히 됐고 v15 에서 `exit=84` / `FileOpenError: Operation expired` 로 **18m53s 를 소모하고 죽었다**(CPU 3.4 s, 즉 전부 대기). MiniAOD 4.6 GB, `xrdcp` 3m9s. ② **grid proxy 를 job 전에 확인한다** — 위 실패의 1 차 원인은 전날 발급한 proxy 가 자정을 넘겨 만료된 것이었다.

---

## 3. Gate 와 증거

D17 을 DECIDED 로 올리는 데 필요한 조건을 gate 로 두고, 각각 무엇으로 증명됐는지 적는다.

| gate | 내용 | 상태 | 증거 |
|:---:|---|:---:|---|
| 1 | customise 로 컬럼이 top-level branch 로 나온다 | **CLOSED** 08-31 | §3.1 |
| 2 | 중앙 v9 와 이름·타입·**값**이 동일 | **CLOSED** 08-31 | §3.2 |
| 3 | 확장값 61/62/**71/72** 가 enriched 경로에서 옳다 | 61/62 만 확인 | §1.1; 71/72 는 `TT4b` 필요 |
| 4 | CRAB `units_per_job` 산정 (D15 상한) | 미착수 | §3.4 의 처리율이 입력 |
| 5 | v15(15_0_18)에서 동일 절차 | 스키마 통과, **값 대기** | §3.3 |

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

`PFMET_pt` 와 `Rho_fixedGridRhoFastjetAll` 이 존재한다 — v9 라면 `MET_pt` / `fixedGridRhoFastjetAll` 이어야 하므로 출력이 진짜 v15 스키마임을 스스로 증명한다. 값 비교 상대는 `e10ceebb-...` (overlap 200/200, `/tmp/central_ttbb_v15.root` 로 복사됨). 실행 대기:

```bash
python3 ~/CMSSW_14_2_1/src/NtupleForge/script/compare_v9_v15.py \
  --v9 /tmp/central_ttbb_v15.root \
  --v15 ~/TTHHGenCategoryTools_v15/CMSSW_15_0_18/src/enriched_v15_smoke.root \
  --prefix "" --ftol 0 --json /tmp/gate5_values.json
```

기대: only-in-ours 3, common 200, NaN census 에 `HTXS_Higgs_y` 200, 실질 불일치 0.

### 3.4 처리율 (gate 4 의 입력)

| | event | 시간 | Hz | 입력 |
|---|---:|---:|---:|---|
| v9 (10_6_32) | 2000 | 5m13.7s | **6.4** | WAN xrootd (I/O 지연 포함) |
| v15 (15_0_18) | 200 | 1m25.0s | **2.4** | 로컬 `/tmp` |

두 단서. ① v9 는 WAN 이라 I/O 가 섞였고 v15 는 로컬이다 — **CPU 격차는 2.7 배보다 크다.** ② 200 event 는 시동 비용(ParticleNet 모델 로딩, conditions) 비중이 커서 정상상태를 과소평가한다. **2000 event 이상으로 다시 재기 전에는 gate 4 에 쓰지 않는다.**

원인은 로그에 있다: 15_0_X NANO 는 MiniAOD 에서 **ParticleNetAK4 를 재계산**한다 (`Updating process to run ParticleNetAK4`, discriminator 34 개, b tagging 을 위해 JEC 를 되돌렸다 다시 적용). v9 에는 없던 작업이다. MiniAOD 는 NanoAOD 보다 파일 수가 훨씬 많으므로(2018 `TTbar_SemiLep` 10,010 파일 — [08](08_troubleshooting.md) T-19) D15 의 10,000 job 상한이 sidecar 때보다 먼저 물린다.

---

## 4. 검증 방법론 — 이 캠페인이 가르친 것

측정 자체보다 오래 남을 것은 **어떻게 재서 어떻게 믿었는가**다. 여섯 개.

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

---

## 5. 환경 · 운영 메모

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

1. **gate 5 값 비교** — §3.3 의 명령. 200 event 로 먼저, 2000 event 로 기록.
2. **gate 3 (71/72)** — `TT4b` MiniAOD 로 같은 절차. `TTbb` 2000 event 에는 `nAddBJets>=4` 가 0 건이라 원리적으로 불가능했다.
3. **gate 4** — 2000 event 이상의 v15 처리율로 `units_per_job` 산정. MiniAOD 파일 수 × ceil 이 D15 상한 10,000 을 넘지 않게. `--preflight --check-das` 가 이미 계산해 준다([08](08_troubleshooting.md) T-19).
4. **적용 순서** — `TT4b` → `TTHHto4b`(신호) → `TTZHTo4b`, `TTZZTo4b`, `tHW`, `TTZToBB`.
5. **NtupleForge 통합** — `job_type: cmsrun | postproc` 로 registry·das_scan·preflight·submit/status/report 재사용 (NtupleForge `01_STATUS` A6).

**열린 결정 — 컬럼 이름.** NanoAOD 컬럼은 현재 `expandedGenTtbarId`(camelCase, EDM instance 이름과 동일, `genTtbarId` 와 같은 관용)이다. 그런데 sidecar TTree 와 analyzer 계약([07](07_analyzer_integration.md))은 `Expanded_genTtbarId` 다. 6 샘플은 enriched, ttbar 3 종은 sidecar 이므로 **analyzer 가 두 이름을 다 알아야 한다.** NanoAOD 관용으로는 camelCase 가 맞고(`Expanded_` 는 `Jet_` 처럼 컬렉션 prefix 로 읽힌다), 계약 통일로는 `Expanded_genTtbarId` 가 맞다. 어느 쪽이든 **결정 후 D17 에 기록**한다. 지금 기본값은 camelCase.

**D17 상태.** 원문의 DECIDED 조건 5 개 중 ①(producer) ②(byte-identity) ⑤(15_0_X) 는 충족, ③(확장값)은 61/62 만, ④(CRAB 상한)은 미착수. 값 비교와 gate 3·4 가 끝나면 DECIDED 로 올릴 근거가 갖춰진다.
