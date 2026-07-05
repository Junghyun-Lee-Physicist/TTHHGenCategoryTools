# TTHHGenCategoryTools

> **한 줄 목적**: 표준 NanoAODv9 `genTtbarId`가 구분하지 못하는 **tt+bbb(추가 b-jet 정확히 3개) / tt+4b(4개 이상)** 를 MiniAODv2 gen 정보로부터 복원(`Expanded_genTtbarId`)하여, ttHH(4b) 분석의 ttbar stitching에 공급한다.
> **대상 독자**: 이 코드를 이어받는 모든 사람/AI. **상태**: 2017 UL 7개 샘플 전량 검증 완료 (2026-06), 병합·rename v11 (2026-07-05).
> **정본 규칙**: 저장소의 문서화 계약은 `DOCUMENTATION_GUIDELINE`(프로젝트 무관 계약)을 따르며, AI 작업 계약은 [`00_PROMPT.md`](00_PROMPT.md)에 있다.

이 저장소(`TTHHGenCategoryTools`)는 세 부분으로 구성된다:

| 디렉토리 | 무엇 | 빌드 방식 |
|---|---|---|
| [`TtbarIdExtender/`](TtbarIdExtender/README.md) | CMSSW 패키지. MiniAODv2에서 gen-level ttbar+HF categorization을 돌려 작은 **sidecar** TTree(`run, luminosityBlock, event, genTtbarId, Expanded_genTtbarId, nAddBJets, nAddBJetsMulti`)를 생산 + CRAB 인프라 + byte-identity 비교기 | `scram b` (CMSSW_10_6_32_patch1) |
| [`Validation/`](Validation/README.md) | 독립(standalone) ROOT/Makefile 도구 모음. sidecar ↔ 중앙 NanoAODv9 의 **per-event byte-identity 검증**, 대용량 external-sort 매칭, 분포 비교 플롯, 그리고 analyzer가 소비할 **per-sample ttbar-Id patch 파일** 추출 | `make` (ROOT만 필요, CMSSW 불필요) |
| [`docs/`](docs/) | 저장소 전체의 번호 붙은 문서 세트 (아래 읽기 순서) | — |

`Validation/`에는 **BuildFile.xml이 없으므로 scram이 빌드하지 않는다** (lxplus에서 `scram b` 1회로 최종 확인 필요 — [OPEN, docs/01_status.md](docs/01_status.md) 참조).

## 읽기 순서 (reading order)

새로 온 사람/새 AI 쓰레드는 아래 순서로 읽는다. 번호는 파일명에 인코딩되어 있다.

| # | 문서 | 왜 읽는가 |
|---|---|---|
| 00 | [`00_PROMPT.md`](00_PROMPT.md) | AI 기여자의 작업 계약 (관점·진실의 레퍼런스·환경 한계·검증 의무). AI는 무엇보다 먼저 읽는다 |
| 01 | [`docs/01_status.md`](docs/01_status.md) | 지금 어디까지 왔고, 무엇이 OPEN인가 — 문서를 여는 가장 흔한 이유 |
| 02 | [`docs/02_physics.md`](docs/02_physics.md) | 왜 이 프로젝트가 존재하는가: 물리 동기, `genTtbarId`/`Expanded_genTtbarId` 인코딩 명세(정본), stitching 분할 |
| 03 | [`docs/03_changelog.md`](docs/03_changelog.md) | 무엇이 언제 바뀌었나 (append-only) |
| 04 | [`docs/04_decisions.md`](docs/04_decisions.md) | 왜 그렇게 만들었나: 결정·근거·기각된 대안·상태 |
| 05 | [`docs/05_architecture.md`](docs/05_architecture.md) | 어떻게 만들어졌나: 생산 → 검증 → 소비의 3단 구조와 데이터 흐름 |
| 06 | [`docs/06_validation_results.md`](docs/06_validation_results.md) | 측정된 검증 결과 전체 (2017 UL, ~7.1억 event) — 숫자의 단일 출처 |
| 07 | [`docs/07_analyzer_integration.md`](docs/07_analyzer_integration.md) | 분석 프레임워크(tempTTHH)가 patch 파일을 소비하는 계약과 실제 구현 |
| 08 | [`docs/08_troubleshooting.md`](docs/08_troubleshooting.md) | 증상 → 원인 → 해결 (개발 중 실제로 겪은 것 전부) |
| 09 | [`docs/09_environment.md`](docs/09_environment.md) | CMSSW 10_6_X 함정과 14_X/15_X migration 체크리스트 |
| 10 | [`docs/10_enriched_nanoaod_archive.md`](docs/10_enriched_nanoaod_archive.md) | (legacy) 폐기된 Approach 2 — enriched NanoAOD 의 사실 기록과 검증 경계 |

하위 디렉토리 `TtbarIdExtender/`와 `Validation/`은 각자 **지역 README**(사용법 중심)를 가진다. `docs/legacy/`에는 병합 이전의 원본 문서 4편이 **동결(frozen) 상태로** 보존되어 있다 — 갱신 금지, 역사적 세부 참조용.

## 30초 빠른 시작

```bash
# (1) sidecar 생산 — lxplus, EL7 컨테이너
cmssw-el7
cd CMSSW_10_6_32_patch1/src && cmsenv
tar xzf TTHHGenCategoryTools_v12.tar.gz   # TTHHGenCategoryTools/{TtbarIdExtender,Validation,docs,...} 생성
scram b -j8
cmsRun TTHHGenCategoryTools/TtbarIdExtender/test/run_ttbarIdExtend_cfg.py \
    inputFiles=<miniaodv2.root> outputFile=ttbarIDExtend.root maxEvents=1000

# (2) 검증 + patch 추출 — ROOT만 있으면 어디서든
cd TTHHGenCategoryTools/Validation && make
bin/matchTtbarId --sidecar-filelist <S> --nano-filelist <N> --out match_X.root
bin/extractTtbarIdPatch --filelist <S> --out ttbarIdPatch_X.root
```

자세한 명령은 각 지역 README, 설계 근거는 `docs/04`, 숫자는 `docs/06`.
