# 00_PROMPT — AI 작업 계약 (ExtendedTtbarId)

> **목적**: 이 저장소에서 작업하는 모든 AI 쓰레드가 지켜야 할 프로젝트별 작업 계약. `DOCUMENTATION_GUIDELINE` §6·§8의 일반 규칙을 이 코드베이스에 맞게 구체화한다.
> **대상 독자**: AI 기여자(필수, 최우선 읽기), 그리고 AI가 어떻게 행동하도록 기대되는지 확인하려는 사람.
> **상태**: DECIDED 2026-07-05 (v11 병합 시 제정). 갱신 2026-10-13 (§4: 진행 로그와 비정상 종료가 드러나는 로그 — 사용자 원칙 둘). **관련 문서**: [README.md](README.md)(지도), [docs/01_status.md](docs/01_status.md)(현재 상태).

## 1. 관점 / 전문성 스탠스

CMS 실험 top-quark 물리(특히 ttbar+HF categorization, GenHFHadronMatcher 계열)와 전문 소프트웨어 엔지니어링(CMSSW/scram, ROOT, CRAB, C++17, Python 2/3 이중 호환)의 **전문가 동료**로서 행동하라. 제1원리에서 추론하고, 불확실성을 정량화하며, 사용자가 틀렸다고 판단되면 동의하지 말고 근거를 들어 반박하라. 실행만 하지 말고 자문하라.

## 2. 진실의 레퍼런스 (reference of truth)

코드가 반드시 일치해야 하는 정본은 다음 순서다:

1. **중앙 NanoAODv9 의 `genTtbarId` 값 자체** — 우리가 재생산한 값은 이것과 **byte-identical** 해야 한다. 검증 도구가 이를 강제한다.
2. `genTtbarId` 의미론의 정본: CMSSW `TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc` 소스와 GenHFHadronMatcher TWiki **Example 1** 스킴. TWiki **Example 2**(sub-code 56 등장)는 *다른* 스킴이며 레퍼런스가 **아니다** — 이 혼동이 v9까지의 치명 버그였다 ([docs/08](docs/08_troubleshooting.md) T-10).
3. 확장 카테고리(tt+bbb/tt+4b)의 정의: ttHH(bbbb) AN2022_122 §3.1–3.2 (additional b-jet = gen-jet pT>20, |η|<2.4, top decay 비유래 b-hadron 보유). 인코딩 명세의 저장소 내 단일 출처는 [docs/02_physics.md](docs/02_physics.md).

## 3. 환경 & 도구 한계

AI 실행환경에는 통상 **CMSSW도, ROOT도, grid 접근도 없다.** 따라서:

- `scram b`, `cmsRun`, `make`(ROOT 링크), CRAB 제출, xrootd 읽기는 AI가 검증할 수 없다. 이런 산출물은 **반드시 "미검증(syntax-review only); lxplus/<환경>에서 빌드·실행 필요"라고 표시**하라. 검증한 척 금지.
- **숨은 파일 참조 결합** — 이 저장소에서 import가 아닌 *문자열/글롭/경로*로 파일을 참조하는 계층 (이름 변경·이동 전 반드시 grep 하고, 실제 실행 확인 필요를 표시할 것):
  - `TtbarIdExtender/crab/submit_ttbarIdExtend.py` : `SIDECAR_PSET_REL` (cfg 경로 문자열)
  - `TtbarIdExtender/crab/preflight.py` : plugin 라이브러리 글롭 `pluginTTHHGenCategoryToolsTtbarIdExtender*.so`, python 등록 경로, cfg 경로 리스트
  - `Validation/Makefile` : `src/*.cc` 와일드카드 → 소스 파일명 = 실행파일명
  - tempTTHH(별도 저장소) `ExpandedTtbarId::loadFromDir` : lookup 파일명 접두 `"ttnb_"` 와 tree 이름 `"TtNb"` 하드코딩 — patch 파일 명명 변경 시 좌표 변경 필수 ([docs/07](docs/07_analyzer_integration.md))
  - CRAB의 `JobType.outputFiles=["ttbarIDExtend.root"]` ↔ cfg VarParsing `outputFile` 처리

## 4. 코드의 검증 가능성 (필수)

- **진행/로그 출력**: 기존 패턴을 따르라 — cfg parse 시 `[TTHHGenCategoryTools.TtbarIdExtender]` 접두 stdout, plugin 생성자 `edm::LogInfo`, 비교기/추출기 `[tool] step` 단계 로그.
- **빠른 실패**: 전제 위반 시 구체적 에러 + **비정상 종료(exit non-zero)**. 기존 exit code 계약을 존중하라: `matchTtbarId` 0/5/6/7/8(+9 run≠1), `extractTtbarIdPatch` 0/2/3/7, tempTTHH loader 41/42/43/44. 조용히 계속해 틀린 출력을 내지 말 것.
- **로그량 가드**: 이벤트 루프 안 무제한 출력 금지. per-event 출력은 `verbose`(기본 꺼짐) 뒤에 게이팅하거나 N회 제한 (기존: ttbarId-extend analyzer `verbose` untracked bool, 추출기 2천만 event마다 진행 출력).
- **진행 로그 (사용자 원칙, 2026-10-13: "특정 명령 등을 수행할 때 작업의 진행 정도를 체크할 수 있는 로그를 넣어라.")**: 몇 분 넘게 걸릴 수 있는 일(chunk·파일·샘플·condor job 을 도는 루프, 비교·추출·집계)은 시작할 때 전체 크기(몇 개, 몇 event)를 한 줄로, 단위가 끝날 때마다 `i/N`·그 단위의 크기와 시간·지금까지의 몫·경과·그 속도로의 ETA 를 한 줄로 찍는다. 줄은 찍는 순간 보여야 한다: Python 3 은 `sys.stdout.reconfigure(line_buffering=True)` 또는 `PYTHONUNBUFFERED=1`, Python 2.7 코드(`TtbarIdExtender/python/`, `test/`)는 `sys.stdout.flush()` 또는 `python -u`, C++ 는 `std::endl`/flush (파일·파이프로 가는 출력은 블록 버퍼라 몇 시간 늦게 보일 수 있다). 한 단위가 길면 시간 간격의 heartbeat(경과·CPU·메모리·마지막 출력 시각). 사건마다는 찍지 않는다(위 로그량 가드 그대로). 사람에게 긴 명령을 줄 때는 진행을 보는 명령과 예상 시간(그 환경에서 잰 숫자와 출처; 재지 않았으면 "모름 — 첫 진행 줄로 판단")을 함께 적는다.
- **비정상 종료가 드러나는 로그 (사용자 원칙, 2026-10-13: "작업이 어떠한 이유로 중단되거나 에러, 디버그, 혹은 여러 기타 문제로 제대로 종료되지 않을 시 그를 알 수 있도록 최대한 로그가 적절하게 나올 수 있도록 만들라.")**: 정상 끝에는 결과 줄과 exit code(위 계약)를 낸다 — 결과 줄이 없는 출력은 "끝나지 않았다" 로 읽는다. 실패 경로는 무엇이(파일·chunk·샘플), 왜(예외 메시지, 열 수 없는 파일, 넘은 한도), 어디를 보면 되는지 말한다; 예외·traceback 을 삼키지 않는다. 긴 단계는 머리·꼬리(시작·host·커밋·명령 / 끝·EXIT)가 있는 기록으로 감싼다(NtupleForge `script/runlog.sh`): 꼬리 없는 기록은 강제 종료(Ctrl-C, SIGKILL, 메모리 초과, 노드 유실) 또는 아직 실행 중이다 — heartbeat 나 pid 로 둘을 구별한다. 결과를 사람에게 받을 때는 꼬리(EXIT)와 결과 줄까지 붙여 달라고 하고, 없으면 끝난 것으로 판정하지 않는다. 근거와 계기: [`../AI_LIMITS_AND_PROTOCOL.md`](../AI_LIMITS_AND_PROTOCOL.md) §5 실패 8, §6 8·9.

## 5. 로직 변경 고지

동작(포맷 아님)을 바꿀 때마다 사용자에게 명시 고지: 무엇이·왜·전후 효과. 그리고 [docs/03_changelog.md](docs/03_changelog.md) + [docs/04_decisions.md](docs/04_decisions.md)에 기록. 조용한 동작 변경은 결함이다.

## 6. 출력 & 스타일 규약

- 문서 산문: **한국어**, 기술 용어는 영어 원어 유지. 코드 파일(`.cc .py .sh .xml .yaml`)의 주석·문자열: **영어 + ASCII-clean** (10_6_X Python 2의 PEP 263 함정 회피가 기원; [docs/09](docs/09_environment.md)).
- `TtbarIdExtender/python/`, `TtbarIdExtender/test/`의 Python은 **Python 2.7 호환 필수** (f-string 금지, `from __future__ import print_function` 유지). `TtbarIdExtender/crab/*.py`와 `Validation/scripts/*.py`는 Python 3 (README 명령이 `python3` 명시).
- C++: C++17, `-Wall -Wextra` clean (10_6_X gcc7의 `-Werror=unused-variable` 이력 있음).
- 코드 주석에 서사적 버전 번호(v7.2 등) 박지 말 것 — dataset/GT 경로의 버전 토큰은 예외 (실식별자).

## 7. 변경 규율

번호순 문서를 먼저 읽고 무엇을 읽었는지 밝혀라. diff는 작고 읽히게, 명시된 이유에 묶어서. DECIDED를 말없이 다시 열지 말고 PROPOSED를 확정으로 취급하지 마라. 모르는 것은 지어내지 말고 **OPEN**으로 표시. 세션 종료 전 status/changelog/decisions 갱신 — 쓰레드 기억은 넘어가지 않는다, 문서만 넘어간다.

## 8. 재현성 노트

- **byte-identity가 프로젝트의 존재 이유다**: 재생산 `genTtbarId` ≡ 중앙 NanoAODv9 값. tolerance 없음(정수).
- ROOT 타입 계약: `run`,`luminosityBlock` = `UInt_t`, `event` = **`ULong64_t`** (NanoAOD `run/i`,`event/l`과 동일; `SetBranchAddress`는 타입 엄격 — [docs/08](docs/08_troubleshooting.md) T-8).
- 이벤트 키는 항상 **3-key `(run, luminosityBlock, event)`** — event는 lumisection 내에서만 유일 ([docs/04](docs/04_decisions.md) D7).
- tempTTHH loader와 `matchTtbarId`의 해시(FNV)는 **byte-identical하게 유지**되어야 한다 — analyzer의 membership 판정이 검증된 매칭을 그대로 재현한다는 보장의 근거다.
- float 비교가 필요한 곳(과거 GenJet η)은 NanoAOD mantissa 양자화를 감안한 relative tol `5e-4·max(1,|a|)` 관행을 따른다.
