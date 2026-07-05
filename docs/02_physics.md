# 02 — Physics: 목적, 근거, 인코딩 명세 (정본)

> **목적**: 이 프로젝트가 왜 존재하는지, 그리고 `genTtbarId` / `Expanded_genTtbarId` 인코딩의 **저장소 내 단일 출처**.
> **대상 독자**: 물리적 의미를 알아야 하는 모든 사람; 코드를 읽기 전의 필독.
> **상태**: DECIDED (내용은 CMSSW 소스·TWiki·AN2022_122로 확정) — 2026-07-05 병합 시 재구성.
> **관련**: 개념의 확장 논의는 tempTTHH `docs/ttbarCategorization.md` §1–§3·§9 (분석 저장소 측 문서), 구현은 [05_architecture.md](05_architecture.md), 검증 수치는 [06_validation_results.md](06_validation_results.md).

## 결론 먼저 (BLUF)

표준 `GenTtbarCategorizer`(NanoAOD `genTtbarId`의 출처)는 **추가 b-jet이 2개 이상이면 개수와 무관하게 전부 sub-code 53/54/55(tt+bb)로 묶는다.** ttHH(bbbb) 분석(AN2022_122)은 tt+bbb(정확히 3개)와 tt+4b(4개 이상)를 별도 카테고리로 요구하므로, 우리가 추가 b-jet **개수**(`nAddBJets`)를 직접 세어 `genTtbarId` 위에 sub-code **61/62(tt+bbb), 71/72(tt+4b)** 를 얹는다. 그 결과가 `Expanded_genTtbarId`다.

## 1. 물리 동기

ttHH(HH→4b) fully-hadronic 최종 상태는 parton level에서 b 6개 + light quark 4개. 지배적 irreducible background는 **ttbar + 추가 b-jet** 계열이다. ttbar MC는 단일 샘플이 아니라 inclusive 5FS(추가 b는 parton shower에서)와 dedicated 4FS ttbb(ME가 명시 생성), 그리고 dedicated tt4b로 나뉘어 생산되며, 같은 위상공간을 중복으로 덮는다. 이를 이중계수 없이 합치려면(**stitching**) per-event heavy-flavour 라벨이 필요하고, tt+nb(=tt+bbb ∪ tt+4b) 경계는 `genTtbarId`만으로는 정의할 수 없다 — 그 간극을 이 프로젝트가 메운다.

"**additional(추가)**"의 정의 (AN2022_122 §3.1, GenHFHadronMatcher 기본값과 동일):
top decay에서 **오지 않은** b/c-hadron을 보유한 gen-jet, acceptance **pT > 20 GeV, |η| < 2.4**.

## 2. 표준 `genTtbarId` 인코딩 (정본: GenTtbarCategorizer.cc, TWiki Example 1)

```
genTtbarId = 10000·min(2, nCJetsFromW)      // top의 W에서 온 c
           +  1000·min(2, nBJetsFromW)      // top의 W에서 온 b (W→cb, 희귀)
           +   100·min(2, nBJetsFromTop)    // t에서 직접 온 b
           +         Z                      // 추가 radiation HF sub-code
```

| sub-code Z | 의미 |
|---:|---|
| 0 | tt+LF (추가 b/c jet 없음) |
| 41 / 42 | tt+c / tt+2c (추가 c-jet 1개; hadron 1 / ≥2) |
| 43·44·45 | tt+cc (추가 c-jet ≥ 2) |
| 51 / 52 | tt+b / tt+2b (추가 b-jet 1개; b-hadron 1 / ≥2) |
| 53·54·55 | tt+bb (**추가 b-jet ≥ 2**, 개수 무관) |

**핵심 사실 두 가지** (v9까지의 버그 원인이자 이 문서가 존재하는 이유):

1. 표준 스킴에 **sub-code 46/56은 존재하지 않는다.** 56은 TWiki **Example 2**(별도 test analyzer `matchGenHFHadrons.cc`)의 "pseudo-additional b jet" 값으로, `genTtbarId`와 무관하다.
2. 추가 b-jet이 2·3·4개든 전부 53/54/55다 — 즉 `genTtbarId`에서 tt+bbb/tt+4b는 **복원 불가능**하다. (MiniAOD에는 GenJet–b-hadron 연관 정보가 남아 있어 한 tier 위에서는 복원 가능 — 그래서 MiniAOD에서 sidecar를 만든다.)

## 3. 확장: `Expanded_genTtbarId` (이 프로젝트의 산출물)

분기 조건은 **오직 `nAddBJets`** (우리가 같은 입력으로 직접 센 un-capped 추가 b-jet 수):

```
Expanded_genTtbarId = genTtbarId                              (nAddBJets <= 2)
                    = (genTtbarId/100)*100 + newSub           (nAddBJets >= 3)
  newSub: nAddBJets == 3 → 61 (multi 0) / 62 (multi ≥1)   [tt+bbb]
          nAddBJets >= 4 → 71 (multi 0) / 72 (multi ≥1)   [tt+4b]
```

| Expanded %100 | 카테고리 | 조건 |
|---:|---|---|
| 61 / 62 | **tt+bbb** | 추가 b-jet 정확히 3개 (62 = 그중 b-hadron ≥2 보유 jet 존재, g→bb 병합) |
| 71 / 72 | **tt+4b** | 추가 b-jet 4개 이상 (72 = multi jet 존재) |

- 앞자리 prefix(100/1000/10000 자리)는 **항상 보존**된다 (예: 253 → 261).
- `nAddBJetsMulti` = 추가 b-jet 중 b-hadron ≥2개를 담은 jet 수. multi 구분(61 vs 62 등)은 AN보다 한 단계 세분(g→bb 연구용)이며, 분석에서는 **61+62 → tt+bbb, 71+72 → tt+4b**로 합친다.
- EDM product instance 이름은 `expandedGenTtbarId`(camelCase — EDM은 instance 이름에 underscore 금지)이고, ttbarId-extend TTree의 최종 branch 이름은 `Expanded_genTtbarId`다. 분석에서 읽는 이름은 후자다.

## 4. 왜 이 분할이 stitching에 정합한가

`Expanded_genTtbarId % 100`은 모든 ttbar event를 **완전하고 서로소인** 카테고리로 나눈다: {0} ∪ {41–45} ∪ {51} ∪ {52} ∪ {53,54,55} ∪ {61,62} ∪ {71,72}. tt+nb 경계는 단일 기준(`nAddBJets ≥ 3`)으로 정의되고, 같은 물리 event는 어느 샘플에 있든 같은 producer·같은 입력(matchGenBHadron 산출물)으로 계산되므로 같은 값을 받는다 → 샘플 간 라벨 일관, double-count도 gap도 없음. tt4b 전수 검증에서 재분류 event가 **전부** 53/54/55에서 나옴이 확인됐다 ([06](06_validation_results.md) §4).

경계의 미묘함: tt+b/2b ↔ tt+bb 경계(51/52 ↔ 53–55)는 표준이 b-hadron 기반, `nAddBJets`는 순수 jet 기반이라 극소수(~0.14%)가 어긋날 수 있으나, 분석의 최종 노드가 tt+mb(=b+2b+bb 합산)이므로 내부 경계 불일치는 상쇄된다. tt+nb 경계는 `nAddBJets` 단일 기준이라 이 문제가 없다.

## 5. Stitching 결정 (분석 채택안)

- **tt+bbb + tt+4b (= tt+nb)**: dedicated **tt4b** LO 샘플로 모델링 (AN option 1).
- 나머지: tt+b/2b/bb(= tt+mb)는 TTbb 4FS, tt+cc/LF는 tt inclusive 5FS.
- keep/reject (analyzer 단계, [07](07_analyzer_integration.md)):

```
tt4b 샘플        : Expanded%100 in {61,62,71,72} 이면 keep,  아니면 reject
그 외 ttbar 샘플 : Expanded%100 in {61,62,71,72} 이면 reject, 아니면 keep
```

따라서 stitching에 참여하는 **7개 샘플 전부**(TT4b, TTbb 4FS Had/SemiLep/DiLep, TTTo Hadronic/SemiLeptonic/2L2Nu)에 확장 id가 필요하다 — 각 샘플의 tt+bb 버킷 안에 숨은 `nAddBJets≥3` event를 골라내야 하기 때문. 물리적 정당화(tt+nb 밀도가 tt4b에서 inclusive의 ~1,800배)는 [06](06_validation_results.md) §5.

## 6. 참고 문헌

- CMSPublic GenHFHadronMatcher TWiki (Example 1 = `genTtbarId` 스킴): https://twiki.cern.ch/twiki/bin/view/CMSPublic/GenHFHadronMatcher
- CMSSW `TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc`; `PhysicsTools/NanoAOD/python/ttbarCategorization_cff.py`
- ttHH(bbbb) AN2022_122 §3.1–3.2 (7-카테고리 정의, stitching options)
