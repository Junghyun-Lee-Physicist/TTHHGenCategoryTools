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

---

## 2018 UL — condor 검증 (진행 중, 2026-07-28)

### 스모크: `ttbb_2L2Nu` (nano 6파일 = 샘플 전체, 1 job)

`matchTtbarIdSorted` 를 이 캠페인에서 **처음** 실데이터로 돌린 결과이며, 같은 샘플의 인터랙티브
`matchTtbarId` 결과와 **완전히 일치**한다 — 두 알고리즘이 같은 결론을 낸다는 실증.

| 항목 | 인터랙티브 `matchTtbarId` | condor `matchTtbarIdSorted` |
|---|---|---|
| nano entries | 4,792,850 (= DAS) | **4,792,850** ✓ |
| matched | 4,792,850 | **4,792,850** ✓ |
| unmatched | 0 | **0** ✓ |
| agree / disagree | 4,792,850 / 0 | **4,792,850 / 0** ✓ |
| nAddBJets≥3 | 15,573 | **15,573** ✓ |
| exit | 0 | **0** ✓ |

**성능 실측** (job 13284921, `condor_history`):

| | 값 |
|---|---|
| wall clock | **1,245 s = 20.8 분** |
| peak memory | **489 MB** (request 2000, CERN 하한 3000) |
| `part_loads` | **347** (index 의 part 수 = 10 → 이상값의 34.7배) |
| 처리율 | **231 k event/분** |

`part_loads` 가 이상값의 34.7배인 것은 **nano 가 키 순서로 저장돼 있지 않다**는 확인이다(사용자가
예측한 대로). 다만 감당 가능하다: 347 × 16 MB = 5.5 GB 추가 EOS 읽기이고, event 당 부하는
**part 총개수와 무관**하게 일정하다(1 load / 13,800 event).

sorted 경로는 이 소형 샘플에서 in-memory(11.5분)보다 **느리다**(20.8분) — 정상이다. sorted 는
메모리를 위해 I/O 를 지불하는 거래이고, 대형에서는 in-memory 가 애초에 불가능하다(15~38 GB).

### 대형 3샘플 외삽 (231 k event/분 기준)

| sample | chunk 수 | chunk 당 event | chunk 당 예상 |
|---|---|---|---|
| TTTo2L2Nu | 8 | ~18 M | ~79분 |
| TTToHadronic | 17 | ~20 M | ~87분 |
| TTToSemiLeptonic | 20 | ~24 M | ~104분 |

49 job 동시 → **전체 wall clock ~1.7시간** 예상. `+JobFlavour = "workday"`(8 h) 안에 여유.
직렬 ~38시간(T-22) 대비 **~22배**.

### 스모크 확정 — 합산기 PASS (job 13284921 재실행, 2026-07-28)

`results/file_ttbb_2L2Nu_0.json` 이 EOS 에 정상 도착하고 합산기가 **PASS** 했다. 하위 카운터까지
인터랙티브와 전부 일치:

| | 인터랙티브 | condor |
|---|---|---|
| tt+bbb (61+62) | 13,811 | **13,811** |
| tt+4b (71+72) | 1,762 | **1,762** |
| sub-code 61 / 62 | — / 4,652 | **9,159 / 4,652** |
| sub-code 71 / 72 | — / 199 | **1,563 / 199** |
| 원 sub-code 53/54/55 | 10,716 / 4,711 / 146 | **동일** |
| 보존식 ge3 == extended | — | 15,573 vs 15,573 |
| 불변식 4종 | 0 | **0** |

**단, 이 실행에서 `nano total == DAS nevents` 가 `[SKIP]` 이었다** — 기본 xsec-db 경로 추정이
lxplus 배치(별도 CMSSW 릴리스)와 맞지 않아서다. 완결성의 유일한 진짜 증명이 꺼진 채 PASS 가 난
것이므로 합산기를 고쳤다(**못 찾으면 FAIL**, [08](08_troubleshooting.md) T-23 ⑦). 값 자체는
`samples_2018UL.json` 에 있고 `TTbb_DiLep` = **4,792,850** 으로 정확히 일치하므로, `--xsec-db` 를
주고 재실행하면 이 기준도 통과한다.

2018 UL DAS nevents (대조 기준):

| KEY | nevents |
|---|---|
| TT4b | 9,844,000 |
| TTbb_Hadronic | 8,049,064 |
| TTbb_SemiLep | 10,378,681 |
| TTbb_DiLep | 4,792,850 |
| TTbar_Hadronic | 334,206,000 |
| TTbar_SemiLep | 476,408,000 |
| TTbar_DiLep | 145,020,000 |

