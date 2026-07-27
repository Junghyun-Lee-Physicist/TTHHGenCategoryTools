# 09 — Environment: CMSSW 10_6_X 함정과 14_X/15_X migration

> **목적**: release-cycle 차이로 인한 함정의 일반화 표와, Run3(14_X+) 이행 시 따라갈 체크리스트.
> **대상 독자**: 새 환경에서 빌드하는 사람; Run3 migration 담당.
> **상태**: 10_6_X 표는 DECIDED (v7.1–v7.2에서 전부 실측). migration은 **미실행** ([01](01_status.md) O5) — 체크리스트만 준비됨.
> **관련**: 각 함정의 발생 맥락은 [08_troubleshooting.md](08_troubleshooting.md) T-4·T-5, 원 기록(전체 표)은 [legacy/GenSidecar_pre-merge_ARCHITECTURE.md](legacy/GenSidecar_pre-merge_ARCHITECTURE.md) §13.

## 결론 먼저 (BLUF)

이 패키지는 **CMSSW_10_6_32_patch1** (UL NanoAODv9 production cycle: Python 2.7, gcc 7, ROOT 6.14, `slc7_amd64_gcc700`, lxplus에서는 `cmssw-el7` 컨테이너)에 pin 되어 있다 (근거: [04](04_decisions.md) D2). 코드는 v7.1–v7.2에서 10_6_X 함정을 전부 통과하도록 **방어적으로** 작성되어 있어, 14_X에서도 대부분 그대로 import/컴파일될 것으로 예상되지만 — **추정 금지**: 이행은 §3 체크리스트로 검증한다.

## 1. 10_6_X에서 지켜야 할 것 (현행 규약)

| 항목 | 규칙 | 어기면 |
|---|---|---|
| Python 파일 인코딩 | `TtbarIdExtender/python`·`test`는 ASCII-clean + PEP 263 헤더 유지, f-string 금지, `from __future__ import print_function` | Python 2가 import 시점에 SyntaxError (T-4) |
| MessageLogger | `process.load("FWCore.MessageService.MessageLogger_cfi")` 명시 후 `categories.append(...)`는 `hasattr` 가드 안에서 | AttributeError / 새 category 무시 |
| InputTag | 항상 명시적 `cms.InputTag(...)` (tuple 자동 변환은 12_X+ 전용) | `'tuple' object has no attribute 'find'` |
| C++ 경고 | unused variable 금지 (`-Werror`) | 빌드 실패 |
| Scheduling | Task 결합은 `Task.associate()` (Sequence `+=` 금지) | "Unrunnable schedule" (T-6) |
| 실행 환경 | lxplus(EL9)에서는 `cmssw-el7` 컨테이너 진입 후 `cmsenv` | scram arch 불일치 |
| **`python3` = 3.6.4** | 3.7+ API 금지: `subprocess.run(..., text=)`·`capture_output=` → `universal_newlines=True` / `stdout=PIPE`. `dict \|=`(3.9), `str.removeprefix`(3.9), `match`(3.10)도 불가 | **런타임** TypeError (import 시점엔 안 잡힌다). 2026-07-27 `submit_ttbarIdExtend.py --preflight` 가 `text=True` 로 즉사 (v13.3) |
| **`LANG=C`** | 파일을 읽을 때 **항상 `encoding=` 명시**. `open()` 기본 인코딩이 ASCII 다 | 파일 어딘가의 non-ASCII 1바이트가 전체를 죽인다: `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2`. 2026-07-27 `datasets.yaml` 주석의 em-dash 하나로 submitter 즉사 (v13.2) |
| **YAML·설정 파일도 ASCII-only** | `crab/*.yaml` 포함. 위 두 항목이 겹치면 진단이 어렵다 | 상동 (v12.5 에서 이미 한 번, v13.2 에서 재발) |
| **PyROOT 사용 불가** | 이 릴리스의 ROOT 6.14 는 **python2 빌드**다. python3 검증 스크립트를 쓰지 말고 **ROOT 매크로**(`Validation/scripts/*.C`)로 작성 | `ImportError: dynamic module does not define module export function (PyInit_libPyROOT)`. 2026-07-27 확인 → `check_extend_invariants.C` 신설 |

`crab/*.py`와 `Validation/scripts/*.py`는 **Python 2 제약(f-string 금지 등)에서는 자유롭지만
Python 3.6 제약은 그대로 받는다** — 위 표의 `python3 = 3.6.4` 행이 그것이다. "Python 3 니까
아무거나 써도 된다"는 뜻이 아니다. `Validation/tools/*.cc`는 CMSSW 무관 — `root-config` 기반
Makefile로 어느 ROOT 6.x에서든 빌드. `Validation/scripts/*.C`(ROOT 매크로)도 환경 무관.

> 이 4개 함정은 `TtbarIdExtender/crab/submit_ttbarIdExtend.py` 헤더에도 요약돼 있다
> (코드를 고치는 사람이 문서를 안 읽을 수 있으므로 의도적 중복 — 규칙 자체의 정본은 이 표다).

## 2. 10_6_X ↔ 14_X+ 호환 요약 (실측 기반)

현재 코드가 이미 "양쪽에서 도는 방향"으로 작성된 항목들:

| 항목 | 10_6_X | 14_X/15_X | 현재 코드 |
|---|---|---|---|
| PEP 263 헤더 | 필수 | 불필요·무해 | 유지 (호환) |
| `categories.append` | 필요 | attribute 자체 폐지 | `hasattr` 가드 → 14_X에선 자동 skip |
| 명시적 `cms.InputTag` | 필수 | 선택 | 명시 사용 (호환) |
| `edm::one::EDAnalyzer<>`, `edm::global::EDProducer<>`, `consumes<>` | OK | OK (10_2–15_X 안정) | 무변경 |
| `ULong64_t`/`BuildIndex`/`SetBranchAddress` 엄격성 | ROOT 6.14 | 6.26+ 동일 | 무변경 |
| FlatTable `IntColumn` 4번째 인자 명시 | **필수** (`defaultColumnType<int>` 없음) | 생략 가능하나 명시도 OK | archive의 enriched 계열에만 해당 |

주의가 필요한 단 하나의 축: **NanoAOD python 모듈 재배치**. `PhysicsTools.NanoAOD.ttbarCategorization_cff`의 위치는 cycle마다 바뀔 수 있다 — §3의 2번이 첫 관문.

## 3. 14_X / 15_X (Run3) migration 체크리스트 — 미실행, 순서대로

1. `cmsrel CMSSW_14_X_Y` + `cmsenv` → 패키지 unpack → `scram b` (컴파일 에러부터).
2. `python3 -c "from PhysicsTools.NanoAOD.ttbarCategorization_cff import categorizeGenTtbar, matchGenBHadron, matchGenCHadron"` — 실패 시 cmssdt LXR에서 새 경로 확인 후 `python/ttbarIdExtend_cff.py`의 import 교체. **가정 말고 실측**.
3. `python3 -c "from TTHHGenCategoryTools.TtbarIdExtender.extendedTtbarId_cfi import extendedTtbarId"` — 우리 모듈 등록 확인.
4. 입력 갱신: `crab/datasets.yaml`에 Run3 MiniAOD dataset + GlobalTag(`124X_mcRun3_...` 계열), `test/run_ttbarIdExtend_cfg.py`의 era modifier `Run2_2017,run2_nanoAOD_106Xv2` → Run3 대응으로 교체.
5. gen-only 스모크: `cmsRun run_ttbarIdExtend_cfg.py inputFiles=<Run3 MiniAOD> maxEvents=10`.
6. `bin/compareExtendToCentral`로 Run3 central NanoAOD(v12+)와 `genTtbarId` byte-identity **재검증** — `genTtbarId` 의미는 NanoAOD 버전 무관(`categorizeGenTtbar`가 원천)이지만, 검증 없이 주장하지 않는다.
7. (enriched를 되살릴 경우에만) FlatTable 헤더 경로 + column API 재확인 — [10](10_enriched_nanoaod_archive.md).

**ttbarId-extend 설계의 이행 비용이 낮은 이유**: NanoAOD step을 거치지 않으므로 NanoAOD가 v9→v15로 바뀌어도 ttbarId-extend 코드는 영향이 없고, 바뀌는 것은 입력 MiniAOD의 era/GT와 (재)검증 대상 central 파일뿐이다 ([05](05_architecture.md) §4).
