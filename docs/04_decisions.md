# 04 — Decision log

> **목적**: "왜 이 선택인가? 다른 후보는? 아직 유효한가?"의 단일 출처.
> **대상 독자**: 설계를 바꾸려는 사람; DECIDED를 다시 열기 전 반드시 여기 확인.
> **상태**: 살아있는 문서 — 마지막 갱신 **2026-07-27** (D15 신설: CRAB task 당 job 10,000 상한).
> **관련**: 시간순 이력은 [03_changelog.md](03_changelog.md), 실패 사례는 [08_troubleshooting.md](08_troubleshooting.md).

각 항목: 선택 / 근거 / 검토·기각된 대안 / 상태.

## D1 — 생산 방식: sidecar (Approach 3) · DECIDED 2026-05-29

- **선택**: MiniAODv2에서 gen-level producer 5개만 돌려 작은 top-level `Events` TTree(sidecar)를 만들고, 분석에서 중앙 NanoAOD에 key-join한다.
- **근거**: (1) NanoAOD step 미사용 → customizer/era-modifier/FlatTable 함정에 면역, release patch 간 안정. (2) event당 ~32 B — 4샘플 ~3 GB vs enriched ~200 GB (100×). (3) 중앙 NanoAOD가 read-only source of truth로 유지됨.
- **기각 대안**: **Approach 2 enriched NanoAOD** — v7.2에서 byte-identity까지 입증됐으나(1,665 branch), NANO step 의존으로 v7→v7.2 동안 6회의 fix-cascading을 유발했고 storage 비용의 99.99%가 중앙 복제였다 → D-DEP1로 폐기. **hash-dict/SQLite/자체 binary lookup** — 순서 의존 없앤 대안들이었으나 메모리/의존성/유지보수 비용으로 기각 (v6 시절 검토).

## D2 — Release pin: CMSSW_10_6_32_patch1 · DECIDED (v7)

- **근거**: UL Run2 NanoAODv9 공식 production cycle (PdmV 사설생산 가이드 명시). gen-level은 14_2_1에서도 일치했지만, byte-identity 주장의 환경을 production과 동일하게 고정.
- **대안**: CMSSW_14_2_1 (v6.1 검증 환경) — gen-level만 일치, reco-level(JEC/JER/tagger)은 원리상 불일치 → 기각.

## D3 — `genTtbarId`는 표준 producer를 그대로 호출 · DECIDED (v6)

- **근거**: 직접 재구현(v4/v5)은 c-from-W ancestor 추적에서 38%까지 무너졌다 — 표준 plugin은 `cHadFromTopWeakDecay` flag를 단독 신뢰하지 않고 mother-chain을 재추적한다. `PhysicsTools.NanoAOD.ttbarCategorization_cff` 통째 import가 canonical (NanoAOD master와 동일 세팅).
- **결과**: byte-identity의 근거. 우리는 그 위 thin extension(`ExtendedTtbarIdProducer`)만 소유한다.

## D4 — 확장 분기 조건: `nAddBJets >= 3` · DECIDED 2026-06 (v10)

- **선택**: `if (nAddBJets >= 3)` → 61/62(==3)·71/72(>=4); prefix 보존.
- **근거**: 표준 스킴에 sub-code 56은 존재하지 않는다(TWiki Example 2와의 혼동). tt4b 950만 event에서 56=0건, `nAddBJets≥3`=188만 건(전부 53/54/55 내) 확정.
- **기각 대안**: `genTtbarId%100==56 && nAddBJets>=3` (v9까지) — 영원히 false, tt+bbb/tt+4b 미생성. 카운트 로직은 처음부터 정확했으므로 무변경.

## D5 — Sidecar 출력: TFileService 대신 직접 TFile · DECIDED 2026-05-29 (v8.1)

- **근거**: TFileService는 tree를 모듈 label 디렉토리(`ttbarIdSidecar/Events`)에 격리 → friend-tree/비교기 모두 prefix를 알아야 해 fragile. 직접 TFile로 top-level `Events` 생성; `endJob`에서 `BuildIndex("run","event")` → `Write("",kOverwrite)`(중복 cycle 방지) → `Close`.

## D6 — 비교기 I/O: `TTree::SetBranchAddress` (TTreeReader 금지) · DECIDED (v6기)

- **근거**: TTreeReader는 `libTreePlayer` 소속인데 BuildFile `<use name="root"/>`는 libRIO+libTree만 링크 → release별 링크 불안정. SetBranchAddress + `SetBranchStatus("*",0)`는 어디서나 빌드되고 I/O도 빠름.

## D7 — 이벤트 키: 3-key `(run, luminosityBlock, event)` · DECIDED 2026-06

- **근거**: 2-key(run,event)는 TTToSemiLeptonic sidecar에서 **15.27M(4.3%) 중복**으로 abort — MC event 번호는 lumisection 내에서만 유일. 중복 감지는 의도된 안전장치였고 정확히 작동했다. `run != 1` 시 abort(MC 전제) 유지.

## D8 — 대용량 매칭: external sort + part-file binary search · DECIDED 2026-06

- **선택**: `sortSplitExtend`(chunk-sort 후 k-way merge, part당 50만 row ≈ 16 MB + `index.txt`) → `matchTtbarIdSorted`(part 1개만 상주).
- **근거**: 전량 map은 TTToHadronic 2.36억 event에서 ~20 GB — Tier3 worker 불가. lumi-범위 chunking은 `scanOrder`로 기각(파일 내부 미정렬 + lumi 범위 대량 중첩 실측).
- **부가 가치**: 정렬 산출물은 analyzer의 향후 direct lookup에도 재사용 가능.

## D9 — Analyzer 소비: 예외-전용 patch 파일 + membership 판정 · DECIDED 2026-06

- **선택**: sidecar에서 tt+nb row만(`Expanded%100∈{61,62,71,72}` ⇔ `nAddBJets≥3`) 추출한 per-sample 파일을 map으로 올려, **map에 있으면 확장값으로 override, 없으면 NanoAOD `genTtbarId` 그대로**.
- **근거**: `nAddBJets≤2`이면 Expanded≡genTtbarId라 lookup 불필요 — 파일이 극소(수만~188만 row). sub-code gating이 필요 없어 b-hadron vs b-jet 경계 미묘함이 아예 진입하지 않음. 추출기·loader 양쪽이 sub-code⇔nAddBJets 동치를 교차검증(불일치 시 abort).
- **기각 대안**: sidecar 전체 friend-tree(대용량 map/order 관리), 전량 lookup 파일.

## D10 — Stitching: tt+nb는 dedicated tt4b에서 (AN option 1) · DECIDED

- **근거**: tt+nb 밀도 실측 — tt4b 19.8% vs inclusive ~0.01% (약 1,800×). inclusive로 tt+nb를 모델링하면 통계가 절망적. keep/reject 규칙은 [02](02_physics.md) §5.

## D11 — subsystem·패키지 rename: 최종 `TTHHGenCategoryTools/TtbarIdExtender` · DECIDED 2026-07-05 (v12가 v11 대체)

- **이력**: `TtbbStudies`(초기) → `ExtendedTtbarId/NanoExtension`(v10) → `ExtendedTtbarId/GenSidecar`(v11) → **`TTHHGenCategoryTools/TtbarIdExtender`(v12, 최종)**.
- **최종 근거**:
  - **패키지 `TtbarIdExtender`**: 이 코드가 하는 일은 "gen 정보로부터 `genTtbarId`를 tt+bbb/tt+4b까지 **확장**한다". v11의 `GenSidecar`는 "sidecar로 전달한다"는 *운반 방식*(은유)을 이름에 담았는데, 사용자 판단으로 **방식이 아니라 역할**을 이름에 담기로 함. "sidecar" 은유는 코드 전반(파일·함수·모듈 라벨)에서 함께 제거([03](03_changelog.md) v12).
  - **subsystem `TTHHGenCategoryTools`**: v11까지 subsystem이 `ExtendedTtbarId`였는데, 패키지를 `TtbarIdExtender`로 하면 경로가 `ExtendedTtbarId/TtbarIdExtender`로 "Extend" 개념이 중복됐다. subsystem은 "이 저장소가 통째로 무엇을 담는가"(ttHH 분석용 gen categorization 도구 모음 = 생산 패키지 + Validation + 문서)를 말하도록 분리.
- **검토·기각 대안**: subsystem — `GenCategoryTools`(범용적이나 분석 맥락 없음), `TtbarIdTools`(TtbarId 중복 잔존); 패키지 — `GenSidecar`(은유), `TtbarIdSidecar`(경로 TtbarId 중복 + 은유), `GenTtbarCategorizer`(CMSSW 표준 plugin명 충돌 — 금지).
- **범위 절제**: 물리 개념·클래스 `ExtendedTtbarIdProducer`, EDM product `Expanded_genTtbarId`, cfi `extendedTtbarId`는 **무변경** — 이건 "확장된 ttbar id"라는 물리 표기이지 subsystem/패키지 이름이 아니며, 산출 데이터·analyzer 계약면. TTree 이름 `Events`도 유지(D13).

## D12 — Lookup 산출물 rename: `ttnb` 계열 → `ttbarIdPatch` 계열 · 도구측 DECIDED 2026-07-05 / analyzer측 PROPOSED

- **선택**: 도구 `extractTtbarIdPatch`, 파일 `ttbarIdPatch_<sample>.root`, tree `TtbarIdPatch`.
- **근거**: `ttnb`는 (a) 물리 표기 tt+bb와 시각적으로 혼동되고(사용자 보고: "output이 ttbb…"), (b) 파일의 **역할**을 말하지 않는다. 이 파일의 본질은 "NanoAOD `genTtbarId` 위에 덧대는 예외-전용 patch"이므로 role-descriptive 이름을 채택. 물리 카테고리 어휘 **tt+nb 자체는 유지**(문서·로그·변수) — 표준 표기이기 때문.
- **검토 대안**: `ttbarIdOverride`(동사적으로 정확하나 "예외 소파일" 뉘앙스는 patch가 우세), `expandedIdLookup`(전량 lookup으로 오독 여지), `ttNbLookup`(혼동 원인 잔존).
- **호환 유지**: 로직 무변경; `--out`/`--out-tree`로 구 규약 생산 가능. 기존 산출물 7개는 구 규약 그대로 보존(내부 tree명 고정). **analyzer(tempTTHH) 좌표 변경 3-line diff는 [07](07_analyzer_integration.md) §4 — 사용자가 적용 확정 시 DECIDED로 승격.**

## D13 — 출력 파일명 `ttbarIDExtend.root`, TTree 이름 `Events` 유지 · DECIDED 2026-07-05 (v12)

- **파일명**: v11까지 `sidecar.root` → v12 **`ttbarIDExtend.root`** (사용자 지정 표기, ID 대문자). "sidecar" 은유 제거의 일부. cff cms.string·함수 기본값·cfg VarParsing·CRAB pyCfgParams/outputFiles 모두 갱신.
- **TTree 이름은 `Events`로 유지**(바꾸지 않음). 근거: (1) analyzer가 top-level `Events`를 기대하도록 D5에서 정리했고 friend-tree 결합이 이 이름에 묶임, (2) 2026-06 production sidecar 파일들의 내부 tree가 `Events`로 굳어 있어 이름을 바꾸면 기존 파일을 못 읽음, (3) 중앙 NanoAOD의 메인 tree도 `Events`라 friend로 나란히 붙일 때 개념적으로 정합. 비교기·매처는 `--tree-*` 인자로 tree 이름을 받으므로(기본값 `Events`) 필요 시 유연.
- **기각 대안**: TTree까지 `TtbarIdExtend`로 rename — friend-tree + 기존 production 파일이라는 결합점이 파일명·패키지명보다 하나 더 많아 재검증 부담이 커서 기각(사용자 확인).

## D14 — 병합 레이아웃: 한 subsystem 루트 아래 패키지 + Validation 병치 · DECIDED 2026-07-05

- **선택**: tar 루트 `TTHHGenCategoryTools/` = CMSSW subsystem 디렉토리이자 저장소 루트. `Validation/`은 BuildFile.xml 없는 standalone(Makefile)으로 병치.
- **근거**: 사용자의 기존 배포 관행(subsystem tar를 `src/`에서 풀기)과 호환; 생산·검증이 한 이력·한 문서 세트를 공유; scram은 BuildFile 없는 디렉토리를 빌드하지 않으므로 간섭 없음.
- **실측·해결 (v12, 2026-07-05)**: 첫 `scram b`에서 예상대로 문제가 터졌다 — scram이 `Validation/src/*.cc`를 BuildFile 없이 자동 컴파일하려다 ROOT 헤더를 못 찾고 전량 실패([08](08_troubleshooting.md) T-15). `Validation/`을 subsystem 밖으로 빼는 대신 **더 가벼운 fallback**을 적용: 소스 디렉토리를 `Validation/src/` → `Validation/tools/`로 rename(Makefile `SRCDIR := tools`). scram은 `src/`만 자동 컴파일 대상으로 보므로 `tools/`는 완전히 무시하고, standalone `make`만 이를 빌드한다. plugin 패키지는 이 빌드에서 정상 컴파일 → subsystem/패키지/plugin-lib 이름은 문제없음이 확인됨.

## D15 — CRAB splitting: **task 당 job 10,000 상한**을 절대 넘기지 않는다 (`units_per_job >= 2`, 기본 10) · DECIDED 2026-07-27

- **규칙 (한 줄)**: `njobs = ceil(nfiles / units_per_job)` 이고 **CRAB 은 task 당 job 10,000 개를
  초과하면 거부한다.** 따라서 `units_per_job` 을 **내리기 전에 반드시 job 수를 확인**한다.
  올리는 방향은 이 상한에 대해 항상 안전하다.
- **왜 위험한가 (이게 핵심)**: 거부가 **제출 시점이 아니라 서버 측에서** 일어난다.
  - `crab submit` 은 **성공을 반환**하고 submitter 는 `submitted : N` 을 찍는다
  - 서버가 나중에 task 를 `SUBMITREFUSED` 로 세워 두고 경고를 남긴다:
    `The splitting on your task generated N jobs. The maximum number of jobs in each task is 10000`
  - `jobsPerStatus` 가 비어 있어 `--report` 행이 **전부 0** → "제출됐지만 아직 안 시작"과
    구분이 안 된다
  - **`crab resubmit` 으로 못 고친다** — resubmit 은 scheduler 에 도달한 task 의 FAILED job 만
    재큐한다. task 를 **다시 제출**해야 한다
  → 즉 **샘플 하나가 조용히 아무것도 만들지 않고, 며칠 동안 모를 수 있다.**
- **실제 사고 (2026-07-27)**: 2018 `TTbar_SemiLep` = MiniAOD **10,010 파일**, 당시
  `units_per_job: 1` → 10,010 jobs → 10 개 초과로 거부. 하루 동안 job 0개.
  총합(20,953)만 보면 정상으로 보였다 — **상한은 per-task 이므로 per-task 로 봐야 한다.**
  증상·복구는 [08](08_troubleshooting.md) **T-19**.
- **결정 값**: `site_config.yaml` `resources.extend.units_per_job` = **10**
  (이 7샘플 최대 task = 1,001 jobs). 최소 허용치는 2 지만 10 을 택한 이유는 CPU 효율 —
  job 2.4분 중 ~90초가 startup 이라 upj=1 은 CRAB 의
  `average jobs CPU efficiency is less than 50%` 경고(실측 20~45%, waste 50~58%)의 원인이었다.
  upj=10 이면 오버헤드 비중 63% → 14%.
- **왜 마음대로 올려도 되는가 (물리 무관성)**: 각 job 은
  `(run, luminosityBlock, event, ...)` 행을 쓰고, 소비자 `matchTtbarId`/`matchTtbarIdSorted` 는
  **filelist 전체에 3-key map 하나**를 만든다 — 행이 어느 파일에서 왔는지 보지 않는다(D7).
  file→job packing 은 **순수 운영 knob** 이다. 위쪽 제약은 `maxJobRuntimeMin`(1440분)뿐이고
  upj=10 이 ~11분/job 이므로 ~130배 여유다.
- **강제 수단 (3중, 모두 유지할 것)**:
  1. **`--preflight --check-das`** 가 DAS `nfiles` 로 per-task `ceil(nfiles/upj)` 를 계산해
     상한 초과 시 **FAIL**, 90% 초과 시 WARN, 그리고 필요한 `units_per_job` 값을 알려 준다.
     캠페인 전 **항상** 돌린다 — 유일한 사전 검사다.
  2. **코드·설정 주석**: `crab/submit_ttbarIdExtend.py` 의 `cfg.Data.unitsPerJob` 대입 지점,
     `crab/site_config.yaml` 의 `units_per_job`(extend·enriched 양쪽),
     `crab/datasets.yaml` 의 per-entry override에 경고 블록.
  3. **`datasets.yaml` per-entry floor**: `TTbar_SemiLep` 에 `units_per_job: 10` 을 명시 —
     기본값과 중복이지만 **의도적**이다. 이 dataset 은 1 이 불가능한 유일한 항목이므로 전역
     기본값이 되돌려져도 살아남는다. (*깨질 수 없는 설정* > *깨진 걸 잡는 검사*.)
- **검토·기각된 대안**:
  - `units_per_job: 2` (최소 수정) — 상한은 피하지만 CPU 비효율이 그대로 남아 기각.
  - `splitting: "Automatic"` — CRAB 이 runtime 기준으로 알아서 쪼개므로 상한 문제가 사라진다.
    그러나 job↔파일 대응이 불투명해져 부분 실패 추적과 완결성 대조가 어려워지고, 2017 캠페인이
    FileBased 로 검증됐으므로 **보류**(PROPOSED, 재검토 가치 있음).
  - 큰 샘플만 별도 task 로 쪼개기 — LFN 아래 timestamp 가 둘 생겨 3-key 중복(exit 7) 위험.
    같은 이유로 `--max-files` 스모크도 금지다(v13.4).
- **다른 저장소에도 같은 함정이 있다**: `NtupleForge/crab/submit_crab.py` 도 FileBased 이고
  **job-count preflight 가 아직 없다**(gap 기록됨). 지금은 NanoAOD 기반이라 최대 task 가 391 jobs
  로 안전하지만(최대 task = `WJetsToLNu_HT200To400_ext1` **780 files → 780 jobs**;
  `TTbar_SemiLep` 은 event 수 1위지만 파일 수는 4위 391 — **job 수는 event 가 아니라 파일이
  정한다**), MiniAOD 로 방향을 돌리거나 10,000 파일 초과 dataset 을 추가하면 즉시 이 함정에
  빠진다. 그 저장소의 `submit_crab.py`·`crabConfig/*.yaml`·`script/build_ul18_from_log.py` 에
  같은 경고를 박아 뒀다.
- **범위 밖 (의도적, 사용자 확인 2026-07-27)**: 워크스페이스의 rename 이전 사본
  `ExtendedTtbarId/NanoExtension/`(구 `submit_sidecar.py` + `units_per_job: 1` +
  `max_memory_mb: 2000`)에는 **경고를 넣지 않는다.** 이 규칙이 적용되는 살아있는 경로는
  `TTHHGenCategoryTools/TtbarIdExtender` 뿐이고, 그 디렉토리는 D11 이력의 유물로 남겨 둔다.
  다시 손대지 말 것 — "일관성"을 이유로 건드리면 동결된 사본을 흔드는 것이다.
  같은 이유로 `NtupleForge` 의 CPV config 8개 + `config_crabTest.yaml` 도 지역 주석 없이
  submitter 측 경고에 의존한다(전부 NanoAOD 입력, 최대 수백 파일).
- **상태**: DECIDED. 값을 바꾸려면 이 항목을 먼저 갱신하고, `--preflight --check-das` 로 검증한
  job 수를 근거로 남긴다.

## D17 — v15 에 중앙본이 없는 샘플에 한해 enriched NanoAOD 부활 (D-DEP1 부분 번복) · PROPOSED 2026-08-31

- **선택**: 생산 방식을 **혼합**한다.
  - 중앙 v15 가 **있는** 샘플(ttbar 3 종 등) → **sidecar 유지** (D1 그대로).
  - 중앙 v15 가 **없는** 6 샘플 → **enriched 사설 생산**: MiniAODv2 를 입력으로
    중앙과 동일한 NANO step 을 돌리면서 `ExtendedTtbarIdProducer` 를 customise 로
    얹어 `Expanded_genTtbarId` 를 branch 로 함께 만든다.
    대상: `TT4b`, `TTHHto4b`(신호), `TTZHTo4b`, `TTZZTo4b`, `tHW`, `TTZToBB`.

- **근거**:
  1. **v15 전수 조사 (2026-08-31)**: registry 64 개 중 중앙 v15 가 없는 것은 위
     6 개뿐이다. 나머지는 Data 포함 전부 존재한다
     (NtupleForge `docs/09` 10 절). 즉 이 6 개는 v15 로 가려면 **사설 생산이
     선택이 아니라 유일한 경로**다.
  2. **D-DEP1 의 기각 사유가 이 6 개에는 성립하지 않는다.** D1 은 "storage 비용의
     99.99 % 가 **중앙 복제**"라고 적었다. v15 에는 복제할 중앙본이 자체가 없으므로
     그 비용은 **중복이 아니라 유일본의 비용**이다.
     ⚠ 절대량이 작아서가 아니다 — TT4b 만 봐도 enriched 약 27 GB 대 sidecar 약
     0.3 GB 로 상대 배율은 여전히 ~90 배다. 바뀐 것은 배율이 아니라 **비교 대상**이다.
  3. **작업이 어차피 필요하다면 확장 branch 는 덤이다.** customise 는 추가만 하므로
     표준 branch 는 동일 코드 경로로 생산된다.
  4. **TT4b 가 sidecar 복잡도의 대부분이다** — tt+nb patch 행 약 200 만 중
     1,882,170 개(94 %)를 공급한다. TT4b 가 enriched 로 넘어가면 3-key 해시 키잉·
     patch 파일·규약(D12)·join 부담의 대부분이 사라진다.
  5. **기술적 실현 가능성은 이미 실증됐다**: v7.2 (2026-05-28) 에서 공통 1,665
     branch 전부 sum-ratio 1.000 ([10](10_enriched_nanoaod_archive.md) §2).

- **기각 대안**:
  - **전면 enriched 복귀** — ttbar 3 종은 중앙 v15 가 있고 355 M event 규모라
    D1 의 중앙-복제 논거가 그대로 유효하다. 기각.
  - **6 개를 v9 로 남기고 나머지만 v15** — 한 분석 안에서 스키마가 갈리면
    `Jet_jetId` 처리부터 샘플마다 달라진다. 기각.
  - **v15 마이그레이션 포기** — v9 NanoAOD 가 parent 대비 2.61 % 결손이고
    (`docs/09` 5 절) v15 는 100 % 덮는다. 기각.

- **상태**: **PROPOSED**. DECIDED 로 올리려면 아래가 필요하다.
  1. 아카이브 cfg 는 그대로 실행 불가다 (`TtbbStudies.NanoExtension` 경로가 v10 에서
     제거됨, [10](10_enriched_nanoaod_archive.md) §3.3). 현행 패키지 기준으로
     **FlatTable producer 를 새로 작성**해야 한다 — `ExtendedTtbarIdProducer` 는
     그대로 쓰고 table 컬럼만 붙인다.
  2. **byte-identity 재검증**. v7.2 결과는 재사용할 수 없다(§4). 중앙본이 존재하는
     샘플(예: `TTbb_4f_TTToHadronic` v9)에서 레시피를 먼저 증명한 뒤, 중앙본이 없는
     TT4b·신호에 적용한다. 도구는 NtupleForge `script/compare_v9_v15.py` +
     `script/pair_v9_v15.py`.
  3. v7.2 검증 당시 split 조건이 sub-code 56 기반(D4 이전의 버그)이었으므로
     **확장값 자체는 enriched 경로에서 검증된 적이 없다**. 물리는 sidecar 경로에서
     입증됐으니([06](06_validation_results.md)) 포장만 새로 검증하면 된다.
  4. **CRAB job 상한 (D15)**. MiniAOD 는 NanoAOD 보다 파일 수가 훨씬 많다.
     `units_per_job` 을 NanoAOD config 에서 그대로 가져오면 안 된다.
  5. v15 는 CMSSW_15_0_X 가 필요하다 (D2 의 release pin 은 v9 용).

## D-DEP1 — Approach 2 (enriched NanoAOD) · DEPRECATED (v8에서 실질, v10에서 파일 제거)

- 폐기 사유는 D1 참조. **검증됐던 사실**과 emit된 cfg 4편은 [10_enriched_nanoaod_archive.md](10_enriched_nanoaod_archive.md)와 `TtbarIdExtender/archive/enriched_nanoaod/`에 보존 — 지식은 버리지 않는다.

> **2026-08-31**: 중앙 v15 가 없는 6 샘플에 한해 **D17 로 부분 번복**되었다 (PROPOSED).

## D16 — 검증 기준 데이터는 이 repo 가 소유한다 (cross-repo 런타임 읽기 금지)

**결정**: 완결성 검증의 기준값(DAS nevents)을 `Validation/data/das_nevents_<era>.json` 으로
**이 repo 에 복제해 커밋**한다. 다른 repo(`tempTTHH/data/samples_<era>UL.json`)를 런타임에 읽지
않는다. tempTTHH 경로는 편의 fallback 으로만 남긴다.

**근거** (2026-07-28 실측): 원래는 tempTTHH 파일만 읽었는데, lxplus 에는 tempTTHH 가 **체크아웃돼
있지도 않다**. 그 결과 `nano total == DAS nevents` 기준이 **조용히 SKIP 되고 샘플은 PASS** 했다
([08](08_troubleshooting.md) T-23 ⑦). 검증 도구가 자기 판정 기준을 외부 의존성으로 두면, 그
의존성이 없는 환경에서 **판정이 약해진 것을 모른 채** 통과한다. 이 프로젝트에서 가장 비싼 실패
유형(T-21 의 13% false pass)과 같은 부류다.

**대가와 그 관리**: 복제는 동기화 의무를 만든다. 그래서 (1) `_meta` 에 출처·생성일·갱신 규칙을
박고, (2) `Validation/README.md` §4.0 의 합산 명령 바로 위에 **상류→이 repo 대응 표**를 두고,
(3) `aggregate_validation.py` 헤더에 같은 목록을 둔다. 동기화 대상 4개: `nevents` 값 /
프로젝트 샘플 키 이름(`SHORT_TO_XSECKEY`) / analyzer patch 규약(`ttnb_*`/`TtNb`) /
NtupleForge dataset 목록.

**기각한 대안**: ① tempTTHH 를 lxplus 에 체크아웃해 경로를 맞춘다 — 환경마다 배치가 달라 같은
문제가 재발하고, 검증이 남의 repo 존재에 의존한다. ② 못 찾으면 SKIP 유지 — 판정이 조용히
약해지는 것을 허용하는 것이므로 기각(**안전장치는 입력이 없으면 통과가 아니라 실패해야 한다**).
③ git submodule — 두 repo 의 릴리스 주기가 다르고, 필요한 것은 7개 정수뿐이다.

**규칙**: 불일치가 나면 `das_nevents_*.json` 을 고치지 않는다. DAS dataset 자체가 바뀐 게
아니라면, 불일치는 검증 실행이 불완전하다는 신호다.
