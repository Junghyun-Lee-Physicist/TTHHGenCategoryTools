# 05 — Architecture: 어떻게 만들어졌나

> **목적**: 생산(GenSidecar) → 검증(Validation) → 소비(analyzer)의 3단 구조, 각 구성요소의 역할과 확장 지점.
> **대상 독자**: 코드를 수정·확장하려는 사람.
> **상태**: DECIDED 구조 (v8.1 ttbarId-extend 설계 + 2026-06 검증 도구 + 2026-07-05 병합 레이아웃).
> **관련**: 물리·인코딩은 [02](02_physics.md)(정본), 설계 결정의 왜는 [04](04_decisions.md), 수치는 [06](06_validation_results.md), 소비 계약은 [07](07_analyzer_integration.md).

## 결론 먼저 (BLUF)

한 event의 확장 ttbar-Id는 다음 경로로 분석에 도달한다: **MiniAODv2 → (GenSidecar, cmsRun/CRAB) → ttbarIDExtend.root → (Validation, byte-identity 검증) → (extractTtbarIdPatch) → ttbarIdPatch_<sample>.root → (analyzer, (run,lumi,event) membership lookup) → per-event `expandedTtbarId` + stitch weight.** NanoAOD 재생산은 어디에도 없다.

## 1. 전체 데이터 흐름

```
                     [ GenSidecar : CMSSW 패키지, scram, CMSSW_10_6_32_patch1 ]
 MiniAODv2 ──▶ matchGenBHadron ─▶ matchGenCHadron ─▶ categorizeGenTtbar ─▶ ExtendedTtbarIdProducer ─▶ TtbarIdExtendAnalyzer
 (slimmedGenJets,          (표준: PhysicsTools.NanoAOD.ttbarCategorization_cff)      (this pkg)              (this pkg)
  ...FlavourInfos,                                        │ genTtbarId                 │ expandedGenTtbarId,      │
  prunedGenParticles)                                     ▼                            ▼ nAddBJets[Multi]         ▼
                                                                                              ttbarIDExtend.root (top-level "Events",
                                                                                              run/lumi/event + 4 Int 계열 branch)
        ┌──────────────────────────────────────────────────────────────────────────────────────────┘
        │                                [ Validation : standalone ROOT/Makefile ]
        ├─▶ compareExtendToCentral (GenSidecar/bin, scram) ─ 소규모 스팟체크: ttbarId-extend.genTtbarId ≡ central
        ├─▶ makeTtbarHist + plotTtbarCompare ─ 분포/shape 비교 (per-bin ratio 숫자 표기)
        ├─▶ matchTtbarId ──────────────┐  전량 per-event 대조 (소샘플: 전체 map)
        ├─▶ sortSplitExtend ─▶ matchTtbarIdSorted ┘ (대샘플: external sort + part binary search)
        └─▶ extractTtbarIdPatch ─▶ ttbarIdPatch_<sample>.root  (tt+nb row만; 구 규약 ttnb_*/TtNb)
                                              │
                     [ analyzer (tempTTHH, 별도 저장소) ]  ▼
                     ExpandedTtbarId::loadFromDir → resolve(run,lumi,event,genTtbarId)
                     → expandedTtbarId branch + StitchFactors multiplier            ([07] 참조)
```

## 2. GenSidecar (CMSSW 패키지) — 구성요소 레퍼런스

| 파일 | 역할 | 핵심 계약 |
|---|---|---|
| `plugins/ExtendedTtbarIdProducer.cc` | 유일한 물리 로직. 표준 `genTtbarId` + `matchGenBHadron` 산출물(genBHadJetIndex, genBHadFromTopWeakDecay) + `slimmedGenJets`에서 acceptance(pT>20, |η|<2.4) 안 `nAddBJets`/`nAddBJetsMulti`를 직접 세고, `nAddBJets>=3`이면 sub-code를 61/62/71/72로 교체(prefix 보존) | EDM products: `expandedGenTtbarId`(underscore 금지 규칙), `nAddBJets`, `nAddBJetsMulti`. `edm::global::EDProducer<>` (stream-safe, 상태 없음) |
| `plugins/TtbarIdExtendAnalyzer.cc` | 자체 TFile을 열어 **top-level** `Events` TTree 작성 (D5). NanoAOD 타입 정합: run/i, luminosityBlock/i, event/l, 나머지 /I. endJob에서 `BuildIndex("run","event")` + `Write(kOverwrite)` | `safeGetInt` try/catch(missing product는 LogError+fallback 0, 카운터 집계), untracked `verbose`로 per-event 로그 게이팅 |
| `python/extendedTtbarId_cfi.py` | producer 기본 파라미터 (acceptance, 4개 InputTag) | 표준 모듈명(`categorizeGenTtbar`, `matchGenBHadron`) 기본값 |
| `python/ttbarIdExtend_cff.py` | 표준 3 producer + 우리 2 모듈의 시퀀스와 **`addTtbarIdExtend(process, outputFile, verbose)`** 원샷 부착 함수. 진입/단계/종료를 stdout으로 보고, 기존 attribute 존중/교체를 명시 로그 | schedule이 이미 있으면 append, 없으면 생성 (`getattr(process,"schedule",None)` — hasattr 함정 회피) |
| `test/run_ttbarIdExtend_cfg.py` | 최소 hand-written cfg (NANO step 없음 → hand-written이 안전한 이유가 주석에 명시). VarParsing: `inputFiles/outputFile/maxEvents/verbose`. CRAB submit-time의 빈 inputFiles를 허용(경고만) | GlobalTag 불필요(gen-only). era modifier는 downstream 일관성용으로만 유지 |
| `bin/compareExtendToCentral.cc` | 소규모 스팟체크 비교기: ttbarId-extend 전체를 `(run<<...)^...` 3-key hash에 적재 후 central을 streaming — `genTtbarId` byte 일치 + sub-code 분포 + tt+bb 보존식(central(53–55) = ttbarId-extend(53–55)+(61–72)) | exit 0 = 전량 일치. `--tree-*`, `--max-events`, `--dump-mismatches` |
| `crab/` | `datasets.yaml`(7개 stitching 샘플, nano_child 병기, DAS parent 확인 절차), `site_config.yaml`(T3_KR_KNU, LFN base, 자원), `submit_ttbarIdExtend.py`(--dry-run/--max-files/--status/--resubmit), `preflight.py`(환경 5종 점검), `resolve_parents.sh`, `status.py` | pset 경로·plugin 글롭이 문자열 결합 — [00_PROMPT](../00_PROMPT.md) §3 |
| `archive/enriched_nanoaod/` | 폐기된 Approach 2의 cmsDriver-emit cfg 4편, **무수정 보존** | 실행 금지·사실 기록은 [10](10_enriched_nanoaod_archive.md) |

Sidecar schema (branch → 의미)는 [02_physics.md](02_physics.md) §3 + 위 analyzer 행이 전부다: `run, luminosityBlock, event, genTtbarId, Expanded_genTtbarId, nAddBJets, nAddBJetsMulti`.

## 3. Validation (standalone) — 구성요소 레퍼런스

CMSSW 불필요; `root-config`만 있으면 `make`. 각 `src/*.cc`가 `bin/<이름>` 실행파일 하나 (Makefile 와일드카드 — 파일명 = 도구명).

| 도구 | 역할 | 실패 계약 |
|---|---|---|
| `makeTtbarHist` | filelist에서 `genTtbarId`(+ ttbarId-extend 모드에서 Expanded/nAddBJets*) 히스토그램 채움. id branch만 읽음 | — |
| `plotTtbarCompare` | ttbarId-extend vs nano sub-code overlay; 채워진 bin 위에 per-bin ratio 숫자(1에서 벗어나면 red). `--match` 모드로 matchTtbarId 산출 히스토도 그림. `--normalize/--logy` | 1.0에서 벗어난 sub-code를 stdout에 나열 |
| `matchTtbarId` | **결정적 검증(소샘플)**: ttbarId-extend 전체를 3-key map으로 적재, 모든 nano event를 lookup — `genTtbarId` 일치 + 확장 무결성 4조건(iff·prefix·정확 매핑·불변) 검사 | exit 0 ok / 5 no-match / 6 id 불일치 / 7 중복 key / 8 확장 무결성 / (9) run≠1 |
| `sortSplitExtend` | external sort: chunk-sort(기본 1000만 row) → k-way merge → `part%05d.root`(기본 50만 row ≈ 16 MB) + `index.txt`(part별 first/last 3-key). part 간 key 범위 비중첩 보장 | `--chunk-size/--part-size`로 메모리 조절 |
| `matchTtbarIdSorted` | 대샘플용 matchTtbarId: index binary-search로 covering part만 적재(1개 상주) | 검사 항목·exit 계약은 matchTtbarId와 동일 |
| `extractTtbarIdPatch` | analyzer 소비용 patch 파일 생산: `Expanded%100∈{61,62,71,72}`(⇔`nAddBJets≥3`) row만 추출, 두 기준 불일치 시 abort. 요약 카운트는 match 로그와 일치해야 함 | exit 0/2 args/3 filelist/7 selection 불일치. 구 규약 호환: `--out ttnb_X.root --out-tree TtNb` |
| `scanOrder` | filelist의 per-file (run,lumi,event) 정렬·범위 진단 (streaming, 메모리 무시 가능) | — |
| `scripts/submit_hist_condor.py`, `scripts/merge_hists.sh` | makeTtbarHist의 HTCondor 병렬화 + hadd 병합 | — |
| `scripts/das_lineage.py` | DAS file-level parent/child lineage 조회 (grid proxy + dasgoclient 필요) | 사용 이력 OPEN ([01](01_status.md) O3) |
| `filelists/` | 7개 샘플의 nano/ttbarId-extend filelist (검증 캠페인 실사용 입력) | — |
| `lookup/` | 2026-06 산출 patch 7편 (**구 규약** ttnb_*/TtNb — 내부 tree명 고정이라 보존; `lookup/README.txt`) | — |

## 4. 왜 이 3단인가 (설계 성질)

1. **release-cycle 면역**: gen-level producer interface는 10_2–14_X에서 불변. NANO step을 안 거치므로 NanoAOD 버전이 v9→v15로 가도 ttbarId-extend 코드는 영향 없음 — 입력 MiniAOD era/GT만 갱신 ([09](09_environment.md)).
2. **검증 단순성**: byte-identity 질문이 branch 1개(`genTtbarId`)로 줄고, 확장 id는 ttbarId-extend 자체 데이터(`nAddBJets`)에 대한 **결정적 함수 검증**으로 완결 (NanoAOD에 비교 대상이 없어도 충분한 이유: base가 byte-identical + 확장은 deterministic mapping — [06](06_validation_results.md) §3).
3. **소비 최소화**: analyzer는 예외-전용 소파일 하나와 membership 판정만 필요 (D9).

## 5. 확장 지점 (새 era/샘플 추가 시)

1. `TtbarIdExtender/crab/datasets.yaml`에 (MiniAODv2, nano_child) 쌍 추가 — parent suffix는 `crab/resolve_parents.sh`로 DAS 확인 후 기입.
2. era가 다르면 `run_ttbarIdExtend_cfg.py`의 era modifier와 datasets.yaml의 era 블록 갱신 ([09](09_environment.md) §3.7).
3. CRAB 4단계 강제 순서: `preflight.py` → `--dry-run` → `--max-files 5` 스모크 → 본제출.
4. `Validation/filelists/`에 nano/ttbarId-extend filelist 생성(`make_filelists*.py`) → 소샘플은 `matchTtbarId`, 대샘플(대략 5천만 event 초과)은 sorted 경로 → `extractTtbarIdPatch`.
