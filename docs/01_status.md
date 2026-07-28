# 01 — Status: 지금 우리는 어디인가

> **목적**: 임의의 에이전트가 "현재 상태"를 확인하는 단일 지점.
> **대상 독자**: 모든 기여자 (사람·AI).
> **상태**: 살아있는 문서 — 마지막 의미있는 갱신 **2026-07-27** (v13.12: 2018 전량 재제출 결정 — upj 10 · mem 2500; T-19 job 상한 사고).
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
| **CRAB `units_per_job` 기본 10 — task 당 job 10,000 상한을 넘기면 SUBMITREFUSED(조용히)** | DECIDED 2026-07-27 | [04](04_decisions.md) **D15**, [08](08_troubleshooting.md) T-19 |

## OPEN — 다음에 반드시 할 일

| # | 항목 | 세부 |
|---|---|---|
| O1 | **rename 후 첫 실빌드/실행 확인 (lxplus)** — ✅ **CLOSED 2026-07-27** | ✅ `scram b -j8` 통과: plugin 패키지(`TtbarIdExtender/`) 정상 컴파일, `Validation/src/`→`tools/` rename으로 scram 간섭 제거([08](08_troubleshooting.md) T-15, [04](04_decisions.md) D14). ✅ `cmsRun run_ttbarIdExtend_cfg.py year=2018` 로 **로컬 2000-event 생산 1회 완료**(7 branch, missing 0) — O6 참조. ⏳ 남은 것 하나: `Validation`에서 `make`(standalone) 후 **소규모 `matchTtbarId` 1회** — grid 산출물이 도착하면 O6 ⑦ 에서 자연히 수행된다 |
| O2 | **analyzer 측 좌표 변경 (PROPOSED)** | patch 파일 새 명명(`ttbarIdPatch_*`/`TtbarIdPatch`)을 tempTTHH `ExpandedTtbarId` loader에 반영할지 결정. 정확한 3-line diff는 [07](07_analyzer_integration.md) §4. 반영 전까지 기존 산출물(`Validation/lookup/ttnb_*.root`, 구 규약)이 현행 계약 |
| O3 | `das_lineage.py` 실사용 검증 여부 불명 | `Validation/scripts/`로 이동 보관. docstring상 file-level MiniAOD↔NanoAOD lineage 도구이나, 과거 실행 기록이 문서에 없음 — 사용 전 1회 동작 확인 필요 |
| O4 | 이전에 제출된 CRAB 프로젝트의 resubmit | 기존 `crab_*` 디렉토리는 구 경로(`.../NanoExtension/...`) pset을 기억함. 구 태스크 resubmit은 구 체크아웃에서 할 것 ([08](08_troubleshooting.md) T-13) |
| O5 | Run3 / CMSSW 14_X migration | 미착수. 체크리스트는 [09_environment.md](09_environment.md) §3 |
| **O6** | **2018UL 생산 + validation (진행 중; 2026-07-27 실기기 확인 완료 단계 표시)** | ✅ **실기기 확인됨**: `scram b` / `preflight.py` 5/5 / `cmsRun year=2018`(era modifier 정상) / 로컬 2000-event 생산(7 branch, missing 0) / **`resolve_parents.sh 2018` 로 7개 MiniAOD 부모 확정 후 `datasets.yaml` 반영·개방** (TTbar_SemiLep 은 mini `-v2`/nano `-v1` **비대칭**). 도중 ASCII 위반(em-dash)으로 submitter 즉사 → 파일 ASCII 환원 + `load_yaml` utf-8 명시로 해소([03](03_changelog.md) v13.2). PyROOT 불가 확인 → `Validation/scripts/check_extend_invariants.C` 매크로로 불변조건 검증. ⚠️ **2018 extend 제출 — 7샘플 중 6샘플만 실제로 돌았다(2026-07-27)**: preflight 31 PASS/0 FAIL, client 는 `submitted : 7` / 20,953 jobs 를 보고했지만 **`TTbar_SemiLep` 은 서버가 `SUBMITREFUSED`** 했다 — 10,010 jobs > CRAB 의 **task 당 상한 10,000**([08](08_troubleshooting.md) **T-19**). 제출 시점엔 거부되지 않고 서버가 나중에 세워 두므로 **로그만 보면 성공으로 보인다.** 나머지 6 task(10,943 jobs)는 정상: 5개 COMPLETED(TT4b 188/188, TTbb_SemiLep 219/219, TTbb_Hadronic 169/169, TTbb_DiLep 103/103) + TTbar_Hadronic 99.6%(7168/7195) + TTbar_DiLep 98.7%(3028/3069), **failed 0**. 산출 LFN `/store/user/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2018` (T3_CH_CERNBOX → `/eos/user/j/junghyun/...`). **조치 (사용자 결정 2026-07-27): 2018 전량 재제출.** `site_config.yaml` 캠페인 기본값을 `units_per_job: 1 -> 10`, `max_memory_mb: 2000 -> 2500`(관측 피크 1731 MB 대비 헤드룸 확보)로 올렸고, `--preflight --check-das` 가 DAS `nfiles` 로 task 당 job 수를 계산해 상한 초과 시 FAIL 하도록 했다. ✅ **재제출 완료 — 7 tasks / 11,946 jobs / failed 0, 전부 COMPLETED (2026-07-27).** 단 설정은 **혼합**이었다: `TTbar_SemiLep` upj=10(**1,003** jobs = 1,001 + CRAB block 경계 +2), 나머지 6개 upj=1(188/7,195/3,069/219/169/103 = MiniAOD 파일 수). 재제출이 `site_config.yaml` 기본값 1→10 커밋 **전**에 이뤄져 `datasets.yaml` per-entry override 만 적용됐기 때문이다 — **증거 확정**: `crab.log` 에 `unitsPerJob = 1`(6)/`10`(SemiLep) 과 **`maxMemoryMB = 2000`**(2500 은 upj=10 과 같은 커밋이므로 그 커밋이 없었다는 증명), task 전부 `260727_1650xx` UTC 신규 제출·skip 0 ([08](08_troubleshooting.md) **T-20**). **무해하므로 재생산하지 않는다**(D15: packing 은 물리에 무관, 산출물 동일). '전부 upj=10 = 2,097 jobs' 는 **다음 제출**의 기대치다. 절차 `TtbarIdExtender/README.md` **§2.2c**. kill 완료 전에 EOS 를 지우면 늦은 stage-out 이 디렉토리를 되살려 timestamp 2개 → `matchTtbarId` exit 7 이 된다. **2017 은 재생산 대상이 아니다**(산출물은 packing 과 무관하게 동일). 로컬 불변조건 7개 PASS(확장 분기 63 event 실측). ✅ **옛 스모크 정리 완료** — `--kill --yes` (KILLED / scheduler COMPLETED done=5/5) → project dir 삭제 → EOS `2018/` 디렉토리 전체 삭제 후 본제출. **새 생산은 clean 한 상태에서 시작**했고 timestamp 중복은 없다. (v13.5 의 중복-제출 가드는 예방용으로 유지.) 코드는 era 파라미터화 완료([03](03_changelog.md) v13): `datasets.yaml` `"2018"` 블록(7샘플, **`enabled:true`/`verified:true` — 2026-07-27 개방됨**), cfg `year=` 옵션, submitter 전달, `resolve_parents.sh 2018`, filelist 스크립트 era 인자. <br>**끝난 단계** ①~⑤: `resolve_parents.sh 2018` → `datasets.yaml` 반영 → `preflight.py` → `--dry-run` → **7샘플 본제출**. ④ 의 `--max-files N` 스모크는 **금지로 전환됐다**(부분 산출물이 CRAB timestamp 를 하나 더 만들어 뒤늦게 `matchTtbarId` exit 7 로만 드러남 — 스모크는 `--process <최소샘플>` 로 **한 샘플 통째로** 한다, [03](03_changelog.md) v13.5). <br>⏳ **남은 순서** ⑥~⑨: ⑥ 완료 대기 → 산출물 `check_extend_invariants.C` 검증 → `make_filelists_miniAOD.py 2018 <EOS경로>`·`make_nano_filelists_das.sh 2018` → `nano2018/`·`sidecar2018/` ⑦ 소형 4샘플 `matchTtbarId`, 대형 3샘플(TTbar_*: 476M/334M/145M — 2017 대비 최대 +38%) `sortSplitExtend`→`matchTtbarIdSorted` ⑧ `extractTtbarIdPatch` 로 patch 7편 → `DerivedCorr/expandedTtbarId/2018` 복사 ⑨ 결과 수치는 [06](06_validation_results.md)에 **append**. **주의**: 2017 의 tt+nb 기대 수치(1,882,170 = 61/62 1,585,810 + 71/72 296,360 — 정본은 [06](06_validation_results.md))는 2018 의 합격 기준이 **아니다**(event 수 자체가 다름). nano 측 입력은 중앙 NanoAODv9 파일 목록으로도 가능(`matchTtbarId` 는 run/lumi/event/genTtbarId 만 읽음) |

## 지금 이 저장소로 할 수 있는 것 (요약)

1. **생산**: `TtbarIdExtender/` — MiniAODv2 → ttbarId-extend (로컬 cmsRun 또는 CRAB 일괄; [TtbarIdExtender/README.md](../TtbarIdExtender/README.md)).
2. **검증**: `Validation/` — ttbarId-extend ↔ 중앙 NanoAOD per-event 대조, 분포 플롯 ([Validation/README.md](../Validation/README.md)).
3. **소비 준비**: `Validation/bin/extractTtbarIdPatch` — analyzer가 올릴 per-sample patch 파일 생성. 기존 7개 산출물은 `Validation/lookup/`에 보존.
