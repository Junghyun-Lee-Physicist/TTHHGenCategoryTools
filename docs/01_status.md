# 01 — Status: 지금 우리는 어디인가

> **목적**: 임의의 에이전트가 "현재 상태"를 확인하는 단일 지점.
> **대상 독자**: 모든 기여자 (사람·AI).
> **상태**: 살아있는 문서 — 마지막 의미있는 갱신 **2026-07-05** (v11 병합·rename).
> **관련**: 숫자 전체는 [06_validation_results.md](06_validation_results.md), 결정 근거는 [04_decisions.md](04_decisions.md), 변경 이력은 [03_changelog.md](03_changelog.md).

## 결론 먼저 (BLUF)

**알고리즘·검증은 완료 상태다.** 2017 UL ttbar stitching 7개 샘플 전체(~7.12억 event)에서 ttbarId-extend `genTtbarId`가 중앙 NanoAODv9와 100% byte-identical, 확장 id(`Expanded_genTtbarId`)의 무결성 조건 전량 통과, analyzer용 patch 파일 7개 추출 완료 (2026-06). 2026-07-05에 저장소 병합(생산 패키지 + 검증 도구)과 rename 을 수행했다. 이름은 최종적으로 subsystem `TTHHGenCategoryTools`, 패키지 `TtbarIdExtender`(NanoExtension→GenSidecar→TtbarIdExtender), 출력 `ttbarIDExtend.root`(구 `sidecar.root`), lookup `extractTtbarIdPatch`(구 `extractTtNb`)로 정리됐다 — **rename 이후 재빌드·스모크 테스트는 아직 실기기에서 수행되지 않았다** (아래 OPEN).

## DECIDED — 확정되어 유지 중인 것

| 항목 | 상태 | 근거 문서 |
|---|---|---|
| Sidecar 방식(Approach 3)으로 생산; enriched NanoAOD(Approach 2)는 폐기 | DECIDED 2026-05-29 | [04](04_decisions.md) D1, [10](10_enriched_nanoaod_archive.md) |
| 확장 분기 조건 = `nAddBJets >= 3` (sub-code 56 의존 제거) | DECIDED 2026-06 (v10) | [04](04_decisions.md) D4, [02](02_physics.md) |
| 2017 UL 7개 샘플 byte-identity + 확장 무결성 검증 | 완료 2026-06 | [06](06_validation_results.md) |
| Analyzer 소비 방식 = per-sample patch 파일 membership lookup | DECIDED | [04](04_decisions.md) D9, [07](07_analyzer_integration.md) |
| Stitching: tt+nb는 dedicated tt4b 샘플에서 (AN option 1) | DECIDED | [02](02_physics.md) §5 |
| 패키지 rename `NanoExtension`→`GenSidecar`→`TtbarIdExtender`, subsystem `ExtendedTtbarId`→`TTHHGenCategoryTools`, 출력 `sidecar.root`→`ttbarIDExtend.root` | DECIDED 2026-07-05 (v12) | [04](04_decisions.md) D11·D13 |
| Lookup 도구/산출물 rename `extractTtNb`/`ttnb_*`/`TtNb` → `extractTtbarIdPatch`/`ttbarIdPatch_*`/`TtbarIdPatch` (도구 기본값 측) | DECIDED 2026-07-05 | [04](04_decisions.md) D12 |
| ttbarId-extend 출력 기본 파일명 `ttbarIDExtend.root` 유지 | DECIDED 2026-07-05 | [04](04_decisions.md) D13 |

## OPEN — 다음에 반드시 할 일

| # | 항목 | 세부 |
|---|---|---|
| O1 | **rename 후 첫 실빌드/실행 확인 (lxplus)** — 부분 완료 (v12) | ✅ `scram b -j8` 통과: plugin 패키지(`TtbarIdExtender/`) 정상 컴파일, `Validation/src/`→`tools/` rename으로 scram 간섭 제거([08](08_troubleshooting.md) T-15, [04](04_decisions.md) D14). plugin-lib 이름은 빌드 성공으로 preflight 글롭과 정합 추정(직접 `.so` 확인은 권장). ⏳ 아직 안 함: `cmsRun run_ttbarIdExtend_cfg.py`로 실제 ttbarId-extend 생산 1회, `Validation`에서 `make`(standalone) 후 소규모 `matchTtbarId` 1회 — 이 두 개로 end-to-end 확인 |
| O2 | **analyzer 측 좌표 변경 (PROPOSED)** | patch 파일 새 명명(`ttbarIdPatch_*`/`TtbarIdPatch`)을 tempTTHH `ExpandedTtbarId` loader에 반영할지 결정. 정확한 3-line diff는 [07](07_analyzer_integration.md) §4. 반영 전까지 기존 산출물(`Validation/lookup/ttnb_*.root`, 구 규약)이 현행 계약 |
| O3 | `das_lineage.py` 실사용 검증 여부 불명 | `Validation/scripts/`로 이동 보관. docstring상 file-level MiniAOD↔NanoAOD lineage 도구이나, 과거 실행 기록이 문서에 없음 — 사용 전 1회 동작 확인 필요 |
| O4 | 이전에 제출된 CRAB 프로젝트의 resubmit | 기존 `crab_*` 디렉토리는 구 경로(`.../NanoExtension/...`) pset을 기억함. 구 태스크 resubmit은 구 체크아웃에서 할 것 ([08](08_troubleshooting.md) T-13) |
| O5 | Run3 / CMSSW 14_X migration | 미착수. 체크리스트는 [09_environment.md](09_environment.md) §3 |

## 지금 이 저장소로 할 수 있는 것 (요약)

1. **생산**: `TtbarIdExtender/` — MiniAODv2 → ttbarId-extend (로컬 cmsRun 또는 CRAB 일괄; [TtbarIdExtender/README.md](../TtbarIdExtender/README.md)).
2. **검증**: `Validation/` — ttbarId-extend ↔ 중앙 NanoAOD per-event 대조, 분포 플롯 ([Validation/README.md](../Validation/README.md)).
3. **소비 준비**: `Validation/bin/extractTtbarIdPatch` — analyzer가 올릴 per-sample patch 파일 생성. 기존 7개 산출물은 `Validation/lookup/`에 보존.
