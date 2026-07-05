# 04 — Decision log

> **목적**: "왜 이 선택인가? 다른 후보는? 아직 유효한가?"의 단일 출처.
> **대상 독자**: 설계를 바꾸려는 사람; DECIDED를 다시 열기 전 반드시 여기 확인.
> **상태**: 살아있는 문서 — 마지막 갱신 **2026-07-05**.
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
- **주의(OPEN)**: "scram이 무시한다"는 이 환경에서 실검증 불가 — [01](01_status.md) O1의 첫 `scram b`에서 확인. 문제가 되면 `Validation/`을 subsystem 밖으로 빼는 fallback이 준비돼 있다(경로 참조는 상대링크뿐).

## D-DEP1 — Approach 2 (enriched NanoAOD) · DEPRECATED (v8에서 실질, v10에서 파일 제거)

- 폐기 사유는 D1 참조. **검증됐던 사실**과 emit된 cfg 4편은 [10_enriched_nanoaod_archive.md](10_enriched_nanoaod_archive.md)와 `TtbarIdExtender/archive/enriched_nanoaod/`에 보존 — 지식은 버리지 않는다.
