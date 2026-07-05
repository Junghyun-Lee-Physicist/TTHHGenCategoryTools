# 06 — Validation results (측정 수치의 단일 출처)

> **목적**: 이 프로젝트가 신뢰 가능함을 입증하는 **측정된** 결과 전부. 다른 문서는 여기로 링크만 한다.
> **대상 독자**: `Expanded_genTtbarId`를 분석에 쓰기 전 근거를 확인하려는 사람.
> **상태**: DECIDED (2017 UL 캠페인 완료 2026-06; 수치는 검증 로그에서 전사). 새 era/샘플 결과는 이 문서에 append.
> **관련**: 검사 로직은 [05](05_architecture.md) §3, 도구 사용법은 [Validation/README.md](../Validation/README.md), 명령 원문과 로그 맥락은 동결 원본 [legacy/Validation_pre-merge_ARCHITECTURE.md](legacy/Validation_pre-merge_ARCHITECTURE.md) §8.

## 결론 먼저 (BLUF)

2017 UL ttbar stitching **7개 샘플, 합계 ~7.12억 event 전량**에서: (1) ttbarId-extend `genTtbarId` ≡ 중앙 NanoAODv9 (**disagree 0, unmatched 0**), (2) 확장 id 무결성 4조건 위반 **0**, 보존식 정확 성립, (3) 재분류 event의 출처는 **전부** 표준 tt+bb 버킷(53/54/55). analyzer용 patch 파일 7편의 카운트가 검증 로그와 일치.

## 1. per-event `genTtbarId` byte-identity — 7샘플 전량 일치 (2026-06)

소샘플 4종은 `matchTtbarId`(전체 map), 대샘플 3종은 `sortSplitExtend`→`matchTtbarIdSorted` 경로.

| 샘플 | nano events | matched | agree | disagree | unmatched |
|---|---:|---:|---:|---:|---:|
| TTToHadronic      | 232,999,999 | 232,999,999 | 232,999,999 | 0 | 0 |
| TTToSemiLeptonic  | 346,052,000 | 346,052,000 | 346,052,000 | 0 | 0 |
| TTTo2L2Nu         | 106,724,000 | 106,724,000 | 106,724,000 | 0 | 0 |
| tt4b              |   9,502,000 |   9,502,000 |   9,502,000 | 0 | 0 |
| ttbb_Hadronic     |   5,694,656 |   5,694,656 |   5,694,656 | 0 | 0 |
| ttbb_SemiLeptonic |   7,318,891 |   7,318,891 |   7,318,891 | 0 | 0 |
| ttbb_2L2Nu        |   3,472,503 |   3,472,503 |   3,472,503 | 0 | 0 |

의미: MiniAODv2에서 표준 chain으로 재유도한 `genTtbarId`가 중앙 값과 byte 단위 동일 — 확장의 **base가 정확**하다.

참고(모집단 효과): 분포 비교에서 TTToSemiLeptonic이 전 sub-code 균일 ~1.027 offset을 보였는데, DAS 확인 결과 MiniAODv2 355,332,000 vs NanoAODv9 child 346,052,000 (NanoAOD production이 ~9.28M, 2.68% drop) — ttbarId-extend(=MiniAOD 유래)가 정당하게 더 많은 것. per-event 검사는 nano에 존재하는 event만 lookup하므로 오염되지 않는다.

## 2. 확장 id (`Expanded_genTtbarId`) 무결성 — 전량 통과

전 샘플에서 다음 4개 위반 카운트가 **모두 0**: extended-but-nAddBJets<3, nAddBJets≥3-but-not-extended, prefix-changed, nAddBJets≤2-changed. 보존식 `#(nAddBJets≥3) == #(61)+#(62)+#(71)+#(72)` 정확 성립.

| 샘플 | tt+nb (nAddBJets≥3) | tt+bbb (61+62) | tt+4b (71+72) | tt+nb 비율 |
|---|---:|---:|---:|---:|
| tt4b              | 1,882,170 | 1,585,810 | 296,360 | 19.8 % |
| ttbb_SemiLeptonic |    26,544 |    23,468 |   3,076 | 0.36 % |
| ttbb_Hadronic     |    23,390 |    20,631 |   2,759 | 0.41 % |
| ttbb_2L2Nu        |    11,238 |     9,953 |   1,285 | 0.32 % |
| TTToSemiLeptonic  |    32,162 | (extract 로그에서 세부) | 〃 | 0.0093 % |
| TTToHadronic      |    25,097 | 〃 | 〃 | 0.0108 % |
| TTTo2L2Nu         |     8,559 | 〃 | 〃 | 0.0080 % |

tt4b의 1,585,810 / 296,360은 v10 수정 전 cross-tab에서 예측한 nAddBJets==3 / ≥4 카운트와 정확히 일치 — split 수정이 의도대로 발동함을 확정.

## 3. 왜 이 검사로 확장 id가 "충분히" 검증되는가

NanoAOD에는 `Expanded_genTtbarId`가 없어 직접 비교 대상이 없다. 논거: (a) §1이 base(`genTtbarId`)의 byte-identity를 입증, (b) 확장은 sidecar가 함께 담는 `(nAddBJets, nAddBJetsMulti)`의 **결정적 함수**이며, 그 함수·prefix 보존·불변(≤2) 조건을 matched event 전량에서 양방향(iff)으로 검사했다. base 정확 + deterministic mapping 검증 = 확장 id 검증 완결.

## 4. 재분류 출처 — 전부 표준 tt+bb 버킷에서 (tt4b 전수)

tt4b에서 60번대로 재분류된 1,882,170 event의 원래 sub-code: **53에서 1,458,666 / 54에서 408,116 / 55에서 15,388** — 51/52 등 다른 코드 유입 0. (a) 표준이 추가 b-jet ≥2를 53/54/55로 뭉뚱그린다는 사실과 (b) 우리가 그 안에서 `nAddBJets≥3`만 정확히 끄집어냄을 동시에 확인.

## 5. 물리적 함의 — stitching 설계(D10)의 데이터 근거

tt+nb 비율: dedicated tt4b **19.8%** ≫ 4FS ttbb ~0.3–0.4% ≫ inclusive ~0.008–0.011%. tt4b가 inclusive 대비 약 **1,800×** 밀도로 tt+nb를 담는다 → "tt+nb는 tt4b에서, 나머지는 각자 샘플에서"가 통계적으로 유일하게 합리적.

## 6. 대용량 경로 성능 (external sort)

`matchTtbarIdSorted`가 TTToSemiLeptonic 3.46억·TTToHadronic 2.33억 event를 **part 1개(~16 MB)만 상주**시킨 채 완주. part 수: TTToHadronic 472 / TTToSemiLeptonic 711 / TTTo2L2Nu 214. 전량-map 방식(~20 GB+)으로는 불가능했던 작업.

## 7. patch 추출(extract) 일관성

7개 샘플 patch 파일의 `selected rows / 61+62 / 71+72` 카운트가 §2의 검증 로그와 일치 — 추출 정확성의 판정 기준. 산출물은 `Validation/lookup/`(구 규약 ttnb_*/TtNb; [lookup/README.txt](../Validation/lookup/README.txt)).

## 8. (참고) ttbarId-extend 성립 이전의 검증 이력

- **v6.1 (CMSSW_14_2_1, TTToHadronic 84k × nano 1.28M)**: genTtbarId full/자릿수별/서브코드, nGenJet, leading-jet pT/η 전부 100%; confusion matrix 완전 대각.
- **v8/v8.1 (2026-05-29, TTbb_4f 100 events)**: ttbarId-extend `genTtbarId` 100/100 byte-identical; sub-code 분포 라인 단위 동일.
- **Approach 2 (v7.2, 2026-05-28)**: enriched NanoAOD 공통 **1,665 branch 전부 ratio=1.000** — 상세와 검증 경계는 [10_enriched_nanoaod_archive.md](10_enriched_nanoaod_archive.md).
