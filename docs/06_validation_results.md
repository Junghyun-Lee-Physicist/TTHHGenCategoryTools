# 06 — Validation results (측정 수치의 단일 출처)

> **목적**: 이 프로젝트가 신뢰 가능함을 입증하는 **측정된** 결과 전부. 다른 문서는 여기로 링크만 한다.
> **대상 독자**: `Expanded_genTtbarId`를 분석에 쓰기 전 근거를 확인하려는 사람.
> **상태**: DECIDED (2017 UL 캠페인 완료 2026-06; 수치는 검증 로그에서 전사). 새 era/샘플 결과는 이 문서에 append. 마지막 append **2026-10-15 (11)** (2016 patch 추출 열넷, 행 수 대조; 그 전 2026-10-15: 2016 preVFP·postVFP — 중앙 NanoAODv9 전량 대조, 맨 끝 절), 그 전 2026-09-28 (2018 UL 중앙 NanoAODv15 재검증).
> **관련**: 검사 로직은 [05](05_architecture.md) §3, 도구 사용법은 [Validation/README.md](../Validation/README.md), 명령 원문과 로그 맥락은 동결 원본 [legacy/Validation_pre-merge_ARCHITECTURE.md](legacy/Validation_pre-merge_ARCHITECTURE.md) §8.

## 결론 먼저 (BLUF)

2017 UL ttbar stitching **7개 샘플, 합계 ~7.12억 event 전량**에서: (1) ttbarId-extend `genTtbarId` ≡ 중앙 NanoAODv9 (**disagree 0, unmatched 0**), (2) 확장 id 무결성 4조건 위반 **0**, 보존식 정확 성립, (3) 재분류 event의 출처는 **전부** 표준 tt+bb 버킷(53/54/55). analyzer용 patch 파일 7편의 카운트가 검증 로그와 일치.

**2018 UL (2026-09-28)**: 2018 patch 를 중앙 **NanoAODv15** 6 샘플 전량(972,574,595 event)에 다시 맞춰 **6/6 PASS**. extend 와 v15 의 event 수가 같은 네 샘플은 tt+nb 수와 61/62/71/72 분해가 patch 추출 표와 정확히 같고, v15 가 더 적은 두 샘플은 기대값과 통계 요동 안에서 맞는다. 보류했던 `ttnb_TTbar_SemiLep.root` 도 v15 용으로 해제. 맨 끝 절.

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

---

## 2018 UL — patch 추출 (extractTtbarIdPatch), **7/7 완료** 2026-07-28

전부 `exit 0`, 전부 도구 자체 교차검사 `selected == nAddBJets>=3` 통과. 구규약으로 뽑았다
(`ttnb_<KEY>.root` / tree `TtNb` — 현행 analyzer 계약, [07](07_analyzer_integration.md) §4).

| sample (short → KEY) | extend rows | tt+nb rows | tt+bbb (61+62) | tt+4b (71+72) | 61 / 62 | 71 / 72 |
|---|---|---|---|---|---|---|
| tt4b → TT4b | 9,844,000 | **1,950,601** | 1,643,462 | 307,139 | 1,237,381 / 406,081 | 273,348 / 33,791 |
| ttbb_Hadronic → TTbb_Hadronic | 8,049,064 | **33,072** | 29,165 | 3,907 | 19,629 / 9,536 | 3,478 / 429 |
| ttbb_SemiLeptonic → TTbb_SemiLep | 10,378,681 | **37,420** | 33,157 | 4,263 | 22,173 / 10,984 | 3,806 / 457 |
| ttbb_2L2Nu → TTbb_DiLep | 4,858,850 | **15,766** | 13,978 | 1,788 | 9,271 / 4,707 | 1,588 / 200 |
| TTTo2L2Nu → TTbar_DiLep | 146,010,000 | **11,790** | 10,541 | 1,249 | 7,311 / 3,230 | 1,146 / 103 |
| TTToSemiLeptonic → TTbar_SemiLep | 478,982,000 | **44,851** | 40,155 | 4,696 | 27,991 / 12,164 | 4,358 / 338 |
| TTToHadronic → TTbar_Hadronic | 343,248,000 | **36,835** | 32,822 | 4,013 | 22,844 / 9,978 | 3,702 / 311 |
| **7샘플 합계** | | **2,130,335** | 1,803,280 | 327,055 | | |

(2017 전체 참고값: tt+nb 1,882,170 = 1,585,810 + 296,360 — **2018 의 기준이 아니다**.)

### extract 수치와 validation 수치의 관계 (중요 — 오해 방지)

`extractTtbarIdPatch` 는 **extend 전체**를 훑고, validation 의 `nAddBJets>=3` 은 **matched(=nano)
event 위에서만** 센다. extend 는 nano 의 상위집합이므로 **extract ≥ validation** 이고, 차이는
extend-only event 안의 tt+nb 개수다. 그래서:

> **extend rows == DAS nevents 인 샘플은 두 값이 정확히 일치해야 한다.**

`ttbb_Hadronic` 이 그것을 실증한다 — extend 8,049,064 == DAS 8,049,064 이고 extract **33,072** =
validation **33,072** (완전 일치). `ttbb_2L2Nu` 는 extend 가 66,000 event 더 많아 차이 **193** 이
났고, 그 193 이 sub-code 분해(61/62/71/72)와 원 sub-code 분해(53/54/55) **양쪽에서 모두 193 으로
합**했다 — 정합성의 증거다(기대값 66,000 × 0.3245% ≈ 214).

**condor 결과 대조용 예측** (extra = extend − DAS nevents):

| sample | extra events | 예측 validation `nAddBJets>=3` |
|---|---|---|
| tt4b | 0 | **1,950,601** (정확히 일치) |
| ttbb_Hadronic | 0 | **33,072** ✅ 이미 확인 |
| ttbb_SemiLeptonic | 0 | **37,420** (정확히 일치) |
| ttbb_2L2Nu | 66,000 | **15,573** ✅ 이미 확인 (예측 ~15,552) |
| TTTo2L2Nu | 990,000 | ~11,710 |
| TTToSemiLeptonic | 2,574,000 | ~44,610 |
| TTToHadronic | 9,042,000 | ~35,865 |

extra == 0 인 세 샘플은 **정확한 등식**이므로 가장 강한 검사다.

### 물리적 타당성 (tt+nb 비율)

| sample | tt+nb / extend |
|---|---|
| tt4b (전용 tt+4b) | **19.82%** |
| ttbb_Hadronic / SemiLep / DiLep | 0.41% / 0.36% / 0.32% |
| TTToHadronic / TTToSemiLeptonic / TTTo2L2Nu (inclusive) | 0.0107% / 0.0094% / 0.0081% |

전용 ≫ ttbb ≫ inclusive 순서가 맞고, tt4b 가 tt+4b(71+72) 비중도 가장 높다(15.7% vs 다른 샘플
~11%) — 진짜 b 4개가 더 자주 나오는 샘플이므로 예상대로다. 2017 에서도 `ttnb_tt4b.root` 가 전체
11.5 MB 중 10.5 MB 였다(같은 구조).

---

## 2018 UL — condor 전량 검증 결과 (49 job, 2026-07-28)

배관은 완전 성공: `--report` 기준 **49/49 ok, fail 0, miss 0**. 물리 판정은 **6/7 PASS, 1 FAIL**.

| sample | 판정 | nano total == DAS | unmatched | disagree | `nAddBJets≥3` | 불변식 |
|---|---|---|---|---|---|---|
| tt4b | **PASS** | 9,844,000 ✓ | 0 | 0 | 1,950,601 | 0 |
| ttbb_Hadronic | **PASS** | 8,049,064 ✓ | 0 | 0 | 33,072 | 0 |
| ttbb_SemiLeptonic | **PASS** | 10,378,681 ✓ | 0 | 0 | 37,420 | 0 |
| ttbb_2L2Nu | **PASS** | 4,792,850 ✓ | 0 | 0 | 15,573 | 0 |
| TTToHadronic | **PASS** | 334,206,000 ✓ | 0 | 0 | 35,849 | 0 |
| TTTo2L2Nu | **PASS** | 145,020,000 ✓ | 0 | 0 | 11,700 | 0 |
| **TTToSemiLeptonic** | **FAIL** | **467,498,000 vs 476,408,000** | 0 | 0 | 43,832 | 0 |

### TTToSemiLeptonic 이 왜 FAIL 인가 — 두 독립 증거

**① 합산기의 결손**: 루프 후 재조회한 `GetEntries()` 합이 DAS 보다 **8,910,000 (1.87%)** 작다.
`matched` 는 DAS 와 정확히 일치했지만 **그것이 가짜 신호였다** — `GetEntry()` 반환값을 검사하지
않아 실패한 읽기가 직전 event 를 재사용했기 때문이다([08](08_troubleshooting.md) T-23 ⑧).

**② extract 와의 차이가 유일하게 어긋난다.**

| sample | 관측차 | 기대차 | 관측/기대 |
|---|---|---|---|
| tt4b / ttbb_Hadronic / ttbb_SemiLeptonic | 0 | 0 | **정확 일치** |
| ttbb_2L2Nu | 193 | 214 | 0.90 |
| TTToHadronic | 986 | 970 | **1.02** |
| TTTo2L2Nu | 90 | 80 | 1.12 |
| **TTToSemiLeptonic** | **1,019** | 241 | **4.23** ★ |

**두 결손이 정량적으로 일치한다**: entry 결손 **1.87%** vs tt+nb 결손 **1.74%**. 우연이 아니다.

**조치**: `checkRead()` 추가 후 `TTToSemiLeptonic` **재실행 필요**. 나머지 6샘플 patch 는 유효하고,
`ttnb_TTbar_SemiLep.root` 만 재검증 통과 전까지 **사용 보류**.

### `part_loads` 실측

chunk 당 4,000–8,000 회. event 수에 비례하고 part 총개수와 무관하다는 예측이 맞았다
(TTToHadronic 687 parts → 7,380/chunk, TTToSemiLeptonic 958 parts → 7,906/chunk,
TTTo2L2Nu 293 parts → 4,371/chunk). 전량이 ~1.7시간에 끝나 최적화는 불필요하다.

---

## 2018 UL: 중앙 NanoAODv15 재검증 (63 job, 2026-09-28), **6/6 PASS**

**왜**: ttHH 생산이 NanoAODv15 로 옮겨 갔으므로(NtupleForge D-2026-09-22-production-order) 2018 patch 를 v15 event 집합 위에서 다시 맞췄다
([01](01_status.md) O8, NtupleForge `docs/12_fastpath_workflow_plan.md` V1). 같은 extend(sidecar, MiniAOD)를 `matchTtbarIdSorted` 로 중앙 v15 에 대조했다.
nano 쪽 목록은 `Validation/filelists/nano2018v15`(`make_nano_filelists_das.sh 2018v15`, 14 / 15 / 8 / 407 / 589 / 169 파일),
완결성 기준은 `Validation/data/das_nevents_2018v15.json`. `tt4b` 는 중앙 v15 가 없어 대상이 아니다(D17 enriched 쪽에서 본다).

**실행**: 2026-09-27 17:49 UTC 에 63 job 제출(cluster 13488511). lxplus 의 `matchTtbarIdSorted` 를 다시 빌드하지 않은 채 제출해서 `TTToHadronic` 21 chunk 중
19 개가 exit 4(nano 파일 읽기 실패; 옛 binary 에는 읽기 재시도가 없다)로 끝났다. 조용한 오답이 아니라 **드러난 실패**였다. 09-28 에 다시 빌드하고
(`strings bin/matchTtbarIdSorted | grep -c reopening` = 1) 그 19 개만 다시 냈다(cluster 13489070): `--report` 63/63 ok, fail 0, miss 0.
합산 `aggregate_validation.py --era 2018 --nano-filelist-dir filelists/nano2018v15 --xsec-db data/das_nevents_2018v15.json` 의 끝줄
**`OVERALL: ALL SAMPLES PASS`**. 로그: NtupleForge `script/runlogs/run_v1_aggregate_20260928_083134.log`(제출은 `run_v1_submit_20260927_174937.log`).

| sample | nano total == v15 DAS | unmatched | disagree | 불변식 4종 | `nAddBJets≥3` (= extended) | 기대값 | 61 / 62 | 71 / 72 | 재분류된 event 의 원 sub-code 53 / 54 / 55 |
|---|---|---|---|---|---|---|---|---|---|
| ttbb_Hadronic | 7,946,064 ✓ | 0 | 0 | 0 | **32,660** | ≈ 32,649 | 19,387 / 9,412 | 3,436 / 425 | 22,812 / 9,548 / 300 |
| ttbb_SemiLeptonic | 10,378,681 ✓ | 0 | 0 | 0 | **37,420** | 37,420 (정확) | 22,173 / 10,984 | 3,806 / 457 | 25,973 / 11,102 / 345 |
| ttbb_2L2Nu | 4,858,850 ✓ | 0 | 0 | 0 | **15,766** | 15,766 (정확) | 9,271 / 4,707 | 1,588 / 200 | 10,853 / 4,766 / 147 |
| TTToHadronic | 343,248,000 ✓ | 0 | 0 | 0 | **36,835** | 36,835 (정확) | 22,844 / 9,978 | 3,702 / 311 | 26,529 / 10,076 / 230 |
| TTToSemiLeptonic | 460,133,000 ✓ | 0 | 0 | 0 | **43,090** | ≈ 43,086 | 26,908 / 11,661 | 4,197 / 324 | 31,072 / 11,754 / 264 |
| TTTo2L2Nu | 146,010,000 ✓ | 0 | 0 | 0 | **11,790** | 11,790 (정확) | 7,311 / 3,230 | 1,146 / 103 | 8,453 / 3,275 / 62 |

읽는 법:

- **정확한 등식 네 개**: extend rows == v15 DAS 인 네 샘플(ttbb_SemiLeptonic, ttbb_2L2Nu, TTToHadronic, TTTo2L2Nu)은 `nAddBJets≥3` 이 위 patch 추출 표의
  tt+nb rows 와 같고, 61/62/71/72 분해까지 한 자리도 다르지 않다. v15 의 tt+nb event 전부가 patch 에 있고 patch 행 전부가 v15 에 있다는 뜻이다.
- **두 샘플은 기대대로 작다**: v15 가 MiniAOD 보다 적다(TTToSemiLeptonic 460,133,000 vs extend 478,982,000, ttbb_Hadronic 7,946,064 vs 8,049,064).
  빠진 event 가 tt+nb 비율에서 무작위라고 보면 44,851 × 460,133,000 / 478,982,000 = 43,086(관측 43,090, 차 +4, 통계 요동 σ ≈ 41),
  33,072 × 7,946,064 / 8,049,064 = 32,649(관측 32,660, 차 +11, σ ≈ 20).
- **unmatched 0**: v15 의 모든 event 가 extend 에 있다. v15 의 부모 MiniAOD 가 sidecar 입력과 같은 판이라는 뜻이다(NtupleForge `docs/12` X2 의 우려 해소).
- **재분류는 전부 53/54/55 에서** 왔고 그 합이 `nAddBJets≥3` 과 같다(예: ttbb_Hadronic 22,812 + 9,548 + 300 = 32,660).
- analyzer 조회 점검(NtupleForge `docs/12` X4)의 샘플별 기대값은 이 표의 `nAddBJets≥3` 이다(전 job 의 hit 합).

**결론**: 2018 patch 중 중앙 v15 가 있는 6 편(`ttnb_TTbb_Hadronic`, `ttnb_TTbb_SemiLep`, `ttnb_TTbb_DiLep`, `ttnb_TTbar_Hadronic`, `ttnb_TTbar_SemiLep`,
`ttnb_TTbar_DiLep`)은 v15 ntuple 에 그대로 쓴다. 07-28 의 v9 FAIL 로 보류했던 **`ttnb_TTbar_SemiLep.root` 도 v15 용으로 보류 해제**: patch 는 extend 전체에서
뽑은 것이고, v9 FAIL 의 원인은 검증 쪽 읽기(`GetEntry()` 반환값 미검사, [08](08_troubleshooting.md) T-23 ⑧)였으며, 이번에는 읽기 검사와 재시도가 있는
도구로 v15 전량에서 통과했다. `ttnb_TT4b.root` 는 중앙 v15 가 없어 이 검사 밖이다(v15 의 `TT4b` 는 enriched 생산이고 확장 id 열을 직접 싣는 설계, D17).
v9 쪽 `TTToSemiLeptonic` 재실행은 하지 않는다(2018 v9 ntuple 보류, NtupleForge D-2026-09-17-ul18-v9-parked).

## 2016 preVFP(`2016APV`)·postVFP(`2016`): 중앙 NanoAODv9 전량 대조 (16 + 22 job, 2026-10-15), **14/14 PASS**

**무엇을**: UL16 의 ttbarId-extend(MiniAODv2 → sidecar, CRAB `ttbarIdExtend_v2/2016APV`·`/2016`, manager `REPORT.txt` ALL PASS 14 task)를 중앙
NanoAODv9(`RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11`, `RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17`)에
`matchTtbarIdSorted` 로 대조([01](01_status.md) O9 ⑧, `Validation/README.md` §0.1c). 완결성 기준 `Validation/data/das_nevents_2016APV.json`,
`das_nevents_2016.json`.

**실행**: 2016APV 16 chunk — 15 개는 cluster 13530917 에서 ok, `file_TTToSemiLeptonic_4` 는 xrootd open 이 1813 s 뒤 `Operation expired`(exit 4)
→ 다시 낸 job 은 셸에 남은 v15 의 cmsenv 때문에 exit 127([08](08_troubleshooting.md) T-42) → `--cmssw-base`·`--container` 를 적어 cluster 13535254
에서 ok. 2016 22 chunk — 첫 제출(13532885) 22 개 모두 같은 이유로 exit 127 → cluster 13535253 에서 22/22 ok. `--report` 두 era 모두
`All chunks produced a result`, 합산 `aggregate_validation.py --era 2016APV|2016` 의 끝줄 둘 다 **`OVERALL: ALL SAMPLES PASS`**
(`~/val_summary_2016APV.json`, `~/val_summary_2016.json`, lxplus).

| era | sample | chunks | nano total == DAS | unmatched | disagree | 불변식 4종 | `nAddBJets≥3` (= extended) | 61 / 62 | 71 / 72 | 재분류된 event 의 원 sub-code 53 / 54 / 55 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016APV | tt4b | 1 | 4,801,000 ✓ | 0 | 0 | 0 | **951,209** | 603,102 / 197,724 | 133,947 / 16,436 | 736,843 / 206,481 / 7,885 |
| 2016APV | ttbb_Hadronic | 1 | 2,303,410 ✓ | 0 | 0 | 0 | **9,278** | 5,417 / 2,751 | 950 / 160 | 6,368 / 2,814 / 96 |
| 2016APV | ttbb_SemiLeptonic | 1 | 2,991,789 ✓ | 0 | 0 | 0 | **10,919** | 6,471 / 3,230 | 1,087 / 131 | 7,554 / 3,275 / 90 |
| 2016APV | ttbb_2L2Nu | 1 | 1,388,348 ✓ | 0 | 0 | 0 | **4,521** | 2,673 / 1,310 | 490 / 48 | 3,162 / 1,320 / 39 |
| 2016APV | TTToHadronic | 4 | 97,260,000 ✓ | 0 | 0 | 0 | **10,384** | 6,475 / 2,837 | 993 / 79 | 7,464 / 2,865 / 55 |
| 2016APV | TTToSemiLeptonic | 6 | 132,178,000 ✓ | 0 | 0 | 0 | **12,381** | 7,697 / 3,401 | 1,170 / 113 | 8,854 / 3,453 / 74 |
| 2016APV | TTTo2L2Nu | 2 | 37,505,000 ✓ | 0 | 0 | 0 | **3,150** | 1,967 / 852 | 306 / 25 | 2,273 / 857 / 20 |
| 2016 | tt4b | 1 | 4,848,000 ✓ | 0 | 0 | 0 | **956,533** | 606,875 / 198,831 | 134,193 / 16,634 | 740,886 / 207,945 / 7,702 |
| 2016 | ttbb_Hadronic | 1 | 2,597,868 ✓ | 0 | 0 | 0 | **10,668** | 6,333 / 3,061 | 1,149 / 125 | 7,479 / 3,090 / 99 |
| 2016 | ttbb_SemiLeptonic | 1 | 3,223,118 ✓ | 0 | 0 | 0 | **11,819** | 6,956 / 3,477 | 1,229 / 157 | 8,184 / 3,503 / 132 |
| 2016 | ttbb_2L2Nu | 1 | 1,571,799 ✓ | 0 | 0 | 0 | **5,040** | 2,968 / 1,487 | 528 / 57 | 3,496 / 1,492 / 52 |
| 2016 | TTToHadronic | 8 | 107,067,000 ✓ | 0 | 0 | 0 | **11,486** | 7,209 / 3,097 | 1,091 / 89 | 8,287 / 3,119 / 80 |
| 2016 | TTToSemiLeptonic | 7 | 144,722,000 ✓ | 0 | 0 | 0 | **13,505** | 8,421 / 3,671 | 1,308 / 105 | 9,717 / 3,694 / 94 |
| 2016 | TTTo2L2Nu | 3 | 43,546,000 ✓ | 0 | 0 | 0 | **3,494** | 2,153 / 958 | 365 / 18 | 2,516 / 961 / 17 |

읽는 법:

- **두 분해의 합이 모두 `nAddBJets≥3` 과 같다**(61+62+71+72 와 53+54+55, 14 행 모두): 재분류는 전부 표준 tt+B 버킷(53/54/55)에서 왔다.
- **tt+nb 비율이 2018 과 같은 크기**: tt4b 19.81 % / 19.73 %(2018 19.8 %), ttbb_* 0.32–0.41 %(2018 v15 0.32–0.41 %), TTTo* 0.008–0.011 %(2018 v15
  0.008–0.011 %). era 합 2016APV 1,001,842, 2016 1,012,545.
- **unmatched 0 은 nano 의 모든 event 가 extend 에 있다는 뜻이다.** UL16 에서는 MiniAOD 가 nano 보다 많은 항목이 다섯이라([01](01_status.md) O9) 그 표본의
  patch(extend 전체에서 뽑는다)는 위 `nAddBJets≥3` 보다 조금 클 수 있다(2018 의 "extract ≥ validation" 과 같은 관계); extend 행 = DAS nano 인 표본은 같아야 한다 —
  patch 추출(⑨)의 행 수로 확인한다.

## 2016 preVFP·postVFP — patch 추출(extractTtbarIdPatch), **14/14 완료** 2026-10-15

lxplus `cmssw-el7`(CMSSW_10_6_32_patch1), `Validation/` 에서 era 마다 `bin/extractTtbarIdPatch --filelist filelists/sidecar<ERA>/filelist_<short>.txt
--out lookup<ERA>/ttnb_<KEY>.root --out-tree TtNb --label <KEY>_<2016preVFP|2016postVFP>`(TTHHAnalyzer 의 이름·tree 규약 = 2018). 열넷 모두 exit 0,
요약마다 `>>> OK: selection consistent (sub in {61,62,71,72} <=> nAddBJets>=3)`. 맥으로 scp 한 뒤 md5 열넷이 lxplus 값과 같음 → TTHHAnalyzer
`DerivedCorr/expandedTtbarId/2016{preVFP,postVFP}/`(그쪽 README.txt 에 md5; `git add -f`).

| era | KEY (short) | extend 입력 행 | DAS nano | patch 행 | 검증 `nAddBJets≥3` | 차 | 기대(extend−nano)×(율) | 61 / 62 / 71 / 72 |
|---|---|---|---|---|---|---|---|---|
| 2016APV | TT4b (tt4b) | 4,801,000 | 4,801,000 | **951,209** | 951,209 | 0 | 0 | 603,102 / 197,724 / 133,947 / 16,436 |
| 2016APV | TTbb_Hadronic | 2,303,410 | 2,303,410 | **9,278** | 9,278 | 0 | 0 | 5,417 / 2,751 / 950 / 160 |
| 2016APV | TTbb_SemiLep | 2,991,789 | 2,991,789 | **10,919** | 10,919 | 0 | 0 | 6,471 / 3,230 / 1,087 / 131 |
| 2016APV | TTbb_DiLep | 1,388,348 | 1,388,348 | **4,521** | 4,521 | 0 | 0 | 2,673 / 1,310 / 490 / 48 |
| 2016APV | TTbar_Hadronic | 97,600,000 | 97,260,000 | **10,435** | 10,384 | +51 | 36 ± 6 | 6,507 / 2,851 / 998 / 79 |
| 2016APV | TTbar_SemiLep | 132,178,000 | 132,178,000 | **12,381** | 12,381 | 0 | 0 | 7,697 / 3,401 / 1,170 / 113 |
| 2016APV | TTbar_DiLep | 37,505,000 | 37,505,000 | **3,150** | 3,150 | 0 | 0 | 1,967 / 852 / 306 / 25 |
| 2016 | TT4b (tt4b) | 4,848,000 | 4,848,000 | **956,533** | 956,533 | 0 | 0 | 606,875 / 198,831 / 134,193 / 16,634 |
| 2016 | TTbb_Hadronic | 2,597,868 | 2,597,868 | **10,668** | 10,668 | 0 | 0 | 6,333 / 3,061 / 1,149 / 125 |
| 2016 | TTbb_SemiLep | 3,337,118 | 3,223,118 | **12,231** | 11,819 | +412 | 418 ± 20 | 7,200 / 3,596 / 1,277 / 158 |
| 2016 | TTbb_DiLep | 1,571,799 | 1,571,799 | **5,040** | 5,040 | 0 | 0 | 2,968 / 1,487 / 528 / 57 |
| 2016 | TTbar_Hadronic | 109,380,000 | 107,067,000 | **11,722** | 11,486 | +236 | 248 ± 16 | 7,348 / 3,165 / 1,118 / 91 |
| 2016 | TTbar_SemiLep | 144,974,000 | 144,722,000 | **13,536** | 13,505 | +31 | 24 ± 5 | 8,436 / 3,684 / 1,311 / 105 |
| 2016 | TTbar_DiLep | 43,630,000 | 43,546,000 | **3,500** | 3,494 | +6 | 7 ± 3 | 2,156 / 961 / 365 / 18 |

읽는 법: extend = DAS nano 인 아홉 행은 patch 행 = 검증의 `nAddBJets≥3` 이 **정확히** 같다(같은 event 집합). extend 가 큰 다섯 행은 patch 가 그만큼
크고, 그 차는 (extend − nano) × (검증의 tt+nb 율)과 맞는다(가장 먼 것: 2016APV TTbar_Hadronic +51 대 36 ± 6, +2.4σ — nano 에 없는 event 라 analyzer 는
그 행을 만나지 않는다). 각 칸(61/62/71/72)도 patch ≥ 검증.

## 2024(Run 3, `RunIII2024Summer24`): extend `REPORT.txt` ALL PASS, lookup 일곱(condor `prep2024`), 중앙 NanoAODv15 대조(156 job) — **matched 전부 일치, unmatched 다섯 표본(nano 의 0.06 % 이하)**

extend(CMSSW_15_0_18, `year=2024`, manager `extend2024`, `REPORT.txt` 2026-10-16 07:21:16 UTC; TTbar_Hadronic job 1012 는 lxplus 에서 직접 —
[04](04_decisions.md) D22):

| task | jobs | rows = MiniAOD ev | ge3 | 61 | 62 | 71 | 72 |
|---|---|---|---|---|---|---|---|
| 2024/TT4b | 46 | 9,898,300 | 1,958,250 | 1,246,292 | 402,583 | 275,596 | 33,779 |
| 2024/TTbar_SemiLep | 1,102 | 484,298,177 | 47,600 | 29,545 | 13,038 | 4,616 | 401 |
| 2024/TTbar_Hadronic | 1,081 | 475,006,856 | 53,889 | 33,541 | 14,598 | 5,301 | 449 |
| 2024/TTbar_DiLep | 1,093 | 470,080,053 | 40,336 | 25,112 | 10,924 | 3,994 | 306 |
| 2024/TTbb_SemiLep | 100 | 22,478,238 | 85,959 | 51,135 | 24,601 | 9,209 | 1,014 |
| 2024/TTbb_Hadronic | 64 | 14,988,225 | 63,776 | 38,101 | 17,924 | 6,942 | 809 |
| 2024/TTbb_DiLep | 71 | 12,498,392 | 42,693 | 25,332 | 12,215 | 4,638 | 508 |

`RESULT: ALL PASS`(7 task, 3,557 job, 모두 PASS).

**lookup**(condor `prep2024`, cluster 13538989; `extractTtbarIdPatch --out-tree TtNb --label <KEY>_2024`, 같은 job 에서 `sortSplitExtend` → EOS
`sorted2024/<short>/`, `index.txt` 마지막): 일곱 job 모두 `RESULT=OK` — patch 행 = ge3, 61/62/71/72 = 위 표, 입력 행 = rows = 정렬 행.
md5(job = EOS `lookup2024/` = 맥 = TTHHAnalyzer 801f059 의 `DerivedCorr/expandedTtbarId/2024/`):

| KEY | md5 |
|---|---|
| TT4b | 7c1d9627f650e67c449e098f97d528e4 |
| TTbb_Hadronic | 7bd8bda6d70cf31caccee8dcfe486351 |
| TTbb_SemiLep | beef3085984f2028363fded52b1d5699 |
| TTbb_DiLep | 799303ed6e6abfa0e53f8e38a3d50c19 |
| TTbar_Hadronic | 860bfaa7b82f7d9334e6174a13180b5a |
| TTbar_SemiLep | 50c4c939ad1bad0520554d7d14287c50 |
| TTbar_DiLep | cff7b32e041a25a35f7d0514e8f4777f |

**DAS nevents, Nano 대 MiniAOD**(TTHHAnalyzer `make_manifest.py`, lxplus 2026-10-16; Nano 합 1,486,995,493 = `Validation/data/das_nevents_2024.json`):

| KEY | Nano | MiniAOD (= extend rows) | Nano − MiniAOD |
|---|---|---|---|
| TT4b | 9,898,300 | 9,898,300 | 0 |
| TTbar_SemiLep | 484,475,057 | 484,298,177 | +176,880 |
| TTbar_Hadronic | 472,535,695 | 475,006,856 | −2,471,161 |
| TTbar_DiLep | 470,123,263 | 470,080,053 | +43,210 |
| TTbb_SemiLep | 22,473,402 | 22,478,238 | −4,836 |
| TTbb_Hadronic | 14,990,580 | 14,988,225 | +2,355 |
| TTbb_DiLep | 12,499,196 | 12,498,392 | +804 |

음수(Nano < MiniAOD)는 extend ⊇ nano 라 정상(2016 의 다섯과 같은 방향). 양수 넷은 [01](01_status.md) O10 의 (i)/(ii) — 대조의 unmatched 가 가른다.

**중앙 NanoAODv15 대조**([../Validation/README.md](../Validation/README.md) §0.1d): preflight READY, 32 PASS(156 job: tt4b 2, ttbb_Hadronic 10,
ttbb_SemiLeptonic 15, ttbb_2L2Nu 11, TTToHadronic 39, TTToSemiLeptonic 40, TTTo2L2Nu 39). smoke(cluster 13540386, `file_ttbb_2L2Nu_0`, nano 20 파일):
nano_entries 787,920 = matched = agree, unmatched 0, disagree 0, 위반 넷 0, `ext_consistent` true, exit 0. 전량 156 job: cluster 13540390(2026-10-16
17:45 UTC 제출) — 결과는 aggregate 뒤 이 절에.

**전량 대조 결과**(2026-10-17, lxplus `--report`: TOTAL `156 156 0 0 0`; `aggregate_validation.py --era 2024 --json-out ~/val_summary_2024.json`):

| sample | nano = DAS | matched | unmatched | disagree | 보존 ge3 = extended | 위반 넷 | MiniAOD − matched | 판정 |
|---|---|---|---|---|---|---|---|---|
| tt4b | 9,898,300 | 9,898,300 | 0 | 0 | 1,958,250 | 0 | 0 | PASS |
| ttbb_Hadronic | 14,990,580 | 14,988,225 | 2,355 | 0 | 63,776 | 0 | 0 | FAIL(unmatched 만) |
| ttbb_SemiLeptonic | 22,473,402 | 22,473,402 | 0 | 0 | 85,937 | 0 | 4,836 | PASS |
| ttbb_2L2Nu | 12,499,196 | 12,498,392 | 804 | 0 | 42,693 | 0 | 0 | FAIL(unmatched 만) |
| TTToHadronic | 472,535,695 | 472,248,265 | 287,430 | 0 | 53,580 | 0 | 2,758,591 | FAIL(unmatched 만) |
| TTToSemiLeptonic | 484,475,057 | 484,276,067 | 198,990 | 0 | 47,598 | 0 | 22,110 | FAIL(unmatched 만) |
| TTTo2L2Nu | 470,123,263 | 470,080,053 | 43,210 | 0 | 40,336 | 0 | 0 | FAIL(unmatched 만) |

`OVERALL: AT LEAST ONE SAMPLE FAILED` — 실패한 검사는 다섯 표본 모두 `unmatched == 0` 하나뿐이다. 모든 chunk exit 0, chunk 이상 없음.
(보존 열은 matched 사건 안의 ge3 라, 위 extend 표의 ge3 보다 extend 에만 있는 사건의 ge3 만큼 작을 수 있다: ttbb_SemiLeptonic 22, TTToHadronic 309,
TTToSemiLeptonic 2.)

**해석.**
1. **lookup 의 내용은 겹치는 모든 사건에서 맞다:** 일곱 표본 모두 disagree 0, 위반 넷 0, 보존 ge3 == extended.
2. **unmatched 는 '어느 쪽 dataset 에 어떤 파일이 VALID 인가' 의 차이다, 중복이 아니다:** ttbb_Hadronic 2,355, ttbb_2L2Nu 804, TTTo2L2Nu 43,210 은
   위 DAS 표의 Nano − MiniAOD 와 정확히 같고 extend 행은 모두 nano 에서 찾혔다(MiniAOD − matched = 0) → nano 에는 지금의 VALID MiniAOD 에 없는 parent
   파일의 사건이 들어 있다([01](01_status.md) O10 의 (i)). (ii) NanoAOD 중복이었다면 그 사건들도 matched 로 잡혀 unmatched 는 0 이었을 것이다.
   TTToSemiLeptonic(nano 에만 198,990, extend 에만 22,110)과 TTToHadronic(nano 에만 287,430, extend 에만 2,758,591)은 **양쪽 모두에** 상대에 없는 파일이
   있다 — 두 dataset 에서 무효가 된 파일이 다르다는 뜻. 파일 단위 확인(`scripts/das_lineage.py`, 아직 실사용 안 됨 — O3)은 남은 일.
3. **분석에 주는 영향:** analyzer 의 lookup 은 tt+nb 행만 갖고, 없는 사건은 NanoAOD 의 `genTtbarId` 를 그대로 쓴다(TTHHAnalyzer `ExpandedTtbarId.h`
   `resolve`). 그래서 잘못 분류될 수 있는 것은 unmatched 중 진짜 tt+≥3b 사건뿐 — 기대 수 = unmatched × (ge3 / matched): TTToHadronic 33, TTToSemiLeptonic
   20, TTTo2L2Nu 4, ttbb_Hadronic 10, ttbb_2L2Nu 3 사건(가중 전), 각 표본 ge3 의 0.06 % 이하. prescan(stitch 의 합)과 production 이 같은 lookup·같은 규칙을
   쓰므로 정규화는 서로 맞는다.
4. **판정 제안(사용자 결정):** "matched 전부 일치 + unmatched 는 DAS 파일 유효성 차이(영향 < 0.1 % of ge3)" 로 2024 lookup 을 쓴다 — TTHHAnalyzer 의
   plan `AN` 전환(그쪽 D-2026-10-15-F)의 문을 연다. 워크스페이스 `coord/DECISIONS_PENDING.md` D1·A1.
