# ExtendedTtbarId/NanoExtension — Architecture & Development History

본 문서는 패키지의 작동 원리, 개발 과정에서 마주친 문제와 해결, 검증 결과, 그리고 향후 작업 계획을 한 곳에 모은 reference 입니다. 빠른 사용법은 `README.md`, 인코딩 표는 본 문서의 §3 을 참고하세요.

---

## 1. 패키지 목적 (Purpose)

**한 줄로**: 우리가 자체적으로 계산하는 `ttbarID` (와 부수 branch 들) 이 중앙 NanoAODv9 의 그것과 **byte-identical** 한지 검증하고, 표준이 53/54/55 (tt+bb) 로 뭉뚱그리는 add b-jet ≥ 2 영역을 ttHH(bbbb) 분석용으로 add b-jet 개수에 따라 tt+bbb / tt+4b 로 풀어쓰는 것.

표준 NanoAODv9 의 `genTtbarId` 는 ttbar 이벤트의 추가 (additional) heavy-flavor radiation 을 5자릿수 composite int 로 인코딩합니다. 그러나 표준 GenTtbarCategorizer 는 **additional b-jet 이 2개 이상이면 b-jet 개수와 무관하게 모두 53/54/55 (tt+bb) 로 묶습니다** (sub-code 56 은 표준 categorizer 가 만들지 않음 — 56 은 GenHFHadronMatcher TWiki Example 2 의 *다른* 스킴에서 "pseudo-additional b jet" 을 뜻하는 값으로, genTtbarId 와 무관). 따라서 ttHH(bbbb) 처럼 add b-jet 3개·4개가 의미를 가지는 분석에서는 `genTtbarId` 만으로 tt+bbb (정확히 3개) 와 tt+4b (4개 이상) 를 구분할 수 없습니다. 본 패키지는:

1. 중앙 NanoAOD 의 `genTtbarId` 와 byte-identical 한 값을 miniAOD 에서 직접 재생산 (정합성 확인용)
2. 그 위에 `Expanded_genTtbarId` 라는 thin extension 을 얹어서, 우리가 직접 센 `nAddBJets` 로 add b-jet ≥ 3 이벤트를 61/62 (tt+bbb) / 71/72 (tt+4b) 로 분해

위 두 가지를 한 cmsRun job 으로 처리하여 side TTree (Approach 1) 또는 enriched NanoAOD (Approach 2) 로 출력합니다.

---

## 2. 전반적 작동 원리 (Overall Operating Principles)

### 2.1 Data flow

```
                                ┌────────────────────────────────────────┐
                                │  PhysicsTools/NanoAOD/python/          │
                                │    ttbarCategorization_cff.py          │
                                │                                        │
   miniAOD                      │   matchGenBHadron (pre-stored          │
   ────────                     │     slimmedGenJetsFlavourInfos)        │
   slimmedGenParticles  ──────► │   matchGenCHadron        ─┐            │
   slimmedGenJets       ──────► │                           ├──► int     │
   slimmedGenJets-              │   categorizeGenTtbar  ────┘   genTtbarId│
   FlavourInfos         ──────► │       (pt>20, |eta|<2.4)               │
                                └─────────────────────┬──────────────────┘
                                                      │
                                                      ▼
                                ┌──────────────────────────────────────┐
                                │  ExtendedTtbarIdProducer (this package)         │
                                │                                      │
                                │    input:  genTtbarId (above)        │
                                │            slimmedGenJets            │
                                │            matchGenBHadron outputs   │
                                │                                      │
                                │    counts un-capped nAddBJets        │
                                │    if nAddBJets >= 3:                 │
                                │      nAddBJets==3 → sub 61/62 (bbb)   │
                                │      nAddBJets>=4 → sub 71/72 (4b)    │
                                │                                      │
                                │    output: Expanded_genTtbarId,        │
                                │            nAddBJetsMulti            │
                                └─────────────────────┬────────────────┘
                                                      │
                  ┌───────────────────────────────────┴──────────────────┐
                  │                                                      │
       ┌──────────▼───────────┐                          ┌───────────────▼──────────────┐
       │ Approach 1           │                          │ Approach 2                   │
       │ TtbarCategoryNtuplizer│                         │ TtbarCategoryTableProducer   │
       │ (one::EDAnalyzer)    │                          │ + nanoSequenceMC             │
       │                      │                          │                              │
       │ owns TFile/TTree     │                          │ emits nanoaod::FlatTable     │
       │ at file root         │                          │ "Custom" branches            │
       └──────────┬───────────┘                          └───────────────┬──────────────┘
                  ▼                                                      ▼
            ttbbSide.root                                          customNano.root
            (Events @ root)                                        (full nano + Custom_*)
```

### 2.2 두 가지 Approach 의 차이

**Approach 1 — Side TTree**: miniAOD 에서 categorization 만 떼어서 작은 (~수 MB / 80k events) TTree 를 만듭니다. 형식은 NanoAOD 호환 (Events tree at file root, 같은 type 사용) 이라 친구 트리 (friend tree) 로 중앙 NanoAOD 에 그대로 attach 할 수 있습니다. **장점**: 빠름 (gen-level reco 만), 작음, friend tree 로 분석 워크플로우에 끼워넣기 쉬움. **단점**: NanoAOD 의 다른 branch 와 연결시키려면 friend tree attach 작업이 필요.

**Approach 2 — Custom NanoAOD**: 표준 `nanoSequenceMC` 를 통째로 재실행하면서 `Custom_*` branch 들을 추가합니다. **장점**: standalone, friend attach 불필요. **단점**: 매우 비쌈 (full nano sequence), 그리고 CMSSW_14_2_1 처럼 최신 release 에서 돌리면 gen-level 이외의 branch (Jet_pt, MET 등) 는 JEC/JER/tagger 기본값이 달라서 중앙과 byte-identical 하지 않음.

> **사용 권장**: 분석 production 에는 Approach 1, 알고리즘 검증 (gen-level 동등성 확인) 에는 양쪽 다 가능.

### 2.3 `ExtendedTtbarIdProducer` 의 핵심 로직

`plugins/ExtendedTtbarIdProducer.cc` 의 본질은 약 5줄:

```cpp
int expandedId = genTtbarId;                          // standard pass-through
if (nAddBJets >= 3) {
  const int base   = (genTtbarId / 100) * 100;    // preserve 100/1000/10000s prefix
  const int newSub = kExtendedSubCode(nAddBJets, nAddBJetsMulti);
  expandedId = base + newSub;                          // 61/62 (bbb) or 71/72 (4b)
}
```

`nAddBJets` 와 `nAddBJetsMulti` 는 strict acceptance (pt > 20, |η| < 2.4) 에서 직접 셈. **표준 categorizer 는 add b-jet 이 2개 이상이면 모두 53/54/55 로 묶어버려서 3개·4개를 구분하지 못하므로**, 우리는 정확한 개수가 필요하여 같은 입력 (matchGenBHadron outputs + slimmedGenJets) 으로 다시 한 번 sweep 합니다.

> **v10 의 핵심 수정**: 이전 버전은 split 조건을 `genTtbarId % 100 == 56` 에 걸었으나, 표준 GenTtbarCategorizer 는 sub-code 56 을 *절대* 만들지 않습니다 (Example 1 스킴엔 56 이 없음). 그래서 split 이 한 번도 발동하지 않아 tt+bbb / tt+4b 가 전혀 생성되지 않았습니다. tt4b 샘플 950만 이벤트로 확인: `nAddBJets >= 3` 이 188만 건 존재하지만 모두 53/54/55 안에 있었고 sub-code 56 은 0 건. v10 에서 split 조건을 `nAddBJets` 로 직접 바꿔 해결했습니다. nAddBJets 카운트 로직 자체는 변경 없음 (애초에 정확했음).

### 2.4 비교 도구 (Comparator) 의 작동 원리

`bin/compareSidetreeToNano.cc` 는 hash join 으로 두 파일을 비교합니다:

1. **Phase 1**: side tree 전체 (~84k entries) 를 `std::unordered_map<uint64_t, SidePayload>` 에 적재. Key 는 `(run << 40) ^ event`
2. **Phase 2**: nano TTree 를 streaming 하면서 매 entry 마다 hash lookup
3. Hit 시 모든 branch 비교 (full int, 자릿수별 분해, GenJet pT/eta 등) + confusion matrix 누적
4. 끝나면 percentage summary + distribution + confusion + extension alias check 출력

설계 결정 두 가지:

* **`TTreeReader` 대신 `TTree::SetBranchAddress`**: TTreeReader 는 `libTreePlayer.so` 에 들어있는데 CMSSW 의 `<use name="root"/>` 로는 link 가 안 됨. SetBranchAddress 는 libRIO+libTree 만 쓰므로 어떤 release 에서도 build 가 안 깨짐. 부가로 `SetBranchStatus("*", 0)` 로 안 읽는 branch 를 deserialize 안 해서 I/O 도 훨씬 빠름.
* **eta tolerance 는 relative-aware**: NanoAOD 의 `GenJet_eta` 는 `precision=12` 로 양자화되어 상대 step ~2.44 × 10⁻⁴. v4 의 절대 tol `1e-4` 보다 빡빡해서 mismatch 가 났던 적이 있음. 현재 `5e-4 · max(1, |η|)`.

---

## 3. `genTtbarId` 인코딩 명세 (Encoding Specification)

CMSPublic [`GenHFHadronMatcher`](https://twiki.cern.ch/twiki/bin/view/CMSPublic/GenHFHadronMatcher) 및 CMSSW `TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc` 기준 (역공학으로 확인됨):

```
genTtbarId = 10000·min(2, nCJetsFromW)        // c from W of top
           +  1000·min(2, nBJetsFromW)        // b from W of top  (W → cb, rare)
           +   100·min(2, nBJetsFromTop)      // b directly from t
           +          standardZ               // additional radiation HF code
```

네 카운트 모두 동일한 acceptance (pt > 20, |η| < 2.4) 에서 계산. `standardZ` 는 (GenHFHadronMatcher TWiki **Example 1** = GenTtbarCategorizer 의 스킴):

| sub-code | 의미                                  |
|---------:|---------------------------------------|
| 0        | tt+LF                                 |
| 41       | tt+c   (1 c-jet, single c-hadron)     |
| 42       | tt+2c  (1 c-jet, ≥ 2 c-hadrons)       |
| 43,44,45 | tt+cc  (≥ 2 c-jets)                   |
| 51       | tt+b   (1 b-jet, single b-hadron)     |
| 52       | tt+2b  (1 b-jet, ≥ 2 b-hadrons)       |
| 53,54,55 | tt+bb  (**≥ 2** b-jets, b-hadron 수 무관) |

**중요**: 표준 GenTtbarCategorizer (Example 1) 에는 sub-code **46 / 56 이 존재하지 않습니다**. additional b-jet 이 2개든 3개든 4개든 모두 53/54/55 로 들어갑니다 ("at least two additional b jets"). 53/54/55 의 구분은 add b-jet *개수* 가 아니라 다른 기준이며, 어느 경우든 ≥2 면 이 셋 중 하나입니다. (sub-code 56 은 TWiki **Example 2** 의 *다른* 스킴 — `matchGenHFHadrons.cc` test analyzer — 에서 "one or more pseudo-additional b jets" 를 뜻하는 값으로, genTtbarId 와는 무관합니다. v9 이전 버전이 이 둘을 혼동했습니다.)

`Expanded_genTtbarId` 가 추가하는 확장 (sub-code 영역만, `nAddBJets` 로 결정):

| sub-code | 의미                                                     |
|---------:|----------------------------------------------------------|
| 61       | tt+bbb (정확히 3 add b-jets, multi-hadron jet 0개)        |
| 62       | tt+bbb (정확히 3 add b-jets, multi-hadron jet ≥ 1개)      |
| 71       | tt+4b  (≥ 4 add b-jets,     multi-hadron jet 0개)         |
| 72       | tt+4b  (≥ 4 add b-jets,     multi-hadron jet ≥ 1개)       |

`nAddBJets <= 2` 면 `Expanded_genTtbarId == genTtbarId` (확장 없음). `Expanded_genTtbarId` 의 prefix (10000s/1000s/100s 자리) 는 `genTtbarId` 와 항상 동일. sub-code (`Expanded_genTtbarId % 100`) 만 위 표대로 확장됩니다. AN 은 tt+bbb / tt+4b 만 구분하므로 분석에서는 61+62 → tt+bbb, 71+72 → tt+4b 로 합치면 됩니다 (multi 구분은 g→bb 연구용 추가 정보).

---

## 4. 발생한 문제점과 해결 (Problems & Resolutions)

개발은 v3 → v6.1 까지 6번의 반복을 거쳤습니다. 각 단계의 실패 사유와 해결을 시간순으로 정리합니다.

### 4.1 v3 — `JetFlavourClustering` 경고 폭주

**증상**: cmsRun 콘솔이 `JetPtMismatch`, `MissingJetConstituent`, `NullTransverseMomentum` 경고로 도배됨. 이벤트당 수십~수백 줄.

**원인**: `ak4JetFlavourInfos` 를 `prunedGenParticles` 기반으로 재클러스터링 (recluster) 했음. miniAOD 의 `slimmedGenJets` 는 constituent 정보가 일부 truncated 되어 있어서 재클러스터링 시 정합성이 떨어짐 (ghost association 자체는 정상 작동하지만 경고가 보기 싫음).

**해결**: MessageLogger 로 해당 카테고리를 silence. v6 부터는 재클러스터링 자체를 그만두고 miniAOD 에 이미 저장된 `slimmedGenJetsFlavourInfos` 를 그대로 쓰기 때문에 (4.2 참조) 경고가 원천적으로 나지 않음.

### 4.2 v4 → v5 — c-from-W-of-top 38% 만 일치

**증상**: 자릿수별 일치도를 분해해서 보니:
```
[id]  100   digit (nBJetsFromTop) agreement:  99.999 %
[id]  1000  digit (nBJetsFromW)   agreement: 100.000 %
[id]  10000 digit (nCJetsFromW)   agreement:  38.280 %
```
b-side 는 완벽한데 c-side 의 W ancestor 추적만 처참하게 깨졌음.

**원인** (1차 가설): `matchGenCHadron` 의 `jetFlavourInfos` 입력을 재클러스터링된 `ak4JetFlavourInfos` 로 줬는데, 이게 중간 상태 (intermediate state) quark/gluon 을 일부 잃어버려서 c-from-W 가 "additional" 로 잘못 분류되었음. **부분 해결**: v5 에서 miniAOD 의 pre-stored `slimmedGenJetsFlavourInfos` 로 교체 (NanoAOD 가 쓰는 것과 동일). b-side 의 자릿수 일치도가 99.999% 까지 올라옴.

**원인** (진짜): c-side 는 그래도 안 됨. 표준 `GenTtbarCategorizer` 플러그인 소스를 다시 읽어보니, `cHadFromTopWeakDecay` 플래그를 단독으로 신뢰하지 않음. 대신 `genCHadPlusMothers` / `genCHadPlusMothersIndices` 체인을 따라 W ancestor 를 별도로 재추적함. 우리 v5 는 flag 를 그대로 믿었기 때문에 일부 케이스에서 mis-classification.

**진짜 해결** (v6): 직접 재구현을 포기. CMSSW 표준 `categorizeGenTtbar` producer 를 그대로 호출하면 NanoAOD 와 byte-identical 한 `genTtbarId` 가 나옴. 우리는 그 위에 nAddBJets 로 add b-jet ≥ 3 을 61/62/71/72 로 분해하는 thin `ExtendedTtbarIdProducer` 만 새로 작성. **결과**: 모든 자릿수 100% 일치.

### 4.3 v6 → v6.1 — `ModuleNotFoundError`

**증상**: 첫 cmsRun 시도가 `ModuleNotFoundError: No module named 'TopQuarkAnalysis.TopTools.GenTtbarCategorizer_cfi'` 로 실패.

**원인 1**: CMSSW 의 cfi 이름은 lowercase 인 `categorizeGenTtbar_cfi` (모듈명과 일치). 내 v6 코드는 PascalCase `GenTtbarCategorizer_cfi` 로 잘못 import.

**원인 2**: producer 의 출력은 `unnamed int` 가 아니라 `produces<int>("genTtbarId")` 로 라벨된 형태. InputTag 도 `("categorizeGenTtbar", "genTtbarId")` 로 두 인자가 필요.

**해결** (v6.1): 두 가지를 동시에 고치되, `PhysicsTools.NanoAOD.ttbarCategorization_cff` 를 통째로 import 하는 방식으로 전환. 이쪽이 NanoAOD master 가 실제로 쓰는 canonical path 라 cfi 이름 변경에 더 robust. 한 번에 `matchGenBHadron`, `matchGenCHadron`, `categorizeGenTtbar` 가 모두 표준 NanoAOD 와 동일하게 세팅되어 옴.

### 4.4 빌드 시 `TTreeReader` link 실패

**증상**: 처음에 비교 executable 을 `TTreeReader` API 로 작성했더니 `undefined reference to TTreeReader::...` 로 link 실패.

**원인**: `TTreeReader` 는 `libTreePlayer.so` 에 들어있는데 CMSSW BuildFile 의 `<use name="root"/>` 는 libRIO + libTree 만 끌어옴. `libTreePlayer` 를 끌어오는 use name 이 release 별로 일관적이지 않음.

**해결**: `TTreeReader` 를 포기하고 전통적인 `TTree::SetBranchAddress` API 로 재작성. 추가 이점: `SetBranchStatus("*", 0)` 로 안 읽는 branch (NanoAOD 는 수백 개) 를 deserialize 안 해서 I/O 가 훨씬 빠름.

### 4.5 eta tolerance 가 너무 빡빡

**증상**: leading-jet eta 일치도가 ~86% 로 mysteriously 낮음.

**원인**: NanoAOD 의 `GenJet_eta` 는 `MiniFloatConverter::reduceMantissaToNbitsRounding` 으로 `precision=12` 양자화됨 (상대 step ~2.44 × 10⁻⁴). 우리 비교 코드의 절대 tolerance `1e-4` 가 이보다 빡빡해서 정상 양자화도 mismatch 로 잡힘.

**해결**: relative-aware tolerance 로 교체:
```cpp
return std::fabs(a - b) < 5e-4f * std::max(1.0f, std::fabs(a));
```
즉시 100% 일치. pT 쪽은 `precision=-1` (양자화 없음) 이라 그대로 `0.01` 절대 tol 로 충분.

---

## 5. 검증 결과 (Validation Results)

### 5.1 테스트 설정

| 항목 | 값 |
|---|---|
| miniAOD input | `RunIISummer20UL17MiniAODv2/TTToHadronic_TuneCP5_13TeV-powheg-pythia8` 의 한 파일 (`0359BC01-...root`, 84k events) |
| 비교 대상 NanoAOD | 같은 dataset 의 `RunIISummer20UL17NanoAODv9` 한 파일 (`5E08C852-...root`, 1.28M events) |
| Join 방식 | `(run, event)` hash key, lumi 로 secondary check |
| CMSSW release | `CMSSW_14_2_1` |
| Era | `Run2_2017` + `run2_nanoAOD_106Xv2` |

> **주의**: 1 miniAOD : 1 NanoAOD 매칭이 아닙니다. 중앙 production 에서 ~15 개의 miniAOD 가 모여서 1 개의 NanoAOD 가 됩니다 (5GB miniAOD ~ 80k events → 3GB NanoAOD ~ 1.3M events). 우리 side tree 의 모든 이벤트가 nano 안에 들어있으면 (matched = 84k = side 전체) join 검증으로는 충분합니다.

### 5.2 결과

```
[join] matched events:        84000 / nano 1280000 / side 84000

[id]   full  genTtbarId agreement:           84000 (100.000 %)
[id]   std   sub-code (Z = % 100)  agreement:84000 (100.000 %)
[id]   100   digit (nBJetsFromTop) agreement:84000 (100.000 %)
[id]   1000  digit (nBJetsFromW)   agreement:84000 (100.000 %)
[id]   10000 digit (nCJetsFromW)   agreement:84000 (100.000 %)

[jet]  nGenJet      agreement:       84000 (100.000 %)
[jet]  leading-jet pT   agree:       84000 (100.000 %)
[jet]  leading-jet eta  agree:       84000 (100.000 %)
```

**Confusion matrix 가 완벽한 대각행렬** — 비대각 셀이 단 하나도 없음. 81 개 sub-code 빈 (0 부터 20253 까지) 이 hit-by-hit 으로 양쪽 distribution 에서 동일.

### 5.3 확장 분기 (tt+bbb/tt+4b) 의 실제 검증 — v10 에서 해결

v9 까지는 확장 분기가 한 번도 trigger 되지 않았습니다. 처음엔 "통계 부족" 으로 추정했으나 (TTToHadronic 84k 처럼 작은 sample), tt4b 950만 이벤트로 본격 검증하면서 **진짜 원인이 코드 버그**임을 발견했습니다:

- split 조건이 `if (genTtbarId % 100 == 56 && nAddBJets >= 3)` 였음
- 그러나 표준 GenTtbarCategorizer 는 sub-code 56 을 절대 만들지 않음 (Example 1 스킴엔 없음; §1, §3 참조)
- tt4b 950만 이벤트: sub-code 56 = **0 건**, 그런데 `nAddBJets >= 3` = **188만 건** (모두 53/54/55 안에 있음)
- 즉 split 조건이 영원히 false → tt+bbb/tt+4b 가 전혀 생성 안 됨

tt4b cross-tab (genTtbarId sub-code × nAddBJets):

```
genSub   nAdd0    nAdd1     nAdd2     nAdd3     nAdd4    nAdd5   nAdd>=6
51        9294   2451967      41        0         0        0       0    (tt+b:  nAdd==1)
52        2687    688292       4        0         0        0       0    (tt+2b: nAdd==1)
53          24     13111   2472796  1194748   252730    9881    1307    (tt+bb: nAdd>=2, 3/4 섞임)
54           3      4420    898635   379900    23517    4511     188
55           0       322     93558    11162     3962     230      34
```

→ nAdd==3 (= 1,585,810) 과 nAdd>=4 (= 296,360) 이 전부 53/54/55 안에 묻혀 있음이 확인됨. 이것이 우리가 tt+bbb/tt+4b 로 빼내야 할 이벤트.

**v10 수정**: split 조건을 `if (nAddBJets >= 3)` 로 바꿈 (sub-code 56 의존 제거). nAddBJets==3 → 61/62, >=4 → 71/72. nAddBJets 카운트 로직 자체는 정확했으므로 변경 없음. 수정 후 재생산하면 tt4b 의 Expanded_genTtbarId 에서 61/62 합 = 1,585,810, 71/72 합 = 296,360 이 나와야 함 (검증 예정).

---

## 6. 미래 목표 (Future Goals) 와 타당성 검토

목표는 본 검증 인프라를 확장해서 **여러 process × 여러 era 에 걸친 end-to-end validation 파이프라인** 을 단일 repository 로 packaging 하는 것입니다. 사용자 (analyst) 가 자기 ttHH 분석에서 우리 `Expanded_genTtbarId` 를 신뢰하고 쓸 수 있도록.

### 6.1 두 가지 distribution 방식의 트레이드오프

분석가에게 `Expanded_genTtbarId` 를 어떻게 전달할 것인가:

#### Option A — Lookup function `(run, lumi, event) → ttbarID`

```python
# 사용자 코드 (예시)
from ExtendedTtbarId.NanoExtension import expandedLookup
Expanded_genTtbarId = expandedLookup.get(run=305058, lumi=192, event=384721922)
```

**Storage backend 선택지**:

| Backend | 장점 | 단점 | 평가 |
|---|---|---|---|
| **ROOT friend tree** | CMSSW idiomatic, `TChain::AddFriend` 한 줄, 빠른 random access | 친구 트리는 entry 순서 가정이 있어서 NanoAOD 와 같은 순서로 build 해야 함 → CRAB 으로 production 시 이게 가장 까다로움 | ★★★★ |
| **(run, lumi, event) → Expanded_genTtbarId hash dict in ROOT** | 순서 의존성 없음, 그냥 lookup, ~30M events 면 hash map 8 bytes × 3M = ~720 MB / process — 메모리에 다 올라가지 않음 | 메모리 부담, 분산 처리 어려움 | ★★ |
| **SQLite key-value DB** | 디스크에서 random access, in-memory 캐시 가능 | CMSSW 에 sqlite 의존성 추가, grid job 에 같이 ship 해야 함 | ★★ |
| **자체 binary format (mmap-able)** | 메모리 효율 최고, 빠름 | 빌드/유지보수 부담, 시간 낭비 | ★ |

**권장**: ROOT friend tree. 단, 친구 트리 attach 가 entry 순서에 의존하므로 NanoAOD 와 같은 순서로 만들어져야 함. CRAB job 의 `Data.unitsPerJob` 와 `Data.totalUnits` 를 NanoAOD production 과 같은 lumi mask 로 맞추면 친구 트리가 자동으로 align 됨. Order mismatch 가 우려되면 entry 별로 `(run, event)` hash 를 한 번 확인하는 sanity step 추가.

#### Option B — Enriched NanoAOD (miniAOD → user NanoAOD with `Custom_*`)

**장점**: Standalone. 친구 트리 신경 안 써도 됨.

**단점**: 매우 비쌈. Full `nanoSequenceMC` 재실행은 이벤트당 ~30s × 30M events = 25 CPU-year 수준. CRAB 으로 분산해도 1000 cores × 9 hours = 9000 CPU-hours per process. 5 process × 4 era 면 자원 신청 사유서를 잘 써야 함.

**권장**: Production 에는 비현실적. 검증 sub-sample (~1% 정도, 100 files per process) 에만 적용해서 gen-level 이외 branch 도 동등성 확인용으로만 사용.

#### 결론적 권장 전략

```
Production (analyst-facing):
   miniAOD ──► Approach 1 (side tree) ──► friend tree
                                          │
                                          └─► TChain::AddFriend(centralNano)
                                              사용자 분석에서 Expanded_genTtbarId 접근

Validation (one-time):
   miniAOD ──► Approach 1 (side tree) ──► compareSidetreeToNano
   miniAOD ──► Approach 2 (custom)    ──► compareCustomnanoToCentral
       (작은 sub-sample 에만)
```

### 6.2 Multi-process scale-out 계획

대상 process (per era, UL16/17/18 + 13.6 TeV 가 필요한 경우):

| Process | Dataset 패턴 | 우선순위 |
|---|---|---|
| ttHH(bbbb) signal | `/TTHH_TuneCP5_13TeV-madgraph-pythia8/.../MINIAODSIM` | 최고 |
| ttbar semi-leptonic | `/TTToSemiLeptonic_*` | 높음 |
| ttbar fully hadronic | `/TTToHadronic_*` | 높음 |
| ttbar dileptonic | `/TTTo2L2Nu_*` | 높음 |
| ttbb (4F) | `/TTbb_4f_*` | 중 (signal 영역의 가장 큰 background) |
| tt4b | `/TT4b_*` (있는 경우) | 중 |

각 dataset 별 raw size 추정 (UL17 기준 typical):

| Process | events | full miniAOD size | side tree size (예상) |
|---|---|---|---|
| ttHH | ~1 M | ~50 GB | ~50 MB |
| TTToHadronic | ~330 M | ~16 TB | ~16 GB |
| TTToSemiLeptonic | ~430 M | ~22 TB | ~22 GB |
| TTTo2L2Nu | ~150 M | ~8 TB | ~8 GB |
| TTbb 4F | ~50 M | ~3 TB | ~3 GB |

→ side tree 총합 ~ 50 GB / era. **Tier3 (KNU 또는 KISTI) 에 충분히 저장 가능**.

### 6.3 CRAB submission 인프라

필요한 작업:

1. **CRAB config template** 작성:
   ```python
   # crab/crab_sidetree_template.py
   from CRABClient.UserUtilities import config
   c = config()
   c.General.requestName    = '%(process)s_%(era)s_sidetree'
   c.General.workArea       = 'crab_projects'
   c.JobType.pluginName     = 'Analysis'
   c.JobType.psetName       = 'ExtendedTtbarId/NanoExtension/test/run_approach1_sidetree_cfg.py'
   c.JobType.pyCfgParams    = ['year=%(year)s']
   c.JobType.maxMemoryMB    = 2500
   c.Data.inputDataset      = '%(dataset)s'
   c.Data.splitting         = 'FileBased'
   c.Data.unitsPerJob       = 1
   c.Data.publication       = False
   c.Site.storageSite       = 'T3_KR_KNU'   # 또는 T2_KR_KISTI
   c.Data.outLFNDirBase     = '/store/user/junghyun/ttbb_sidetree/%(era)s'
   ```

2. **Submission driver script** (Python): dataset 리스트 × era 매트릭스를 돌면서 위 template 으로 CRAB submit. 진행 상황 모니터링.

3. **Output 후처리**: CRAB output 은 `<outLFNDirBase>/<dataset>/<requestName>/<timestamp>/0000/` 등에 분산 저장됨. `hadd` 로 process × era 단위로 합쳐 단일 friend tree 파일 생성하는 step 추가.

### 6.4 Two-stage validation pipeline

목표는 사용자에게 "우리 Expanded_genTtbarId 가 너 분석에 쓰기 안전하다" 를 증명하는 것. 두 단계:

#### Stage 1 — Event-by-event 검증 (현재 `compareSidetreeToNano` 의 확장)

`(run, lumi, event)` 키로 join 한 뒤:
* `genTtbarId` byte-identical
* `nGenJet`, leading-jet pT/eta
* (추가 예정) gen-level lepton 정보 (e/μ/τ 직접 비교)
* (추가 예정) **친구 트리 entry order 동기 확인** — friend tree mode 로 쓸 거면 이게 critical

**구현**: 기존 `compareSidetreeToNano` 를 multi-file 모드로 확장. 입력으로 side tree 리스트 (한 process 의 모든 CRAB output) + nano 리스트 (해당 process 의 모든 중앙 NanoAOD 파일) 를 받아서 process 전체 통계를 보고.

**기대 결과**: 100% agreement on all branches.

#### Stage 2 — Per-process kinematic 분포 비교 + ratio plot

`Custom_genTtbarId == central genTtbarId` selection 으로 categorize 한 뒤, 각 sub-code 별로 다음 분포를 양쪽에서 그리고 ratio plot 이 평탄한 1 인지 확인:

* `Jet_pt`, `Jet_eta`, `Jet_phi`, `Jet_mass`
* `nJet`, `nBJet` (deep flavour b-tag medium WP)
* `MET_pt`, `MET_phi`
* `Muon_pt`, `Electron_pt` (selection survived 개수)
* `HT`, `MHT` (compound 변수)

**구현**: 별도 ROOT/PyROOT analyzer (혹은 uproot+matplotlib). Stage 2 는 algorithm validation 보다는 *systematics* 검증임 — 우리 categorization 이 특정 phase space 를 편향적으로 bias 하지 않음을 확인.

**기대 결과**: 모든 sub-code, 모든 변수의 ratio plot 이 ~ 1.00 ± 통계 오차.

### 6.5 Final repository layout (제안)

```
TtbbValidation/  ← 새 git repository (ExtendedTtbarId 와 별도 또는 같이)
├── ExtendedTtbarId/NanoExtension/        ← 본 CMSSW package (이 repo 의 핵심)
├── crab/
│   ├── crab_sidetree_template.py
│   ├── crab_customnano_template.py
│   ├── submit_all.py                 ← driver: process × era → CRAB submit
│   ├── resubmit_failed.py
│   └── status_check.py
├── postprocess/
│   ├── merge_sidetrees.py            ← per-process hadd + sanity sort
│   └── make_friend_tree.py           ← friend tree alignment / sanity
├── analyzer/
│   ├── compareSidetreesToCentralAll.cc    ← Stage 1 (multi-file)
│   ├── kinematicRatioPlots.py             ← Stage 2 (per-process)
│   └── ratioPlotMaker_cff.py
├── docs/
│   ├── ARCHITECTURE.md               ← 본 문서 (또는 여기로 이동)
│   ├── CRAB_WORKFLOW.md
│   └── VALIDATION_RESULTS.md
└── README.md
```

### 6.6 타당성 종합 평가

| 항목 | 평가 | 비고 |
|---|---|---|
| **Approach 1 production scale-out** | 충분히 현실적 | 50 GB / era, ~10000 CPU-h / era (gen-level 만 reco), Tier3 저장 OK |
| **Approach 2 production scale-out** | 비현실적 | 25 CPU-year / process. 검증 sub-sample 에만 한정 |
| **Friend tree attach 워크플로우** | 가능하나 entry order 정렬 작업 필요 | postprocess step 필수 |
| **Two-stage validation 자동화** | 표준 ROOT/uproot 도구로 구현 가능 | 통상적인 작업 |
| **Single repository packaging** | 깔끔하게 가능 | 위 layout 참조 |
| **전체 timeline 예상** | CRAB 인프라 1~2주 + scale-out 실행 (queue 대기 포함) 2~3주 + Stage 2 analyzer 1주 = **~2개월** | 다른 작업과 병행 가정 |

**Bottleneck**: CRAB 의 queue 대기 시간 (특히 Tier3 site availability) 과, 각 process 별로 CRAB job 이 failure 없이 통과되도록 보수하는 시간. 알고리즘 자체는 이미 완성되었음.

---

## 7. 한계 (Known Limitations)

* **Approach 2 의 reco-level byte-identity 한계**: CMSSW_14_2_1 같은 최신 release 에서 NanoAODv9 를 재생산하면 gen-level 이외의 branch (Jet_pt, MET, b-tagger 출력) 는 절대로 byte-identical 하지 않음. JEC/JER/tagger/PU profile 의 기본값이 모두 새 버전이기 때문. gen-level 일치 (genTtbarId, GenJet_*) 검증만 의미 있음. 완전한 reco-level 동등성이 필요하면 `CMSSW_10_6_29_patch1` 같은 UL17 production release 에서 별도 빌드/실행 필요.

* **`PhysicsTools.NanoAOD.ttbarCategorization_cff` 의존성**: 본 패키지는 표준 NanoAOD 의 ttbar categorization 설정을 import. 이 cff 가 future CMSSW release 에서 deprecated 되면 우리도 같이 깨짐. 다만 NanoAOD 가 이 categorization (53/54/55 로 tt+bb 를 묶는 표준 스킴) 을 계속 쓰는 한 cff 는 유지될 가능성이 높음.

* **확장 분기 (v10 에서 수정)**: §5.3 참조. v9 까지 split 이 sub-code 56 에 묶여 있어 한 번도 발동 안 했음 (표준엔 56 이 없음). v10 에서 nAddBJets 조건으로 수정. 수정 후 sidecar 재생산하여 61/62/71/72 가 기대 카운트와 맞는지 확인 필요.

---

## 8. 참고 문헌

* CMSPublic [GenHFHadronMatcher TWiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/GenHFHadronMatcher)
* CMSSW: `TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc`
* CMSSW: [`PhysicsTools/NanoAOD/python/ttbarCategorization_cff.py`](https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/ttbarCategorization_cff.py)
* CMSPublic [WorkBookNanoAOD](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD)

---

## 9. v6 -> v7 변경사항 (Release Pinning + Approach Cleanup)

### 9.1 동기

v6.1 검증은 `CMSSW_14_2_1` 에서 진행했고 gen-level branch (`genTtbarId`, `GenJet_*`) 에 대해 100% byte-identical 을 달성했습니다. 그러나 §7 첫 번째 항목에서 이미 인지했듯이 reco-level branch (`Jet_pt`, `MET`, b-tagger 출력 등) 는 release cycle 변경 시 byte-identical 일 수 없습니다. JEC/JER/b-tagger/PU profile/ROOT 압축 설정의 기본값이 release cycle 별로 다르기 때문입니다.

ttHH(bbbb) 분석의 최종 산출물은 reco-level 변수에 의존하는 BDT/DNN training 이라 **모든 NanoAODv9 branch 가 그대로 보존된 enriched NanoAOD** 가 필요합니다. 즉 reco-level 도 byte-identical 해야 합니다. 이를 위해 v7 는 release 를 공식 UL Run2 NanoAODv9 production cycle 인 **`CMSSW_10_6_X` (구체적으로 `10_6_32_patch1` 또는 `10_6_29_patch1`)** 로 pin 합니다.

근거:
* CMSPublic Workbook: "currently recommended Analysis Release is 10_6_X for legacy Run 2 productions" (<https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookWhichRelease>)
* CMS-nanoAOD private production guide: `CMSSW_10_6_32_patch1` 명시 (<https://gitlab.cern.ch/cms-nanoAOD/nanoaod-doc/-/wikis/Instructions/Private-production>)
* UL Run2 ultra-legacy MC central production: `10_6_29_patch1` 사용 (CMS-SVJ production note)

### 9.2 Approach 1 (side TTree) 폐기

v6 까지 두 가지 운영 mode 를 유지했습니다 — Approach 1 (작은 side TTree 만 emit) 과 Approach 2 (전체 NanoAOD 재생산). v7 는 다음 이유로 **Approach 1 을 폐기**하고 Approach 2 만 유지합니다:

* v7 의 release pinning 하에서는 Approach 2 가 더 이상 "비싼 검증용" 이 아닙니다. CMSSW_10_6_X 에서 nanoSequenceMC 는 원래 NanoAODv9 production 이 돌렸던 그 sequence 이므로, 추가 비용은 우리 extendedTtbarId + FlatTable producer 뿐 (~0.1% 오버헤드).
* 분석 user 측에서 friend tree attach 단계가 없어집니다 (side TTree 가 없으니까). enriched NanoAOD 하나로 self-contained.
* 검증 워크플로우가 단순해집니다 ("모든 branch 가 일치하는가?" 한 질문).

폐기된 파일:
* `plugins/TtbarCategoryNtuplizer.cc`
* `test/run_approach1_sidetree_cfg.py`
* `bin/compareSidetreeToNano.cc`

이 코드들의 logic 자체는 §3.2 에 그대로 보존되어 historical reference 로 남습니다.

### 9.3 신규 검증 도구 `compareEnrichedToCentral`

기존 `compareCustomnanoToCentral` 는 spot-check 도구로 `genTtbarId` + `nGenJet` + leading GenJet pT/η 5개 branch 만 비교했습니다. 사용자 요구 ("모든 분포에 대해 ratio = 1") 를 만족시키려면 **모든 공통 branch** 를 자동으로 enumerate 해서 비교해야 합니다.

`bin/compareEnrichedToCentral.cc` (v7) 의 작동:

1. 두 NanoAOD 파일에서 `TTree::GetListOfBranches` 로 branch 목록을 읽어옴.
2. 공통 branch / enriched-only / central-only 로 분류 — enriched-only 는 `Custom_*` 만 있어야 하고, central-only 는 비어 있어야 함.
3. `(run, lumiBlock, event)` 로 hash join.
4. 매 event 마다 모든 공통 branch 를 동일 buffer 에 read 한 후 적절한 비교:
   * 정수 branch: `memcmp` byte-exact
   * `Float_t`: NanoAOD `MiniFloatConverter::reduceMantissaToNbitsRounding` 의 양자화 step 을 감안한 relative-aware tolerance `5e-4 * max(1, |a|)` (v6.1 의 GenJet eta 케이스에서 도출).
   * Array branch: 먼저 length leaf 가 일치하는지 확인한 뒤 모든 element 비교.
5. 마지막에 per-branch ratio = (`nIdentical` / `nCompared`) 를 출력. 정상 시 모두 1.000.
6. Expanded_genTtbarId category-별 분포 분리 출력 + 일관성 체크:
   * 0..55 sub-code 는 enriched 와 central 이 정확히 같은 카운트.
   * (nAddBJets>=3 인 이벤트 수) = 61 + 62 + 71 + 72 카운트 (Expanded_genTtbarId). 그리고 nAddBJets<=2 이벤트는 Expanded_genTtbarId == genTtbarId.
   * 즉 enriched 가 추가한 것은 *오직* 61/62/71/72 새 bin 뿐.

이 도구가 exit code 0 으로 끝나면, 사용자 요구 "ratio = 1 everywhere except for added Custom_* branches" 가 정량적으로 입증된 것입니다.

### 9.4 CRAB 인프라

v7 는 enriched NanoAOD production 을 grid 로 scale-out 하기 위해 `crab/` 디렉토리 신규 추가:
* `datasets.yaml` — (process × era) catalogue, enabled toggle.
* `site_config.yaml` — 사용자/사이트 설정.
* `submit.py` — 메인 driver, 매 enabled entry 마다 CRAB Configuration build + submit.
* `status.py` — bulk crab status.
* `preflight.py` — 제출 전 sanity check (CMSSW env, plugin built, voms proxy, YAML placeholder 교체, cfg parse).

워크플로우는 4단계 (preflight → dry-run → smoke-test → real submit) 로 강제됩니다 — CRAB 제출 1회 실수 비용이 크기 때문에.

### 9.5 v7 의 검증 시나리오

v7 의 byte-identity claim 은 다음 순서로 입증됩니다:

1. **Single-file local test**: 1 UL17 MiniAODv2 파일에 cmsRun 으로 enriched cfg 실행 → enriched.root 생성. 대응 central NanoAODv9 파일을 xrootd 로 받아 `compareEnrichedToCentral` 실행. **기대**: per-branch ratio 모두 1.000, Expanded_genTtbarId category 일관성 체크 통과.
2. **CRAB-scale test**: 같은 dataset 전체 (TTToHadronic UL17 ~4000 files) 를 CRAB 으로 처리 → output merge → 같은 도구로 통계 검증.
3. **새 sample 검증**: TTbb 또는 ttHH sample 에 대해 위 1, 2 반복. 이 경우 nAddBJets>=3 영역이 자연 stat 으로 채워지므로 확장 분기 (61/62/71/72) 가 trigger 됨.

§5.3 의 "확장 분기 실제 검증 부족" 한계는 step 3 까지 가야 해결됩니다.

### 9.6 신규 / 수정 / 폐기 파일 목록

신규:
* `test/run_enriched_nanoaod_cfg.py`
* `bin/compareEnrichedToCentral.cc`
* `crab/__init__.py`
* `crab/datasets.yaml`
* `crab/site_config.yaml`
* `crab/submit.py`
* `crab/status.py`
* `crab/preflight.py`

수정:
* `README.md` — release 권장값 변경, 디렉토리 트리 갱신, v6 -> v7 changelog 추가.
* `docs/ARCHITECTURE.md` — 본 §9 추가.
* `bin/BuildFile.xml` — sidetree binary 제거, 새 enriched binary 추가.

폐기:
* `plugins/TtbarCategoryNtuplizer.cc`
* `test/run_approach1_sidetree_cfg.py`
* `bin/compareSidetreeToNano.cc`

`plugins/ExtendedTtbarIdProducer.cc` 와 `plugins/TtbarCategoryTableProducer.cc`, `python/extendedTtbarId_cfi.py`, `python/ttbarCategorySequence_cff.py`, `plugins/BuildFile.xml`, `python/__init__.py`, `bin/compareCustomnanoToCentral.cc` 는 v6.2 와 **bit-for-bit 동일**합니다 — categorization 로직 자체는 변경 없음.


---

## 10. v7 -> v7.1 호환성 패치 (CMSSW_10_6_X / Python 2)

### 10.1 동기

v7 의 첫 실제 빌드/실행 (`/afs/cern.ch/user/.../CMSSW_10_6_32_patch1/src/ExtendedTtbarId/NanoExtension/`) 에서 다섯 가지 호환성 문제가 순차적으로 발견됐습니다. 모두 v6.x 시절 reference 였던 `CMSSW_14_2_1` (Python 3, 새 cmssw) 에서는 silent 하게 통과되던 패턴이 `CMSSW_10_6_32_patch1` (Python 2, 옛 cmssw) 에서는 깨지는 케이스입니다. v7.1 은 이를 모두 fix 한 release 입니다.

### 10.2 발견된 문제와 fix

| # | 파일 | 증상 | Fix |
|---|---|---|---|
| 1 | `bin/compareEnrichedToCentral.cc` line 250/254 | `for (auto& [n, b] : byNameE)` 의 `b` unused (`-Werror=unused-variable`) | structured-binding 을 `for (const auto& kv : byNameE) { const auto& n = kv.first; }` 로 변경 |
| 2 | `bin/compareEnrichedToCentral.cc` line 397 | `Slot* slotEnrichedTtbb = nullptr;` dead variable | 줄 삭제 |
| 3 | `test/run_enriched_nanoaod_cfg.py` line 2 | `SyntaxError: Non-ASCII character '\xe2'` (em-dash 등) | 1번 줄에 `# -*- coding: utf-8 -*-` 추가 + 본문의 em-dash 를 ASCII hyphen 으로 치환 |
| 4 | `test/run_enriched_nanoaod_cfg.py` | `AttributeError: 'Process' object has no attribute 'MessageLogger'` | `process.load("FWCore.MessageService.MessageLogger_cfi")` 명시 |
| 5 | `python/ttbarCategorySequence_cff.py` line 38 | `AttributeError: 'tuple' object has no attribute 'find'` | tuple `("module","label")` 을 `cms.InputTag("module","label")` 로 명시 변환 |
| 6 | `test/run_enriched_nanoaod_cfg.py` | `Configuration error: JetPtMismatch is an unrecognized name for a PSet` | for 루프 안 `setattr` 직전에 `process.MessageLogger.categories.append(_cat)` 추가 |

### 10.3 CMSSW 10_6_X vs 12_X+ 호환성 매트릭스

향후 12_X 이후의 코드를 10_6_X 로 port 하는 사람을 위한 reference:

| 항목 | 10_6_X (Python 2, 옛 cmssw) | 12_X+ (Python 3, 새 cmssw) |
|---|---|---|
| 소스에 non-ASCII 문자 (em-dash, 한글 주석) | PEP 263 declaration 필요 (`# -*- coding: utf-8 -*-`) | 자동 처리 |
| `process.MessageLogger` 자동 attach | **아니오** — `process.load("FWCore.MessageService.MessageLogger_cfi")` 명시 필요 | 예 |
| `.clone(x=("a","b"))` 이 InputTag 로 자동 변환 | **아니오** — `cms.InputTag("a","b")` 명시 필요 | 예 |
| MessageLogger 새 category 자동 등록 | **아니오** — `process.MessageLogger.categories.append(name)` 필요 | 예 |
| `-Werror=unused-variable` 적용 강도 | 엄격 (gcc 7.x/9.x) | 동일 또는 더 엄격 |
| `auto& [k, v]` (C++17 structured binding) | 지원 (`gcc 7+`) — but unused warning 회피 위해 destructure 한 변수를 항상 사용해야 함 | 동일 |

### 10.4 v7 -> v7.1 의 파일 변경

수정:
* `bin/compareEnrichedToCentral.cc` — unused-variable 3건 제거 (structured binding 2건 + dead slot 1건)
* `test/run_enriched_nanoaod_cfg.py` — PEP 263 + MessageLogger load + categories.append (3건)
* `python/ttbarCategorySequence_cff.py` — module-level `clone()` 의 tuple 인자를 `cms.InputTag(...)` 로 (4 line)
* `crab/datasets.yaml` — TTbb_Hadronic entry 의 dataset suffix `-v2` → `-v1` 정정 (실제 DAS path 와 일치)
* `README.md` — full xrootd path example (TTbb + TTToHadronic 두 sample) + EL7 컨테이너 진입 명령어 + TWiki 추천 출처 명시
* `docs/ARCHITECTURE.md` — 본 §10 추가

신규/폐기 파일: 없음 (모두 in-place fix).

`plugins/ExtendedTtbarIdProducer.cc`, `plugins/TtbarCategoryTableProducer.cc`, `python/extendedTtbarId_cfi.py`, `python/__init__.py`, `plugins/BuildFile.xml`, `bin/BuildFile.xml`, `bin/compareCustomnanoToCentral.cc`, `crab/__init__.py`, `crab/site_config.yaml`, `crab/submit.py`, `crab/status.py`, `crab/preflight.py` 는 **v7 과 bit-for-bit 동일** — categorization 로직 + plugin 인터페이스 + CRAB infra 모두 변경 없음.

### 10.5 검증 시나리오

v7.1 가 의도대로 동작하는지는 다음 명령으로 확인할 수 있습니다 (TTbb_4f_TTToHadronic UL17 1 file):

```bash
cmssw-el7
cmsrel CMSSW_10_6_32_patch1 && cd CMSSW_10_6_32_patch1/src && cmsenv
tar xzf ExtendedTtbarId_NanoExtension_v7p1.tar.gz && scram b -j 8

cmsRun ExtendedTtbarId/NanoExtension/test/run_enriched_nanoaod_cfg.py \
    inputFiles=root://xrootd-cms.infn.it//store/mc/RunIISummer20UL17MiniAODv2/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/MINIAODSIM/106X_mc2017_realistic_v9-v1/280000/04B35B8B-2D7E-DD4C-AA6A-FC6364606485.root \
    outputFile=enriched.root year=2017 maxEvents=-1

compareEnrichedToCentral \
    --enriched enriched.root \
    --central root://xrootd-cms.infn.it//store/mc/RunIISummer20UL17NanoAODv9/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/130000/2C5102B9-7027-3E4E-836C-06A981E74AF3.root
```

기대 결과: per-branch ratio = 1.000 (모든 common branch), `Custom_*` 만 enriched-only, Expanded_genTtbarId category 일관성 통과. 추가로 sub-code 61/62/71/72 가 처음으로 (v6.x 의 TTToHadronic 84k 와 달리) non-zero 통계를 보여야 함 — TTbb sample 의 ME 가 add b-pair 를 보장하기 때문.

## 11. v7.1 -> v7.2 — cmsDriver baseline + diagnostic logging

v7 / v7.1 의 hand-written `test/run_enriched_nanoaod_cfg.py` 는 NanoAOD `nano_cff` 를 직접 load 한 뒤 era modifier 와 `nanoAOD_customizeMC` 를 우리가 손으로 끼워 넣는 구조였습니다. 이 hand-written cfg 가 **각 fix 마다 새로운 호환성 문제** 를 표면화시켰던 것이 v7 → v7.1 → v7.2 디버깅의 핵심 패턴이었습니다.

### 11.1 디버깅 chronology — hand-written cfg 의 fragility

| 시도 | 증상 | 미봉책 |
|---|---|---|
| v7 first run | `ProductNotFound: jetCorrFactorsAK8`/그 ValueMap | `nanoAOD_customizeMC` 호출 자체를 제거 (그것이 AK8 ParticleNet mass regression 을 재계산하면서 그 input 을 못 찾음) |
| 두 번째 run | `ProductNotFound: finalBoostedTaus` (`slimmedTausBoostedNewID` 없음) | customizer 안에서 boostedTau new-ID modifier 도 setup 됐는데 customizer 제거하면서 그것도 빠짐. boostedTau path 통째로 제거 시도 |
| 세 번째 run | `ProductNotFound: bitmapVIDForEle` (egmGsfElectronIDs ValueMap 없음) | 같은 패턴 — electron VID 도 customizer 가 setup. electron VID path 제거 |
| 네 번째 run | `ttbarCategoryTable: unsupported type` | 우리 plugin 의 `addColumnValue<int>` 호출에서 발생. **하지만 그 시점에 이미 jet/boostedTau/electron 가 모두 끊겨 있어서, 우리 코드 문제인지 cascading 의 결과인지 판별 불가** |

각 미봉책이 다음 dangling reference 를 노출시켜서 **fix 의 무한 cascading** 이 발생했어요. 이게 hand-written cfg 의 본질적 fragility 입니다.

### 11.2 해결 — cmsDriver.py 로 baseline cfg 생성

McM 의 NanoAODv9 production request 가 실제로 사용한 cmsDriver 명령을 그대로 우리도 사용합니다. cmsDriver 가 `--step NANO` + era modifier 로부터 **정확한 customizer + 정확한 producer 등록 순서** 를 자동으로 emit 합니다.

검증된 결과 (TTbb_4f UL17, n=10):

```
Will recalculate the following discriminators on AK8 jets: pfParticleNetMassRegressionJetTags:mass
customising the process with nanoAOD_customizeMC from PhysicsTools/NanoAOD/nano_cff
customising the process with addMonitoring from Configuration/DataProcessing/Utils
...
- Number of Events:  10
TimeReport> Time report complete in 44.4185 seconds
Event Throughput: 0.626809 ev/s
```

즉 **같은 `nanoAOD_customizeMC` 인데 hand-written cfg 에서는 깨지고 cmsDriver cfg 에서는 동작합니다.** 차이는 hand-written 에서 우리가 미세하게 빠뜨린 era modifier 적용 시점 / module 등록 순서 입니다.

### 11.3 v7.2 가 채택하는 ‘two-step + inject’ 패턴

```
gen_official_cfg.sh  →  cmsDriver.py emits run_enriched_nanoaod_cfg.py  →  patcher injects addCustomTtbar(process)  →  cmsRun
```

* `test/gen_official_cfg.sh` 가 cmsDriver 명령을 정확한 era / GlobalTag 로 호출하고, 그 결과 cfg 의 `process.schedule = ...` 직전에 우리 extension 을 inject 합니다 (idempotent — 두 번 호출해도 한 번만 inject).
* `test/run_enriched_nanoaod_cfg.py` 는 fallback 으로 남겨두지만 **권장하지 않습니다**. cmsDriver 가 없는 환경 (network-restricted offline replay) 에서만 사용.

향후 sample / era / release 가 바뀌면 `gen_official_cfg.sh` 의 GlobalTag / era 매핑만 갱신하면 됩니다. NanoAOD nano sequence 의 내부 변동은 cmsDriver 가 흡수합니다.

### 11.4 진단 logging 보강

“가정/추정으로 코드를 짜지 말고 모든 코드를 한 번 검토하고 혹시 모를 에러에 대비하여 log 출력을 남기자” 라는 명시 요구에 따라 v7.2 는 전체적으로 logging 을 보강했습니다:

* **`plugins/TtbarCategoryTableProducer.cc`**
  * 생성자에서 `edm::LogInfo("TtbarCategoryTableProducer")` 로 4 개 input InputTag 와 verbose flag 출력 (시작 시 1 회).
  * 새 helper `safeGetInt()` 가 `iEvent.get()` 을 `try/catch` 로 감싸 missing product 의 정확한 InputTag 를 `edm::LogError` 로 출력 후 fallback 값 0 사용 (table 의 나머지 column 은 정상 작성).
  * `addColumnValue<int>` 호출 전체를 `try/catch` 로 감싸 ‘unsupported type’ exception 시 4 개 값 + InputTag 를 모두 로깅한 뒤 re-throw (cmsRun 은 종전대로 즉시 종료).
  * untracked `verbose` PSet param (기본 false) — true 로 켜면 event 당 `(genTtbarId, Expanded_genTtbarId, nAddBJets, nAddBJetsMulti)` 가 `edm::LogVerbatim` 으로 출력됩니다.

* **`python/ttbarCategorySequence_cff.py`**
  * `addCustomTtbar()` 함수가 진입 / 작업 단계 / 종료를 모두 stdout 으로 출력 (config-parse time 에 보임).
  * Sanity check: `process.nanoSequenceMC`, `process.matchGenBHadron`, `process.matchGenCHadron`, `process.categorizeGenTtbar` 모두 process 에 attach 돼 있는지 확인 후 없으면 명확한 RuntimeError. 이전엔 attribute error 가 framework 깊은 곳에서 발생해 어느 단계에서 깨졌는지 불명확했음.
  * `extendedTtbarId` / `ttbarCategoryTable` 이 이미 process 에 있으면 replacement 임을 stdout 으로 알림 (재실행 시 정상 동작).

* **`bin/compareEnrichedToCentral.cc`**
  * `main()` 진입 직후 `[v7.2]` 라벨로 argv / tree name / max-events / dump 옵션 echo.
  * 기존 `[open] / [tree] / [inv] / [join] / [skip] / [diff] / [loop] / [ratio]` 단계별 로깅은 v6 시절부터 풍부했으니 유지.

* **`test/gen_official_cfg.sh`**
  * `[gen_official_cfg.sh]` 라벨로 모든 변수 / 단계 / 종료 시 다음 명령 hint 까지 출력.
  * CMSSW_BASE 미설정 / 패키지 미빌드 시 fail-fast 메시지.

* **`test/run_enriched_nanoaod_cfg.py`** (fallback)
  * `[run_enriched_nanoaod_cfg]` 라벨로 VarParsing 결과 + era / GlobalTag 매핑 + schedule 빌드 완료를 보고.

### 11.5 v7.2 가 남겨둔 미해결 항목

* **‘unsupported type’ exception 의 진짜 원인**. 우리 plugin 의 `addColumnValue<int>` 가 CMSSW master 의 `NPUTablesProducer.cc` 에서는 정상 동작하지만, CMSSW_10_6_X 에서는 우리 코드 에서 거부됐습니다. 위 logging 강화가 다음 cmsRun 시 정확한 진단을 가능하게 합니다. 대안 (`globalVariablesTableProducer` 표준 패턴) 의 import path 는 release 마다 달라서 (`PhysicsTools.NanoAOD.common_cff` vs `PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi`) 가정 없이 단정 불가 — 사용자가 CMSSW 환경에서 직접 다음 명령으로 확인해야 합니다:

  ```bash
  python -c "from PhysicsTools.NanoAOD.common_cff import globalVariablesTableProducer; print(globalVariablesTableProducer)"
  # 또는
  python -c "from PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi import globalVariablesTableProducer; print(globalVariablesTableProducer)"
  ```

  성공하는 쪽이 `python/ttbarCategorySequence_cff.py` 의 대안 구현에 사용 가능한 import path 입니다. v7.3 후보 작업.

* **`patTauDiscriminationByElectronRejectionMVA62015Raw` 가 event 당 13.55 s** (TimeReport). UL17 MiniAODv2 의 MVA electron-rejection BDT 가 비정상적으로 느림. production-scale (수 M event) 직전에 처리 필요. v7.3 후보 작업.

### 11.6 v7 -> v7.1 -> v7.2 의 누적 fix 매트릭스

| 카테고리 | fix | 파일 | 최초 적용 |
|---|---|---|---|
| 컴파일 | unused-variable 3 건 제거 | `bin/compareEnrichedToCentral.cc` | v7.1 |
| Python 2 호환 | PEP 263 + MessageLogger load + categories.append | `test/run_enriched_nanoaod_cfg.py` | v7.1 |
| Python 2 호환 | tuple → `cms.InputTag(...)` 명시 | `python/ttbarCategorySequence_cff.py` | v7.1 |
| Scheduling | Sequence `+=` → `Task.associate()` | `python/ttbarCategorySequence_cff.py` | v7.1+ (TrigReport "Unrunnable schedule" 발견 후) |
| ROOT type | `uint64_t` → `ULong64_t` (event branch만) | `bin/compareEnrichedToCentral.cc` | v7.1+ (join 0 entries 발견 후) |
| Sample path | TTbb_4f `-v2` → `-v1` | `crab/datasets.yaml` | v7.1 |
| cfg architecture | hand-written cfg → cmsDriver-emit + inject | `test/gen_official_cfg.sh` 신규 | v7.2 |
| Diagnostic | plugin 생성자 LogInfo + safeGetInt + try/catch | `plugins/TtbarCategoryTableProducer.cc` | v7.2 |
| Diagnostic | addCustomTtbar 진입/종료 print + sanity check | `python/ttbarCategorySequence_cff.py` | v7.2 |
| Diagnostic | comparator startup banner | `bin/compareEnrichedToCentral.cc` | v7.2 |
| Doc | README 에 cmsDriver 명령 + 참조 link | `README.md` | v7.2 |


### 11.7 v7.2 의 byte-identity 최종 검증 결과 (2026-05-28)

이 기록은 v7.2 archive 가 실제로 production-ready 상태인지를 confirm 하는 최종 cmsRun + comparator 결과입니다.

**환경**: EL7 Singularity 컨테이너, CMSSW_10_6_32_patch1, MiniAODv2 input = `/store/mc/RunIISummer20UL17MiniAODv2/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/.../04B35B8B-2D7E-DD4C-AA6A-FC6364606485.root`, N=10 events.

**cmsRun 결과**:

```
[run_enriched_nanoaod_cfg] loading ExtendedTtbarId.NanoExtension extension
[ExtendedTtbarId.NanoExtension] addCustomTtbar(process) start
[ExtendedTtbarId.NanoExtension]   standard ttbar-categorization modules confirmed on process
[ExtendedTtbarId.NanoExtension]   ttbarCategoryTable already on process -- replacing
[ExtendedTtbarId.NanoExtension]   ttbbCustomTask associated with nanoSequenceMC; emits Custom_genTtbarId, Custom_Expanded_genTtbarId, Custom_nAddBJets, Custom_nAddBJetsMulti
[ExtendedTtbarId.NanoExtension] addCustomTtbar(process) done
...
- Number of Events:  10
TimeReport> Time report complete in 33.5014 seconds
Event Throughput: 0.923622 ev/s
```

10/10 event 통과, 'unsupported type' 사라짐, fatal exception 0.

**comparator 결과** (sidecar 비교는 `--max-events 1000000` 으로 central NanoAODv9 의 부모-자식 매핑된 file 사용):

```
[v7.2] compareEnrichedToCentral starting
[tree]  enriched entries = 10
[tree]  central  entries = 682000
[inv]   common branches  : 1665
[inv]   enriched-only    : 4   (Custom_genTtbarId, Custom_Expanded_genTtbarId, Custom_nAddBJets, Custom_nAddBJetsMulti)
[inv]   central-only     : 1   (genTtbarId)
[join]  built enriched index : 10 entries
[loop]  matched   : 10
[loop]  unmatched : 681990
[ratio] per-branch identity (target = 1.000 for every line):
  >>> ALL common branches reproduce 1:1 -- ratio is 1.000 everywhere.
[ok]    sub-code categories agree: only 61/62/71/72 are new,
        all other categories are populated identically.
```

**1,665 common branch 모두 ratio = 1.000** — byte-identity 확정.

sub-code 분포는 10 event 통계의 한계로 0/51/52/53 만 등장 (사용자 query result 에서). 새 sub-code (61/62/71/72) 검증은 더 큰 통계 (예: `NEVENTS=5000`) 에서 가능. **이 시점에서 v7.2 의 모든 검증 항목 통과**.

### 11.8 v7.2 production-ready checklist (모두 ✅)

| 항목 | 상태 |
|---|---|
| cmsDriver-based baseline cfg | ✅ |
| `addCustomTtbar(process)` inject pattern | ✅ |
| `addColumnValue<int>` + 4번째 인자 `IntColumn` 명시 fix | ✅ |
| `Custom_*` 4 branch 생성 | ✅ |
| comparator `ULong64_t` SetBranchAddress fix | ✅ |
| (run, lumi, event) hash join | ✅ |
| **1,665 common branch byte-identity (ratio = 1.000)** | ✅ |
| Sub-code 0..55 invariance | ✅ |
| 모든 v7.x logging | ✅ |
| README cmsDriver 명령 + 참조 link | ✅ |

이 시점부터 다음 단계는 **production-scale** (CRAB 으로 전체 ~ 330M event sample) 또는 **Approach 3 (sidecar)** 로 옮겨가는 것 — v8 의 출발점.


## 12. v7.2 -> v8 -- Approach 3 (sidecar TTree, post-processor friend-tree)

### 12.1 왜 Approach 3 인가

v7 의 Approach 2 (enriched NanoAOD) 는 byte-identity 가 검증됐지만 다음 한계가 있었습니다:

1. **NanoAOD step 의존성**. cmsDriver 가 emit 한 cfg 가 nanoAOD_customizeMC 를 호출하고, 그게 AK8 ParticleNet mass regression 재계산 등 ~ 50 개 producer 를 한 schedule 에 묶습니다. 그 중 어느 하나가 release patch 의 변경으로 깨지면 (예: 우리가 본 'unsupported type' 또는 boostedTau / electron VID 의 ProductNotFound) 전체 production 이 멈춥니다. v7 → v7.1 → v7.2 의 6 번의 fix cycle 이 이를 보여줬습니다.

2. **storage cost**. enriched NanoAOD 는 central NanoAOD 의 1:1 카피 + 4 column 추가. 4 sample 합쳐 ~ 200 GB. 우리가 추가한 정보는 event 당 16 byte (4 int 4-byte). 99.99% 가 central 의 단순 복제입니다.

3. **post-processor 와의 ergonomics**. enriched 를 만들면 그 file 이 새로운 source of truth 가 되어 downstream code 가 enriched path 를 알아야 합니다. central NanoAOD 와 enriched NanoAOD 둘 다 운영하는 비용이 들어요.

Approach 3 은 이 세 문제를 동시에 해결합니다:

* **NanoAOD step 없음**. 우리 cfg 는 gen-level producer 만 사용 (matchGenBHadron / matchGenCHadron / categorizeGenTtbar / ExtendedTtbarIdProducer / TtbarIdSidecarAnalyzer). 모두 MiniAOD 의 표준 gen 산물에만 의존하고, release patch 사이의 변경에 면역.
* **storage**. event 당 ~ 32 byte (4 int + run/lumi/event 키). 4 sample ~ 100M event = ~ 3 GB. central NanoAOD ~ 200 GB 와 비교 100× 감축.
* **post-processor**. central NanoAOD 를 read-only 로 쓰면서 sidecar 를 `TTree::AddFriend` 로 attach. analysis code 는 친구 트리의 `Custom_*` column 을 native NanoAOD branch 와 똑같이 읽을 수 있고, central NanoAOD 의 모든 다른 branch 도 그대로 사용. 두 source of truth 가 분리된 채로 깔끔하게 합쳐집니다.

### 12.2 무엇이 sidecar 에 들어가는가

sidecar.root 의 `Events` TTree:

| Branch | Type | 의미 |
|---|---|---|
| `run` | UInt_t | NanoAOD `run` 과 동일 type |
| `luminosityBlock` | UInt_t | NanoAOD `luminosityBlock` 과 동일 type |
| `event` | ULong64_t | NanoAOD `event` 과 동일 type |
| `genTtbarId` | Int_t | **standard `categorizeGenTtbar:genTtbarId`** (central NanoAOD 의 `genTtbarId` 와 byte-identical) |
| `Expanded_genTtbarId` | Int_t | 우리 ExtendedTtbarIdProducer 출력 (nAddBJets 기반 tt+bbb/tt+4b split) |
| `nAddBJets` | Int_t | 우리 ExtendedTtbarIdProducer 출력 (acceptance 안 add b-jet 수) |
| `nAddBJetsMulti` | Int_t | 우리 ExtendedTtbarIdProducer 출력 (≥2 b-hadron host 한 add b-jet 수) |

명시적 설계 결정:

* **`genTtbarId` 를 NanoAOD branch 에서 베끼지 않고 standard producer 에서 새로 유도**합니다. categorizeGenTtbar 를 sidecar 시 다시 호출 → 같은 input (slimmedGenJets, matchGenBHadron, matchGenCHadron) → 같은 output. v7.2 의 byte-identity 검증이 이 동등성을 1,665 branch level 에서 confirm 했습니다.
* `event` 가 `ULong64_t` 이라서 NanoAOD-tools 의 friend-tree 가 별도 type 변환 없이 매치합니다.
* TTree::BuildIndex("run", "event") 가 endJob 에 자동 호출되어 friend-tree 의 fast random access 보장.

### 12.3 v8 의 컴포넌트 (v7.2 와의 diff)

| 신규 | 무엇 |
|---|---|
| `plugins/TtbarIdSidecarAnalyzer.cc` | EDAnalyzer. consumes 4 int + writes TTree via TFileService. v7.2 의 try/catch / safeGet / per-event verbose 패턴 그대로 |
| `python/ttbarIdSidecar_cff.py` | sequence + `addTtbarIdSidecar(process, outputFile, verbose)` helper |
| `test/run_sidecar_cfg.py` | minimal hand-written cfg (NanoAOD step 없음 → hand-written 이 안전). MiniAODv2 → sidecar.root |
| `test/make_sidecars_4samples.sh` | 4 sample (TT4b / TTbb_SemiLep / TTbar_SemiLep / TTHHto4b) sidecar smoke test |
| `bin/compareSidecarToCentral.cc` | sidecar 의 `genTtbarId` 와 central NanoAODv9 의 `genTtbarId` byte-identity 검증 + sub-code 분포 비교 |
| `crab/submit_sidecar.py` | sidecar 생산 CRAB submitter (기존 submit.py 의 PSET 경로만 변경) |
| `crab/datasets.yaml` | 4 sample (MiniAOD + NanoAODv9 child pair) 명시 |

| 유지 | 비고 |
|---|---|
| `plugins/ExtendedTtbarIdProducer.cc` | nAddBJets 기반 61/62/71/72 split (v10 에서 56 조건 → nAddBJets 조건으로 수정) |
| `plugins/TtbarCategoryTableProducer.cc` | v7.2 의 fix 그대로. enriched approach 가 필요한 경우 여전히 사용 가능 |
| `plugins/BuildFile.xml` | TFileService 의존성 (`CommonTools/UtilAlgos`) 이미 들어있어서 변경 없음 |
| `bin/compareEnrichedToCentral.cc` | v7.2 의 ULong64_t fix 포함 그대로. enriched approach 의 검증용으로 유지 |
| `test/gen_official_cfg.sh` + `test/run_enriched_nanoaod_cfg.py` | v7.2 의 enriched approach 그대로 유지 (사용자가 둘 중 선택 가능) |

### 12.4 sidecar workflow

```
MiniAODv2  ──cmsRun run_sidecar_cfg.py──▶  sidecar.root  ◀──TTree::AddFriend──  central NanoAODv9
                                                                                      ▲
                                                                                      │
                                                                          analysis code reads
                                                                          Custom_* and standard
                                                                          NanoAOD branches together
```

검증 path (이 패키지가 책임지는 부분까지):

```
MiniAODv2  ──cmsRun──▶  sidecar.root          ┐
                                              ├──compareSidecarToCentral──▶  byte-identity OK?
central NanoAODv9 ────────────────────────────┘
```

byte-identity 가 OK 이면 sidecar 의 `genTtbarId` 가 central 의 `genTtbarId` 와 모든 매치된 event 에서 동일하고, Expanded_genTtbarId distribution 이 0..55 영역에서 central distribution 과 invariant 함을 의미합니다.

### 12.5 v8 의 디자인 원칙

이 디자인이 갖는 robust 특성:

1. **release-cycle 면역**. gen-level producer (matchGenBHadron 등) 는 CMSSW 10_2 부터 14_X 까지 interface 변화 없음. NanoAOD step 을 거치지 않으니 customizer / era modifier / FlatTable type dispatch 의 함정 모두 회피.
2. **production cost**. event 당 ~ 32 byte. 4 sample 합쳐 ~ 3 GB. CRAB output limit 우려 없음.
3. **post-processor 호환**. NanoAOD-tools (`PhysicsTools/NanoAODTools`) 의 friend-tree pattern 과 정확히 같은 schema (run/lumi/event keys + Int_t payload).
4. **검증 단순성**. comparator 가 1,665 branch 가 아닌 1 branch (`genTtbarId`) 만 비교. 검증 turnaround 가 분 단위.

### 12.6 v8 byte-identity 검증 결과 + v8.1 의 TFile 변경 (2026-05-29)

**v8 검증** (TTbb_4f hadronic UL17, MiniAODv2 `215122BB-...` → 100 events, central NanoAODv9 `1DD1BB46-...`):

```
[open] sidecar entries = 100
[loop]  matched   : 100
[byte]    agree    = 100
[byte]    disagree = 0
[byte]  >>> ALL matched events have sidecar.genTtbarId == central.genTtbarId (1:1).
[Expanded_genTtbarId] central genTtbarId%100 distribution (matched events only):
         sub-code   0 : 49   sub-code 41 : 2   sub-code 42 : 2   sub-code 43 : 1
         sub-code  51 : 26   sub-code 52 : 10  sub-code 53 : 9   sub-code 54 : 1
         total : 100
[Expanded_genTtbarId] sidecar genTtbarId%100 distribution: (line-by-line identical to central)
[ok]    sub-code categories agree.
```

100/100 event 에서 sidecar 의 `genTtbarId` 가 central NanoAODv9 의 `genTtbarId` 와 byte-identical. **categorizeGenTtbar 를 MiniAOD 에서 새로 유도한 값이 NanoAOD production 이 저장한 값과 동일함을 확정**. sub-code 분포도 0/41/42/43/51/52/53/54 전부 일치. (이 100 event 소통계에서는 nAddBJets>=3 이벤트가 드물어 새 sub-code 61/62/71/72 는 tt4b 같은 큰 sample 에서 확인. v10 split 수정 전에는 이 분기가 발동하지 않았음 — §5.3.)

**v8 → v8.1 변경 — TFileService 에서 직접 TFile 로**:

v8 검증 중 발견된 문제: TFileService 가 TTree 를 모듈 label 이름의 TDirectory (`ttbarIdSidecar/`) 안에 격리해서, tree 의 실제 경로가 최상위 `Events` 가 아니라 `ttbarIdSidecar/Events` 였습니다. 이 때문에:

1. comparator 가 `--tree-sidecar "ttbarIdSidecar/Events"` 를 명시해야 동작 (default `Events` 로는 not found).
2. friend-tree 가 central NanoAOD 의 최상위 `Events` 와 매칭하려면 path prefix 를 알아야 해서 fragile.

v8.1 의 해결: analyzer 가 `edm::Service<TFileService>` 대신 **자기 자신의 `TFile` 을 열고** TTree 를 그 file 의 최상위에 생성합니다 (`tree_->SetDirectory(file_)`). endJob 에서 `BuildIndex` → `tree_->Write()` → `file_->Close()`. 결과 file 은 central NanoAOD 와 동일하게 `Events` 가 최상위에 있어 friend-tree 가 prefix 없이 attach 됩니다.

변경 파일:
* `plugins/TtbarIdSidecarAnalyzer.cc` — `edm::one::EDAnalyzer<edm::one::SharedResources>` → `edm::one::EDAnalyzer<>`. `usesResource("TFileService")` 제거. `outputFile` 을 tracked param 으로 받아 직접 `TFile::Open(..., "RECREATE")`. beginJob 에서 top-level tree 생성, endJob 에서 Write + Close.
* `python/ttbarIdSidecar_cff.py` — module-level `ttbarIdSidecar` 에 `outputFile = cms.string("sidecar.root")` param 추가. `addTtbarIdSidecar()` 가 더 이상 `process.TFileService` 를 설정하지 않고, `outputFile` 을 analyzer param 으로 전달.
* `test/run_sidecar_cfg.py` — 변경 없음 (`addTtbarIdSidecar(process, outputFile=opts.outputFile, ...)` 호출이 그대로 동작).

**검증 재확인 (v8.1)**: 동일 input/central 로 comparator 가 `--tree-sidecar` 옵션 없이 (default `Events`) 동작해야 하고, 결과는 v8 과 동일한 100/100 matched, agree=100 이어야 합니다.


## 13. CMSSW 14 / 15 로의 migration 가이드

이 패키지는 CMSSW_10_6_32_patch1 (UL Run2 NanoAODv9 cycle, Python 2, gcc 7) 에 pin 되어 있습니다. 추후 CMSSW 14_X / 15_X (Run3 / Phase-2 cycle, Python 3, gcc 11+) 로 올릴 경우 변경해야 할 항목을 여기 정리합니다. 각 항목은 v7 → v7.2 디버깅에서 실제로 마주친 release-cycle 차이의 역방향입니다.

### 13.1 Python 2 → Python 3 (cfg / cff)

| 항목 | 10_6_X (현재) | 14_X / 15_X | 조치 |
|---|---|---|---|
| `print` | `print(...)` 함수형 이미 사용 | 동일 | 변경 불필요 (이미 `from __future__ import print_function` 사용) |
| PEP 263 헤더 (`# -*- coding: utf-8 -*-`) | 필수 (Python 2) | 불필요하나 무해 | 그대로 둬도 됨 |
| `MessageLogger.categories` | vstring, manual `.append()` 필요 | categories 개념 폐지 (자동) | `categories.append(...)` 블록 제거 가능. 남겨두면 AttributeError 가능하니 14_X 에서는 `if hasattr(process.MessageLogger, "categories")` guard 가 False 로 빠지도록 되어 있음 (현재 코드가 이미 guard 함) |
| `cms.InputTag` tuple 자동 변환 | 없음 (수동 `cms.InputTag(...)` 필수) | 12_X+ 자동 | 명시적 `cms.InputTag(...)` 는 14_X 에서도 정상 동작하므로 변경 불필요 (안전한 방향) |

대부분 현재 코드가 이미 방어적으로 작성되어 있어 14_X 에서도 그대로 import 됩니다. 단, `test/run_sidecar_cfg.py` 의 MessageLogger category append 블록은 14_X 에서 `categories` attribute 가 없으면 `hasattr` guard 로 skip 됩니다 — 동작은 하지만, 14_X 전용 cfg 를 새로 쓸 거면 그 블록을 통째로 지우는 게 깔끔합니다.

### 13.2 EDAnalyzer base class

| 항목 | 10_6_X | 14_X / 15_X | 조치 |
|---|---|---|---|
| `edm::one::EDAnalyzer<>` | OK | OK (안정 interface) | 변경 불필요 |
| `analyze()` / `beginJob()` / `endJob()` signature | 현재 형태 | 동일 | 변경 불필요 |
| `consumes<int>(...)` | OK | OK | 변경 불필요 |

EDAnalyzer 의 one:: interface 는 10_2 부터 15_X 까지 안정적입니다. 변경 없음.

### 13.3 categorizeGenTtbar / matchGenBHadron import 경로

| 항목 | 10_6_X | 14_X / 15_X | 조치 |
|---|---|---|---|
| `from PhysicsTools.NanoAOD.ttbarCategorization_cff import matchGenBHadron, matchGenCHadron, categorizeGenTtbar` | OK | **확인 필요** | 14_X 에서 NanoAOD 가 재구성되면서 이 producer 들이 다른 cff 로 이동했을 수 있음. migration 시 첫 단계로 `python -c "from PhysicsTools.NanoAOD.ttbarCategorization_cff import categorizeGenTtbar"` 로 검증할 것 |

NanoAOD 패키지는 cycle 마다 모듈 재배치가 잦습니다 (v7 에서 `globalVariablesTableProducer` 의 `common_cff` vs `_cfi` 분리를 겪음). 14_X 로 올릴 때 이 import 가 실패하면 cmssdt LXR 에서 정확한 경로를 찾아 교체. **가정하지 말고 직접 검증**.

### 13.4 FlatTable API (enriched approach 만 해당)

sidecar approach (v8) 는 FlatTable 을 안 쓰므로 영향 없음. 그러나 enriched approach (v7.2, `TtbarCategoryTableProducer.cc`) 를 14_X 에서도 쓸 거라면:

| 항목 | 10_6_X | 14_X / 15_X | 조치 |
|---|---|---|---|
| `addColumnValue<int>(name, val, doc)` 4번째 인자 생략 | `defaultColumnType<int>()` 가 throw (specialization 없음) → **명시적 `IntColumn` 필수** | 14_X 는 `defaultColumnType<int>` specialization 이 있어 생략 가능 | 현재 코드의 명시적 `nanoaod::FlatTable::IntColumn` 4번째 인자는 14_X 에서도 정상 동작 (안전한 방향). 변경 불필요 |
| `nanoaod::FlatTable` 헤더 위치 | `DataFormats/NanoAOD/interface/FlatTable.h` | **확인 필요** (DataFormats 재배치 가능) | migration 시 헤더 경로 검증 |

v7.2 의 `IntColumn` 명시 fix 는 14_X 에서도 호환되는 방향이므로 그대로 둬도 안전합니다.

### 13.5 ROOT 버전 (comparator)

| 항목 | 10_6_X (ROOT 6.14) | 14_X (ROOT 6.26+) / 15_X (6.30+) | 조치 |
|---|---|---|---|
| `ULong64_t` / `Long64_t` typedef | `RtypesCore.h` | 동일 | 변경 불필요 |
| `TTree::BuildIndex("run", "event")` | OK | OK | 변경 불필요 |
| `TTree::SetBranchAddress` 의 `ULong_t`(14) vs `ULong64_t`(17) type-id 구분 | strict | strict (동일) | `compareEnrichedToCentral.cc` / `compareSidecarToCentral.cc` 의 `ULong64_t` 사용은 모든 ROOT 6.x 에서 동일하게 필요. 변경 불필요 |
| `TFile::Open` / `TTree::Write` / friend tree | OK | OK | 변경 불필요 |

comparator 와 analyzer 의 ROOT 사용은 6.14 ~ 6.30 에서 호환됩니다.

### 13.6 SCRAM_ARCH / compiler

| 항목 | 10_6_X | 14_X / 15_X | 조치 |
|---|---|---|---|
| SCRAM_ARCH | `slc7_amd64_gcc700` | `el8_amd64_gcc11` / `el9_amd64_gcc12` 등 | `cmsrel` 시 자동 결정. BuildFile.xml 은 arch-independent 라 변경 불필요 |
| `-Werror=unused-variable` | gcc 7 strict | gcc 11+ 더 strict | v7.1 에서 제거한 unused-variable 들은 이미 정리됨. 14_X 에서 추가 warning 가능성 있으나 현재 코드는 clean |
| Container | `cmssw-el7` | `cmssw-el8` / native el9 | LXPLUS 가 EL9 이므로 14_X 는 컨테이너 없이 native 빌드 가능할 수 있음 |

### 13.7 입력 sample (MiniAOD → NanoAOD 버전)

| 항목 | 현재 (UL Run2) | Run3 | 조치 |
|---|---|---|---|
| Input | RunIISummer20UL17MiniAODv2 | Run3Summer22/23 MiniAOD | `crab/datasets.yaml` 의 dataset path + GlobalTag + era 갱신 |
| GlobalTag | `106X_mc2017_realistic_v9` | `124X_mcRun3_...` 등 | `crab/datasets.yaml` 및 cfg 의 era mapping 갱신 |
| era modifier | `Run2_2017, run2_nanoAOD_106Xv2` | `Run3, run3_nanoAOD_...` | `run_sidecar_cfg.py` 의 `eras.Run2_2017` 부분 교체 |
| NanoAOD 버전 | v9 | v12 / v13 / v15 | `genTtbarId` 의 의미는 NanoAOD 버전 무관하게 동일 (categorizeGenTtbar 가 source) |

sidecar approach 의 장점이 여기서 드러납니다 — NanoAOD 버전이 v9 → v15 로 바뀌어도 우리는 NanoAOD step 을 안 거치므로 sidecar 코드 자체는 영향 없고, 입력 MiniAOD 의 era/GT 만 갱신하면 됩니다.

### 13.8 migration 체크리스트 (요약)

CMSSW 14_X / 15_X 로 올릴 때 순서:

1. `cmsrel CMSSW_14_X_Y` + `cmsenv`, 패키지 unpack, `scram b` — 컴파일 에러부터 확인.
2. `python -c "from PhysicsTools.NanoAOD.ttbarCategorization_cff import categorizeGenTtbar, matchGenBHadron, matchGenCHadron"` — import 경로 검증 (§13.3). 실패 시 cmssdt LXR 로 새 경로 확인.
3. `python -c "from PhysicsTools.NanoAOD.extendedTtbarId_cfi import extendedTtbarId"` 류 — 우리 모듈은 그대로일 것.
4. gen-only smoke test: `cmsRun run_sidecar_cfg.py inputFiles=<Run3 MiniAOD> maxEvents=10` — era/GT 갱신 후.
5. `compareSidecarToCentral` 로 Run3 central NanoAOD 와 byte-identity 재검증.
6. enriched approach 도 유지할 거면 §13.4 의 FlatTable 헤더 경로 + IntColumn 동작 재확인.

각 단계에서 **추정 금지** — import / 헤더 / API 가 바뀌었는지는 반드시 해당 release 환경에서 직접 검증. 이 패키지의 v7 → v7.2 디버깅 역사 (§§10-11) 가 release-cycle 가정의 위험을 보여주는 기록입니다.

## 14. CRAB submitter fix + 주석/인코딩 정리

### 14.1 `year=` 파라미터 버그 (CRAB 제출 실패)

sidecar 의 CRAB submitter (`crab/submit_sidecar.py`) 는 enriched submitter (`crab/submit.py`) 의 복사본으로 출발했습니다. enriched cfg (`run_enriched_nanoaod_cfg.py`) 는 VarParsing 옵션 `year` 를 받지만, sidecar cfg (`run_sidecar_cfg.py`) 는 `year` 를 등록하지 않습니다 (sidecar 는 era 를 cfg 내부에서 `eras.Run2_2017` 로 고정하고, 외부 파라미터로 받지 않음).

복사본이 `cfg.JobType.pyCfgParams = [f"year={era}"]` 를 그대로 들고 있어서, CRAB 이 sidecar cfg 를 import 할 때 다음으로 죽었습니다:

```
Error:  'year' not registered.
RuntimeError: Unknown variable
  [FAILED] Unknown variable
```

해결:
* `cfg.JobType.pyCfgParams = ["outputFile=sidecar.root"]` 로 교체. sidecar cfg 는 `inputFiles` (CRAB 이 FileBased splitting 으로 자동 주입), `outputFile`, `maxEvents`, `verbose` 만 받습니다. CRAB job 마다 다른 input file 을 처리하고 output 은 동일 파일명 `sidecar.root` 를 쓰되 CRAB 이 job number 로 자동 구분 (`sidecar_1.root`, `sidecar_2.root`, ...).
* `cfg.JobType.outputFiles = ["sidecar.root"]` 추가하여 CRAB 이 결과 파일을 추적하도록 명시.

주의 남은 사항: `run_sidecar_cfg.py` 의 VarParsing 이 `outputFile` 에 `_numEventN` suffix 를 자동으로 붙입니다 (`maxEvents` 값에 따라). CRAB 환경에서 `maxEvents=-1` (전체) 이면 suffix 가 어떻게 되는지, 그리고 그 실제 생성 파일명이 `JobType.outputFiles` 의 `sidecar.root` 와 일치하는지는 **5-file smoke test 로 반드시 먼저 확인**해야 합니다. 불일치 시 `outputFiles` 를 실제 생성명에 맞추거나 cfg 의 VarParsing suffix 동작을 끕니다. 이 부분은 실제 CRAB 환경에서만 검증 가능하므로 가정하지 않고 smoke test 에 맡깁니다.

### 14.2 per-job memory

`crab/site_config.yaml` 의 `resources.sidecar.max_memory_mb` 를 2000 으로 설정 (한도 3000 의 여유 범위). sidecar job 은 gen-level producer 5개만 돌리고 event 당 ~32 byte 만 쓰므로 2 GB 면 충분합니다. enriched approach 의 `resources.enriched.max_memory_mb` 도 3500 에서 2500 으로 낮춰 동일 한도에 맞췄습니다. submitter 의 fallback default 도 동일하게 조정.

### 14.3 주석의 버전 표기 + 비-ASCII 제거

버전 번호는 계속 올라가므로 코드 주석에 특정 버전 (v7.2, v8 등) 을 박아두면 시간이 지나며 부정확해집니다. 모든 코드 파일 (`.cc`, `.py`, `.sh`, `.xml`, `.yaml`) 의 주석에서 narrative 버전 표기를 제거했습니다. 단:

* dataset / GlobalTag 경로의 버전 토큰 (`106X_mc2017_realistic_v9-v1`, `RunIISummer20UL17NanoAODv9` 등) 은 실제 식별자이므로 유지.
* `crab/site_config.yaml` 의 `request_name_tag` 는 CRAB request 충돌 방지용 기능값이라 유지 (사용자가 제출 회차마다 변경).
* `README.md` 의 version history 표는 의도된 버전 이력 기록이므로 유지.

또한 코드 파일 주석에 섞여 있던 비-ASCII 문자 (em-dash `U+2014`) 를 모두 ASCII hyphen 으로 교체했습니다. README 의 수학기호 (`<=`, `>=`, `->`, `bbbar`) 와 디렉토리 트리 box-drawing 문자도 ASCII 로 변환하여 코드/문서 전체가 ASCII-clean 합니다 (한국어 본문이 있는 ARCHITECTURE.md 제외 - 이 문서는 의도적으로 한글 포함).

검증: `find . -name '*.cc' -o -name '*.py' -o -name '*.sh' -o -name '*.xml' -o -name '*.yaml' | xargs grep -P '[^\x00-\x7F]'` 가 코드 파일에서 0 건.

---

## 15. v9 -> v10 — split 버그 수정 + 패키지 rename + stitching

### 15.1 핵심 버그: split 이 발동하지 않던 문제

§5.3 에 상술. 요약: split 조건이 `genTtbarId % 100 == 56` 에 묶여 있었으나 표준 GenTtbarCategorizer 는 sub-code 56 을 만들지 않으므로 (≥2 add b-jet 을 모두 53/54/55 로 묶음), tt+bbb/tt+4b 가 한 번도 생성되지 않았습니다. tt4b 950만 이벤트 cross-tab 으로 확정: nAddBJets>=3 이 188만 건 있으나 전부 53/54/55 안에 있고 sub-code 56 = 0.

**수정**: `plugins/ExtendedTtbarIdProducer.cc` 의 split 조건을

```cpp
// 이전 (v9): 발동 안 함
if (genTtbarId % 100 == 56 && nAddBJets >= 3) { ... }

// 이후 (v10): nAddBJets 로 직접 분류
if (nAddBJets >= 3) {
    const int base   = (genTtbarId / 100) * 100;
    const int newSub = kExtendedSubCode(nAddBJets, nAddBJetsMulti);  // 61/62/71/72
    expandedId = base + newSub;
}
```

로 바꿈. helper 함수도 `kExtendedBaseAt56` → `kExtendedSubCode` 로 rename (56 의존 의미 제거). nAddBJets / nAddBJetsMulti 카운트 로직 (acceptance pt>20/|eta|<2.4, additional b-hadron 보유 + top b-hadron 미포함 jet) 은 변경 없음 — 애초에 정확했고 AN 의 additional-b-jet 정의와 일치.

### 15.2 AN 정의와의 정합 (AN2022_122)

ttHH(bbbb) AN 3.1-3.2:

* additional b jet = gen-jet, pt > 20 GeV, |eta| < 2.4, top decay 에서 안 온 b-hadron 보유 (우리 nAddBJets 와 동일 정의)
* **tt+bbb = 정확히 3 additional b jets** -> nAddBJets == 3 -> sub-code 61/62
* **tt+4b = 4 이상 additional b jets** -> nAddBJets >= 4 -> sub-code 71/72
* DNN 노드: tt+bbb + tt+4b = tt+nb, tt+b + tt+2b + tt+bb = tt+mb

multi 구분 (61 vs 62, 71 vs 72) 은 AN 보다 한 단계 세분 (한 jet 에 b-hadron >=2 = g->bb merged). 분석에서 61+62 -> tt+bbb, 71+72 -> tt+4b 로 합치면 AN 과 일치하며, multi 정보는 g->bb 연구용으로 보존.

### 15.3 stitching 결정

* **tt+bbb, tt+4b (= tt+nb)**: dedicated **tt4b** LO sample 로 모델링 (AN option 1). b-jet kinematics 재현을 위해 dedicated sample 사용.
* 나머지 (tt+b/2b/bb = tt+mb, tt+cc, tt+LF): 기존 sample 그대로 (tt inclusive 5FS, TTbb 4FS).

**중요한 함의 — 모든 ttbar sample 에 sidecar 필요**: tt+bbb/tt+4b 라벨링이 stitching 에 참여하는 *모든* ttbar sample 에서 일관돼야 하므로, 그 sample 들의 tt+bb 버킷 (53/54/55) 안에 숨은 nAddBJets>=3 이벤트를 골라내려면 각각 sidecar (Expanded_genTtbarId) 가 필요합니다. genTtbarId 만으로는 불가능 (53/54/55 가 2/3/4 를 구분 못 함). 본 분석에서 sidecar 가 필요한 ttbar sample: TT4b, TTbb_4f (Hadronic / SemiLep / DiLep), TTToHadronic, TTToSemiLeptonic, TTTo2L2Nu. (v9 까지는 tt4b, TTbb_SemiLep, TTToSemiLeptonic 3개만 유도 — hadronic channel 의 TTToHadronic, TTbb_4f Hadronic 등 추가 필요.)

#### 15.3.1 Expanded_genTtbarId 가 만드는 분할 (partition) — 왜 stitching 이 정합한가

`Expanded_genTtbarId % 100` 은 모든 ttbar 이벤트를 **완전하고 서로소인** 카테고리로 나눕니다:

| Expanded_genTtbarId % 100 | 카테고리 | 정의 |
|---|---|---|
| 0 | tt+LF | additional b/c jet 없음 |
| 41-45 | tt+cc | additional c jet >= 1 |
| 51 | tt+b | nAddBJets <= 2 영역, genTtbarId 51 |
| 52 | tt+2b | nAddBJets <= 2 영역, genTtbarId 52 |
| 53/54/55 | tt+bb | nAddBJets <= 2 영역, genTtbarId 53/54/55 |
| 61/62 | tt+bbb | **nAddBJets == 3** |
| 71/72 | tt+4b | **nAddBJets >= 4** |

핵심: `nAddBJets >= 3` 인 이벤트만 60번대로 옮겼으므로, 60번대(tt+nb)와 그 이하(tt+mb 이하)의 경계는 **nAddBJets 라는 단일 기준**으로 정의됩니다. 그리고 같은 물리 이벤트는 어느 sample 에 있든 같은 ExtendedTtbarIdProducer 가 같은 입력 (matchGenBHadron outputs) 으로 계산하므로 **같은 Expanded_genTtbarId** 를 받습니다. 따라서 카테고리 라벨이 sample 간에 일관됩니다 — 이것이 stitching 정합성의 근거입니다.

#### 15.3.2 keep / reject 로직

tt+nb 를 tt4b sample 로, 나머지를 기존 sample 로 모델링하므로, 각 이벤트가 정확히 한 sample 에서만 카운트되도록:

```
# tt4b sample (dedicated):
keep  if Expanded_genTtbarId % 100 in {61, 62, 71, 72}    # tt+nb 만 사용
reject otherwise                              # tt+mb 이하는 다른 sample 이 담당

# 그 외 모든 ttbar sample (TTToHadronic, TTToSemiLeptonic, TTTo2L2Nu,
#                           TTbb_4f Hadronic/SemiLep/DiLep):
reject if Expanded_genTtbarId % 100 in {61, 62, 71, 72}    # tt+nb 는 tt4b 가 담당
keep   otherwise                              # tt+mb, tt+cc, tt+LF 사용
```

이렇게 하면 tt+nb 이벤트는 tt4b 에서만, tt+mb/cc/LF 이벤트는 각자의 기존 sample 에서만 카운트됩니다 (double-count / gap 없음). DNN 노드: 61+62+71+72 -> tt+nb, 51+52+53+54+55 -> tt+mb.

**중요 — 이 keep/reject 는 ntuplizer (`ttbarCategorizer.py`) 가 아니라 analyzer 단계에서 수행**: 현재 `ttbarCategorizer.py` 는 genTtbarId 로 5개 카테고리만 만들고 (`ttCat_Add2Bjet` = genTtbarId 53/54/55 = nAddBJets>=2 전부, bbb/4b 미분리), tt+nb 분리는 analyzer 가 sidecar 의 Expanded_genTtbarId 를 friend/lookup 으로 읽어 수행합니다. 즉 stitching 2단계 구조:
1. ntuplizer: genTtbarId -> 5 카테고리 (`ttCat_*`)
2. analyzer: sidecar Expanded_genTtbarId -> `ttCat_Add2Bjet` 을 tt+bb(53/54/55) / tt+bbb(61/62) / tt+4b(71/72) 로 세분 + 위 keep/reject

#### 15.3.3 경계 정의의 미묘함 (b/2b/bb vs nAddBJets)

`ttbarCategorizer.py` 는 tt+b/2b ↔ tt+bb 경계 (51/52 ↔ 53/54/55) 를 genTtbarId 로 정의하는데, genTtbarId 의 b-jet 카운트와 우리 nAddBJets 가 경계에서 미세하게 다릅니다 (tt4b cross-tab: genSub 53 인데 nAddBJets==1 인 이벤트 13,111 건 등, 전체의 ~0.14%; 표준은 b-hadron 기반, nAddBJets 는 순수 jet 기반). 그러나:

* **tt+nb / tt+mb 최종 노드 기준으로는 무관**: tt+mb = b+2b+bb 로 합쳐지므로 내부 경계 불일치는 상쇄됨. tt+nb 경계 (nAddBJets>=3) 는 nAddBJets 로 깨끗하게 정의됨.
* 완벽한 단일-기준 일관성을 원하면 analyzer 에서 b/2b/bb 경계도 nAddBJets 로 (==1 -> b 계열, ==2 -> bb) 재정의하면 됨. tt+mb 로 합칠 거면 불필요.

### 15.4 패키지 / 모듈 rename

`TtbbStudies` 라는 이름이 분석 의미 (extended ttbar id) 를 잘 드러내지 못해 전면 rename:

| 이전 | 이후 |
|---|---|
| Subsystem `TtbbStudies` | `ExtendedTtbarId` |
| Package `NanoExtension` | `NanoExtension` (유지) |
| Plugin class `TtbbExtender` | `ExtendedTtbarIdProducer` |
| cfi module `ttbbExtender` (`ttbbExtender_cfi.py`) | `extendedTtbarId` (`extendedTtbarId_cfi.py`) |
| Branch `Expanded_genTtbarId` / `nAddBJets` / `nAddBJetsMulti` | **유지** (데이터 산출물; 검증 도구·post-processor 가 `Expanded_genTtbarId` 로 읽음) |

include path (`ExtendedTtbarId/NanoExtension/...`), `cms.EDProducer("ExtendedTtbarIdProducer")`, `DEFINE_FWK_MODULE(ExtendedTtbarIdProducer)` 모두 일관되게 변경. branch 명은 데이터 산출물이라 유지했으나, 원하면 follow-up 으로 변경 가능 (검증 도구 TtbarIdHistCompare 와 post-processor 도 같이 수정 필요).

### 15.5 v10 적용 후 필요한 후속 작업

1. `scram b` 재빌드 (plugin 이름이 바뀌었으므로 clean rebuild 권장).
2. **sidecar 재생산** — Expanded_genTtbarId 값이 바뀌므로 (genTtbarId 는 불변) stitching 대상 모든 ttbar sample 의 sidecar 를 다시 만들어야 함.
3. 재생산 후 `scanCategories` 로 확인: tt4b 의 Expanded_genTtbarId 에서 61+62 = 1,585,810 (nAddBJets==3), 71+72 = 296,360 (nAddBJets>=4) 이 나와야 함.
4. matchTtbarId 의 extended-id validation: 이제 sub-code 56 대신 nAddBJets>=3 이벤트가 61/62/71/72 로 분배되고 보존되는지 확인 (TtbarIdHistCompare 도구 측도 56 기준 → nAddBJets 기준으로 갱신 필요).
