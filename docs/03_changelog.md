# 03 — Changelog (append-only)

> **목적**: 무엇이 언제 바뀌었나. 새 항목은 **아래에 추가만** 한다 (append-only).
> **대상 독자**: 최신 변경을 따라잡으려는 모든 기여자.
> **상태**: 살아있는 문서 — 마지막 항목 **2026-10-16 (2)** (O10: 1012 직접 생성 끝·CRAB 자리, manager 다시 띄움 → `EXIT=0`(DONE), 추출·정렬은 condor job — T-44 tmux, T-45 manager lock; `.gitignore` 에 `crab.log`; 00_PROMPT §10: 오래 걸리는 lxplus 단계는 condor). 그 전 2026-10-16 (O10: TTbar_Hadronic job 1012 멈춤 → `crab kill` → resubmit 거부 → 같은 입력으로 직접 생성, T-43·D22; O11 신설). 그 전 2026-10-15 (11) (O9 ⑨: 2016 patch 열넷 추출·행 수 대조·md5; O10: 2024 patch 를 검증과 병렬로 — 사용자 "run3 먼저"). 그 전 2026-10-15 (10) (O9 ⑧: 2016 두 era 대조 ALL PASS, [06](06_validation_results.md) 에 수치). 그 전 2026-10-15 (9) (T-42: 검증 job 의 CMSSW 영역은 스크립트의 영역 — 2016 22 job 이 exit 127). 그 전 2026-10-15 (8) (O10: 2024 CRAB 제출 3,557 job, manager `extend2024`; NanoAOD > MiniAOD 네 샘플과 DAS 확인; O9 ⑧ 진행). 그 전 2026-10-15 (7) (T-41: 명령 블록을 셸 경계와 비밀번호 프롬프트에서 나눔, `switch`; O9 ⑧ 결과). 그 전 2026-10-15 (6) (T-40: 검증 `--report`·`--resubmit-failed` 가 condor queue 를 본다, 찍는 명령은 절대 경로, `batch_name`). 그 전 2026-10-15 (5) (O10: era 2024(Run 3) extend 준비 — v15 영역, `--fill`, release 짝, 검증 도구의 2024, 독립 검토 반영). 그 전 2026-10-15 (4)(T-39, manager.log 줄마다 닫기), (3)(T-38), (2)(O9 ⑦: 검증 도구가 2016APV·2016 을 안다). 그 전 2026-10-15 (2016 제출 완료; `launch_extend.sh` 의 끝 요약이 el7 의 bash 4.2 에서 안 찍힌 것 T-37). 그 전 2026-10-14 (3) (두 era 제출의 pset 캐시 거부 T-36, condor manager, §9 AI 세션 규칙).
> **관련**: 각 변경의 "왜"는 [04_decisions.md](04_decisions.md), 문제·해결 세부는 [08_troubleshooting.md](08_troubleshooting.md). v3–v10의 원자적 세부는 동결 원본 [legacy/GenSidecar_pre-merge_ARCHITECTURE.md](legacy/GenSidecar_pre-merge_ARCHITECTURE.md)에 보존.

표기: 날짜가 문서에 명시돼 있던 항목만 일 단위로 적고, 나머지는 월 단위로 적는다 (지어내지 않는다).

## 2026-05 — 생산 패키지의 성립 (v3 → v8.1)

- **v3–v5**: miniAOD에서 categorization 재구현 시도. 재클러스터링 경고 폭주(v3), c-from-W 38% 불일치(v4) → pre-stored `slimmedGenJetsFlavourInfos` 채택(v5)으로 b-side 회복, c-side는 여전히 실패. ([08](08_troubleshooting.md) T-1·T-2)
- **v6/v6.1**: 재구현 포기, 표준 `categorizeGenTtbar`를 그대로 호출하는 구조로 전환 → 전 자릿수 100% 일치. cfi import 경로/InputTag 2-인자 수정. TTToHadronic 84k × NanoAOD 1.28M join 검증에서 `genTtbarId`·GenJet 지표 전량 100%.
- **v7 (release pinning)**: reco-level까지 byte-identical하려면 UL production release가 필요 → **CMSSW_10_6_32_patch1** pin. Approach 2(enriched NanoAOD) 중심으로 재편, `compareEnrichedToCentral`(전 branch 자동 열거 비교)·CRAB 인프라 신설. 구 Approach 1 파일 폐기.
- **v7.1**: 10_6_X(Python 2/gcc7) 호환 6건 fix — PEP 263, MessageLogger 명시 load, `categories.append`, tuple→`cms.InputTag`, unused-variable, dataset suffix `-v2→-v1`. ([08](08_troubleshooting.md) T-4)
- **v7.2 (2026-05-28)**: hand-written NANO cfg의 fix-cascading을 종식 — **cmsDriver-emit + inject 패턴** 채택. 진단 로깅 전면 보강(safeGet/try-catch/생성자 LogInfo). **최종 검증: TTbb_4f UL17, N=10, 공통 1,665 branch 전부 ratio=1.000 (byte-identity), enriched-only는 `Custom_*` 4개뿐.** ([10](10_enriched_nanoaod_archive.md))
- **v8 (2026-05-29)**: **Approach 3 = sidecar** 신설 (NanoAOD step 없음, event당 ~32 B). `TtbarIdExtendAnalyzer`, `ttbarIdExtend_cff`, `run_ttbarIdExtend_cfg.py`, `compareExtendToCentral`, `submit_ttbarIdExtend.py`. 검증: TTbb_4f 100/100 event에서 sidecar `genTtbarId` ≡ 중앙 값.
- **v8.1 (2026-05-29)**: TFileService가 tree를 `ttbarIdSidecar/Events`로 격리하는 문제 → analyzer가 **자기 TFile을 직접 열어 top-level `Events`** 생성으로 변경 (friend-tree prefix 문제 해소). `tree_->Write("",kOverwrite)`로 중복 cycle 제거.

## 2026-06 — 버그 수정, rename, 전수 검증 (v9 → v10 + 검증 캠페인)

- **v9**: CRAB 제출 버그 fix(`year=` 미등록 파라미터 제거, `JobType.outputFiles` 선언), per-job 메모리 2000MB, 코드 파일 비-ASCII 제거·주석 버전표기 제거.
- **v10**: **치명 버그 수정** — 확장 분기 조건이 존재하지 않는 sub-code 56에 걸려 있어 tt+bbb/tt+4b가 한 번도 생성되지 않던 문제를 `nAddBJets >= 3` 조건으로 교체 (tt4b 950만 event cross-tab으로 확정; 카운트 로직 자체는 무변경). 패키지 rename `TtbbStudies`→`ExtendedTtbarId`, plugin `TtbbExtender`→`ExtendedTtbarIdProducer`, cfi `ttbbExtender`→`extendedTtbarId`, branch `ttbbId`→`Expanded_genTtbarId`. Approach-2 파일(ttbarCategorySequence_cff.py, TtbarCategoryTableProducer.cc, gen_official_cfg.sh 등) 패키지에서 제거. stitching 문서화, CRAB `--status/--resubmit` 일괄 옵션.
- **검증 도구 확립 (TtbarIdHistCompare, 파일 mtime 6/1–6/6)**: `makeTtbarHist`/`plotTtbarCompare`(분포), `matchTtbarId`(전량 map 대조), `scanOrder`(파일 정렬 진단 — lumi 범위 대량 중첩 확인), `sortSplitExtend`+`matchTtbarIdSorted`(external sort, ~16MB 상주), `extractTtNb`(analyzer용 tt+nb lookup 추출). 2-key(run,event) join이 TTToSemiLeptonic에서 15.27M 중복으로 실패 → **3-key로 확정**.
- **전수 검증 캠페인 완료**: 7개 샘플 ~7.12억 event, `genTtbarId` byte-identity **disagree 0 / unmatched 0**, 확장 무결성 위반 0, 보존식 성립. tt4b 61+62 = 1,585,810 / 71+72 = 296,360 (§5.3 예측치와 일치). per-sample lookup 7개 추출. 전체 수치: [06_validation_results.md](06_validation_results.md).
- **tempTTHH analyzer 통합**: `ExpandedTtbarId` 클래스(standalone loader) + `resolve()` per-event 적용 + stitch multiplier + prescan 61–72 bin. (분석 저장소 측; 계약은 [07](07_analyzer_integration.md))

## 2026-07-05 — v11: 저장소 병합 + rename 2건 (이번 변경)

**동작 변경 고지 (logic-change announcements)** — 아래 3건이 동작/계약에 영향:

1. **패키지 rename `ExtendedTtbarId/NanoExtension` → `TTHHGenCategoryTools/TtbarIdExtender`** (D11). 영향: python import 경로 `TTHHGenCategoryTools.TtbarIdExtender.*`, CRAB pset 경로, preflight의 plugin-lib 글롭(`pluginTTHHGenCategoryToolsTtbarIdExtender*`)·python 등록 경로. 모듈/클래스/branch 이름은 무변경. **재빌드 필수(clean 권장)**; 구 CRAB 프로젝트 resubmit 주의 ([08](08_troubleshooting.md) T-13). 이 변경은 문법 검토만 됨 — lxplus 확인 OPEN ([01](01_status.md) O1).
2. **Lookup 도구 rename + 기본값 변경** (D12): `Validation/src/extractTtNb.cc` → `extractTtbarIdPatch.cc` (Makefile 와일드카드로 자동 반영), 출력 tree 기본 `TtNb` → `TtbarIdPatch`, 권장 파일명 `ttnb_<S>.root` → `ttbarIdPatch_<S>.root`. **로직 무변경**; 구 규약은 `--out ... --out-tree TtNb`로 계속 생산 가능. analyzer 측 좌표 변경은 PROPOSED ([07](07_analyzer_integration.md) §4). 기존 산출물 7개는 구 규약 그대로 `Validation/lookup/`에 보존 (파일 내부 tree명이 `TtNb`이므로 파일명만 바꾸면 오히려 계약이 깨짐).
3. **오정보 주석 수정**: `TtbarIdExtendAnalyzer.cc` 헤더의 "sub-code 56 split" 서술(pre-v10 잔재)을 nAddBJets 기반 서술로 정정; friend-tree 예시 alias `"ttbb"` → `"sidecar"`.

**구조 변경 (동작 무관)**:
- 병합 레이아웃: tar 루트 = `ExtendedTtbarId/`, 하위에 `TtbarIdExtender/`(CMSSW 패키지) + `Validation/`(구 TtbarIdHistCompare, standalone) + `docs/`(본 문서 세트) + `README.md` + `00_PROMPT.md`. `Validation/`은 BuildFile.xml이 없어 scram 대상 아님(확인 OPEN).
- 문서 전면 재구성: DOCUMENTATION_GUIDELINE v2 준수 (번호 파일, BLUF, 상태 라벨, one-fact-one-place). 구 문서 4편(`GenSidecar`·`Validation` 각각의 README/ARCHITECTURE)은 `docs/legacy/`에 **동결 보존** (갱신 금지 표시).
- 폐기된 Approach-2의 cmsDriver-emit cfg 4편을 `TtbarIdExtender/archive/enriched_nanoaod/`에 **무수정 보존** + 사실-한정 README ([10](10_enriched_nanoaod_archive.md)). `das_lineage.py` → `Validation/scripts/` (사용 이력 OPEN, [01](01_status.md) O3).
- 배포물 위생: 컴파일 산출물(`Validation/bin/*`, `*.pyc`, `__pycache__`), macOS `._*` 파일 제거. `Validation/ttnb/` → `Validation/lookup/` (내용 byte-동일 + README.txt 추가).

## 2026-07-05 — v12: sidecar 은유 폐기 + subsystem/패키지/출력 rename (이번 변경)

v11 직후 사용자 요청으로 이름 체계를 한 번 더 정리했다. 핵심 동기: "sidecar"는 은유일 뿐 이 도구가 **무엇을 하는지**(ttbarId를 확장) 말해주지 않는다.

**동작/계약 영향 rename** (전부 logic 무변경):

1. **subsystem `ExtendedTtbarId` → `TTHHGenCategoryTools`**. tar 루트·scram subsystem 디렉토리·모든 문서 경로 서술·CRAB pset 상대경로가 따라 바뀜. (물리 개념/클래스 `ExtendedTtbarIdProducer`, product `Expanded_genTtbarId`는 무변경 — 그건 "확장된 ttbar id"라는 물리 표기이지 subsystem 이름이 아님.)
2. **패키지 `GenSidecar` → `TtbarIdExtender`** (이력: NanoExtension→GenSidecar→TtbarIdExtender). python import `TTHHGenCategoryTools.TtbarIdExtender.*`, plugin-lib 글롭 `pluginTTHHGenCategoryToolsTtbarIdExtender*`, preflight python-init 경로.
3. **출력 파일 기본명 `sidecar.root` → `ttbarIDExtend.root`** (cff cms.string, cff 함수 기본값, cfg VarParsing, CRAB pyCfgParams+outputFiles). **TTree 이름 `Events`는 유지** (friend-tree 결합 + 기존 production 파일 호환; [04](04_decisions.md) D13 근거 그대로).
4. **파일/함수/모듈 라벨의 "sidecar" 전면 제거**: `run_sidecar_cfg.py`→`run_ttbarIdExtend_cfg.py`, `ttbarIdSidecar_cff.py`→`ttbarIdExtend_cff.py`, `TtbarIdSidecarAnalyzer`→`TtbarIdExtendAnalyzer`(클래스+DEFINE_FWK_MODULE+cff type string 동시), `compareSidecarToCentral`→`compareExtendToCentral`, `sortSplitSidecar`→`sortSplitExtend`, `submit_sidecar.py`→`submit_ttbarIdExtend.py`, `addTtbarIdSidecar()`→`addTtbarIdExtend()`, EDM 모듈 라벨 `ttbarIdSidecar`→`ttbarIdExtend`(+ Sequence/Path).
5. **Validation 도구 인터페이스 rename + 하위호환**: CLI 플래그 `--sidecar*`→`--extend*`, `--mode sidecar`→`--mode extend`, 히스토그램 write 이름 `h_sidecar_*`→`h_extend_*`. **구 규약 전부 하위호환**: 구 플래그·구 모드값 그대로 받고(별칭), `plotTtbarCompare`의 히스토그램 로더는 `h_extend_*`가 없으면 `h_sidecar_*`로 fallback → 2026-06에 생산된 검증 ROOT 파일과 구 명령이 안 깨짐.
6. **CRAB 출력 LFN `.../ExtendedTtbarId/sidecar` → `.../TTHHGenCategoryTools/ttbarIdExtend`** (향후 제출에만 영향). **주의**: 기존 검증 production 데이터는 물리적으로 구 경로에 그대로 있으므로, `make_filelists_miniAOD.py`의 `SAMPLE_DIR`은 실제 데이터 위치(구 경로)를 유지하고 그 사실을 주석으로 명시. `filelists/sidecar/` 디렉토리명도 "데이터 위치 라벨"로 유지(rename하면 데이터가 옮겨진 것처럼 오도됨).

**구조**: tar 루트 = `TTHHGenCategoryTools/`, 배포물 `TTHHGenCategoryTools_v12.tar.gz`. `docs/legacy/`의 병합-이전 원본 4편과 `archive/enriched_nanoaod/`는 v12에서도 **무수정 동결** (그 안의 옛 이름은 역사적으로 정확함).

**검증 경계**: 이 rename은 AI 환경(CMSSW/ROOT 없음)에서 문법 검토·py compile만 됨. lxplus 실빌드는 [01](01_status.md) O1. 특히 scram이 생성하는 plugin-lib 이름이 `pluginTTHHGenCategoryToolsTtbarIdExtender*`로 나오는지(preflight 글롭과 일치) 실기기 확인 필요.

## 2026-07-05 — v12.1: 첫 lxplus 빌드 수정 (`Validation/src` → `Validation/tools`)

첫 `scram b -j8`에서 scram이 `Validation/src/*.cc`를 BuildFile 없이 자동 컴파일하려다 ROOT 헤더(`TChain.h` 등)를 못 찾아 전량 실패([08](08_troubleshooting.md) T-15). 원인은 scram이 `<Package>/src/`를 특수 취급하는 것. **해결**: 소스 디렉토리 `Validation/src/` → `Validation/tools/` rename, Makefile `SRCDIR := tools`. scram은 `tools/`를 무시하고 standalone `make`만 빌드. plugin 패키지(`TtbarIdExtender/`)는 정상 컴파일되어 subsystem/패키지/plugin-lib 이름 정합 확인됨([04](04_decisions.md) D14 fallback 적용). 부수로 `-Wcomment` 경고 유발하던 주석 예시의 줄 끝 `\` 제거. README(top·Validation)의 빌드 서술을 이 레이아웃으로 갱신하고, 최상위 README·패키지 README에 `cmsrel CMSSW_10_6_32_patch1` + `git clone` 설정 절차 추가.

## 2026-07-05 — v12.2: CRAB psetName을 절대경로로 (제출 실패 수정)

첫 CRAB 제출이 전 샘플 `Cannot find CMSSW configuration file ...run_ttbarIdExtend_cfg.py`로 실패. 원인: `submit_ttbarIdExtend.py`가 `JobType.psetName`을 저장소-상대 문자열(`TTHHGenCategoryTools/TtbarIdExtender/test/...`)로 넘겼는데, CRAB은 이를 **실행 시점의 현재 디렉토리 기준**으로 해석한다. `TtbarIdExtender/`에서 실행하면 경로가 이중으로 붙어 못 찾음(`src/`에서 실행할 때만 맞았음). `--dry-run`은 pset 존재를 확인하지 않아 통과했다. **해결**: `EXTEND_PSET = str(PKG_ROOT / "test" / "run_ttbarIdExtend_cfg.py")` 절대경로로 변경 → 어느 디렉토리에서 실행해도 해결됨. (preflight는 `$CMSSW_BASE/src/<rel>` 절대경로로 확인하므로 원래 통과했음.) 참고: 실패한 제출도 빈 `crab_projects/crab_*` 껍데기를 남기며(`.requestcache` 없음), 재제출 전 이 디렉토리들을 지워야 한다([08](08_troubleshooting.md) T-16).

## 2026-07-05 — v12.3: CRAB `--kill` 추가

`submit_ttbarIdExtend.py`에 `--kill`(+ `--yes`) 추가. 기존 `crab_action_one(action=...)` 경로를 그대로 재사용하므로 `crab kill`이 `--status`/`--resubmit`과 동일하게 `--process`/`--era` 필터를 존중하고 기존 프로젝트에만 동작한다. 파괴적 명령이라 기본적으로 y/N 확인 프롬프트를 띄우고 `--yes`로 생략 가능. 세 bulk action(`--status`/`--resubmit`/`--kill`)은 상호배타(동시 지정 시 에러). `--kill`은 job만 죽이고 프로젝트 디렉토리는 남긴다. README §2.3 갱신.

## 2026-07-05 — v12.4: CRAB 출력지를 개인 EOS로 (`T3_CH_CERNBOX`)

첫 실제 제출이 `SUBMITREFUSED`(EOS write-check 403)로 grid에 안 나감. 원인: `storage_site: T2_CH_CERN`이 `/store/user/`를 CMS 실험 EOS(`/eos/cms/store/user/`, 별도 활성화 필요)로 매핑([08](08_troubleshooting.md) T-17). lxplus 개인 EOS(`/eos/user/j/junghyun/`)가 목적지이므로 `site_config.yaml`의 `storage_site`를 **`T3_CH_CERNBOX`**로 정정(out_lfn_base는 `/store/user/junghyun/...` 유지 — CERNBOX 사이트가 이를 `/eos/user/j/junghyun/...`로 매핑). README §2.0의 잘못된 T2_CH_CERN 설명 정정 + `crab checkwrite` 사전확인 단계 추가. (이전 v12에서 T2_CH_CERN을 개인 EOS로 안내한 것은 오류였음.)

## 2026-07-05 — v12.5: CRAB 파일 ASCII 위반 수정 (em-dash)

`site_config.yaml`과 `submit_ttbarIdExtend.py`에 v12.3/v12.4 편집 때 들어간 em-dash(`—`, U+2014)가 CMSSW의 py2-era ASCII 로더에서 `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2`를 일으킴 (`crab-setup.sh` 환경의 PyYAML/python3.6이 파일을 ASCII로 읽음). 모두 `--`로 치환. `crab/`·`test/`·`python/` 전 파일 non-ASCII 전수검사 clean 확인. (이 프로젝트의 ASCII-clean 규칙은 [09](09_environment.md) §1 — CRAB/설정 파일도 예외 없이 지켜야 함.)

## 2026-07-26 — v13: 2018UL 대응 (era 파라미터화) — **unverified, lxplus 실행 필요**

사용자 지시: "TTHHGenCategoryTools으로 UL18을 진행 — full 로 잘 돌아가는지 validation 까지". 이번 변경은 **연도 파라미터화 + 2018 블록 등재**까지이며, 실제 생산·검증은 아직 수행되지 않았다.

- **`TtbarIdExtender/crab/datasets.yaml`**: `"2018"` era 블록 신설(7개 stitching 샘플). `nano_child` 는 **DAS 확정값** — NtupleForge `script/das_ul18_scan.sh` 로그(`das_ul18_scan_20260726_1657.log`)에서 가져왔으므로 `config_ttHH2018UL.yaml` 의 모집단과 정의상 일치한다. 반면 MiniAODv2 `dataset:` 의 **`-vN` 접미사는 미검증**(nano child 에서 복사) → 전 항목 `enabled:false` / `verified:false` 로 두어 실수 제출을 차단. 각 항목 notes 에 2018 vs 2017 event 수를 기록(예: TTbar_SemiLep 476,408,000 vs 346,052,000 → sorted 검증 경로 필수).
- **`TtbarIdExtender/test/run_ttbarIdExtend_cfg.py`**: `year` VarParsing 옵션 추가(기본 `2017` → 기존 동작 불변). era modifier 를 `Run2_2017` 하드코딩에서 year→era 매핑으로 교체. **매핑은 `getattr` 지연 해석** — dict 리터럴로 `eras.*` 를 즉시 평가하면 해당 릴리스에 없는 era 이름 하나가 2017 포함 전 연도를 깨뜨리기 때문. **물리량 불변**: gen-level 전용이고 `matchGenBHadron`/`categorizeGenTtbar`/`extendedTtbarId` 는 era-modified 가 아니므로 값이 바뀌지 않는다 — provenance(라벨) 정정이다.
- **`TtbarIdExtender/crab/submit_ttbarIdExtend.py`**: `JobType.pyCfgParams` 에 `year=<era>` 추가 → datasets.yaml 의 era 키가 실제로 pset 에 전달된다(기존 "cfg 에 year 파라미터 없음" 주석 폐기).
- **`TtbarIdExtender/crab/resolve_parents.sh`**: era 인자화(`bash resolve_parents.sh 2018`). 2018 nano child 7개 + 캠페인/`sed` 문자열을 era 별로 분기. 2018 MiniAOD 부모 확정에 이 스크립트를 쓴다.
- **`Validation/filelists/make_filelists.py`, `make_filelists_miniAOD.py`**: era 인자화(`python make_filelists.py 2018 [SAMPLE_DIR]`). 출력 디렉토리가 `nano`/`sidecar` 로 **고정**되어 있어 다른 연도로 실행하면 커밋된 2017 filelist 를 덮어쓰던 문제를 제거 → 2018 은 `nano2018/`, `sidecar2018/`. 기본값(인자 없음)은 2017 이며 기존 동작과 동일.
- 검증(로컬에서 가능한 범위): 두 filelist 스크립트 parse OK + era 인자 동작(미지원 era/경로 누락 시 FATAL) 확인, `datasets.yaml` PyYAML 파싱 후 2017=7 enabled·verified / 2018=7 모두 disabled 확인, cfg·submitter ASCII+구문 확인. **CMSSW 빌드·cmsRun·CRAB 제출은 미수행.**

## 2026-07-26 — v13.1: submit_ttbarIdExtend.py `--preflight` + DAS 기반 nano filelist 생성기

- **`crab/submit_ttbarIdExtend.py --preflight` (신규, 읽기 전용).** `--dry-run` 보다 강한 사전 점검:
  환경(cmsenv/CRABClient/proxy), pset 존재·compile·**`year` 옵션 유무**, site_config(out_lfn_base
  placeholder/ 형식), 그리고 era 별 dataset 상태 — 경로 문법(MINIAODSIM/NANOAODSIM), **campaign
  문자열에 era 키가 들어있는지**, MiniAOD/Nano의 primary dataset 일치, `enabled`/`verified` 조합
  (enabled=true·verified=false 는 FAIL), 기존 CRAB 프로젝트 존재. `--check-das` 를 붙이면 모든
  MiniAOD/Nano 경로를 DAS 로 조회해 **잘못된 `-vN` 접미사를 제출 전에 잡는다**.
  로그 `crab/preflight_extend_<eras>_<timestamp>.log`, FAIL 있으면 exit 1.
- **`Validation/filelists/make_nano_filelists_das.sh` (신규).** nano 측 filelist 를 로컬 디렉토리
  탐색 대신 **DAS 에서 직접** 만든다(7 샘플 일괄, master + per-job split + summary 로그).
  `matchTtbarId` 가 run/lumi/event/genTtbarId 만 읽으므로 중앙 NanoAODv9 로 검증이 가능하고,
  따라서 2018 은 자체 ntuple 생산을 기다리지 않고 바로 검증할 수 있다.
  사용: `./make_nano_filelists_das.sh 2018` → `nano2018/`.
- 문서 정합성 수정(2026-07-26 감사): `datasets.yaml` 헤더의 "미확인 항목은 `verified: true` 로
  표시" 문구를 `verified: false`(+ `enabled: false`)로 정정 — 2018 블록의 실제 상태와 일치.

## 2026-07-27 — v13.2: 2018 부모 확정 + ASCII 위반 수정 + 로컬 불변조건 검증 매크로

**lxplus 실행으로 확인된 것** (사용자 로그, 2026-07-27):

- `scram b -j8` 통과, `crab/preflight.py` 5/5 PASS, `cmsRun ... year=2018` 이 의도대로
  `era modifier = Run2_2018 + run2_nanoAOD_106Xv2` 를 선택. **v13 의 era 파라미터화가 실기기에서 동작.**
- `cmsRun` 로컬 실행(UL18 MiniAODv2, 2000 event) 성공: top-level `Events` 7 branch 생성,
  `endJob summary: total rows=2000 missing genTtbarId=0 missing Expanded_genTtbarId=0
  missing nAddBJets=0 missing nAddBJetsMulti=0`.
- **`resolve_parents.sh 2018` 로 7개 MiniAODv2 부모 전부 확정** → `datasets.yaml` 2018 블록에
  반영하고 `verified/enabled: true` 로 개방. **`TTbar_SemiLep` 이 비대칭이었다** —
  MiniAOD `-v2` / Nano `-v1`. 추측했다면 틀렸을 자리다(파일 헤더가 경고했던 바로 그 케이스).

**수정 (2건, 모두 실행 중 발견):**

1. **ASCII 위반 재발 (v12.5 와 동일 계열).** `datasets.yaml` 에 em-dash 1개와 `sec.` 기호 1개가
   들어가 있어 submitter 가 즉사했다:
   `UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 7566`.
   원인은 CMSSW_10_6_X 의 `LANG=C` — python3.6 `open()` 기본 인코딩이 ASCII 라서 파일 전체가
   못 읽힌다. 조치: (a) `datasets.yaml`·`submit_ttbarIdExtend.py`·`resolve_parents.sh` 를
   **순수 ASCII 로 환원**(패키지 전체 재검사: 위반 0), (b) `load_yaml()` 이 `encoding="utf-8"`
   을 명시하도록 고쳐 **같은 실수가 다시는 치명적이 되지 않게** 함.
2. **PyROOT 사용 불가 발견.** CMSSW_10_6_32_patch1 의 ROOT 6.14 는 python2 용 빌드라
   python3 에서 `import ROOT` 가 `ImportError: ... (PyInit_libPyROOT)` 로 죽는다. 따라서
   신규 **`Validation/scripts/check_extend_invariants.C`** (순수 ROOT 매크로)를 추가:
   `Expanded_genTtbarId` 인코딩 계약 7개를 로컬 산출물에서 검증한다 —
   `nAddBJets<=2` 불변 / `==3`→61,62 / `>=4`→71,72 / **sub-code 56 부재** / prefix 보존 /
   원 sub-code∈{53,54,55} / `run==1`, 그리고 61·62·71·72 카운트와 "확장 분기가 한 번도
   안 타졌다"는 경고까지 출력. 사용: `root -l -b -q 'scripts/check_extend_invariants.C("<file>")'`.
   로직은 합성 데이터로 파이썬 이식본을 통해 검증(정상 4행 위반 0, 오류 5행 전부 검출);
   **ROOT 실행은 미검증.**
   부수 확인: VarParsing 이 `maxEvents` 지정 시 출력 파일명에 `_numEventN` 을 붙인다
   (`ttbarIDExtend_local2018_numEvent2000.root`). CRAB 은 maxEvents 를 쓰지 않으므로
   `JobType.outputFiles` 와의 정합은 유지된다.

## 2026-07-27 — v13.3: py3.6 호환성 수정 + 로컬 불변조건 검증 통과 (2018)

**로컬 검증 통과 (실기기, 2026-07-27)** — 2018 producer 는 물리적으로 정상이다:

```
scanned 20000 events; nAddBJets>=3 : 63   (61=34 62=23 71=6 72=0)
  PASS le2_unchanged / eq3_in_61_62 / ge4_in_71_72 / no_subcode_56
  PASS prefix_preserved / orig_was_53_54_55 / run_is_1
VERDICT: ALL INVARIANTS PASS
```

`maxEvents=20000` 으로 키운 덕에 **확장 분기가 실제로 63 event 에서 타졌다** (2000 event 에서는
0 이었다). 즉 v10 치명 버그(sub-code 56)가 살던 경로가 2018 에서 정상 동작함을 실측으로 확인했다.
`endJob summary: total rows=20000 missing (전부)=0`.

**수정 — `submit_ttbarIdExtend.py` 가 py3.6 에서 즉사 (v13.1 에서 내가 넣은 버그):**

- `subprocess.run(..., text=True)` 는 **python 3.7+** API 인데 이 패키지는
  CMSSW_10_6_32_patch1 = **python 3.6.4** 에 pin 되어 있다 → `--preflight` 가
  `TypeError: __init__() got an unexpected keyword argument 'text'` 로 죽었다.
  2곳을 `universal_newlines=True` 로 교체 (같은 저장소의 `Validation/scripts/das_lineage.py:121`
  이 이미 그 규약을 주석까지 달아 쓰고 있었는데 놓쳤다).
- 재발 방지: 파일 헤더에 **"PYTHON 3.6 ONLY -- DO NOT USE 3.7+ APIs"** 블록을 추가하고
  이 환경의 함정 4개를 한자리에 명시 — `text=`/`capture_output=`(3.7+), `dict |=`·
  `removeprefix`(3.9+/3.10+), `LANG=C` 로 인한 `open()` ASCII 기본값, PyROOT 사용 불가.
  AST 로 `subprocess.run` 의 3.7+ 키워드 잔존 여부를 재검사(0건).
- 참고: `tempTTHH`·`NtupleForge` 는 CMSSW_14_2_1(py3.9)이라 `text=True` 가 정상이며 실제로
  lxplus 에서 동작 확인됨 — 이 제약은 **10_6_X 패키지에만** 적용된다.

## 2026-07-27 — v13.4: `--check-das` -json 수정, `--max-files` 비권장화, 제출 정책 확정

**수정 2건 (둘 다 실행 중 발견, 둘 다 내가 넣은 버그):**

1. **`--check-das` 가 14/14 FAIL (거짓)**. `dasgoclient -query "summary dataset=..."` 의
   **plain-text** 출력은 컬럼 레이아웃이라 `nevents=N` 정규식이 절대 안 맞는다. 데이터셋은
   멀쩡했다 — 같은 셸에서 `file dataset=` 쿼리가 10,010개 파일을 세었고 CRAB 이 스모크를
   정상 접수했다. `-json` + `summary[0].nevents` 로 교체(plain-text fallback 유지).
   **같은 버그를 NtupleForge `submit_crab.py` 에서 먼저 고쳤는데 이 파일로 전파하지 않은 것**이
   원인 — 두 저장소가 같은 DAS 헬퍼 패턴을 복제하고 있다는 신호다.
2. **argparse `--help` 가 `ValueError: unsupported format character` 로 깨짐**. help 문자열의
   `100%` 를 이스케이프하지 않아서. argparse 는 help 를 `%`-포맷하므로 리터럴 `%` 는 `%%`.
   전 옵션(11개) help 를 실제로 `format_help()` 로 통과시키는 검사를 추가로 수행.

**제출 정책 [DECIDED 2026-07-27, 사용자]:**

- **`units_per_job` 은 1 유지** (2017 생산과 동일 조건). MiniAOD 파일이 NanoAOD 보다 훨씬 많아
  7샘플 = **20,953 jobs** (TTbar_SemiLep 만 10,010) 이고 job 하나는 47k event ≈ 55 s 로
  오버헤드 비중이 크지만, "2017 과 동일" 을 우선한다. 참고 수치: `units_per_job=10` 이면
  2,097 jobs / job 당 ~9분. (당시 예측치. **실제 완료 캠페인은 혼합 설정 11,946 jobs** — v13.14)
- **`--max-files` 로 스모크하지 않는다.** `Data.totalUnits=N` 은 **완결 불가능한 부분 task** 를
  만든다: 103 files 중 5개만 도는 task 가 `--report` 에 `done 5/5 = 100%` 로 뜨지만 실제
  커버리지는 5% 이고, 나머지를 처리하려면 같은 dataset 을 **또** 제출해야 해서 같은 LFN 아래
  timestamp 디렉토리가 둘로 갈린다 → `make_filelists_miniAOD.py` 가 둘 다 주워 3-key 중복
  (`matchTtbarId` exit 7). **대신 최소 dataset(`TTbb_DiLep`, 103 files)을 통째로** 던져
  스모크로 쓴다. `--max-files` 의 help 를 DISCOURAGED 로 바꾸고 이유를 명시했다.
  (기존에 `--max-files 5` 로 나간 스모크 task 는 kill·정리 후 재제출.)

## 2026-07-27 — v13.5: 2018 extend 7샘플 제출 완료 + 중복 제출 가드

**제출 완료 (실기기)**: `--preflight --check-das` **31 PASS / 1 WARN / 0 FAIL** 후
7샘플 전부 제출 성공 (`submitted : 7`, task name 7개 유일, timestamp 123350~123411).
job 수 = MiniAOD 파일 수 합계 **20,953** (`units_per_job: 1`).

**preflight 이 부수적으로 드러낸 사실 — MiniAOD 와 NanoAOD 의 event 수가 다르다:**

| sample | MiniAODv2 | NanoAODv9 | nano/mini |
|---|---|---|---|
| TT4b | 9,844,000 | 9,844,000 | 1.0000 |
| TTbar_SemiLep | 478,982,000 | 476,408,000 | 0.9946 |
| **TTbar_Hadronic** | 343,248,000 | 334,206,000 | **0.9737** |
| TTbar_DiLep | 146,010,000 | 145,020,000 | 0.9932 |
| TTbb_SemiLep / Hadronic | 동일 | 동일 | 1.0000 |
| TTbb_DiLep | 4,858,850 | 4,792,850 | 0.9864 |

2017 에서 이미 확인된 현상과 같다(중앙 NanoAOD 가 부모 MiniAOD event 의 일부를 떨어뜨림;
2017 TTToSemiLeptonic 2.68% — [06](06_validation_results.md)). **버그가 아니다.** 다만
운영상 중요한 함의가 있다: extend(=MiniAOD 기반)는 nano 보다 event 가 **많다**. `matchTtbarId`
는 nano 를 순회하며 extend map 에서 찾으므로 `unmatched 0` 기준은 그대로 유효하고(extend ⊇ nano),
남는 extend row 는 조회되지 않을 뿐이다. **반대로 완결성 점검 시 기준 수치를 혼동하면 안 된다** —
extend 생산 완결성은 **MiniAOD** nevents, ntuple/prescan 완결성은 **NanoAOD** nevents 로 본다.

**신규 가드 — `Validation/filelists/make_filelists_miniAOD.py`:**

- `check_single_crab_submission()` 추가: 샘플별로 CRAB LFN 의 timestamp 디렉토리
  (`<primary>/<tag>/<YYMMDD_HHMMSS>/0000/`)가 **2개 이상이면 즉시 FATAL(exit 3)** 하고,
  지울 디렉토리와 각 파일 수를 그대로 출력한다. `ALLOW_MULTI_CRAB_SUBMISSION=1` 로 우회 가능.
- **왜**: 2026-07-27 에 이 상황이 실제로 만들어질 뻔했다 — `--max-files 5` 부분 task 의 5 job 이
  이미 끝나 EOS 에 파일 5개가 남은 상태였고, 그대로 전체 재제출했다면 같은 LFN 아래 timestamp 가
  2개(103022=5 files, 123411=103 files) 공존했을 것이다. **실제로는 사용자가 kill → project dir
  삭제 → EOS `2018/` 전체 삭제까지 수행해 clean 하게 재제출했으므로 사고는 없었다.** 가드는 예방용. `os.walk` 는 둘 다 주워 event 가 중복되고, 그 결과는
  한참 뒤 `matchTtbarId` **exit 7 (3-key duplicate)** 로만 드러난다 — 원인 추적이 비싸다.
  이제 filelist 생성 시점에 잡힌다. 정상 제출 1개면 `[crab] <sample>: submission timestamp ...`
  로 어느 제출을 썼는지 로그에 남는다.
- 합성 경로로 동작 검증(단일 → 통과, 이중 → FATAL 대상 검출). 실제 EOS 실행은 미검증.

---

## 2026-07-27 — v13.6: 재현성 감사 — README 정리, 깨진 명령 수정, 상태 문서 정정 (코드 로직 무변경)

Phase 3(analyzer 2018 대응) 착수 전에 "지금까지의 진행 사항이 문서에 제대로 남아 있는가"를
점검한 결과다. **C++/CMSSW 로직 변경 없음.**

**README 4편에 연도 재현 절차 추가** (감사 전 4편 모두 "2018" 언급이 **0회**였다):

- `README.md` — 30초 빠른 시작에 `year=2018`, 불변조건 매크로, preflight 체인 추가.
  헤더 상태줄에 v13.x(2018 제출 완료, 검증 대기) 반영.
- `TtbarIdExtender/README.md` — §2.2 preflight 순서(`--max-files` 금지 명시),
  §2.2b 2018 재현(`resolve_parents.sh 2018` + MiniAOD⊋NanoAOD 주의).
- `Validation/README.md` — §0.1 era 인자·중복 제출 가드, §0.2 불변조건 매크로,
  §4.1 2018 복붙 블록(short-name → project-key 매핑 포함).
- 워크스페이스 `RUNBOOK_UL18_to_controlplots.md` 가 저장소 간 실행 순서의 정본이라는
  포인터를 `README.md` 에 명시(중복 서술 방지).

**깨져 있던 명령 수정 (복붙하면 실패했다):**

- `Validation/README.md` §6 의 `bin/scanOrder --filelist <fl> --report-every 5000000` —
  `scanOrder.cc` 는 `--filelist/--tree/--max-files/--csv/-h` 만 받고 나머지는
  `ERROR: unknown arg` + exit 2 다. 실제 플래그 4개로 교체.
- `Validation/README.md` §0 이 "스크립트 상단 `SAMPLE_DIR` 를 고친 뒤 **인자 없이** 실행"
  이라고 해 §0.1(era 인자 필수)과 정면으로 모순했다 → `era [SAMPLE_DIR]` 규약으로 통일.
  `make_filelists.py 2018` 은 `SAMPLE_DIR_BY_ERA["2018"]` 가 빈 문자열이라 **2번째 인자가
  필수**(없으면 FATAL)라는 점도 명기.
- `TtbarIdExtender/README.md` §2.4 의 "`make_filelists_miniAOD.py` 의 `SAMPLE_DIR` 로 지정" —
  지금은 `SAMPLE_DIR_BY_ERA` + CLI 2번째 인자다 → 실제 명령으로 교체.
- `Validation/README.md` 에 `## 0.` 이 **두 개** 있어 §0.1/§0.2 가 어디에 걸리는지 모호했다
  → 앞의 워크플로 절을 번호 없는 절로 변경.

**상태 문서 정정 (완료된 것을 "미완"이라 하고 있었다):**

- `docs/01_status.md` **O1 CLOSED** — "⏳ 아직 안 함: `cmsRun` 으로 실제 생산 1회" 는 O6 에
  기록된 로컬 2000-event 생산으로 이미 충족돼 있었다(같은 표 안에서 자기모순).
- `docs/01_status.md` **O6** — 제출 완료를 선언한 뒤에도 `datasets.yaml … enabled:false`,
  "다음 순서 ① resolve_parents → ⑤ 본제출", 그리고 v13.4/v13.5 에서 **금지로 전환된**
  `--max-files 5` 스모크를 여전히 권하고 있었다 → 끝난 단계(①~⑤)와 남은 단계(⑥~⑨)로 분리,
  `--max-files` 금지 이유 명시, 2017 tt+nb 수치의 정본이 `06_validation_results.md` 임을 표시.
- `crab/datasets.yaml` 헤더의 "Every entry is enabled:false on purpose" / "-vN suffix is
  UNVERIFIED" → **해석·제출 완료** 서술로 교체하고, 그 규칙은 **새 era 를 추가할 때의 절차**로
  재배치. 비대칭 `-vN`(2018 TTbar_SemiLep, 2017 TTbar_Hadronic)은 "정상, 고치지 말 것"으로 명시.
  파일은 ASCII-only 유지 확인(v13.2 재발 방지).

**`.gitignore`**: v13.5 에서 Write 도구로 재생성한 파일이 아직 **untracked(`??`)** 라 아무것도
보호하지 못하고 있다 — 커밋 필요. 또한 `Validation/lookup/ttnb_*.root` 7개(12 MB)는
**추적 중**인데 새 규칙이 `ttnb_*.root` 를 무시하도록 되어 있어 규칙이 무력하다(추적 중 파일에는
gitignore 가 적용되지 않는다). `Validation/README.md` 는 이 파일들을 의도적 보존물로 설명하므로
**규칙에 예외를 두든 git 에서 내리든 한쪽으로 정리**할 것 (미결).

**정리(삭제)**: `Validation/filelists/__pycache__`, 추적 중이던 `.DS_Store`(working tree 에서
삭제 — `git rm --cached` 로 index 에서도 내려야 한다), v13.5 에서 지운 preflight 로그 2개는
아직 index 에 남아 있어 `git rm` 필요.

---

## 2026-07-27 — v13.7: 진행 중 CRAB 부분 산출물로 하는 로컬 검증 워크북 (코드 무변경)

extend 캠페인(7 task / 20,953 job)이 **아직 돌고 있는 상태**에서, 이미 EOS 에 stage-out 된
파일만으로 이 저장소의 도구를 검증하는 절차를 워크스페이스 루트
`WORKBOOK_local_test_partial_CRAB.md` 에 정리했다. **C++/스크립트 변경 없음.**

**왜 부분 산출물로도 유효한가 (이 워크북의 근거)**:
`matchTtbarId` 는 nano 를 순회하며 extend map 을 조회하고, **`unmatched > 0` 이어도 exit 0** 을
낸다(`tools/matchTtbarId.cc:476-481`). 실패로 판정하는 것은 5(matched 0) · 6(genTtbarId 불일치) ·
7(3-key 중복) · 8(확장 불변식 위반) · 9(`run != 1`) 뿐이다. 따라서 **정확성**(byte-identity +
확장 불변식)은 지금 전부 검증 가능하고, 검증 못 하는 것은 **완결성**(nevents 대조)뿐이다.
이 사실을 문서 맨 앞(BLUF)에 표로 박아 두었다 — 예전에는 "부분 산출물이면 매칭을 못 돌린다"고
오해할 여지가 있었다.

**수록 테스트**:

- **A** `scripts/check_extend_invariants.C` 를 나온 파일마다 — filelist 도 nano 도 불필요하고
  파일 단위로 독립이라 부분 산출물에 가장 잘 맞는다. `VERDICT: ALL INVARIANTS PASS` 를 grep.
- **B** `make_filelists_miniAOD.py 2018 <EOS>` — **v13.5 중복 제출 가드의 첫 실제 EOS 실행**
  (그때까지 합성 경로로만 검증됐다). FATAL exit 3 이 나면 그건 가드가 제대로 작동한 것.
- **C** `matchTtbarId` 를 **가장 작은 `ttbb_2L2Nu`(nano 6 파일 / 4,792,850 event)** 부터.
  nano 를 앞 몇 파일로 자르면 부분 extend 와 겹침이 0 이 되어 exit 5 가 날 수 있으므로
  **nano 는 자르지 않는다**. 작은 4샘플(≤15 파일)만 하고, 큰 3샘플(`TTTo*`, 최대 391 파일 /
  476 M)은 external-sort 경로가 필요해 **완료 후 §2-5 에서 한 번만** 한다.
- **E** `extractTtbarIdPatch` 는 **스키마 확인용으로만**. 부분 patch 를
  `tempTTHH/DerivedCorr/expandedTtbarId/2018` 에 복사하면 빠진 event 가 조용히 "확장 안 됨"으로
  처리되어 **틀린 물리 결과**가 나온다 → `/tmp` + `PARTIAL_DO_NOT_USE_` 접두사로 강제.

**작성 중 하위 에이전트 검증으로 잡은 결함**(워크북에 반영):
`$?` 가 `| tee` 때문에 **tee 의 상태**라 exit 5/6/7/8/9 가 전부 0 으로 보이던 문제
(→ `${PIPESTATUS[0]}`), `ls bin/` 기대 목록에 이 저장소 `Validation/bin/` 에 없는
`compareExtendToCentral`(그건 `TtbarIdExtender/bin/` 쪽)이 들어 있던 것, `matchTtbarId` 의
**exit 3**(filelist 비었거나 못 엶)이 문서화되지 않아 물리 실패와 섞일 수 있던 것.

---

## 2026-07-27 — v13.8: `--report` 추가 (NtupleForge 와 대칭) + `crab/status.py` 집계 버그 수정

사용자 지적: "왜 여기엔 `--status` 만 있고 NtupleForge 처럼 `--report` 는 없나?"
**설계 이유가 없었다 — 그냥 비대칭이었다.** NtupleForge `submit_crab.py` 는 2026-07 에
`--report`(compact 표)를 얻었는데 이 저장소는 못 받았다.

**신설 — `crab/submit_ttbarIdExtend.py --report`**

- per-sample 정렬 표: `done / run / idle / transf / fail / other / total` + **TOTAL 행**.
  `--process`/`--era` 필터를 존중하고, 새 task 를 제출하지 않는 **읽기 전용**이다.
- `--status`(= `crab status` 원본 전량 출력)와의 역할 분리를 help 와 README §2.3 에 명시.
  `--status`/`--report`/`--resubmit`/`--kill` 은 **넷 중 하나만** 허용(기존 셋 → 넷).
- `contextlib.redirect_stdout` 으로 CRAB 의 verbose dump 를 삼켜서, 7개 task 출력에 표가
  묻히지 않게 했다.
- **버킷 규칙을 NtupleForge 와 의도적으로 중복**(`REPORT_COLUMNS`,
  `KNOWN_OTHER_STATES`, `summarize_status`, `print_report`). 두 저장소는 CMSSW 릴리스가 달라
  모듈을 공유할 수 없지만 컬럼이 어긋나면 두 캠페인 리포트를 나란히 못 읽는다 →
  **양쪽 파일 주석에 "한쪽만 바꾸지 말 것"을 박아 뒀다.**
  실측 검증: 같은 입력으로 두 저장소의 `print_report` 출력이 **byte-identical**,
  `REPORT_COLUMNS`·`KNOWN_OTHER_STATES` 도 동일함을 확인.

**버그 수정 — `crab/status.py` 의 job 집계가 맞지 않았다**

- 기존: `done/run/idle/fail` 만 찍고 `tot=sum(jobs.values())` → **`transferring` 이
  아예 안 보이는데 tot 에는 포함**되어 `done+run+idle+fail ≠ tot`. `units_per_job: 1` 로
  job 이 ~21k 개이고 상당수가 T3_CH_CERNBOX stage-out 중 `transferring` 에 오래 머물기 때문에
  **가장 큰 버킷이 투명인간**이었다. `cooloff`/`held`/`unsubmitted` 도 동일하게 사라졌다.
- 수정: `submit_ttbarIdExtend.py` 의 `summarize_status` 를 **import 해서 재사용**
  (one-fact-one-place; 두 도구가 "other" 정의를 두고 어긋날 수 없다). 이제
  `transf`·`other` 컬럼이 찍히고 **모든 job 이 찍히는 컬럼에 들어가 tot 과 일치**한다.
- 코드가 모르는 상태가 나오면 두 도구 모두 **`[WARN] unknown CRAB job state(s)`** 로 보고한다
  (조용히 `other` 에 삼키지 않는다).
- 두 스크립트의 용도 차이를 `status.py` 헤더에 문서화: `status.py` 는 **workArea 스캔**
  (datasets.yaml 이 바뀌었어도 찾아냄), `--report` 는 **datasets.yaml 기반**(era/process 필터).

**환경 제약 준수**: py3.6 호환(3.7+ API 없음), ASCII-only, argparse `%` 이스케이프 확인,
`py_compile` 통과. 실행 중인 캠페인에는 영향 없다 — 읽기 전용이고, CRAB sandbox 는 제출
시점에 동결되므로 submitter 수정이 이미 뜬 job 에 닿지 않는다.

---

## 2026-07-27 — v13.9: `--resubmit` 결과 보고 수정 — "resubmitted : 3" 이 거짓이었다

사용자가 2018 `--resubmit` 로그를 공유했고, 요약이 `resubmitted : 3` 인데 **실제로 재제출된
task 는 2개**였다. 원인은 `crabCommand("resubmit", ...)` 의 통보 방식이 일관되지 않은 것이며,
세 가지 결과가 두 개의 **오해를 유발하는** 라벨로 뭉개져 있었다 (전문: [08](08_troubleshooting.md) **T-18**).

| CRAB 이 실제로 한 말 | 예외? | 예전 라벨 | 실제 의미 |
|---|---|---|---|
| `Resubmit request sent to the server.` | 아니오 | `[resubmit ok]` ✔ | 유일한 진짜 성공 |
| `Found no jobs to resubmit. Only jobs in status failed...` | **예** | `[resubmit FAILED]` ✘ | **실패 job 이 없다 = 좋은 소식** |
| `The task has not been submitted to the Grid scheduler yet ... will not proceed with the resubmission.` | **아니오** | `[resubmit ok]` ✘✘ | **거부됨 — 아무것도 재큐되지 않았다** |

세 번째가 위험한 쪽이다: 예외를 던지지 않으므로 성공으로 집계돼 **"실패 job 을 재제출했다"고
착각**하게 만든다.

**수정**:

- `crab_action_one()` 이 CRAB 의 stdout/stderr 를 캡처해 `    | ` 접두사로 **그대로 되돌려 찍고**
  (숨기지 않는다), `classify_resubmit(text, exc)` 로 **sent / nothing / refused / unclear /
  error** 로 분류한다. 텍스트가 예외보다 우선한다 — CRAB 이 benign 케이스를 예외로 알리기 때문.
- 반환형을 bool → outcome 문자열로 바꾸고, **`sent` 만** 재제출로 집계한다.
  아는 표식이 하나도 없으면 `unclear` — **성공으로 치지 않는다**(조용한 오보 방지).
- 요약 끝에 outcome breakdown + `NOTE: 'refused' tasks were NOT resubmitted. Re-run
  --resubmit for them in a few minutes.` + (sent 가 0이면) `=> Nothing was actually
  resubmitted in this pass.` 를 찍는다.
- `--status`/`--kill` 도 같은 캡처·에코 경로를 타지만 판정은 기존대로 ok/error 2분법이다.
- 사용자 로그의 **5가지 실제 문자열 + 침묵/타 예외 2건**으로 분류기 회귀 테스트 통과.
  그 로그를 다시 넣으면 요약이 `resubmitted : 2` (sent 2 / nothing 4 / refused 1 / noproj 7) 로 나온다.

`TtbarIdExtender/README.md` §2.3 에 출력 읽는 법 표를 추가했다.

---

## 2026-07-27 — v13.10: **CRAB task 당 job 10,000 상한** — 2018 TTbar_SemiLep 이 조용히 죽어 있었다

v13.9 로 `--resubmit` 출력이 정직해진 직후, 사용자가 `--status` 원문을 공유해 **진짜 원인**이
드러났다: `TTbar_SemiLep_2018_extend` 의 서버 상태가 `SUBMITREFUSED` 이고 경고가
`The splitting on your task generated 10010 jobs. The maximum number of jobs in each task is 10000`.
즉 **하루 동안 이 task 는 job 을 한 개도 돌리지 않았다.** 전문: [08](08_troubleshooting.md) **T-19**.

**왜 못 잡았나** — 세 겹으로 숨었다:

1. **제출 시점에 거부되지 않는다.** client 는 `submitted : 7` 로 성공을 보고하고 서버가
   *나중에* task 를 세워 둔다. 그래서 제출 로그·문서에 "7 tasks / 20,953 jobs"가 남았다.
   실제로 돈 것은 **6 tasks / 10,943 jobs**.
2. **총합만 보면 정상이다.** 20,953 = 188 + **10,010** + 7,195 + 3,069 + 219 + 169 + 103.
   per-task 값을 상한과 비교해야 보이는데 preflight 가 그걸 안 했다.
3. **`--report` 행이 전부 0 이다.** `jobsPerStatus` 가 비어 있으니 "아직 안 시작"과 구분이 안 된다.
   게다가 `crab resubmit` 은 **scheduler 에 도달한 task 의 FAILED job 만** 재큐하므로 원리적으로
   손을 못 쓴다 — v13.9 가 `refused` 로 정직하게 보고한 게 이 상황이었다.

**수정 (세 겹 모두)**:

- **예방** — `--preflight --check-das` 가 DAS `summary` 의 `nfiles` 도 읽어
  `ceil(nfiles / units_per_job)` 을 계산한다. `CRAB_MAX_JOBS_PER_TASK = 10000` 초과면 **FAIL**
  (+ 필요한 `units_per_job` 값을 계산해 알려 준다), 90% 초과면 WARN, 그 외 PASS 로 job 수를 찍는다.
  `units_per_job` 우선순위는 `build_config()` 와 동일(항목별 override > `resources.extend`).
- **수정** — `datasets.yaml` 2018 `TTbar_SemiLep` 에 **`units_per_job: 2`**(→ 5,005 jobs)를 박고,
  "1 로 되돌리지 말 것"과 이유를 항목 주석에 남겼다. 항목별 override 는 원래 지원되던 기능이다.
- **가시성** — `--report`/`--status` 가 task-level `SUBMITREFUSED`/`SUBMITFAILED`/`FAILED`/
  `UNKNOWN`(=`DEAD_TASK_STATES`)을 `[!! ... !!] this task will NEVER run` 로 찍고 CRAB 의 해당
  경고 줄을 인용하며, `--report` 요약 끝에 **DEAD TASK 목록**과 복구 지침을 낸다
  ("all-zero 행은 '아직 안 시작'이 아니다").

**T-17 과의 구별**: 둘 다 `SUBMITREFUSED` 지만 T-17 은 stage-out 권한(HTTP 403), 이건 job 수
초과다. `--status` 의 CRAB 원문 경고 줄로 갈린다. 그리고 **이 경우는 산출물이 없으므로 EOS 청소가
불필요**하다 — project dir 만 지우고 재제출한다.

문서 정정: "7 tasks / 20,953 jobs 제출 완료" 라고 적었던 3곳
(`TtbarIdExtender/README.md` §2.2b, `docs/01_status.md` O6, 워크스페이스 RUNBOOK 헤더)을
**6 tasks / 10,943 jobs 실행 + TTbar_SemiLep 재제출 필요**로 고쳤다.

---

## 2026-07-27 — v13.11: `units_per_job` 을 2 → **10** (사용자 지적; CPU 효율까지 회수)

v13.10 은 상한(10,000)만 넘기려고 최소값 **2** 를 넣었다. 사용자가 더 나은 지적을 했다 —
*"expanded ttbar id 는 run/lumi/event 로 각각 이벤트를 다 읽어들이니 file 개수를 몇 개로 하든
상관없다"*. 맞다. 그래서 10 으로 올렸다.

**왜 맞는가 (계약으로 확인)**: 각 job 은 `(run, luminosityBlock, event, ...)` 행을 쓰고,
소비자 `matchTtbarId`/`matchTtbarIdSorted` 는 **filelist 전체에 3-key map 하나**를 만든다 —
행이 어느 파일에서 왔는지 보지 않는다(`tools/matchTtbarId.cc` 의 map 적재 루프).
따라서 file→job 묶음은 **물리에 완전히 무관**하고, 순수 운영 knob 이다.

**그러면 1 은 왜 나빴나** (2018 `TTbar_SemiLep` 실측, 파일당 ~47.6k event ≈ 55초 + 시작 ~90초):

| `units_per_job` | jobs | job 당 | 시작 오버헤드 비중 | |
|---|---|---|---|---|
| 1 | 10,010 | ~2.4분 | ~63% | CRAB 상한 초과 → SUBMITREFUSED |
| 2 | 5,005 | ~3.3분 | ~45% | v13.10 의 최소 수정 |
| **10** | **1,001** | **~10.7분** | **~14%** | **채택** |
| 20 | 501 | ~19.8분 | ~7% | 가능(walltime 상한 1440분과 무관) |

즉 upj=1 은 CRAB 이 매 task 마다 내던 `average jobs CPU efficiency is less than 50%` 경고의
원인 그 자체였다(2026-07-27 실측 CPU eff 20~45%, waste 50~58%). 부수 효과로 출력 파일이
10,010 → **1,001** 개가 되어 뒤의 `sortSplitExtend`/`matchTtbarIdSorted` 도 싸진다.
참고 스케일: 이 7샘플의 MiniAOD/NanoAOD 파일 수 비는 **~22.5**(SemiLep 은 25.6)이므로
MiniAOD 10개는 아직 NanoAOD 파일 1개분 event 보다 적다.

**의도적으로 하지 않은 것 — 나머지 6 task 는 그대로 뒀다.** 완료 4개 + 99% 진행 2개(failed 0)의
`units_per_job` 을 바꾸려면 kill → project dir 삭제 → **EOS 산출물 삭제** → 전량 재생산이 필요하고
(같은 LFN 에 timestamp 두 개가 생기면 3-key 중복 → `matchTtbarId` exit 7), 그건 끝난 일을
버리는 짓이다. 값 조정은 **어차피 재제출해야 하는 task 에만** 한다 — `TTbar_SemiLep` 은
SUBMITREFUSED 라 산출물이 아예 없어 공짜로 바꿀 수 있었다.
결과적으로 2018 은 **혼합 설정**(SemiLep 만 10, 나머지 6개는 1)이고, 위 "물리에 무관" 때문에
무해하다. 재제출 후 2018 총 job 수 = **11,944**.

`TtbarIdExtender/README.md` §2.2b 에 `units_per_job` 전용 절(표 + "끝난 task 는 건드리지 말라"
경고)을 추가했고, T-19 의 ② 항목도 10 기준으로 갱신했다.

---

## 2026-07-27 — v13.12: 사용자 결정 — 2018 전량 재제출, 캠페인 기본값 upj 10 / mem 2500

v13.11 은 `TTbar_SemiLep` 항목만 10 으로 올리고 나머지 6 task 는 "끝난 일을 버리지 말자"는
이유로 upj=1 그대로 뒀다. 사용자가 **전량 재제출**을 선택했으므로 그 제약이 사라졌고, 캠페인
설정을 통일했다.

**`crab/site_config.yaml` `resources.extend`**:

| | 이전 | 이후 | 근거 |
|---|---|---|---|
| `units_per_job` | 1 | **10** | v13.11 의 효율 분석 (job 2.4분 중 90초가 startup → 오버헤드 63%→14%) |
| `max_memory_mb` | 2000 | **2500** | 관측 피크 **1731 MB**(2018 TTbb_Hadronic) 대비 헤드룸 13% → 44% |
| `max_runtime_min` | 1440 | 1440 (무변경) | 예상 job 시간 ~10.7분이라 상한과 무관 |

**메모리를 올린 이유**(사용자 지시): 피크 메모리는 job 이 처리하는 파일 **수**의 함수가 아니라
(순차 처리라 누적되지 않는다) **가장 무거운 입력 파일**의 성질이다. 다만 job 당 10 파일이면
"무거운 파일을 포함한 job"의 비율이 ~10배가 되므로 상한에 닿는 job 이 늘어난다. gen-only job 이
2.5 GB 를 요청해도 거의 모든 slot 에 매칭되므로 헤드룸이 사실상 공짜다.

**2018 전량 재제출 효과(기대치)**: 7 tasks / **20,953 → 2,097 jobs** (정확히 10배).
**[2026-07-27 실측 정정]** 실측 결과(2026-07-27 완료): **7 tasks / 11,946 jobs / failed 0, 전부 COMPLETED**. 설정이 **혼합**으로 돌았다 — `TTbar_SemiLep` 만 upj=10(1,003 jobs; 1,001 + CRAB block 경계로 +2), 나머지 6개는 upj=1(= MiniAOD 파일 수). 재제출이 `site_config.yaml` 기본값을 10 으로 올리기 **전에** 이뤄져 `datasets.yaml` per-entry override 만 적용된 상태였다. **무해하다**(D15: packing 은 물리에 무관) → 재생산하지 않는다. upj=10 기본값은 **다음 제출부터** 적용된다.
샘플별: SemiLep 1,001 / Hadronic 720 / DiLep 307 / TTbb_SemiLep 22 / TT4b 19 /
TTbb_Hadronic 17 / TTbb_DiLep 11.

**`datasets.yaml` 의 per-entry `units_per_job: 10`(SemiLep)은 남겨 뒀다** — 이제 기본값과 같아
중복이지만 **의도적 floor** 다: 이 dataset 은 upj=1 이 물리적으로 불가능한 유일한 항목이므로,
누가 전역 기본값을 되돌려도 이 항목은 살아남는다. (preflight 도 FAIL 시키지만, *깨질 수 없는
설정* > *깨진 걸 잡는 검사*.) 그 이유를 항목 주석에 명시했다.

**신설 — `TtbarIdExtender/README.md` §2.2c "한 연도를 처음부터 다시 제출"**: 순서가 중요한
7단계 절차(kill → **run/idle/transf 가 0 이 될 때까지 대기** → EOS 삭제 → project dir 삭제 →
preflight → 제출 → SUBMITREFUSED 확인) + 재제출 후 기대 job 수 표.
**왜 순서인가**: kill 완료 전에 EOS 를 지우면 뒤늦게 stage-out 하는 job 이 지운 디렉토리를
되살리고, 그게 새 제출의 timestamp 와 공존해 3-key 중복 → `matchTtbarId` **exit 7** 이 된다.
(v13.5 의 timestamp 가드가 filelist 단계에서 잡지만, 애초에 안 만드는 게 맞다.)

**2017 은 재생산하지 않는다.** upj=1 로 완료된 산출물은 packing 과 무관하게 동일하며 그대로
유효하다 — 효율은 이미 지난 일이다. 이 문장을 README 와 site_config 주석 양쪽에 박았다.

---

## 2026-07-27 — v13.13: job 10,000 상한을 **규칙으로 승격** — D15 신설 + 값 결정 지점 전부에 경고

사용자 지시: *"number of job 개수 정하는 위치에 주석으로 job 개수가 10000개가 넘으면 에러 뜨니까
units_per_job 개수 조정말라는 얘기를 기입해 두고 docs에도 기입해서 추후 이 값에서 문제가 발생
안하도록 만들라."* T-19 는 **사고 기록**이라 "다음에 이 값을 만지는 사람"이 읽을 위치가 아니었다.
그래서 규칙을 **DECIDED 항목**으로 올리고, **값을 정하는 모든 지점**에 경고를 박았다.

**신설 — [04](04_decisions.md) D15** (이 규칙의 정본):
`njobs = ceil(nfiles/units_per_job)`, 상한 10,000/task, 거부가 서버 측이라 조용함,
`resubmit` 으로 복구 불가, 물리 무관성(D7 3-key 매칭이 file→job packing 을 안 봄) 근거,
3중 강제 수단, 기각 대안(`units_per_job: 2` / `splitting: Automatic` / 큰 샘플 분할).
[01](01_status.md) DECIDED 표에도 한 줄 등재.

**경고를 박은 지점 — 이 저장소**:

| 위치 | 무엇 |
|---|---|
| `crab/submit_ttbarIdExtend.py` `cfg.Data.unitsPerJob` 대입부 | **실제 코드 지점.** 여기엔 경고가 전혀 없었다 — 가장 중요한 누락이었다. 증상 4단계 + 3중 가드 + "올리는 건 안전" 명시 |
| `crab/site_config.yaml` `resources.extend.units_per_job` | `!!` 박스로 "DO NOT LOWER" + preflight 명령어 |
| `crab/site_config.yaml` `resources.enriched.units_per_job` | 폐기 경로지만 `1` 이 남아 있어 복사될 위험 → 같은 경고 |
| `crab/datasets.yaml` per-entry override | 기존 주석에 floor 의도 명시 (v13.12) |
| `TtbarIdExtender/README.md` §2.2b | 절 맨 앞에 🚫 규칙 박스 (올리기=안전 / 내리기=검증 필수) |

**경고를 박은 지점 — NtupleForge (같은 함정이 있는데 가드가 없었다)**:

`submit_crab.py` 도 FileBased 이고 **job-count preflight 가 없다**. 지금은 NanoAOD 기반이라
최대 task 가 **780 jobs**(2018UL `WJetsToLNu_HT200To400_ext1`, 780 files)로 안전하다 —
`TTbar_SemiLep` 은 event 수 1위지만 파일 수는 4위(391)이고 **job 수는 파일이 정한다**(초기
서술을 이렇게 정정). MiniAOD 로 돌리거나 10,000 파일 초과
dataset 을 추가하면 즉시 같은 사고가 난다. 그래서:
`crab/submit_crab.py`(`conf.Data.unitsPerJob` 대입부),
`crabConfig/config_ttHH2017UL.yaml`,
`script/build_ul18_from_log.py`(→ **생성되는 2018 config 2개에 자동으로 각인**되므로 재생성에도
살아남는다. 재생성 후 config 2개 + `samples_2018UL.json` 무변경 확인),
그리고 문서 `docs/03_DECISIONS.md` **D-2026-07-27-crab-job-limit** +
`docs/05_troubleshooting.md` **A16**(예방 항목, 아직 발생 안 함을 명시).
NtupleForge 쪽 **preflight job-count 체크 부재는 OPEN gap 으로 명시**했다.

**핵심 표현 하나**: "`units_per_job` 을 조정하지 말라"가 아니라
**"내릴 때만 위험하다"** 로 적었다. 올리는 방향은 job 수를 줄이고 물리에 무관하며 walltime
여유가 130배라 항상 안전하다 — 무조건 금지로 적으면 v13.11 의 효율 개선(1→10) 자체가 금지되는
모순이 된다.

---

## 2026-07-27 — v13.14: 2018 extend 캠페인 **완료** (11,946 jobs, failed 0) + LANG=C 출력 크래시 수정

### (1) 실측 정정 — 완료된 캠페인은 "전부 upj=10 / 2,097 jobs" 가 아니다

`--report` 실측: **7 tasks 전부 COMPLETED / 11,946 jobs / failed 0.**
설정이 **혼합**이었다:

| sample | MiniAOD files | jobs | upj |
|---|---|---|---|
| TTbar_SemiLep | 10,010 | **1,003** | **10** (per-entry override) |
| TTbar_Hadronic | 7,195 | 7,195 | 1 |
| TTbar_DiLep | 3,069 | 3,069 | 1 |
| TTbb_SemiLep / TT4b / TTbb_Hadronic / TTbb_DiLep | 219/188/169/103 | 동일 | 1 |
| **합계** | 20,953 | **11,946** | |

재제출이 v13.12 의 `site_config.yaml` 기본값 1→10 커밋 **이전**에 이뤄져,
`datasets.yaml` 의 per-entry override 만 적용된 v13.11 상태로 돌았다.
`TTbar_SemiLep` 이 **1,003**(= 1,001 + 2)인 것은 CRAB 의 FileBased 분할이 block 경계를
넘지 않기 때문 — upj=10 이 실제로 적용된 증거다.

**재생산하지 않는다**: packing 은 물리에 무관하고(D15) 산출물은 동일하며 failed 0 이다.
`units_per_job: 10` 기본값은 **다음 제출부터** 적용된다.

**AI 측 오진 기록 (재발 방지)**: filelist 로그의 `TTTo2L2Nu 3069 files` 를 보고
"upj=1 로 돌았다 → SemiLep 이 또 SUBMITREFUSED 일 것" 이라고 판단해 사용자에게 filelist
삭제와 작업 중단을 지시했다. **틀렸다.** 원인은 **제출 이후에 커밋된 config 를 이미 제출된
캠페인에 대입**한 것이다. 게다가 하필 `TTbar_SemiLep` 이 유일하게 override 로 보호된
샘플이었다. 교훈: **돌고 있는/끝난 캠페인의 설정은 현재 워킹트리가 아니라 `--report` 의
job 수로 판정한다** — job 수는 제출 시점 설정의 직접 증거다.
'2,097' 을 완료 상태로 서술한 6곳(README 3, 01_status, 03_changelog, RUNBOOK, datasets.yaml,
T-19)을 실측값으로 정정했다.

### (2) `LANG=C` 함정의 세 번째 변종 — print() 출력 (실제 크래시)

`make_filelists_miniAOD.py` 가 `filelist_TTTo2L2Nu.txt` 를 쓴 직후
`UnicodeEncodeError: 'ascii' codec can't encode characters` 로 죽었다. 원인은 출력 문자열의
box-drawing 문자 `\u2514\u2500`:

```
print(f"       \u2514\u2500 Split into folder: ...")   # <- LANG=C 에서 stdout=ASCII
```

- **v12.5/v13.2 는 파일 *읽기*(`open()` encoding)와 *소스* 인코딩 문제였고, 이건 *출력* 이다.**
  같은 뿌리(`LANG=C`)의 세 번째 변종이라 [09](09_environment.md) 표에 없던 축이다.
- **성공 경로에 있었다** → 매 샘플 터진다. 실제로 1/7 샘플만 만들어진 **반쪽 상태**로 중단됐다.
- 더 나쁜 것: **v13.5 의 중복 제출 FATAL 가드 메시지가 한글이었다** → 가드가 발동하는 순간
  진단문 대신 traceback 이 나왔을 것이다. 정작 필요할 때 못 읽는 가드였다.

**수정 (2중)**: 두 생성기(`make_filelists_miniAOD.py`, `make_filelists.py`)의 **출력 문자열
15개를 전부 ASCII 화**(한글 주석은 유지 — 소스는 UTF-8 로 디코딩되므로 무해) + **stdout 안전망**
추가(py3.6 호환 `TextIOWrapper(errors="replace")`; 향후 stray non-ASCII 가 있어도 `?` 로
degrade 되고 반쪽 상태로 죽지 않는다).
`LANG=C LC_ALL=C PYTHONIOENCODING=ascii` 로 실제 재현해 **정상 경로 / FATAL 가드(exit 3) /
`ALLOW_MULTI_CRAB_SUBMISSION=1` 우회** 3경로 모두 확인.

> **주의할 논점**: 소스를 ASCII-clean 하게 만드는 것만으로는 부족하다 — 리터럴 `\u2514`
> 이스케이프는 파일에서는 ASCII 지만 `print()` 시점에는 non-ASCII 다. [09](09_environment.md)
> 의 "ASCII-only 파일" 규칙이 이 경우를 못 막는다는 뜻이므로, 규칙을 **"출력 문자열은 ASCII"**
> 로 읽어야 한다.

---

## 2026-07-28 — v13.15: 검증을 HTCondor 로 (submitter + JSON 카운터 + 합산기)

사용자 지시: *"이런 작업 그냥 condor로 한 방에 되도록 만드는게 맞는 것 같은데. 왜 터미널
3개에서 명령을 3개나 하고 있었지?"* 맞는 지적이고, 실측이 그걸 뒷받침한다 — 남은 대형
3샘플이 **직렬 ~38시간**이다. 경위는 [08](08_troubleshooting.md) **T-22**.

**신설**

| 파일 | 역할 |
|---|---|
| `Validation/scripts/submit_validation_condor.py` | 정렬(`--sort-only`) → 스모크(`--smoke`) → 전량 제출. nano chunk 1개 = job 1개 |
| `Validation/scripts/aggregate_validation.py` | chunk JSON 합산 + DAS 대조 → 샘플별 PASS/FAIL 1장 |
| `matchTtbarIdSorted --json PATH` | 기계가 읽는 카운터(22 key). regex 긁기 대신 |

**실측 근거**: 소형 매칭 11.5분(4.79 M) / 29분(8.05 M) → 대형 145·334·476 M 은 ~6·13·19시간.
CPU 효율 25% 로, 병목은 계산이 아니라 **중앙 NanoAOD ~1.2 TB WAN 읽기**. 따라서 nano 를
쪼개는 것이 정확히 맞는 축이다. 정렬은 반대로 싸다 — 146 M rows **10분54초**, peak RSS 881 MB.

**설계 결정 4개**

1. **파이프라인 통일** — 전 샘플 `sortSplitExtend` → `matchTtbarIdSorted`. "이 샘플은 정렬이
   필요한가"를 손으로 판단하던 분기를 없앴고, job 메모리가 in-memory map 수 GB → **~16 MB**.
2. **job = nano chunk** — `make_nano_filelists_das.sh` 가 `SPLIT_SIZE=20` 으로 이미 만들어 둔
   split 을 소비(주석에 "per-condor-job splits" 라고 적혀 있던 그 용도). 대형 45 + 소형 4 job.
3. **산출물 EOS 강제** — `--out-base` 가 `/afs/` 면 **FATAL 로 거부**. AFS quota(94% 실측)와
   ~25시간 토큰이 6~19시간 job 과 양립하지 않는다는 것을 두 번의 `TFile::Flush` I/O error 로
   확인했다.
4. **합산기의 판정 기준에 완결성을 넣었다** — `all chunks present` 와
   **`sum(nano_entries) == DAS nevents`** 가 1급 기준이다. T-21 의 교훈("`unmatched` 는 데이터
   손실에 단조 감소하므로 단독으로는 완결성 증명이 될 수 없다")을 코드로 옮긴 부분이다.
   `--no-das-check` 가 있지만 help 에 DISCOURAGED 로 표시.

**검증 범위(정직하게)**: JSON 스키마·합산·판정 로직은 stub ROOT + 합성 fixture 로 확인했다.
특히 **`unmatched 0` 이고 모든 chunk 가 내부적으로 깨끗한데 chunk 1개가 없는 경우 → DAS 대조가
FAIL 을 잡아내는 것**을 재현했다(이게 T-21 사고의 정확한 형태다). disagree·불변식 위반·사후
truncation 전파도 확인. **condor 제출 경로는 이 환경에서 검증 불가** — 그래서 `--preflight`
(쓰기 없는 점검)와 `--smoke`(1샘플 1 chunk)를 먼저 통과시키는 순서를 문서·코드 양쪽에 박았다.

`Validation/README.md` **§4.0** 을 권장 경로로 신설하고, 기존 §4.1 인터랙티브 절차는
"스팟체크용"으로 강등했다. `.gitignore` 에 `valout*/`·`match_*.root`·`.done_*` 추가.

---

## 2026-07-28 — v13.16: condor 실행 환경 수정 (첫 `--preflight` 이 두 개를 잡았다)

v13.15 를 실기기에서 `--preflight` 돌렸더니 FAIL 2건. **둘 다 실제 문제였고 하나는 설계 결함**이다.

**① `condor_submit not on PATH` — 실행 환경이 갈린다는 것을 내가 놓쳤다.**
`condor_submit` 은 cmssw-el7 컨테이너에 없고 **EL9 호스트**에만 있다. 반면 `Validation/bin/*` 는
그 컨테이너에서 빌드된 **slc7_amd64_gcc700 / ROOT 6.14** 바이너리라 EL9 워커에서 못 돈다. 즉

> **제출 = EL9 호스트 · 실행 = EL7 컨테이너**

v13.15 는 `submit_hist_condor.py` 를 따라 `getenv = True` 를 썼는데, 그건 **EL9 호스트 환경을 EL7
payload 에 물려주는** 잘못이다. 수정:

- `getenv = False`, 대신 submit 파일이 `MY.SingularityImage` 로 EL7 이미지를 요청
  (`--container` 로 교체 가능, preflight 가 cvmfs 경로 존재를 확인)
- job 스크립트가 **스스로** `source /cvmfs/cms.cern.ch/cmsset_default.sh` →
  `scramv1 runtime -sh` 로 릴리스를 세팅 → 어떻게 제출됐는지와 무관하게 재현 가능
- **바이너리를 transfer** 한다 — 워커에는 이 홈의 AFS 토큰이 없어 `bin/` 을 AFS 로 읽으면 실패한다.
  ROOT 라이브러리는 cvmfs 에서 오므로 실행 파일만 옮기면 충분하다
- 생성 파일의 모든 경로를 **절대경로**로 (`transfer_output_remaps` 가 상대경로에 특히 취약)
- job 스크립트에 단계별 가드 + 고유 exit code. **실측 확인**: 바이너리 없음 **127** /
  sorted `index.txt` 없음 **125** / chunk 없음 **126**. 원인이 로그 첫 줄에 뜬다
- 남은 **가정 하나를 명시**: sorted part 를 EOS POSIX 로 직접 읽는다(lxplus batch 관례).
  `index.txt` 가 `ifstream` 이라 XRootD URL 로 대체할 수 없어서다. preflight 가 이걸 WARN 으로
  띄우고, 안 보이면 job 이 125 로 분명히 죽는다 — 49 job 이 조용히 실패하는 것보다 낫다

**② `x509 proxy not found` — preflight 자체의 버그.**
`$X509_USER_PROXY` 만 보고 있었는데 `voms-proxy-init` 은 그 변수를 export 하지 않고
`/tmp/x509up_u<uid>` 에 쓴다. 정상 발급된 세션을 FAIL 로 오진한 것. `--proxy` →
`$X509_USER_PROXY` → `/tmp/x509up_u<uid>` 순으로 찾도록 수정.

`Validation/README.md` §4.0 에 **단계별 실행 위치 표**(make/sort=컨테이너, preflight/제출=호스트,
job=자동 EL7)를 넣었다. 이게 없으면 다음 사람이 같은 곳에서 막힌다.

---

## 2026-07-28 — v13.17: 정렬 7/7 완료 + `/eos/user` 경로 보존 수정

**정렬 전량 완료** (`--sort-only`, 전부 exit 0, `_tmp_*` 자동 정리 확인):

| sample | extend rows | parts |
|---|---|---|
| tt4b / ttbb_Hadronic / ttbb_SemiLeptonic / ttbb_2L2Nu | (소형) | — |
| TTTo2L2Nu | 146,010,000 | 293 (기존, SKIP) |
| TTToHadronic | 343,248,000 | 687 |
| TTToSemiLeptonic | 478,982,000 | 958 |

extend row 수가 nano event 수보다 **많은 것은 정상**이다 — extend 는 nano 의 상위집합이고,
`matchTtbarId` 가 `unmatched (nano-only)` 로 재는 방향이 바로 그것이다(ttbb_2L2Nu 실측:
extend 4,858,850 ⊃ nano 4,792,850, unmatched 0). event 번호가 `lumi×1000` 인 것도
MC 규약(lumisection 당 1000 event)과 일치한다.

**버그 수정 — 내가 v13.16 에서 넣은 것.** 절대경로화를 `Path.resolve()` 로 했더니 심볼릭 링크를
따라가 `/eos/user/j/junghyun/...` 가 `/eos/home-j/junghyun/...` 로 재작성되어 생성 파일
(`match.sub`, `match.args`)에 박혔다. `/eos/user/...` 는 문서화된 안정 경로이자 condor 워커가
마운트하는 이름이고, `/eos/home-j/...` 는 내부 실현 경로라 워커에 없을 수 있다 — 그대로 제출하면
**49 job 전멸**이었다. `os.path.abspath()` 로 교체했다(심볼릭 링크 미추적, 절대화만).

교훈: **사용자가 준 경로 표기를 보존한다.** 정규화가 곧 개선은 아니다. 이건 `--sort-only` 로그를
읽다가 발견했다 — 스모크를 먼저 돌리는 순서가 여기서도 값을 했다.

---

## 2026-07-28 — v13.18: submit 파일에서 `/eos` 제거 (schedd 거부 해결)

`--preflight` 는 31 PASS / 0 FAIL 로 통과했는데 실제 `condor_submit` 이 거부했다:

> `Standard batch schedds cannot use /eos paths directly within the submit file.`

**내가 구분하지 못한 것**: job 이 **런타임에** EOS 를 POSIX 로 읽는 것과, **제출 시점에** condor 가
그 경로를 관리하도록 요구하는 것은 다른 문제다. 후자만 금지돼 있다. 상세는 [08](08_troubleshooting.md) **T-23**.

CERN 문서의 방법 1 을 적용했다:

| | 전 (거부) | 후 |
|---|---|---|
| `executable`, `args`, `output/error/log` | `--out-base` (EOS) | **`--work-base` (AFS)** — 기본 `Validation/condor_val<era>/` |
| 결과 전송 | `transfer_output_remaps` → `/eos/...` | **`output_destination = root://eosuser.cern.ch//eos/.../results/`** |
| sorted 경로 | condor argument | **job 스크립트에 baked-in** (스크립트 내용은 검사 대상 아님) |

부수 변경: `output_destination` 은 한 디렉토리로만 보내므로 json/·root/ 분리가 불가능 →
합산기가 `results/` 를 보도록 갱신(구 `json/` 레이아웃 fallback 유지). 로그는 AFS 로 가지만 KB
단위라 quota 무관하고, **각 job 이 JSON 을 stdout 에도 찍으므로 EOS 전송이 실패해도 숫자는
`.out` 에서 복구된다**.

**재발 방지 2중**: `--work-base` 가 `/eos` 면 FATAL, 그리고 **생성된 `.sub` 를 스스로 grep** 해서
맨 `/eos/` 가 남아 있으면 제출 전에 FATAL. 정규식은 실패했던 5줄 + 정상 6줄로 단위 검증
(`root://eosuser.cern.ch//eos/...` 통과, 맨 `/eos/` 차단). XRootD 의 **호스트 뒤 슬래시 2개**도
따로 검증했다 — `rstrip()` 으로 1개가 되는 실수를 그 검증에서 잡았다.

---

## 2026-07-28 — v13.19: proxy 를 schedd 가 읽을 수 있는 곳으로 (HOLD 해결)

제출은 통과했는데 job 이 hold 됐다:

> `Transfer input files failure at access point bigbird27 ... reading from file
> /tmp/x509up_u148947: (errno 2) No such file or directory`

**`/tmp` 은 노드 로컬**이다. 제출은 `lxplus9103`, 파일을 실어 보내는 것은 access point
(`bigbird27`) — 거기엔 그 파일이 없다. 상세는 [08](08_troubleshooting.md) **T-24**.

**내 preflight 의 결함**: "제출 노드에서 proxy 가 보이는가"만 봤다. 봐야 했던 것은 "**schedd 가**
읽을 수 있는가"다. 그래서 31 PASS 를 주고도 hold 를 막지 못했다 — v13.16 에서 proxy 탐지를 고칠 때
`/tmp` 라는 위치 자체가 문제라는 것까지 생각하지 못했다.

`stage_proxy()` 신설:

- 찾은 proxy 가 `/tmp/` 아래면 **`~/.x509up_condor` (AFS 홈)로 복사**, 권한 `0600`
- git 작업 트리(`condor_val*/`)가 아니라 홈에 두는 이유: proxy 는 자격증명이다
- **제출마다 복사** → 갱신된 proxy 가 자동 반영
- preflight 는 `/tmp` proxy 를 **PASS 가 아니라 WARN** 으로 보고하고 복사 예정 위치를 출력

단위 검증: `/tmp` → 홈 0600 사본(내용 동일) / 이미 공유 위치면 그대로 / preflight 는 복사하지 않음.

**부수 관찰**: `condor_q -better-analyze` 가 `RequestMemory = 3000 (mb)` 로 보고했다 — 우리가 준
2000 보다 크다(CERN 로컬 설정의 하한으로 보임). nano 쪽 사전 정렬(최악 ~586 MB)을 넣을 여유가
그만큼 더 있다는 뜻이다.

---

## 2026-07-28 — v13.20: proxy 는 자동 복사가 아니라 **강제**로 (v13.19 설계 기각)

v13.19 에서 `/tmp` proxy 를 `~/.x509up_condor` 로 자동 복사하게 만들었는데 사용자가 기각했다:

> *"굳이 그런식으로 자동화하면 home에 voms가 남는게 싫음. … 그냥 제출 전에 voms하는걸 반드시
> 하도록 만들면 됨."*

타당하다. **자격증명을 사용자 모르게 홈에 남기는 것은 좋은 기본값이 아니다.** 자동 복사를
전부 제거하고 `resolve_proxy()` 로 교체했다 — **아무것도 쓰지 않고 검사만** 한다:

| 상황 | 동작 |
|---|---|
| proxy 없음 | 제출 **거부** + 해결 명령 출력 |
| `/tmp` 아래 (기본 출력 위치) | 제출 **거부** — schedd 가 못 읽는다 |
| 남은 수명 < 1 h | 제출 **거부** |
| 남은 수명 < 24 h | preflight WARN (캠페인이 더 오래 살 수 있다) |
| 공유 위치 + 충분한 수명 | PASS, 남은 시간 출력 |

거부할 때마다 이 한 줄을 그대로 출력한다:

```
voms-proxy-init -voms cms -rfc --valid 192:00 --out $PWD/proxy.cert && export X509_USER_PROXY=$PWD/proxy.cert
```

`Validation/README.md` §4.0 에 **제출 전 필수 단계**로 넣고, `.gitignore` 에
`proxy.cert`·`*.proxy`·`x509up_u*` 를 추가했다 — 작업 디렉토리에 만들게 안내하므로 커밋
사고를 막아야 한다.

수명 검사를 넣은 이유: 캠페인이 proxy 보다 오래 살면 XRootD 읽기 실패가 **T-21 의 transient
AAA 와 구분되지 않는다**. 그 혼동을 한 번 겪었으니 미리 잡는다.

단위 검증 6가지: proxy 없음 / `/tmp` 에만 있음 / `--proxy` 로 `/tmp` 명시 / 존재하지 않는 경로 /
공유 위치 정상 / 안내 명령 동반.

---

## 2026-07-28 — v13.21: `set -u` 가 job 을 죽이고 있었다 + 실패를 숨기지 않게

스모크 job 이 워커에서 즉시 죽었다. `.err` 한 줄이 전부였다:

> `cmsset_local.sh: line 8: CVS_RSH: unbound variable`

**내가 job 스크립트에 건 `set -u` 가 CMSSW 환경 세팅을 죽였다.** `cmsset_default.sh` 는 유명하게
`-u` non-clean 인데, `-u` 에서 미설정 변수 참조는 즉시 shell 종료다. 첫 setup 줄에서 끝난 것이다.
상세는 [08](08_troubleshooting.md) **T-25**.

그리고 **두 번째 결함이 그 원인을 가렸다**: `transfer_output_files` 는 파일이 반드시 있어야 하는
계약이라, payload 가 죽으면 condor 가 HOLD 하고 hold 이유로 *transfer 에러*를 보고한다. 진짜
원인은 `.err` 한 줄에 있었는데 그게 안 보였다.

**수정 4가지**

1. **`set -u` 전역 제거** (`set -o pipefail` 만 유지). 서드파티 셸을 source 하는 스크립트에
   `-u` 를 걸면 안 된다.
2. **환경 세팅 성공을 검증** — `command -v root-config` 실패 시 **exit 123** + 이유 출력.
   matcher 는 ROOT 를 링크하니 그 없이 진행할 의미가 없다.
3. **출력 보장을 `trap ... EXIT` 로** — 꼬리의 검사는 조기 abort 시 실행되지 않는다(이번이 정확히
   그 경우). trap 은 어디서 죽어도 돈다. 실패 시 `job_failed:true` + 실제 exit code 스텁을 써서
   전송을 성공시키고, 합산기가 그 chunk 를 **FAILED**(누락이 아니라)로 표시한다.
4. `sorted parts in index` 를 로그에 추가 — 다음 스모크에서 EOS 가시성을 한눈에 본다.

**확인된 성공 하나**: `.out` 의 `os=CentOS Linux release 7.9.2009` — **`MY.SingularityImage` 가
EL9 워커에서 EL7 컨테이너를 정상 제공**했다. T-22 ⑥의 환경 분리 설계가 맞았다는 실증이다.

**아직 미확인**: 워커의 EOS POSIX 가시성. job 이 setup 에서 죽어 그 검사(exit 125)에 도달하지
못했다. 다음 스모크가 그것을 본다.

---

## 2026-07-28 — v13.22: 도는 선례로 수렴 (`TopCPVGenCategorizer/condor`)

사용자 지적: *"왜 이렇게 condor에서 에러가 나게 하냐? tempTTHH condor job 같은거 확인해봐.
너 너무 복잡하게 코드 짜는거 아님?"*

**맞는 지적이었다.** 같은 워크스페이스에 CERN 에서 실제로 돌던 참조가 있었다 —
`TopCPVGenCategorizer/condor/{submit_all.sh,runJob.sh}`. 그걸 먼저 읽지 않고 설계해서
참조가 이미 피해 둔 함정을 하나씩 다시 밟았다. 대조는 [08](08_troubleshooting.md) **T-26**.

| | 돌던 참조 | v13.21 (내가 한 것) |
|---|---|---|
| 출력 | `transfer_output_files = ""` + job 이 직접 `xrdcp` | condor 에 위임 → **hold, 원인 은폐** |
| `set -u` | 안 씀 | 씀 → cmsset 에서 즉사 |
| 바이너리 | AFS 에서 직접 읽음 | 전송(가정 과함) |
| proxy | 제출 디렉토리로 복사 + `use_x509userproxy` | (강제 방식으로 별도 해결) |

**핵심 변경 하나**: **condor 가 출력을 관리하지 않는다.** `transfer_output_files = ""` 로 두고
job 이 `xrdfs mkdir -p` → `xrdcp -f` 로 결과를 EOS 에 올린다. 이 하나로 `output_destination`,
`transfer_output_remaps`, 그리고 **hold-on-missing-output 실패 유형 전체**가 사라진다.
`use_x509userproxy = true`, `notification = never` 도 참조에서 가져왔다.

**유지한 것**: `MY.SingularityImage`(참조는 `MY.WantOS="el8"` 이지만 우리 payload 는 slc7 이고
SingularityImage 로 EL7 이 실측 확인됐다 — 도는 것을 바꾸지 않는다), 실패 스텁 JSON + `trap`
(합산기가 실패 chunk 를 누락과 구분하려면 여전히 필요), `.sub` 의 `/eos` 자기검사.

**교훈**: 같은 워크스페이스에 도는 선례가 있으면 **그것을 먼저 읽는다.** 새 인프라 코드를 쓰기 전
`find . -iname '*condor*'` 부터 할 일이었다.

---

## 2026-07-28 — v13.23: 스모크 성공 + XRootD 슬래시 버그(2회째) 수정

**스모크가 물리적으로 완전 성공했다.** `matchTtbarIdSorted` 를 이 캠페인에서 처음 실데이터로
돌렸고, 인터랙티브 `matchTtbarId` 와 **모든 카운터가 일치**했다. 수치와 성능 실측은
[06](06_validation_results.md) 에 기록.

확인된 것 (전부 그동안의 미지수였다):

- EL7 컨테이너 (`os=CentOS Linux release 7.9.2009`)
- cvmfs CMSSW 세팅 (`root-config` 발견, `SCRAM_ARCH=slc7_amd64_gcc700`)
- **워커가 EOS 를 POSIX 로 읽음** (`sorted parts in index: 10`) → `--part-url-prefix` 우회 불필요
- nano 전량 접근 + **DAS 값 일치** (4,792,850)
- **`part_loads = 347`** (이상값 10 의 34.7배) — nano 가 키 순서가 아니라는 사용자 예측이 맞았다.
  다만 event 당 부하는 part 총개수와 무관하게 일정하므로 대형에서도 외삽 가능
- wall **20.8분**, 메모리 **489 MB** → 대형 chunk 당 ~1.3–1.7 h, 49 job 동시 **~1.7 h**

**버그 수정 — 같은 실수 2회째.** EOS `results/` 가 비어 있었다: `xrdcp ... rc=54`.
XRootD 는 host 와 절대경로 사이에 **슬래시 2개**를 요구하는데 1개였다. v13.18 에서 이미 잡고
단위검증까지 했는데, v13.22 에서 `output_destination` 을 제거하며 `rstrip("/")` 로 재조립해
되살아났다. 상세는 [08](08_troubleshooting.md) **T-27**.

- **코드에 단정문**을 넣었다 — `dest_url` 의 `://` 뒤에 `//` 가 없으면 제출 전 FATAL.
  검증했던 불변식을 사람 기억이 아니라 코드로 고정한다
- **xrdcp 재시도 3회 + backoff** — 정상 계산된 chunk 의 JSON 을 EOS 하나 때문에 잃으면 안 된다
- **영구 실패 시 exit 122** — 물리 결과가 정상이어도 그렇게 한다. 전송 실패는 조용히 넘어가면 안 된다

**설계가 값을 한 확인**: v13.22 의 "condor 에게 출력을 맡기지 않는다" 덕분에 이 job 은 **hold 되지
않고** exit 0 으로 끝났고 **숫자가 `.out` 에 남았다**. 이전 설계라면 hold + transfer 에러로 원인이
또 은폐됐을 것이다.

---

## 2026-07-28 — v13.24: 문서 정리 — 사건 로그를 규칙으로, README 를 실동작 절차로

사용자 지시: *"실패한 경우를 모두 다 기록하는건 의미 없는 것 같고 docs에 '핵심 에러를 발생시킬수
있는 오류'를 기록해 두자. … 현재 동작하는 코드까지 왔으니 이 동작하는 코드 구조 및 지금까지
사용했던 것 중 확실하게 동작하고 validation을 확인할 수 있는 명령어들을 readme에 업데이트."*

**① [08] 사건 5건 → 규칙 1건.** condor 관련 T-23~T-27(개별 사건 기록, 합계 ~6.9 k자)을
**T-23 "CERN HTCondor 6대 함정"** 하나로 압축했다. 개별 사건의 서사보다 **재발 조건**이 다음 사람에게
쓸모 있다. 원 사건 기록은 이 changelog v13.16–v13.23 에 남아 있으므로 정보 손실은 없다.

6대 함정: ① submit 파일에 `/eos` 금지 ② proxy 를 `/tmp` 에 두지 않음 ③ job 스크립트에 `set -u`
금지 ④ `transfer_output_files = ""` + job 이 직접 `xrdcp` ⑤ **[은폐형]** 출력 전송 계약이 payload
실패를 transfer 에러로 위장 → `trap ... EXIT` + 스텁 JSON ⑥ XRootD host 뒤 슬래시 2개.

⑤를 "은폐형"으로 따로 표시한 이유: 그것 때문에 ③의 진짜 원인(`.err` 한 줄)이 두 번 안 보였다.
**실패를 숨기는 결함은 실패 자체보다 비싸다.**

**② [Validation/README] §4.0 을 실동작 절차로 재작성** (81 → 152 라인). 추가한 것:

- **구조 도식** — 무엇이 EL9 호스트에서, 무엇이 EL7 워커에서 도는지
- **위치 표** — make/sort=컨테이너, preflight/제출=호스트, 스캐폴딩=AFS, 결과=EOS
- **0단계 proxy** 를 필수 단계로 명시 (`--out $PWD/proxy.cert`)
- **점증 제출** — 스모크 1 → 소형 4 → 전량 49
- **exit code 진단표** (0/4/6/8/122/123/124–127)
- **판정 기준 박스** — DAS 대조가 1급 기준인 이유(`unmatched 0` 단독으로는 완결성 증명 불가)
- **성능 실측표** — 20.8분 / 489 MB / part_loads 347 / 231 k event/분

상단 워크플로 도식과 도구 표에도 condor 경로를 넣어, "전량이면 §4.0" 이 첫 화면에서 보이게 했다.

**③ [05_architecture] §3.1 신설** — 분할 축이 **nano 쪽**이고 extend 는 정렬본 전체를 본다는 것
(경계 효과 없음), `Row` 32 B × 500 k = 16 MB 상주, 그리고 EL9/EL7 두 층 구조.

**④ [06_validation_results]** — 스모크 실측(교차검증 표 + 성능 + 대형 외삽)은 v13.23 에서 기록됨.

---

## 2026-07-28 — v13.25: 스모크 합산기 PASS + 꺼진 안전장치 수정

스모크 재실행에서 EOS 전송까지 성공하고 합산기가 **PASS**. 하위 sub-code 까지 인터랙티브와 전부
일치 — 수치는 [06](06_validation_results.md).

**그런데 `nano total == DAS nevents` 가 `[SKIP]` 인 채로 PASS 가 났다.** 완결성의 유일한 진짜
증명(T-21)이 꺼져 있었는데 판정은 통과였다. 원인은 기본 xsec-db 경로 추정이
`TTHHGenCategoryTools` 와 `tempTTHH` 가 **같은 CMSSW 릴리스**에 있다고 가정한 것 — lxplus 는
10_6_32_patch1 / 14_2_1 로 나뉜다.

수정 ([08](08_troubleshooting.md) **T-23 ⑦**):

- **db 를 못 찾으면 FAIL.** SKIP 은 `--no-das-check` 를 **명시할 때만**
- 형제 CMSSW 릴리스까지 후보 탐색, 실패 시 시도한 경로 전부 출력
- **명시한 `--xsec-db` 는 fallback 금지** — 없으면 그냥 FAIL. 사용자가 지정한 파일을 말없이 다른
  것으로 바꾸는 것은 명확한 에러보다 나쁘다 (이건 테스트가 잡아줬다)

일반 규칙으로 T-23 에 박았다: **안전장치는 입력이 없으면 통과가 아니라 실패해야 한다.**
⑤(payload 실패가 transfer 에러로 위장)와 같은 부류라 "은폐형" 으로 함께 묶었다.

단위검증 4가지: db 없음 → FAIL / 정상 → PASS / 값 불일치 → FAIL / `--no-das-check` → SKIP.

---

## 2026-07-28 — v13.26: DAS 기준값을 이 repo 로 (cross-repo 런타임 의존 제거)

v13.25 에서 "db 를 못 찾으면 FAIL" 로 고쳤는데, 실제로 lxplus 에서 돌리니 **경로를 고치는 문제가
아니었다** — tempTTHH 가 lxplus 에 **아예 체크아웃돼 있지 않다**. 사용자 지적: *"이건 lxplus에
똑같은게 없다. 직접 validation 같은 곳에 파일 옮겨줘야해."*

**맞는 지적이고, 원래 설계가 틀렸다.** 완결성 검증의 기준값을 **다른 repo 에서 런타임에** 끌어오고
있었다. 검증 도구는 자기 기준 데이터를 들고 있어야 한다.

**신설**: `Validation/data/das_nevents_{2017,2018}.json` — 7샘플의 DAS nevents, **Validation 짧은
이름으로 키잉**(filelist 이름과 동일), `_meta` 에 출처·생성일·**갱신 규칙**을 명시:

> *"불일치가 나면 이 파일을 고쳐서 '해결'하지 말 것. 검증 실행이 불완전하다는 뜻이다."*

탐색 순서: `--xsec-db`(명시 시 그것만, fallback 없음) → `$TTHH_XSEC_DB` → **in-repo** →
tempTTHH(편의 fallback). 두 키 형식(짧은 이름 / 프로젝트 키 + `nevents` 중첩)을 모두 지원해
어느 쪽 파일이든 쓸 수 있다.

이제 `python3 scripts/aggregate_validation.py --era 2018` 만으로 DAS 대조가 동작한다 — 추가 인자
불필요. 실제 스모크 JSON 으로 확인: `nano total == DAS nevents 4,792,850 vs 4,792,850` **PASS**.

[08](08_troubleshooting.md) **T-23 ⑦** 갱신.

---

## 2026-07-28 — v13.27: 복제한 기준 데이터의 동기화 의무를 명문화 (D16)

사용자 지시: *"configure를 직접 가지고 왔으므로 tthh analyzer나 ntuple forge의 configure가
바뀌었을 때 본 프로젝트 코드에도 반영해야 한다는 사실을 docs 및 readme의
aggregate_validation.py 명령어 부분 근처에 주석으로 남겨둬라."*

v13.26 에서 DAS nevents 를 이 repo 로 복제했다. 복제는 **동기화 의무**를 만들고, 그 의무는
기억이 아니라 문서에 있어야 한다. 세 곳에 같은 내용을 뒀다 — 사람이 실제로 보는 위치가 다르므로
중복이 맞다:

1. **`Validation/README.md` §4.0** — 합산 명령 **바로 위**에 경고 박스 + **상류→이 repo 대응 표**
2. **`scripts/aggregate_validation.py` 헤더** — 같은 목록 (코드를 여는 사람용)
3. **`docs/04_decisions.md` D16** (신설) — 결정·근거·기각한 대안 3개·규칙

동기화 대상 4개와 안 했을 때의 증상:

| 상류 | 이 repo | 안 바꾸면 |
|---|---|---|
| `samples_<era>UL.json` 의 `nevents` | `data/das_nevents_<era>.json` | 완결성 기준이 틀린 값과 비교 |
| 프로젝트 샘플 키 이름 | `SHORT_TO_XSECKEY` | tempTTHH fallback 조회 실패 |
| analyzer patch 규약 (`ttnb_*`/`TtNb`) | `extractTtbarIdPatch --out/--out-tree` | analyzer 가 **조용히 INACTIVE** |
| NtupleForge dataset | `make_nano_filelists_das.sh` | filelist 가 옛 dataset 을 가리킴 |

세 곳 모두에 같은 규칙을 반복했다: **불일치가 나면 json 을 고쳐서 '해결'하지 말 것.** DAS dataset
자체가 바뀐 게 아니라면 불일치는 검증 실행이 불완전하다는 신호다.

D16 이 기각한 대안: tempTTHH 를 lxplus 에 체크아웃(환경마다 재발) / 못 찾으면 SKIP 유지(판정이
조용히 약해짐) / git submodule(릴리스 주기가 다르고 필요한 건 정수 7개).

---

## 2026-07-28 — v13.28: `--report` + `--resubmit-failed` (chunk 단위) + WARN 정리

**① `--report`** — chunk 별 배관 상태(ok / fail / miss)를 샘플별로 집계해 표로 낸다. 실패한
chunk 이름과 exit code 를 그대로 보여주고, 재제출 명령을 출력한다. **물리 판정은 하지 않는다** —
그건 `aggregate_validation.py` 의 일이고 의도적으로 중복하지 않았다(한 사실을 한 곳에서).

**② `--resubmit-failed`** — `--report` 가 실패/누락이라고 본 chunk **만** 다시 제출한다.

**③ 사용자 질문에 대한 답 (문서화)**: *"chunk단위로 다시 돌리는게 괜찮나? … 각 miniAOD 이벤트마다
일치하는 NanoAOD event를 찾아야 하는데 메모리 문제 없나?"* — 방향이 반대여서 문제없다. extend 쪽은
**이미 디스크에 정렬**돼 있고, job 은 자기 nano chunk 를 스트리밍하며 `index.txt`(수십 KB) +
**정렬 part 1개**(16 MB)만 상주시킨다. 그래서 메모리는 **chunk 크기와 무관하게 일정**하고(실측 peak
489 MB), 재제출은 처음과 **같은 비용**이다. 각 chunk 가 정렬본 전체를 보므로 경계 효과도 없다 —
그것이 chunk 를 재제출 단위로 쓸 수 있는 이유다. README §4.0 의 3.5단계에 박아뒀다.

**④ preflight WARN 제거** — `worker must see EOS (POSIX)` 는 스모크가 `sorted parts in index: 10`
을 찍어 **실증**했으므로 PASS 로 바꿨다. 줄 자체는 남겼다(실제 환경 의존성이고, 깨지면 job 이
125 로 죽는다). 이제 preflight 는 **FAIL 0 / WARN 0** 이 정상 상태다.

단위검증: A=[ok, exit 4, missing] · B=[ok, 스텁 exit 123] fixture 로 report 표·합계·재제출 args
3줄(정확히 실패한 것만)을 확인. 전부 성공 시 "Nothing to resubmit" 도 확인.

---

## 2026-07-28 — v13.29: patch 명명 규약 결정 + 양쪽 repo 에 다음 작업 등록

사용자 질문: *"`--out-tree TtNb` … 이거 나중에 tempTTHH를 업데이트 하면 되는거 아니냐?"* → 맞다.
다만 **지금은 구규약을 유지**하기로 결정하고, 다음 작업으로 양쪽에 기록했다.

**결정**: 2018 patch 도 `ttnb_<KEY>.root` / tree `TtNb` 로 뽑는다. 이 플래그는 임시 우회가 아니라
**현행 정식 규약**이다.

**중요한 기술적 사실** (기본값을 그냥 뒤집으면 안 되는 이유): 2017 patch 7편
(`Validation/lookup/`)은 **파일 안의 tree 이름이 `TtNb`** 다 — 파일 바이너리에서 확인했다. 즉
파일명 rename 으로 해결되지 않고, loader 기본값을 `TtbarIdPatch` 로 뒤집으면 2017 을 못 읽어
**KNU Tier3 에서 재추출**해야 한다. 그래서 권장 방식은 기본값 교체가 아니라 **fallback 추가**
(`TtbarIdPatch` 시도 → 없으면 `TtNb`) 다. flag day 없이 마이그레이션되고 2017·2018 모두 동작한다.

**지금 하지 않는 이유 3개**: ① 2018 control plots 의 크리티컬 패스가 아니다(tempTTHH 는 별도
repo·별도 릴리스, C++ 수정+재빌드+테스트가 병목). ② era 별 규약 혼재가 플래그 하나보다 나쁜
함정이다. ③ **틀렸을 때 실패가 조용하다** — loader 가 INACTIVE(fatal 아님)로 떨어져 확장 id 가
적용 안 된 플롯이 나온다.

기록 위치:
- `docs/07_analyzer_integration.md` §4 — PROPOSED → **OPEN**, 결정·권장 방식·기각 이유
- `docs/01_status.md` **O2** — 위 요약 + 상대편 포인터
- `tempTTHH/docs/STATUS.md` OPEN **항목 2** (신설) + `tempTTHH/docs/CHANGELOG.md`
  — 상대 repo 에도 남겨야 그쪽을 만지는 사람이 본다. 검증 방법(`active()` true, `size()` ==
  patch row 수)까지 적었다

---

## 2026-07-28 — v13.30: patch 추출 6/7 완료 + extract↔validation 관계 확립

6샘플 추출 완료(전부 exit 0, 전부 도구 교차검사 통과). 수치는 [06](06_validation_results.md).
`TTToHadronic` 1개 진행 중.

**구조적 확인 — extract 와 validation 수치가 다른 이유가 확정됐다.** extract 는 **extend 전체**를,
validation 은 **matched(=nano)** 만 센다. extend ⊇ nano 이므로 extract ≥ validation 이고 차이는
extend-only event 의 tt+nb 다. 따라서:

> **extend rows == DAS nevents 인 샘플은 두 값이 정확히 같아야 한다.**

`ttbb_Hadronic` 이 실증했다 — extend 8,049,064 == DAS 8,049,064, extract 33,072 = validation
33,072. 그리고 `ttbb_2L2Nu` 의 차이 193 은 **두 가지 독립 분해**(61/62/71/72 와 53/54/55)에서
모두 193 으로 합했다. 이것이 이 관계가 우연이 아니라는 증거다.

이 관계는 **검사 도구**가 된다: `tt4b`(0), `ttbb_Hadronic`(0), `ttbb_SemiLeptonic`(0) 은 extra 가
0 이므로 condor 결과와 **정확한 등식**을 요구할 수 있다 — 06 에 예측값 표를 넣었다.

**물리적 타당성도 확인**: tt+nb 비율이 전용 tt4b **19.8%** ≫ ttbb 0.32–0.41% ≫ inclusive
0.008–0.009% 순이고, tt4b 가 tt+4b(71+72) 비중도 최고(15.7% vs ~11%)다. 2017 에서 `ttnb_tt4b.root`
가 전체 용량의 91%였던 것과 같은 구조다.

---

## 2026-07-28 — v13.31: patch 추출 7/7 완료 + `lookup2018/` 을 커밋 대상으로

`TTToHadronic` 완료 (36,835 rows, exit 0, 교차검사 OK). **7샘플 전부 완료**:

| | tt+nb rows |
|---|---|
| 7샘플 합계 | **2,130,335** = tt+bbb 1,803,280 + tt+4b 327,055 |
| (2017 참고) | 1,882,170 = 1,585,810 + 296,360 |

**`lookup2018/` 을 커밋한다 (2026-07-28 결정, 2017 선례와 동일).** analyzer 는 **KNU 에서** 돌고
patch 는 **lxplus 에서** 생산되며, 7개 합쳐 ~12 MB 다. 커밋이 곧 환경 간 전송 수단이다.

`.gitignore` 를 두 군데 고쳐야 했다 — 그냥 `lookup20*/` 규칙을 지우는 것으로는 부족했다:

1. `Validation/lookup20*/` 디렉토리 규칙 제거 (대신 `lookup20*/_tmp*/` 만 무시)
2. **전역 `ttnb_*.root` 규칙에 예외** — 이것이 실제로 막고 있었다. 2017 파일은 이 규칙이 추가되기
   *전에* 추적됐기 때문에 영향을 안 받았을 뿐이다(gitignore 는 이미 추적 중인 파일에 무효).
   `!Validation/lookup/ttnb_*.root` + `!Validation/lookup20*/ttnb_*.root` 로 예외를 명시했고,
   장래를 위해 `ttbarIdPatch_*.root` 에도 같은 예외를 넣었다.

검증: `git check-ignore` 로 ① `lookup2018/ttnb_*.root` **추적됨** ② `Validation/ttnb_STRAY.root`
(작업 디렉토리의 유실물) **무시됨** ③ `logs2018/` **무시됨** ④ 2017 파일 8개 계속 추적됨.
"유실 재생산물은 막고 큐레이션된 산출물만 커밋" 이라는 원래 의도가 유지된다.

`Validation/lookup2018/README.txt` 신설 — 2017 `lookup/README.txt` 관례를 따라 출처·구규약을 쓴
이유·**short→projectKey 매핑표**·재생산 명령·커밋하는 이유를 적었다.

---

## 2026-07-28 — v13.32: 전량 검증 6/7 PASS + **가장 위험한 버그를 잡았다** (`GetEntry` 미검사)

condor 49 job **배관 100% 성공**(49/49 ok). 물리 **6/7 PASS**. 수치는 [06](06_validation_results.md).

**`TTToSemiLeptonic` FAIL 은 진짜이고, 원인은 내 코드였다.** `GetEntry()` 는 실패 시 `<=0` 을
돌려주는데 **반환값을 검사하지 않았다**. 실패한 읽기는 브랜치 버퍼에 **직전 event 값을 남기고**,
루프는 조용히 중복 event 를 처리한다 — matched 도 늘고 agree 도 되고 **모든 카운터가 깨끗하다**.
실제로 `matched` 가 DAS 와 정확히 일치해 통과처럼 보였다, nano entry 의 **1.87%** 가 읽기에
실패했는데도.

두 독립 경로로 발각됐다: 루프 후 `GetEntries()` 가 8,910,000 작았고, extract 와의 차이가 다른
6샘플은 기대 대비 0.90–1.12배인데 이 샘플만 4.23배였다. **두 결손 비율 1.87% vs 1.74% 일치**로
확정.

**수정 3가지**: ① 모든 `GetEntry()` → `checkRead()`, `<=0` 이면 **exit 10** (4곳)
② JSON 에 `nano_entries`(루프 실행 수)와 `nano_entries_postloop`(루프 후 재조회) **분리 기록** →
실행 중 열화가 **FAIL** 로 표시 ③ 합산기가 **모든** problem 출력(`problems[0]` 만 찍어 추적이
지연됐다).

[08](08_troubleshooting.md) **T-23 ⑧** 등록(8대 함정). **교훈: 반환값을 버리는 I/O 는 확신에 찬
오답을 만든다.**


---

## 2026-07-29 — v13.33: 재시도를 **읽기 경로**로 옮겼다 (nano lazy open 제거)

`checkRead()` 투입 후 첫 재실행에서 `TTToSemiLeptonic` 20 chunk 중 **10개가 exit 10**. 배관은
정상(20/20 결과 도착)이고, 합산기는 `nano total 245,394,000 vs DAS 476,408,000` 으로 FAIL.

**진단은 로그 한 줄로 끝났다 — 실패 지점이 전부 파일 경계였다.** FATAL entry 10개가 모두
**2000 의 배수**(23406000, 22728000, 20528000, 12078000, 23352000, 24816000, 24230000, 23744000,
22810000, 20692000)고, 에러는 `TNetXNGFile::Open: [ERROR] Operation expired` 17건이었다. 파일
중간 손상이 아니라 **다음 파일을 여는 데 실패**한 것이다.

`TChain::Add()` 는 등록만 하고 실제 open 은 루프 도중 경계에서 lazy 하게 일어나는데, **그
open 에는 재시도가 없었다.** T-21 때 넣은 `assertAllFilesOpen()` 의 재시도는 물리 데이터를 한
줄도 읽지 않는 경로를 지키고 있었다 — 방어막이 잘못된 자리에 있었고, 파일마다 open 이 2회라
job 이 스스로 redirector 부하를 2배로 만들고 있었다.

**수정 (`tools/matchTtbarIdSorted.cc`)**:

| | 전 | 후 |
|---|---|---|
| nano 순회 | `TChain` (경계에서 lazy open, 재시도 없음) | 파일 단위 명시 루프, `openWithRetry()` 10회 · backoff 10/20/40/80/160 후 300 s 고정 · **총 예산 25분** |
| 파일당 open | 2회 (사전 점검 + lazy) | 2회지만 **둘 다 재시도**, lazy 경로 제거 |
| mid-file 읽기 실패 | 즉시 exit 10 | 재open + 재bind + 같은 local entry 재seek 3라운드 → 그래도 실패면 exit 10 |
| 완결성 검사 | `assertChainComplete()` (체인 길이) | `assertReadComplete()` (**실제로 읽은 entry 수**) — 더 강함 |

JSON 3키 의미 갱신: `nano_entries`=실제 읽은 수, `nano_entries_postloop`=읽기용으로 열었을 때 본
`GetEntries()` 합(사전 점검과 독립된 2차 측정), `nano_entries_opencheck`=사전 점검 합. 셋이
일치해야 한다는 합산기 계약은 그대로다.

**exit 10 은 버그가 아니라 정상 동작이었다** — 같은 사건이 직전 캠페인에서는 조용한 중복
event 로 1.87% 를 갉아먹었다(T-23 ⑧). 이번엔 소리내며 죽었을 뿐이다.

미적용: `matchTtbarId`(비정렬, 인터랙티브 스팟체크용)에는 extend·nano 양쪽 TChain 에 **같은 잠재
결함이 남아 있다**. condor 는 `matchTtbarIdSorted` 만 쓰므로 우선순위를 낮췄다 — [01](01_status.md) OPEN.

남은 의문: 다른 6샘플 29 chunk 는 exit 0 인데 이 샘플만 50% 다. nano 가 `-v1` 비대칭이라 replica
배치가 다를 가능성 → `dasgoclient -query="site dataset=..."` 로 비교할 것. 세부는
[08](08_troubleshooting.md) **T-24**.

### 재시도 예산은 관측으로 정했다 (같은 날 추가)

처음엔 5회·총 150초로 잡았다가 **cluster 13293958 의 타임스탬프를 보고 25분으로 올렸다.**

| | 종료 시각 (UTC) | 실행 시간 |
|---|---|---|
| 살아남은 10 chunk | 07:25–07:39 | 81–95분 |
| 죽은 10 chunk | 07:16 하나, **07:44–08:05** 아홉 | 72분, 100–121분 |

성공한 job 은 **전부 07:39 이전에 끝났고**, 실패는 **07:44 이후에만** 났다. 즉 나쁜 창이
**최소 21분** 열려 있었다는 뜻이고, 150초짜리 재시도로는 어차피 다 죽었을 것이다. job flavour 가
`workday`(8 h)이고 실제 작업이 1.5~2 h 이므로 open 당 25분 재시도는 감당 가능하다 — chunk 를
통째로 잃는 것보다 싸다. 사전 open-check 는 **fail-fast 가 목적**이므로 반대로 짧게(3회·120초)
분리했다.

### `.err`/`.out` 로 확정한 것 (추정 아님)

실패 job `.0` 전문:

```
Unable to load sec.protocol plugin libXrdSecztn.so        <- 무해 (T-21 에서 확인)
Error in <TNetXNGFile::Open>: [ERROR] Operation expired   <- 단 1건
FATAL: nano GetEntry(23406000) returned 0 ...  Exit 10
```

같은 job 의 `.out`:

```
>>> nano open-check 20/20 files OK, total entries = 24726000
[matchSorted]   nano scanned 20000000 / 24726000
```

**20개 파일이 시작 시점에 전부 열렸고 tree 도 있었다** — 20 job 전원이 `20/20`(마지막 chunk 는
`11/11`)이다. 따라서 "파일이 깨졌다 / 브랜치가 없다 / replica 가 없다"는 **전부 배제된다**.
DAS 대조도 같은 결론이다: SemiLep 은 dataset 37 사이트·파일 21 replica 로 오히려 TTToHadronic
(31 / 14)보다 넓게 퍼져 있다. 남은 설명은 **루프 도중의 lazy open 1건이 타임아웃했다** 뿐이고,
`Operation expired` 가 정확히 그 자리에 1건만 있다. 성공 job 의 `.err` 에는 이 줄이 아예 없다.

## 2026-08-31 ~ 09-02 — v14.0: enriched NanoAOD 경로 부활 (D17) — python 파일 하나, 새 C++ 0

**왜.** NtupleForge 의 v15 마이그레이션 전수 조사에서 registry 64 개 중 6 개(`TTHHto4b`·`TT4b`·`TTZHTo4b`·
`TTZZTo4b`·`tHW`·`TTZToBB`)에 **중앙 NanoAODv15 가 없다**는 것이 확정됐다. 이 6 개는 어차피 사설 생산이라
D1 의 기각 사유("중앙 복제 비용")가 성립하지 않는다 → D-DEP1 을 이 6 개에 한해 부분 번복(D17, PROPOSED).

**무엇을 추가했나 — 딱 하나.** `TtbarIdExtender/python/ttbarIdTable_cff.py` (71 줄, 커밋 `a438485`):
`ExtendedTtbarIdProducer` 의 세 int 프로덕트를 `GlobalVariablesTableProducer` 로 top-level branch
`expandedGenTtbarId` / `nAddBJets` / `nAddBJetsMulti` 로 내보내는 `customise(process)`. 릴리스가
`genTtbarId` 를 내보내는 `ttbarCategorization_cff.py` 와 같은 꼴이다. `try/except ImportError` 로 10_6_X
(`cms.EDProducer(...)`)와 15_0_X(생성 cfi `.clone()`)를 한 파일이 커버하고, 어느 분기를 탔는지 로그에 찍는다.
C++ 은 무수정 — `edm::global::EDProducer<>` 라 15_0_18 에서 그대로 컴파일됐다.

**D17 원문의 비용 추정이 틀렸다.** "FlatTable producer 를 새로 작성" 이라 적었는데, 전제(table 컬럼을 붙이는
물건이 없다 — `grep nanoaod::FlatTable` 0 건)는 맞았지만 해법이 릴리스 안에 있었다. producer 가 consume 하는
4 개(`categorizeGenTtbar:genTtbarId`, `matchGenBHadron:genBHadJetIndex`/`genBHadFromTopWeakDecay`,
`slimmedGenJets`)가 **전부 중앙 시퀀스 산출물**이라 상위 모듈을 하나도 건드리지 않는다 — 이것이 "중앙과
동일" 주장의 근거다.

**검증 (기준 샘플 `TTbb_4f_TTToHadronic` UL17, 중앙본이 있는 샘플에서 먼저).**

| gate | 결과 |
|:---:|---|
| 1 | v9 2000 event: 3 컬럼 top-level. branch **1669 = 중앙 1666 + 3** |
| 2 | 중앙 v9(`2C5102B9`, 우리 event 2000/2000 포함)와 event-matched: **3,332,000 값 `--ftol 0` 실질 불일치 0**, 정수 불일치 0, 중앙에만 있는 branch 0, 공통 1666 타입 동일. 중앙은 CMSSW_10_6_26, 우리는 10_6_32_patch1 → 차이 0 (D2 문구 정정) |
| 3 | 61/62 확인: `nAddBJets==3` 6 event 가 53→61 ×4, 54→62 ×2 (Multi 기준, 총수 보존). **71/72 는 미확인** — `nAddBJets>=4` 0 건, `TT4b` 필요 |
| 5 | 15_0_18 무수정 빌드. 200 ev smoke: **1906 = 중앙 v15 1903 + 3**, 타입 불일치 0, `PFMET_pt`/`Rho_*` 존재(진짜 v15 스키마), 앞 10 ev 의 gen 값이 v9 와 동일. **값 비교 대기** |
| 4 | 미착수. 처리율 v9 6.4 Hz(WAN) / v15 2.4 Hz(200 ev, 로컬) — v15 는 ParticleNetAK4 재계산으로 훨씬 비쌈 |

**중앙 레시피는 DAS 에서 원문으로 받았다.** `dasgoclient -query="config dataset=..."` 의 해시로
ReqMgr config cache 에서 PSet 을 내려받으면 5 행에 cmsDriver 원문이 있다. v9(`086c69c1...`)와 v15(`f8c6f9a4...`)의
`--era Run2_2017,run2_nanoAOD_106Xv2` 와 부모 MiniAODv2 가 **완전히 같고**, 차이는 릴리스·GT 둘뿐.

**비교기 수정 (NtupleForge `compare_v9_v15.py`, 커밋 `c0eab1e`).** 첫 실행이 100 % 불일치를 보고했는데 전부
`nan` vs `nan`(`HTXS_Higgs_y`, `PuppiMET_*JER*`)이었다. 양쪽 NaN 은 agreement 로 처리하되 **건수를 세어 출력**;
인덱싱은 key 3 branch 만 읽어 20m46s → 수 분.

**사고.** v15 첫 실행이 proxy 만료 + WAN 직독으로 `exit=84` / 18m53s 소모(T-28). 파일을 stale 영역
(`~/MiniAODExtension/.../ExtendedTtbarId/NanoExtension`, v10 이름)에 먼저 만들었다가 정본으로 옮김(T-32).

**문서.** [11_enriched_nanoaod.md](11_enriched_nanoaod.md) 신설(이론·레시피·gate·검증 방법론·환경). 04 의 D17
진행 절 4 개를 gate 표 하나로 압축하고 상세를 11 로 이관. D2 문구 정정. 09 §4(15_0_18 실측표) 신설.
08 T-25~T-32. 10 에 SUPERSEDED 배너. 01 O7 · README 색인 11.

**열린 결정.** NanoAOD 컬럼 이름 `expandedGenTtbarId`(현재, camelCase) vs sidecar 계약 `Expanded_genTtbarId`.
혼합 생산이라 analyzer 가 둘 다 다뤄야 한다 — 결정 후 D17 에 기록.

## 2026-09-07 — v14.1: D17 gate 3·4·5 닫힘 + HTCondor 검증 배치 (`TtbarIdExtender/condor/`)

**무엇이 닫혔나** ([11](11_enriched_nanoaod.md) §3, [04](04_decisions.md) D17 표).

| gate | 결과 |
|:---:|---|
| 3 | TT4b 2017 MiniAOD 2000 ev 를 v9(10_6_32_patch1)·v15(15_0_18)로 처리 — 규칙 위반 0, 71/72 51 건, **두 릴리스의 전이표 동일** (61←53, 62←54·55, 71←53, 72←54). 표는 [02](02_physics.md) §3 에도. |
| 4 | 처리율 batch 실측: v15 **1.26 ev/s**, v9 **6.12 ev/s** (4.9×). 부재 6 샘플 × 2 era 의 MiniAOD = 3,525 파일 / 125.4M ev → `FileBased` 1 파일/job, 3,525 job / 16 task, task 당 ≤ 486. 메모리(job report, `cmsRun -j`): 1 스레드 `PeakValueRss` **2,977 MB**, plain 과 ours 차 0.6 MB — 1 코어 CRAB 기본(2,000 MB) 초과 → 1 차 안 `numCores=1`/`maxMemoryMB≈3500`(cfg 는 중앙 원문 그대로, 스레드 옵션 없음), 서버 거부 시에만 2 코어·2 스레드 ([11](11_enriched_nanoaod.md) §6). |
| 5 | v15 2000 ev 대 중앙 `--ftol 0`: **정수 불일치 0**; float 차이는 `*_area`(ghost 난수, event 이력), `HTXS_*`(0 vs 3e-5 잔차), DeepTau raw(NN 추론의 하드웨어 의존 마지막 비트, 저장 정밀도 한 칸) 세 부류만. customise 를 뺀 중앙 cfg 를 같은 event 에 돌린 **음성 대조군이 같은 부류·같은 값을 재현**하고, 같은 노드에서 연달아 돌린 plain vs ours 는 **`--zero` 비트 동일**(`control_v15_200` ALL PASS, TAG 1128) → customise 는 3 컬럼 외 아무것도 바꾸지 않는다. |

**"동일" 의 정의가 셋으로 갈렸다** ([11](11_enriched_nanoaod.md) §4.7, T-35): 같은 노드·같은 job = 비트 동일(예외 없음) /
다른 머신 = NN 출력의 마지막 ULP 만 / 다른 job 이력(중앙) = 세 부류. 정수 branch 와 우리 3 컬럼은 어디서도 달라선 안 된다.
처음 대조군은 batch 의 plain 과 lxplus 의 ours 를 비교해 DeepTau 한 값에서 깨졌다 — 하드웨어 변수를 대조군에 섞은 설계
실수. 대조군은 같은 job 에서 plain·ours 를 연달아 돌리도록 재설계.

**새 코드 — `TtbarIdExtender/condor/`** (`submit.sh`, `runTask.sh`, `config.sh`, `check_expanded.py`, `judge_compare.py`,
README). 4 task(`control_v15_200`, `timing_v15_2k`, `tt4b_v9_2k`, `tt4b_v15_2k`)를 HTCondor 로 돌려 EOS
`/eos/user/j/junghyun/ttHH/{enriched,json,logs}/<TAG>/` 에 출력·비교 JSON·전체 로그·cfg·job report·PASS/FAIL 요약을 남긴다.
판정은 기계가 한다 (`judge_compare.py` 허용 부류 3분법, `check_expanded.py` 규칙 검사, `%MSG-e` 는 `JetPtMismatch|MissingJetConstituent`
만 허용). v15 는 `MY.WantOS="el8"`, v9 는 el9 호스트에서 `cmssw-el7` 로 자기 재실행 — 둘 다 실측 동작.

**CERN batch 에서 배운 것** ([08](08_troubleshooting.md) T-33~T-35): stdout 스트리밍 금지(2025-11) → 첫 제출 거부;
`set -u` 아래에서 `cmsset_default.sh` → `CVS_RSH: unbound variable` 즉사; 하드웨어 의존 NN 추론.

**운영 규칙 변경.** 임시 파일은 lxplus `/tmp`(노드별) 가 아니라 EOS `ttHH/{miniaod,central,enriched,json,logs}` 에.

**부수 관찰.** MiniAOD 부모가 중앙 NanoAOD v9 보다 1–4 % 많은 event 를 가진 dataset 이 있다(`tHW` 2017, `TTZToBB` 2018,
`TTZZTo4b_ext1` 2018) — enriched 가 그만큼 더 온전하다. cmsRun `%MSG-e` 14 건은 전부 `JetPtMismatch`
(`JetFlavourClustering:genJetAK8FlavourAssociation`, 중앙 시퀀스, T-1 부류).

**문서.** 11 (§2.3 EOS 규칙, §2.4 배치, §3 gate 표, §3.3 값 비교 표 + 파일 LFN, §3.4 처리율·MiniAOD 표·job 산정, §3.5 gate 3,
§4.7, §5, §6), 02 §3 실측 전이표, 04 D17 표·상태, 08 T-33~T-35 + HTCondor 절 머리, 01 O7, README.
**열린 결정** 은 그대로 컬럼 이름 하나 — 결정 시 D17 을 DECIDED 로.

## 2026-09-11 — D17 대상 6 → 5 샘플 (`TTZToBB` 제외)

**결정(NtupleForge 쪽, 사용자).** Run 2 v15 분석은 ttZ(hadronic Z) 를 v15 에 이미 있는 inclusive
`TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8`(UL17 13.98M / UL18 19.82M, VALID) 에서 취한다 — Run 3 의 `TTZ-ZtoQQ-1Jets` 와
같은 처리이고 hadronic 채널에는 bb 전용보다 완전하다(cc/light 가 mistag 로 들어옴). 근거·대안은 NtupleForge
`docs/03_DECISIONS.md` D-2026-09-11-ttz-hadronic-from-ttzqq.

**이 저장소에의 영향.** enriched 생산 대상은 `TT4b`, `TTHHto4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW` 의 **5 샘플 / 14 dataset**:
3,192 파일 / 108,323,000 ev / ≈ 23,900 core-h / 14 task / ≈ 0.31 TB(§3.4 표에서 `TTZToBB` 2017·2018 두 행 제외).
코드·cfg 변경 없음. `json/miniaod_parents_absent6.txt` 는 그대로 두고 `TTZToBB` 행을 쓰지 않는다.

**문서.** 01(상태 줄·BLUF 정정·DECIDED 표), 04(D17 정정 문단, D-DEP1 주석), 11(§3.4 정정 블록, 작업 3·6).

## 2026-09-11 (밤) — D17 범위가 full Run 2 로 (5 샘플 × 4 era-half)

**결정(NtupleForge 쪽, 사용자).** 2016 preVFP/postVFP 를 점검한 결과 네 Run 2 v15 캠페인의 부재 목록이 **완전히 같았다**
(`das_inventory_ul16{pre,post}_{v15,v9}`; NtupleForge D-2026-09-11-run2-scope-2016). 중앙 요청을 5 종 × 4 era-half =
**28 dataset / 약 162M ev** 로 넓혔다.

**이 저장소에의 영향.** 중앙 요청이 거절될 때의 enriched 대체 생산 범위도 2016 을 포함한다. 2016 은 half 당 7 dataset ·
27.1M ev(v9 기준) → 전체 약 162M ev, **≈ 36,000 core-h, 28 task**(2017/2018 의 23,900 core-h 를 event 수로 환산).
2016 MiniAOD 부모의 파일 수는 미조회라 job 수·TB(≈ 0.47 TB 예상)는 확정값이 아니다. 2016 레시피는 2018 과 마찬가지로
중앙 cmsDriver 원문(era `Run2_2016[_HIPM]`, 2016 GT)을 받아 옮겨야 한다 — 코드 변경은 없다.

**문서.** 04(D17 범위 확대 문단), 01(상태 줄).

## 2026-09-17: enriched 는 병행 트랙 (사용자 결정), 2016 MiniAODv2 입력 확정

**결정(NtupleForge 쪽, 사용자).** 중앙 "NanoAODv15 from MiniAODv2" 요청의 답장을 기다리는 동안 같은 5 종의 enriched 생산을
**병행**한다. 이전 문서의 "거절 시 대체" 는 전부 이 뜻으로 고쳤다(04 D17 문단, 11 §3.4 인용문, 01 상태 줄).
NtupleForge `docs/03_DECISIONS.md` D-2026-09-17-run2-v15-two-tracks.

**입력 수치.** 2016 MiniAODv2 부모(NtupleForge `das_inventory_ul16{pre,post}_miniaodv2_20260916_*.tsv`): preVFP 873 파일 /
27,245,000 ev / 2.10 TB, postVFP 864 파일 / 27,098,000 ev / 2.12 TB. 전체 4,929 파일 / 162,666,000 ev; core-h·TB 추정(≈ 36,000, ≈ 0.47)은 그대로.

**착수 전 결정 2 개(미결).** 글루(NtupleForge `job_type: cmsrun` vs `TtbarIdExtender/crab/` pset 교체), 컬럼 이름
(`expandedGenTtbarId` vs `Expanded_genTtbarId`). 코드 변경 없음.

**같은 날 추가(09-17).** 컬럼 이름 결정: `genTtbarIdExpanded`(사용자). D17 → DECIDED. 적용(producer label, sidecar 컬럼 통일, loader)은 다음 작업.

## 2026-09-27: 2018 patch 를 NanoAODv15 에서 다시 맞추는 준비 (`2018v15`)

**왜.** ttHH 생산이 NanoAODv15 로 옮겨 갔고(NtupleForge D-2026-09-22-production-order), analyzer 는 v15 ntuple 에 2018 patch 를
실행 시 붙인다. O6 의 검증은 v9 nano 기준이었고 `TTToSemiLeptonic` 은 FAIL(읽기 실패, T-23 ⑧) 상태였다. v15 에서 한 번 맞추면
v15 에서의 유효성과 `TTToSemiLeptonic` 재실행이 같이 끝난다. 계획은 NtupleForge `docs/12_fastpath_workflow_plan.md` (V1).

**바뀐 것.**
- `Validation/filelists/make_nano_filelists_das.sh`: era `2018v15` (campaign `RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1`,
  출력 `nano2018v15/`). 캠페인에 중앙 dataset 이 없는 샘플은 `NO_CENTRAL` 목록으로 "예상된 SKIP" 로 기록하고 rc 를 1 로 만들지 않는다
  (`2018v15` 의 `tt4b`; 다른 샘플이 없으면 전과 같이 rc 1). 다른 era 의 동작은 그대로.
- `Validation/data/das_nevents_2018v15.json` (신규): 중앙 v15 의 DAS event 수 6 개(NtupleForge `script/das/das_ttHH_2018UL_v15_20260923_0853.log`,
  09-03 스캔과 같은 값). `aggregate_validation.py --xsec-db` 로 준다.
- `Validation/README.md` §0.1b, [01](01_status.md) O8.

**새로 확인한 사실.** 2018 v15 는 MiniAOD 를 전부 덮지 않는다: `TTToSemiLeptonic` 460,133,000 (extend 478,982,000, JMENano 판 v15 는
478,982,000), `ttbb_Hadronic` 7,946,064 (extend 8,049,064). 나머지 넷(TTToHadronic 343,248,000, TTTo2L2Nu 146,010,000, ttbb_SemiLeptonic
10,378,681, ttbb_2L2Nu 4,858,850)은 extend 와 같다. 2017 에서 확인한 "v15 = MiniAOD 100 %" 는 2018 에 그대로 옮길 수 없다.

**검증 (오프라인).** 스캔 로그의 파일 수(14 / 15 / 8 / 407 / 589 / 169)를 돌려주는 가짜 `dasgoclient` 와 가짜 `voms-proxy-info` 로
`2018v15` 실행: rc 0, `tt4b` SKIP 한 줄, split 1+1+1+21+30+9 = 63 개(= condor job 수). 잘못된 era 는 rc 2, `2018` 은 이전과 같은 경로.
실제 DAS 조회는 lxplus 에서(RUNBOOK §11 [c]).

## 2026-09-28: 2018 patch 의 중앙 NanoAODv15 재검증 통과 (O8 CLOSED)

- **결과**: `aggregate_validation.py --era 2018 --nano-filelist-dir filelists/nano2018v15 --xsec-db data/das_nevents_2018v15.json` 의 끝줄
  `OVERALL: ALL SAMPLES PASS`. 여섯 샘플 전량(972,574,595 event, 63 job)에서 nano total == v15 DAS, unmatched 0, disagree 0, 불변식 0.
  extend 와 v15 의 event 수가 같은 네 샘플은 patch 추출 표와 정확히 같고, v15 가 적은 두 샘플은 기대값대로다. 표: [06](06_validation_results.md) 끝 절.
- **따라서**: v15 ntuple 에 쓸 2018 patch 6 편 확정. 07-28 의 v9 FAIL 로 보류했던 `ttnb_TTbar_SemiLep.root` 도 v15 용으로 해제
  ([01](01_status.md) O8, O6 ⑦). v9 쪽 재실행은 하지 않는다(2018 v9 ntuple 보류).
- **실행 기록**: 09-27 제출(cluster 13488511)은 lxplus 의 `matchTtbarIdSorted` 를 다시 빌드하지 않은 채여서 `TTToHadronic` 19/21 chunk 가 exit 4
  (옛 binary 에는 읽기 재시도가 없다; 실패가 드러났을 뿐 틀린 값은 없다). 09-28 재빌드(`strings bin/matchTtbarIdSorted | grep -c reopening` = 1)
  뒤 `--resubmit-failed` 로 19 개만 다시(13489070) → 63/63 ok. 로그는 NtupleForge 쪽 runlog(`run_v1_aggregate_20260928_083134.log`).
- 코드 변경 없음(문서만: 01, 03, 06).

## 2026-10-13 — AI 작업 계약: 진행 로그와 비정상 종료가 드러나는 로그 (사용자 원칙)

- `00_PROMPT.md` §4 에 두 규칙(사용자 2026-10-13, 원문 인용): 몇 분 넘게 걸리는 일은 시작할 때 전체 크기, 단위가 끝날 때마다 `i/N`·몫·경과·ETA 한 줄,
  한 단위가 길면 시간 간격의 heartbeat, 줄 버퍼(Python 2.7 코드는 `sys.stdout.flush()` 또는 `python -u`); 정상 끝의 결과 줄과 exit code, 실패 경로의 원인,
  머리·꼬리가 있는 기록(꼬리 없음 = 강제 종료 또는 아직 실행 중). 근거와 계기: 워크스페이스 `AI_LIMITS_AND_PROTOCOL.md` §5 실패 8, §6 8·9.
- 코드 변경 없음(문서만: `00_PROMPT.md`, 이 파일).

## 2026-10-14 — 2016 preVFP(`2016APV`)·postVFP(`2016`) extend 생산 준비 (D19, O9)

**왜.** 사용자가 ttHH 를 full Run 2 로, 중앙 NanoAODv9 에서 돌리기로 했다(TTHHAnalyzer D-2026-10-14-B). 2017·2018 patch 는 있으므로 2016 두
기간만 새로 만든다. 결정과 기각한 대안은 [04](04_decisions.md) D19.

**동작 변경 고지.**
1. `crab/resolve_parents.sh`: era `2016APV`·`2016` 추가. 각 parent 를 `datasets.yaml` 의 `dataset:` 과 비교해 MATCH / MISMATCH / ABSENT 를 찍고
   `RESULT: ... MATCH n/7` 로 끝난다. **exit code 가 생겼다**: 0 전부 MATCH, 3 하나라도 아님(전에는 항상 0), 2 인자·era 오류, 1 dasgoclient 없음.
   `--apply`(신규): 전부 MATCH 일 때만 그 era 블록의 MATCH 항목에서 `enabled`/`verified` 두 줄을 true 로 바꾸고 diff 를 보여 준다; 다른 줄이
   바뀌거나 열리지 않은 항목이 있으면 쓰지 않고 exit 4. 2017·2018 의 출력은 줄 몇 개(MATCH, RESULT)가 늘었을 뿐 같다.
2. `crab/submit_ttbarIdExtend.py --preflight`: "campaign vs era" 를 era 별 캠페인 접두 표(`_ERA_CAMPAIGN_PREFIX`)로 본다(옛 규칙은 UL16 을
   못 가른다; 2017·2018 항목의 판정은 같음). 새 검사 "pset year values": 고른 era 가 cfg 의 `_ERA_NAME_BY_YEAR` 키에 없으면 FAIL
   (CRAB 의 제출 시 pset import 가 ValueError 로 죽기 전에). `enabled:false` WARN 의 안내 문구가 `--apply` 를 가리킨다.
3. `crab/datasets.yaml`: era 블록 `"2016APV"`·`"2016"` 7 샘플씩(NtupleForge DAS 인벤토리 `das_inventory_ul16{pre,post}_{miniaodv2,v9}_*.tsv`
   에서 그대로, 전부 `enabled:false`/`verified:false`). 머리말에 `--apply` 한 문단. 2017·2018 블록은 그대로.

**문서.** `TtbarIdExtender/README.md` §2.2d(명령 전부)·`--preflight` 설명, [05](05_architecture.md) §5(새 era 절차; `--max-files` 스모크 줄을 금지 규칙에
맞춤), [04](04_decisions.md) D19, [01](01_status.md) O9.

**검증 (오프라인, 컨테이너; lxplus 실행은 아직).** 가짜 `dasgoclient`·`voms-proxy-info`·CRAB client 로:
- `resolve_parents.sh` 시험 37/37 PASS — 스크립트의 NANO 목록 = yaml 의 nano_child(네 era), 읽기 전용은 파일을 안 바꿈, `--apply 2016APV` 는
  정확히 14 줄(enabled 7 + verified 7)만 바꾸고 `2016`·2017·2018 은 그대로, 두 번째 `--apply` 는 "nothing to change", MISMATCH·parent 없음·parent
  둘이면 exit 3 이고 쓰지 않음, 인자 오류 exit 2, dasgoclient 없음 exit 1, 임시 파일 남지 않음. gawk·mawk·nawk 결과 동일.
- preflight `--era 2016APV,2016 --check-das`: 잠금 상태 0 FAIL(WARN 15 = 닫힌 항목 14 + "submittable 0"), `--apply` 뒤 68 PASS / 0 WARN / 0 FAIL,
  job 수 427 + 693(인벤토리 nfiles). `--era 2017,2018`: 26 PASS / 0 FAIL(전과 같은 판정). 음성 대조: postVFP dataset 을 2016APV 블록에 넣으면
  "campaign vs era" FAIL; cfg 가 모르는 era 는 "pset year values" FAIL.
- `--dry-run`: 14 task, requestName `<name>_2016APV_extend`/`<name>_2016_extend`, outLFN `.../ttbarIdExtend_v2/2016APV`·`/2016`,
  `year=2016APV`/`year=2016`, unitsPerJob 10(site_config).
- 14 개 dataset 문자열·event 수·파일 수를 인벤토리 TSV 와 프로그램으로 대조(전부 VALID, primary 일치). 파일 ASCII, 제출기는 Python 3.6 문법.

## 2026-10-14 (2) — `crab/launch_extend.sh`: 확인 절차 전부를 한 명령으로 (O9)

**왜.** 사용자: 확인 절차를 자동화해서 한 번에 돌리고 싶다. 같은 날의 `TtbarIdExtender/README.md` §2.2d 명령 (0)–(3) 을 사람이 하나씩 보던
판정까지 포함해 한 스크립트로 묶었다. 감시·재제출·완료 점검을 하는 manager 는 다음 일([01](01_status.md) O9).

**새 파일 `TtbarIdExtender/crab/launch_extend.sh`** (bash 4.2, ASCII). 단계: 1 env(CMSSW_10_6, cmsRun·root·dasgoclient, CRABClient — 없으면
`crab-setup.sh` 를 source, proxy ≥ 24 h, era 블록 존재) → 2 local(era 마다 TTbb_DiLep MiniAOD 한 파일, `cmsRun year=<ERA>`; exit 0, era modifier 줄,
출력 파일, endJob 의 missing 0) → 3 invariants(`check_extend_invariants.C` ALL INVARIANTS PASS) → 4 resolve(MATCH 7/7) → 5 apply → 6 preflight
(exit 0, `READY TO SUBMIT`, WARN 0) → 7 dryrun(attempted = 항목 수, skipped 0) → `--submit` 이면 8 submit(submitted = 항목 수, `[FAILED]`·`[skip]` 없음)
→ 9 report(기다린 뒤 `--report`, DEAD TASK 없음). 첫 실패에서 멈추고 exit 10–18 과 읽을 로그를 찍는다. 출력은 전부
`crab/launch_logs/<UTC>_<eras>/launch.log`(머리·꼬리, 꼬리 없음 = 죽음; `.gitignore` 에 `launch_logs/` 추가), 단계마다의 로그, 로컬 출력.
resolve 로그는 `crab/resolve_parents_<ERA>_<시각>.log` 로 복사(커밋용, 2018 관례). 작업 디렉터리는 `TtbarIdExtender/` 로 고정(CRAB
`work_area` 가 상대 경로라서). SIGINT·SIGTERM 은 꼬리에 EXIT 130.

**`resolve_parents.sh --help`**: 머리말 전체를 찍게 고침(전에는 제목 세 줄만 — `resolve_nano_children.sh` 에서 옮겨 온 sed 범위 탓).

**검증 (오프라인; lxplus 실행 전).** 가짜 `cmsRun`·`root`·`dasgoclient`·`voms-proxy-info`·CRAB API 로 사례마다 새 사본에서: 정상(`--submit`, 14 task;
yaml 의 2016 두 블록 열림, project dir 14, resolve 로그 복사, 화면 = launch.log), `--submit` 없음(READY, project dir 없음), MISMATCH(13, yaml 그대로),
era modifier 다름(11), endJob missing(11), cmsRun exit 65(11), 불변조건 FAIL(12), proxy 1 h(10), CMSSW 14(10), 이미 있는 project dir(15, 제출 0),
SUBMITREFUSED(18), task 하나 제출 실패(17, 나머지 안내), `--skip-local`(0), 잘못된 era·`--era` 없음(2), SIGTERM(130, 꼬리 있음).

## 2026-10-14 (3) — 첫 lxplus 실행: 2016APV 제출, 2016 은 pset 캐시로 거부(T-36) → 제출기 수정; condor manager; §9 AI 세션 규칙

**실행 기록 (lxplus931, 20:39–20:42 UTC, commit 6118faa).** `bash crab/launch_extend.sh --era 2016APV,2016 --submit`: 1 env OK; 2 로컬 cmsRun
두 era(20000 ev 씩, era modifier `Run2_2016_HIPM`/`Run2_2016`, missing 0, 89 s); 3 불변조건 ALL PASS(2016APV: nAddBJets>=3 62 = 61 38 + 62 20 + 71 4;
2016: 49 = 27 + 13 + 9); 4 parent MATCH 7/7 두 era; 5 `--apply` 14 + 14 줄; 6 preflight 68 PASS / 0 WARN / 0 FAIL(DAS 수와 job 수 427 + 693 이
인벤토리와 같음); 7 dry-run 14; 8 제출: **2016APV 7 task 제출됨**(task 이름 `261014_2041xx:junghyun_crab_<sample>_2016APV_extend`), **2016 7 task 는
모두 `A different CMSSW configuration was already cached`** 로 실패 → exit 17. 첫 제출에서 CRAB 이 grid pass phrase 를 물었다(myproxy 위임 갱신;
사용자가 입력).

**동작 변경 고지.**
1. `crab/submit_ttbarIdExtend.py`: 제출을 task 마다 **별도 프로세스**(fork)에서 한다(T-36 의 원인과 CRAB 문서의 방식). 출력·판정(`[submitted]`/
   `[FAILED]`)은 같다; 실패 줄에 child 의 exit code 가 붙는다. 새 `--clean-failed-shells [--yes]`: 고른 task 의 project dir 중 `.requestcache` 가
   없는 껍데기를 찾아(목록, exit 1) `--yes` 면 `crab_projects/_failed_<UTC>/` 로 옮긴다(지우지 않음; `.requestcache` 있는 dir 은 건드리지 않음).
2. 새 `crab/extend_manager.py`(결정론적 감시·재제출·완료 점검), `crab/manager_condor.sh`(lxplus batch 로 제출), 새
   `Validation/scripts/check_extend_sample.C`(task 의 모든 출력 파일을 하나씩 열어 행 수·불변조건·tt+nb 수; `GetEntry` 반환값 검사). 규칙은
   `TtbarIdExtender/README.md` §2.2d. `.gitignore` 에 `TtbarIdExtender/crab/manager/`.
3. `crab/launch_extend.sh`: `git` 은 머리줄용이라 필수 도구 목록에서 뺐다(batch 컨테이너에 없을 수 있음).
4. `00_PROMPT.md` §9(사용자 방향): 사람이 없을 때는 결정론적 manager 만; 디버깅 → 제출은 사용자가 볼 수 있을 때; AI 세션의 커밋은
   `agent/<날짜>-<주제>` branch; lxplus 로그 사본은 `runlogs/lxplus/`(새 디렉터리); 사용자 확인 없이 하지 않는 일과 멈출 때.

**문서.** [08](08_troubleshooting.md) T-36, README §2.2d(tmux 권고 삭제 — lxplus 에서는 ssh 가 끊기면 같이 끊김(사용자), 두 era 제출, 껍데기 정리,
manager), [01](01_status.md) O9, [04](04_decisions.md) D20, `runlogs/README.md`.

**검증 (오프라인; lxplus 실행 전).** pset 캐시를 흉내 낸 가짜 CRAB 에서 옛 제출기 `--era 2016APV,2016` = 7 제출 + 7 FAILED(같은 오류 문구),
새 제출기 = 14 제출. 껍데기: 2016 7 개 목록(exit 1) → `--yes` 로 옮김 → 다시 목록 0 → 2016 만 재제출 7 → `.requestcache` 14. launcher 11 사례 +
두 era 한 번 제출(14) 그대로 통과. manager 23 사례(정상, 재제출, 소진 ALERT·`--clear-alerts`, SUBMITREFUSED, 정체, status 오류, proxy, timestamp 2,
파일 누락, 행 수 차이, 읽기 실패, 불변조건 위반, xrootd 경로, exit 75 와 이어 가기, `--launch` 의 era 별 판단·실패·이미 낸 era·dry-run) + era 별 4 사례
(2016APV 는 감시만·2016 만 launch 해 14 task DONE, 껍데기 ALERT 둘, 일부만 있는 era ALERT) + lock 4 + SIGTERM + 인자 오류. `manager_condor.sh` 의
job 파일을 그린 뒤 가짜 `/cvmfs` 에서 `job.sh` 를 condor 처럼 돌려 `cmssw-el7` 재실행 → cmsenv → crab-setup → manager → launch → 감시 → 점검 →
DONE. `check_extend_sample.C` 는 진짜 ROOT 6.40 에서 합성 파일로(정상, 56 위반, 없는 파일, 빈 목록) 기대대로. 시험 중 잡은 결함 하나:
`manager_condor.sh` 가 `/etc/os-release` 를 source 하면 `NAME`(manager 이름)과 `ID` 가 덮인다 → 서브셸에서만 읽게 고침.

## 2026-10-15 — 2016 제출 완료; `launch_extend.sh` 의 끝 요약이 el7 에서 안 찍힘 (T-37)

**lxplus (사용자, 03:07–03:15 UTC, commit 3f76932).** `--era 2016APV --report`: 6 task COMPLETED, TTbar_SemiLep RUNNING(198 job 중 173
done). `--era 2016 --clean-failed-shells --yes`: 10-14 의 껍데기 7 개를 `crab_projects/_failed_20261015_030819/` 로. `launch_extend.sh --era 2016
--submit`: 1–9 단계 모두 OK(로컬 20000 ev 와 불변조건 PASS, MATCH 7/7, preflight 40 PASS, 7 task 제출, 5 분 뒤 report 에서 6 RUNNING · 1
SUBMITTED). 두 era 의 14 task 가 모두 CRAB 에 있다.

**동작 변경 고지.** `crab/launch_extend.sh`: `main` 이 성공하면 `return 0` 대신 `exit 0` 으로 끝난다(`--submit` 없는 실행도). 위 실행은 9 단계를
다 OK 로 찍고 끝났는데 끝 요약(`RESULT: SUBMITTED`, 커밋 안내, `=== END ... EXIT=0`)이 없었다 — `main | tee` 의 subshell 에 건 EXIT trap 을 bash 4.2
(cmssw-el7)는 함수가 그냥 `return` 하면 돌리지 않는다(`exit` 하면 돌린다: 실패 경로는 늘 찍혔다). 오프라인 시험은 bash 5.2 라 못 잡았다. exit
code 는 그대로 0 이었다(manager 는 exit code 만 본다). [08](08_troubleshooting.md) T-37.

**검증 (오프라인, bash 5.2).** `bash -n`; 가짜 도구로 두 era 제출(`RESULT: SUBMITTED` + `END EXIT=0`), `--submit` 없음(`RESULT: READY` + `END EXIT=0`),
MATCH 6/7(`STOPPED at step 4/9` + `END EXIT=13`). bash 4.2 에서의 확인은 다음 lxplus 실행(또는 manager 의 `--launch`)에서.

## 2026-10-15 (2) — O9 ⑦: 검증 도구가 2016APV·2016 을 안다 (CRAB 이 도는 동안)

**lxplus (사용자, 04:11 UTC).** `manager_condor.sh --era 2016APV,2016 --name extend2016` → condor cluster 13519511(감시·재제출·완료 점검).
lxplus 의 `datasets.yaml`(두 era 열림)과 resolve log 셋을 커밋(b92e99e).

**동작 변경 고지.**
1. `Validation/filelists/make_filelists_miniAOD.py`: era `2016APV`·`2016`(기본 경로 = CERN EOS `.../ttbarIdExtend_v2/<era>`; 이 캠페인의 stage-out 이
   `T3_CH_CERNBOX`). 끝 줄 `RESULT OK | RESULT FAIL` 과 exit code: 0 일곱 샘플 모두, 1 빠지거나 빈 샘플, 2 SAMPLE_DIR 없음, 3 CRAB timestamp 둘(예전
   가드). 전에는 SAMPLE_DIR 이 없거나 샘플이 빠져도 exit 0 이었다.
2. `Validation/filelists/make_nano_filelists_das.sh`: era `2016APV`(`RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11`)·`2016`
   (`RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17`) → `nano2016APV/`, `nano2016/`.
3. 새 `Validation/data/das_nevents_2016APV.json`, `das_nevents_2016.json`: 완결성 기준(TTHHAnalyzer `data/samples_2016{pre,post}VFP_UL.json` 의 DAS
   nevents, dataset 이름도 `_meta` 에). 2016 의 일곱 수는 10-15 lxplus preflight 의 DAS 조회(nano nevents)와 같다.
4. `aggregate_validation.py`: 끝의 안내문을 era 일반으로(2017 의 수치는 다른 era 의 기준이 아님). `submit_validation_condor.py` 는 era 를 경로 이름에만
   쓰므로 그대로.

**문서.** `Validation/README.md` §0.1c(2016 두 era 의 filelist·정렬·condor 검증·집계·patch 추출과 TTHHAnalyzer 의 `2016preVFP`/`2016postVFP` 로
옮기기), [01](01_status.md) O9.

**검증 (오프라인, 가짜 EOS 트리·가짜 dasgoclient).** nano: 두 era rc 0, 캠페인 문자열이 DAS 조회에 그대로, 45 파일 → 20 개씩 세 split, 모르는 era
rc 2. extend: 일곱 샘플 rc 0 `RESULT OK`(Python 3.9 로), 기본 EOS 경로가 없을 때 rc 2, 한 샘플 디렉터리 없음 rc 1, 빈 샘플 rc 1, timestamp 둘 rc 3,
모르는 era rc 1. 집계: 가짜 chunk JSON 으로 2016APV `ALL SAMPLES PASS`(DAS 기준 파일을 찾음), 2016 의 한 샘플 +1 event → FAIL `DIFF -1`, chunk 하나
없음 → `all chunks present 2/3` FAIL. condor 제출기 `--dry-run --era 2016APV`: 13 job(작은 샘플 1, 큰 샘플 3 씩)의 `match.args`·`match.sub`.

## 2026-10-15 (3) — condor manager 가 crab-setup 에서 멈춤(exit 94): `job.sh` 가 crab-setup.sh 를 인자 없이 (T-38)

**lxplus (사용자).** 04:11 UTC 에 낸 manager job(cluster 13519511)이 04:12:53 에 `FATAL CRABClient not importable after crab-setup.sh (exit 94)`
로 끝났다 — manager 는 시작하지 않았다(상태 파일·CRAB task 는 그대로). CRAB task 들은 영향 없이 grid 에서 돈다.

**원인.** `job.sh` 는 condor 의 job id 를 `$1` 로 받는데, 최상위에서 `source /cvmfs/cms.cern.ch/common/crab-setup.sh` 를 불러 crab-setup.sh 가 그
`$1`(`13519511.0`)을 자기 첫 인자(선택 인자: client 판)로 받았다(가장 유력; 출력을 버려 직접 증거는 없음). 오프라인 시험은 인자를 무시하는 가짜
crab-setup.sh 와 미리 채운 `PYTHONPATH` 로 돌아 이 길을 못 봤다. [08](08_troubleshooting.md) T-38.

**동작 변경 고지 (`TtbarIdExtender/crab/manager_condor.sh` 가 쓰는 `job.sh`).**
1. crab-setup.sh 를 인자 없이 부르는 함수 `crab_setup` 안에서 source 한다(위치 인자가 새지 않음). 출력은 버리지 않고 job 의 scratch 에
   `crab_setup.log` 로.
2. exit 94 면 manager.log 에 python3 의 경로·판, `PYTHONPATH` 의 crab 항목, crab-setup 출력과 `import CRABClient` 오류의 끝 20 줄(`[job]   ` 줄).
3. 성공하면 `[job] ... CRABClient from <dir>` 한 줄(어느 client 가 잡혔는지).
manager(`extend_manager.py`)·`launch_extend.sh` 는 그대로(`launch_extend.sh` 는 인자 없이 부르는 `main` 안에서 source 하므로 같은 문제가 없다).

**검증 (오프라인, bash 5.2; `job.sh` 는 cmssw-el7 의 bash 4.2 에서 도는데 쓴 구문은 4.2 에도 있는 것뿐).** 첫 인자를 client 판(`prod|pre|dev`,
없으면 `prod`)으로 읽고 모르는 판이면 `return 1` 하는 가짜 crab-setup.sh, 가짜 cmssw-el7(재실행 경로 포함)·cmsset·scramv1, `PYTHONPATH` 없이
시작하는 job(인자 = `13519511.0`): HEAD(1550939)의 `job.sh` → exit 94, manager.log 의 FATAL 줄이 lxplus 와 같음; 새 `job.sh` → `CRABClient from
.../fakecrab/CRABClient`, `starting extend_manager.py`, manager 가 `--era 2016APV,2016 --name ... --lock-owner condor:13519511.0` 를 받음(rc 0);
crab-setup 이 다른 이유로 실패하면(가짜의 `FAKE_CRAB_BROKEN`) 새 `job.sh` 는 exit 94 + 진단 줄(crab-setup 의 오류 문구, `ModuleNotFoundError`).
생성된 `job.sh` 는 `bash -n`(5.2, 5.1)과 shellcheck 깨끗; `manager_condor.sh` 의 shellcheck 경고 수는 전과 같음(2), ASCII-only. bash 4.2 에서의
확인은 다시 낸 manager job 의 `[job] ... CRABClient from ...` 줄(T-37 의 교훈: el7 스크립트는 4.2 에서 한 번 돌기 전에는 "시험됨" 이 아니다).

## 2026-10-15 (4) — T-38 확정, manager 다시 제출됨; manager.log 를 줄마다 닫는다 (AFS write-on-close, T-39)

**lxplus (사용자, 05:05 UTC).** c0d9cd0 을 pull 해 `manager_condor.sh --era 2016APV,2016 --name extend2016` → cluster 13519526. el7(bash 4.2)
안에서 `CRABClient from /cvmfs/cms.cern.ch/share/cms/crab/1.0/lib/prod/CRABClient`, `starting extend_manager.py`. T-38 원인 확정:
`/cvmfs/cms.cern.ch/common/crab-setup.sh` 3–7 행이 `$1` 을 CRAB client 판(`prod|pre|dev`)으로 보고 그 밖이면 `ERROR: Invalid CRAB type`.

**관찰.** 시작 21 초 뒤 lxplus 의 manager.log 에 `[manager]` 줄이 없었다. manager 는 manager.log 를 한 번 열어 두고 줄마다 flush 만 했는데,
AFS 는 쓴 host 가 닫거나 fsync 해야 다른 host 에 보여 준다 → lxplus 에서는 manager 가 끝날 때까지 안 보일 수 있다. [08](08_troubleshooting.md)
T-39. 확인(07:01 UTC): `condor_tail -maxbytes 4000 13519526.0` 에는 check 1–4(05:07, 05:37, 06:07, 06:37 UTC)와 task 표가
있는데 lxplus 의 manager.log 는 `starting extend_manager.py` 에서 멈춰 있었다. 이 job 은 다시 내지 않는다 — 97 % 였고 완료 점검은 끊으면
처음부터다; 그 줄들은 manager 가 끝나며 파일을 닫을 때 나타난다.

**진행 (check 4, 06:38 UTC).** jobs 1108/1137(97.4 %), task 13/14 끝(2016APV 일곱, 2016 여섯), 남은 것 2016/TTbar_DiLep 78/107(run 15,
transferring 14); 실패 0, 재제출 0, proxy 182 h.

**동작 변경 고지 (`TtbarIdExtender/crab/extend_manager.py`).** `Log` 가 줄마다 열고(append) → 쓰고 → flush → `os.fsync` → 닫는다(전에는 시작할
때 한 번 열어 끝까지). 내용·순서·stdout 은 그대로. 이미 도는 manager 에는 다음 시작부터 적용(다시 제출하거나 22 시간 뒤 exit 75 의 재큐).

**검증 (오프라인, 가짜 CRAB·EOS·root·xrdfs).** 같은 시나리오를 옛/새 코드로 돌려 manager.log 와 stdout 을 비교: 정상 DONE, 재제출 DONE, 재제출
소진 ONCE, 죽은 task·정체·status 오류·proxy 부족 STOPPED, timestamp 2 개·파일 누락·행 수 차이·읽을 수 없는 파일·불변조건 위반 CHECK FAILED,
SUBMITREFUSED ONCE, `--launch` DONE·실패 STOPPED, 두 era 중 2016 만 launch DONE — 16 개 모두 exit code 같고 로그는 시각(과 시험 디렉터리
이름)만 다름. 도는 manager 의 열린 fd 중 manager.log: 옛 1, 새 0. SIGTERM: 둘 다 exit 143, END 줄, lock 지움. Python 3.11·3.9 컴파일,
ASCII-only (3.6 전용 구문 없음).

## 2026-10-15 (5) — O10: era 2024(Run 3) extend 준비 — v15 영역, `resolve_parents.sh --fill`, release 짝 검사, 검증 도구의 2024 (D21)

**lxplus (사용자).** manager `extend2016`(cluster 13519526) `RESULT DONE`, `REPORT.txt` ALL PASS 14 task(O9 ⑥ 끝). ⑦ filelist: `sidecar2016APV`·
`sidecar2016` `RESULT OK` 7/7, nano 두 era rc 0. ⑧ 정렬(`--sort-only`, cmssw-el7) 시작. 사용자 결정: 2024 도 만든다(D21; "그래야 tt+B 뿐 아니라
tt+3b, tt+4b도 stitching을 하지"), 진행 방식은 절충([../00_PROMPT.md](../00_PROMPT.md) §10 신설).

**동작 변경 고지 — 2024 를 위해.** (Run 2 의 네 era 는 그대로; 아래 "검증" 의 old/new 비교.)
1. `test/run_ttbarIdExtend_cfg.py`: `year=2024` → `cms.Process(..., eras.Run3_2024)` 하나, 줄 `era modifier = Run3_2024`. Run 2 는 여전히
   `<era> + run2_nanoAOD_106Xv2`. 이 release 에 era 가 없으면(10_6 의 `Run3_2024`) 이름을 대고 멈춘다.
2. `crab/datasets.yaml`: `"2024"` 블록(GT `150X_mcRun3_2024_realistic_v2` 기록용, `era_modifiers: ["Run3_2024"]`), 일곱 항목 `dataset: ""`,
   `nano_child` = TTHHAnalyzer `samples_2024.json` 의 NanoAODv15, `enabled`/`verified` false.
3. `crab/resolve_parents.sh`: era 2024(Nano/MiniAOD 캠페인), `--fill`(EMPTY 항목의 `dataset: ""` 에만 DAS parent; parent 하나·같은 primary·처리 이름
   `RunIII2024Summer24MiniAOD*` 일 때만, 하나라도 아니면 아무것도 안 씀 exit 3; 쓴 뒤 다시 읽기, diff 출력; 사후 검사 실패 exit 4). `--fill` 과
   `--apply` 는 함께 못 씀(exit 2). EMPTY 항목은 읽기 전용 실행에서 `--fill` 을 안내.
4. `crab/launch_extend.sh`: era 마다 release 계열(`2024` = `CMSSW_15_0_`), 다르면 한 호출에 섞지 않음(exit 10); 단계 2 의 era 줄 검사는 2024 에서
   `Run3_2024`; resolve 실패 안내에 `--fill`.
5. `crab/submit_ttbarIdExtend.py`: 제출 경로는 release 가 선택한 era 에 맞을 때만(bulk action 은 검사 안 함); `dataset: ""` 은 preflight 에서 닫힌 항목
   WARN·열린 항목 FAIL, DAS 조회 안 함, 제출 루프는 `--force` 여도 건너뜀(`unresolved` 줄); preflight `--check-das` 의 "MiniAOD on disk"(DAS `site`;
   tape 뿐이면 WARN) — **2024 만**.
6. `crab/manager_condor.sh`: 영역의 SCRAM arch 로 job 의 container(slc7 → `cmssw-el7`, el8 → `cmssw-el8`, el9 → 그대로), era 와 영역의 짝 검사,
   `dataset: ""` 이 남은 era 는 호스트에서 거부(exit 2, `--fill` 안내). `crab/extend_manager.py`: 같은 경우 `IndexError` 대신 안내와 exit 2.
7. `Validation/`: `make_nano_filelists_das.sh 2024`(Run 3 primary → 같은 short name), `make_filelists_miniAOD.py 2024`(EOS `ttbarIdExtend_v2/2024`),
   `submit_validation_condor.py` 의 이미지 = 영역의 arch(모르면 el7 + WARN; `--container` 우선), 새 `data/das_nevents_2024.json`.

**독립 검토(에이전트) 반영.** 확인된 셋: ① tape 확인이 Run 2 preflight 에도 들어가 Run 2 launch 를 멈출 수 있었음 → 2024 만, 안내에 수동 경로.
② `dataset: ""` 에서 manager 가 `IndexError` → 6. ③ `--force` 가 빈 2024 항목을 세어 Run 2 제출을 release 로 거부, `--force --era 2024` 는 빈
`inputDataset` 을 낼 수 있었음 → 5. 의심 둘: ④ `cat tmp > yaml` 은 먼저 비우므로 쓰기 실패에 yaml 이 잘릴 수 있음 → `--fill`·`--apply` 모두 같은
디렉터리의 `mv`(원자적), mode 유지, 실패면 exit 4 와 검사 끝난 임시 파일 이름. ⑤ arch 를 모르면 이미지가 조용히 el7 → WARN.

**검증 (오프라인; 가짜 cmsRun·dasgoclient·CRABClient·cvmfs·EOS 트리).** cfg 14/14(다섯 year 의 era 줄과 Process modifier, Run 2 넷은 HEAD 와
같음, 2022 거부, `Run3_2024` 없는 release 거부). resolve 18/18(2024 EMPTY 7 → `--fill` 7 줄만 → MATCH 7/7 → `--apply`; 잘못된 parent 넷은 아무것도
안 씀; 2016 은 HEAD 와 같은 줄; 일부만 빈 경우; mode 유지; `mv` 실패 → exit 4, yaml 그대로). launch 13/13(15_0 에서 2024 READY·SUBMITTED,
10_6 에서 2024 거부, 2018+2024 거부, 10_6 의 2016 READY, tape 뿐 → 단계 6 exit 15, HEAD 패키지는 2024 를 모름, `--fill` 전 → 단계 4 exit 13 과 yaml
그대로). 제출기 13/13(release 거부·bulk 면제·빈 항목 WARN/FAIL·DAS 조회 생략·`--force` 둘·Run 2 preflight 는 HEAD 와 env·시각·era 목록 줄만 다름).
manager 9/9(15_0 → `cmssw-el8` 재실행, 10_6 의 `job.sh` 는 HEAD 와 같음, el9 그대로, 2024 `job.sh` 가 manager 를 띄움, 빈 2024 거부 둘). 검증 도구
35/35(2024 nano 일곱 목록·split·`-v3` 만, Run 2 다섯 era 의 출력 트리·로그가 HEAD 와 같음, 2024 extend 목록·가드, 이미지 el7/el8/el9·`lib/` arch·덮어쓰기,
10_6 의 제출 파일·preflight 가 HEAD 와 같음, 집계 2024 PASS·DIFF·빠진 chunk). shellcheck 경고 0, `bash -n`, Python 3.6 문법(vermin), 추가 줄
ASCII. 실제 `CMSSW_15_0_18` + Summer24 MiniAODv6 는 lxplus 의 `launch_extend.sh --era 2024` 단계 2–3 이 처음 확인한다; v15 영역의 Validation
첫 빌드도 lxplus 에서.

**문서.** `TtbarIdExtender/README.md` §2.2e, `Validation/README.md` §0.1d, [01](01_status.md) O10·O9·O5, [04](04_decisions.md) D21,
[09](09_environment.md) §3, [../00_PROMPT.md](../00_PROMPT.md) §10(작업 블록마다 진행 방식을 묻는다).

## 2026-10-15 (6) — 검증 `--report`·`--resubmit-failed` 가 condor queue 를 본다; 찍는 명령은 절대 경로; `batch_name = val_<era>` (T-40)

**lxplus (사용자, 2026-10-15; condor 의 시각은 CEST).** 2016APV·2016 정렬 끝(`[sort] ... exit=0` 열넷), preflight 두 era `32 PASS, 0 WARN, 0 FAIL`, smoke 2016APV
(cluster 13528330, ttbb_2L2Nu) 결과 ok. 전량: 2016APV 16 job(13530795), 2016 22 job(13530802). 1 분 뒤 `--report` 가 2016APV 의 idle 15 chunk 를
missing 과 "need re-running" 으로 찍음 → `condor_rm junghyun`(38 job 모두) → 찍힌 명령은 `scripts/` 가 빠져 실패 → `scripts/` 를 붙여
`--resubmit-failed`: 2016APV 15 chunk(13530917). 2016 은 다시 내야 한다. [08](08_troubleshooting.md) T-40.

**동작 변경 고지 (`Validation/scripts/submit_validation_condor.py`).**
1. `--report`: `condor_q -constraint 'Cmd =?= "<work base>/run_match.sh"'` 로 job 이 queue 에 있는 chunk 를 찾아 `queue` 칸에 센다(idle/running/
   held, cluster.proc 와 함께; 예전 결과가 있어도 queue 가 이긴다 — 그 job 이 덮어쓴다); 실패가 아니라고 찍고 queue 조회 명령을, held 면
   `condor_q -hold`·`condor_rm` 을, 한 chunk 에 job 이 둘이면 중복 WARN 을 찍는다. exit 0 모두 ok, 1 실패·job 없는 missing·held, 2 기다리기만,
   3 condor_q 를 못 물었고 ok 아닌 chunk 가 있음(다시 내라는 명령을 찍지 않는다; 전에는 결과가 없으면 1).
2. `--resubmit-failed`: queue 에 job 이 있는 chunk 는 내지 않고 목록만; condor_q 가 없거나 실패하면 거부(FATAL).
3. 다음 명령(`--resubmit-failed`, `--report`, `--sort-only`, aggregate, 제출 뒤의 report·monitor·remove)을 절대 경로로, 그 호출의 옵션(`--samples`,
   디렉터리, `--memory`·`--flavour` …)을 붙여 shell-quote 해서 찍는다. nano filelist 안내는 `cd <Validation>/filelists && ./make_nano_filelists_das.sh`.
5. `run_match.sh` 는 옆에 쓰고 rename(다시 낼 때 queue 의 job 이 반쯤 쓴 파일을 읽지 않게).
4. submit file 에 `batch_name = val_<era>` — `condor_q`·`condor_rm -constraint 'JobBatchName == "val_<era>"'` 로 한 캠페인만.
`aggregate_validation.py`·job 의 `run_match.sh`·`match.args` 는 그대로.

**독립 검토(에이전트) 반영.** 확인된 일곱: 찍는 명령이 `--samples`·디렉터리를 버림(실패한 smoke 뒤 붙여 넣으면 캠페인 전체 제출) → 3; condor_q 없을
때도 "re-run them" 과 명령 → exit 3; ok 결과 + queue 의 job 을 ok 로 셈 → queue 가 이김; held 만 남아도 "wait" → exit 1; 한 chunk 의 job 둘 중
하나만 보임 → 목록; 상대 경로 힌트 셋 → 절대; symlink 로 부르면 틀린 경로 → resolve. 의심 셋: `run_match.sh` 를 덮어쓰는 중에 시작하는 job → 5;
myschedd 가 바뀌면 옛 job 이 안 보임 → 문서(T-40, 머리말); ClassAd `==` 은 대소문자 무시 → `=?=` 와 escape.

**검증 (오프라인, 가짜 condor_q·condor_submit).** 24/24: 사용자의 경우(smoke ok + idle 5 → exit 2, 다시 내라는 말 없음; `--resubmit-failed` 는 아무것도
안 쓰고 안 냄), 섞인 경우(running·held·job 없는 missing·exit 4·실패 뒤 다시 낸 idle → exit 1, queue 3, 실패 둘만 다시 냄), JobStatus 3·4 는 queue 밖,
다른 work base 의 job 은 무관, condor_q 없음·실패(report exit 3·명령 없음, resubmit 거부), 절대 경로와 옵션, `batch_name`, 모두 ok → exit 0, ok 결과 +
queue 의 job → queued, held 만 → exit 1, job 둘, 실패한 smoke 의 힌트(`--samples` 유지), `--smoke` 제출의 힌트(`--samples`·`--memory 3000`), 빈칸 있는
경로, `run_match.sh` 의 rename. 2026-10-15 (5) 의 검증 도구
시험 35/35 다시 통과(10_6 영역의 `match.sub` 은 `batch_name` 한 줄만 다름; `run_match.sh`·`match.args`·stdout 은 HEAD 와 같음).

**문서.** [08](08_troubleshooting.md) T-40, `Validation/README.md` §4.0 3.5단계(queue 칸, 지울 때는 그 캠페인만)·§0.1c, [01](01_status.md) O9.

## 2026-10-15 (7) — 명령 블록을 셸 경계와 비밀번호 프롬프트에서 나눈다; lxplus 의 git 에 `switch` (T-41); O9 ⑧ 진행

**lxplus (사용자).** 2016APV 다시 낸 15 chunk(13530917) 끝: 16 중 15 ok, `file_TTToSemiLeptonic_4` exit 4(nano 를 재시도 후에도 못 읽었거나 읽은
entry 수 ≠ open-check — 보통 일시적 AAA; 로그 확인 뒤 그 하나만 다시). 2016 은 아직 다시 내지 않음(22 missing, queue 0). 맥의 4bf41b6 은 push 됨.
2024 준비 블록을 한 번에 붙인 결과는 [08](08_troubleshooting.md) T-41: `switch` 없어 pull 실패, `cmssw-el8` 뒤의 줄이 호스트에서 돎, v15 clone 이 옛 코드.

**문서만 (코드 변경 없음).** `TtbarIdExtender/README.md` §2.2e 와 `Validation/README.md` §0.1c·§0.1d 의 블록을 셸 경계(호스트 ↔ 컨테이너)와 비밀번호를
묻는 명령(`switch`, `voms-proxy-init`, 첫 CRAB 제출)에서 나누고 `exit` 를 따로 뒀다; §2.2e 에 `switch`. smoke 와 전량, 끝난 뒤의 report·집계도 기다릴 곳에서
나눴다. 규칙: [../00_PROMPT.md](../00_PROMPT.md) §6. [01](01_status.md) O9·O10.

## 2026-10-15 (8) — O10: 2024 CRAB 제출(7 task, 3,557 job), manager `extend2024`; NanoAOD > MiniAOD 네 샘플과 DAS 확인; O9 ⑧ 진행

**lxplus (사용자), 2024.** T-41 대로 나눈 블록으로 다시: `switch` → v15 clone pull → `cmssw-el8` 에서 `scram b clean && scram b -j8` →
`resolve_parents.sh 2024` → `--fill` → MATCH 7/7 → `launch_extend.sh --era 2024` READY(로컬 cmsRun·불변조건·resolve·`--apply`·preflight·dry-run) →
`--skip-local --submit` → `RESULT: SUBMITTED`, 7 task RUNNING, 3,557 job. condor manager `extend2024` = cluster 13532975(`SCRAM arch=el8_amd64_gcc12 ->
job runs in cmssw-el8`, proxy 191 h). `datasets.yaml`(2024 parent 일곱, 열림)과 resolve 로그 둘을 lxplus 에서 커밋(fb54da9); 맥의 1eab70d 가 먼저
올라가 있어 push 가 `rejected (fetch first)` → `git pull --rebase` 뒤 push. `TtbarIdExtender/README.md` §2.2e (i) 의 commit 과 push 사이에
`git pull --rebase` 를 넣었다(올라온 것이 없으면 아무것도 안 한다).

**NanoAOD > MiniAOD.** 네 샘플에서 중앙 NanoAODv15 의 DAS nevents 가 그 MiniAODv6 parent 보다 많다(UL16 다섯 항목과 반대 방향). TTbb_DiLep 의
차이 804 가 launch 의 로컬 시험 파일(그 MiniAOD 의 DAS 목록 첫 파일)의 event 수와 같아 그 파일이 invalid 인지 사용자가 DAS 로 확인: `is_file_valid: 1`,
`nevents: 804`, valid 목록 604 파일 = summary `nfiles` → 그 가설은 기각. 표, 남은 두 설명, 2024 검증에서 가르는 법: [01](01_status.md) O10.

**O9 ⑧ (2016 대조).** 2016APV `file_TTToSemiLeptonic_4` 의 exit 4 는 nano 파일 하나의 xrootd open 이 1813 s 뒤 `Operation expired`(일시적) →
그 chunk 만 다시(cluster 13532884). 2016 22 chunk 제출(cluster 13532885), 16:19 CEST 에 19 끝·3 도는 중.

**문서만 (코드 변경 없음).** [01](01_status.md) O9·O10·O3, `TtbarIdExtender/README.md` §2.2e (i), `Validation/README.md` §0.1d(Nano > MiniAOD 인 2024 의
unmatched 가 어디에 어떻게 나오는지).

## 2026-10-15 (9) — 검증 job 이 셋업하는 CMSSW 영역은 스크립트가 들어 있는 영역(`$CMSSW_BASE` 가 아니다): 2016 22 chunk 가 exit 127 (T-42)

**lxplus (사용자).** v15 clone 의 커밋은 rebase 뒤 c7d72cc 로 push, 맥 b1874f3 push. 2016 `--report`: 22 chunk 모두 `exit 127`, queue 0;
`condor_history` 의 ExitCode 127 ×22. 원인(확인: 그 셸의 `CMSSW_BASE` 가 v15 영역, job 의 `SCRAM_ARCH=el8_amd64_gcc12`, .err 의 `symbol lookup error: ... undefined symbol: _ZN6TClass8GetClassERKSt9type_infobb`)과 즉시 조치(`--resubmit-failed --cmssw-base <10_6 영역>`):
[08](08_troubleshooting.md) T-42.

**코드 (`Validation/scripts/submit_validation_condor.py`).** `job_cmssw_base()`: job 의 영역 = `--cmssw-base`, 없으면 스크립트가 들어 있는 영역(그
`bin/` 을 job 이 싣고 간다); `$CMSSW_BASE` 는 스크립트가 CMSSW 영역 밖일 때만. 다르면 제출·`--resubmit-failed`·`--preflight` 에 WARN(preflight 는
`$CMSSW_BASE of this shell` 행), 제출 출력에 `[job env] <영역>   image <이미지>`. `run_match.sh`: `[job] CMSSW_BASE=` 줄, `ldd -r` 가 matcher 의
라이브러리나 matcher 자신의 심볼을 못 찾으면 exit **121**(못 찾은 것을 .out 에; ROOT 라이브러리 안의 undefined 는 보지 않는다), matcher 가 127·126 으로 끝나면 그 뜻(loader; 메시지는 .err)을 .out 에. 10_6 영역에서
만든 파일은 옛 코드와 그 추가 줄만 다르다(T6 d9 를 그렇게 고쳤다).

**시험.** 새 T8 15/15 — 묵은 `$CMSSW_BASE`(v15) → 10_6·el7 과 WARN, `--cmssw-base` 우선, 같은 영역의 다른 철자(symlink)는 WARN 없음, 설정 없음, preflight
의 행, 영역 밖 사본, `--resubmit-failed`, 그리고 생성된 `run_match.sh` 를 가짜 ldd·matcher·xrdcp 로 실제로 돌려 121(라이브러리 없음)·127 설명·정상 0·exit 4
에는 설명 없음, `ldd -r` 의 matcher 심볼(121)과 라이브러리 쪽 심볼(멈추지 않음). 옛 코드로 돌리면 T8 11 FAIL(시험이 고친 것을 잡는다). T6 35/35, T7 24/24. 실제 `ldd -r` 의 줄 형식은 작은 C 프로그램으로 확인했다(심볼을 뺀 라이브러리 → `undefined symbol: foo<TAB>(./matchTtbarIdSorted)`,
실행하면 `symbol lookup error` 와 127 — 2016 job 과 같은 모양).

**문서.** [08](08_troubleshooting.md) T-42, [01](01_status.md) O9, `Validation/README.md` §0.1c 의 한 줄과 진단표(121, 127).

## 2026-10-15 (10) — O9 ⑧ 끝: 2016APV·2016 대조 두 era 모두 `OVERALL: ALL SAMPLES PASS` (14 표본)

**lxplus (사용자).** T-42 의 재제출(`--cmssw-base`·`--container` 명시, 이미지 el7·영역 10_6 확인): 2016 22 job(cluster 13535253), 2016APV 1 job(13535254).
`--report` 두 era 모두 `All chunks produced a result`(16/16, 22/22), `aggregate_validation.py` 두 era 모두 **`OVERALL: ALL SAMPLES PASS`** — unmatched·disagree·
불변식 위반 0, nano 합 = DAS, 61/62/71/72 와 53/54/55 의 합이 `nAddBJets≥3` 과 같다(14 행). 수치: [06](06_validation_results.md) 맨 끝 절. 다음: ⑨ patch 추출.

**곁가지(같은 날, lxplus).** AFS 홈이 95 % — 원인은 원격 편집기 서버(`~/.vscode-server` 787 MB, `~/.cursor-server` 620 MB)와 캐시(`~/.cache/pip` 430 MB,
`~/.cache/vscode-cpptools` 122 MB), 예전 프로젝트; 이 저장소의 두 clone 은 합 237 MB. 사용자가 그것들을 지워 70 %. O10: manager check 9(18:20 UTC) jobs
3552/3557, task 5/7, 실패 0.

**문서만 (코드 변경 없음).** [06](06_validation_results.md), [01](01_status.md) O9·O10.

## 2026-10-15 (11) — O9 ⑨: 2016 patch 열넷 (끝); O10: 2024 는 patch 를 검증과 병렬로

- **O9 ⑨ 끝.** lxplus `cmssw-el7`(CMSSW_10_6_32_patch1)에서 `extractTtbarIdPatch --out-tree TtNb --label <KEY>_<2016preVFP|2016postVFP>` 열넷, 모두 exit 0과
  `selection consistent`. extend = DAS nano 인 아홉 표본은 patch 행 = 검증의 `nAddBJets≥3` 이 정확히 같고, extend 가 큰 다섯은 차가 (extend − nano) × 율과
  맞는다(2016APV TTbar_Hadronic +51 대 36 ± 6 이 가장 멀다 — nano 에 없는 event). 맥으로 scp, md5 열넷 일치 → TTHHAnalyzer
  `DerivedCorr/expandedTtbarId/2016{preVFP,postVFP}/`(그쪽 README.txt; `*.root` 는 gitignore 라 `git add -f`). 수치: [06](06_validation_results.md) 맨 끝.
- **O10.** manager `extend2024` check 11(10-15 19:20 UTC) 3,552/3,557 — TTbar_SemiLep 4·TTbar_Hadronic 1 job 이 18:20 부터 run, 실패 0. 사용자가 2024 의
  tt+nb control plot 을 가장 먼저 원함 → `RESULT DONE` 뒤 filelist(⑥)와 patch 추출을 검증보다 먼저 하고, 검증(정렬 + condor 대조)은 병렬로 돌려 최종 plot 의
  문으로 둔다(TTHHAnalyzer D-2026-10-15-J). 코드 변경 없음.


## 2026-10-16 — O10: TTbar_Hadronic job 1012 가 멈춤 → kill → resubmit 거부 → lxplus 에서 직접 생성 (T-43, D22); O11 신설

- **진단(대시보드, 사용자가 연 CMS Task Monitoring).** 1012 는 Retry 0, 15:46:42 UTC T2_FR_GRIF 시작, 재시작 없이 12.4 h running 에 CPU 0.149 h(효율 1.2 %) — site 실패·재제출도 배치 지연도 아니고 worker 에서 멈춘 job. task 의 나머지 1,080 job 은 16:35 UTC 무렵까지 모두 exit 0. 세부: [08](08_troubleshooting.md) T-43.
- **조치(사용자, lxplus).** `crab kill` → condor 쪽 Removed(exit 50667) → `crab resubmit --jobids=1012 ...` 를 서버가 거부(`You cannot resubmit jobs if the task is in status KILLED`) → `condor_rm 13538986`(manager) → `crab report`(1,080 job: 10,796 파일, 474,564,656 event) → 1012 의 입력 10 파일(DAS 442,200 event) → lxplus `cmssw-el8` 에서 `cmsRun run_ttbarIdExtend_cfg.py year=2024`(07:49 CEST 시작, 입력은 IN2P3·FNAL 에서 읽힘; 결과 점검·`xrdcp --posc`·`state.json`·manager 재시작은 진행 중). 받는 기준과 기각한 대안: [04](04_decisions.md) D22.
- **나머지 여섯(⑥ 준비, 사용자 lxplus).** `make_filelists_miniAOD.py 2024` RESULT OK(sidecar 3,556 = 3,557 − 1: tt4b 46, ttbb_2L2Nu 71, ttbb_Hadronic 64, ttbb_SemiLeptonic 100, TTTo2L2Nu 1,093, TTToHadronic 1,080, TTToSemiLeptonic 1,102; 각 timestamp 1 개), `make_nano_filelists_das.sh 2024` rc 0(3,052), v15 영역의 첫 Validation 빌드 rc 0(ROOT 6.32.13, 일곱 binary). 추출·정렬은 접속을 유지할 수 있을 때 — lxplus 의 tmux 는 ssh 가 끊기면 같이 끊긴다(D20, 사용자 확인; AI 가 처음에 반대로 안내했다가 정정). TTToHadronic 은 1012 가 들어간 뒤 filelist 를 다시 만들고 따로 돈다(1,080 개 목록으로 정렬하면 `--sort-only` 가 다음에 '이미 정렬됨'으로 건너뛴다).
- **O11 신설(미래).** 사용자: "언젠가는 이걸 그냥 crab job으로 다시 만들어서 결과 비교해보자 … 2024 플랏 만들고 run2 작업 돌아가면서 하면 될듯." — [01](01_status.md) O11.
- **코드 변경 없음.** OPEN 으로 둔 것: manager 가 `dbStatus` 로 KILLED 를 보게; extend `max_runtime_min` 1440 을 줄이기(T-43).

## 2026-10-16 (2) — O10: 1012 직접 생성 끝 → CRAB 자리, manager 다시 띄움; 추출·정렬은 condor job (T-44, T-45); 오래 걸리는 lxplus 단계는 condor (00_PROMPT §10)

- **1012(사용자, lxplus).** tmux(lxplus992)에 건 첫 실행(07:49 CEST)이 ssh 끊김과 함께 사라짐([08](08_troubleshooting.md) T-44) → 처음부터 다시: 출력 3,250,618 bytes, 행 442,200 = 입력 10 파일의 DAS nevents, `check_extend_invariants.C` PASS → `xrdcp --posc` 로 `.../TTbar_Hadronic_2024_extend/261015_141145/0001/ttbarIDExtend_1012.root`(task 의 EOS 파일 1,081). 받는 기준: [04](04_decisions.md) D22.
- **manager.** `state.json` 에 TTbar_Hadronic 을 done·jobs 1081(원본 `.before_manual_1012`); condor_rm 한 manager(cluster 13538986)의 `manager.lock` 을 `manager.lock.stale_13538986` 로 옮김(T-45) → 다시 띄움: cluster 13538988(07:00 UTC) — 완료 점검(timestamp 1 개, 파일 = job·id 1..N, 행 = DAS MiniAOD nevents, 불변조건) 뒤 07:21:16 UTC `=== END extend_manager.py EXIT=0`(0 = DONE; `REPORT.txt` 의 표는 다음 항목에).
- **⑥ 준비.** filelist 다시: sidecar 3,557(tt4b 46, ttbb_2L2Nu 71, ttbb_Hadronic 64, ttbb_SemiLeptonic 100, TTTo2L2Nu 1,093, TTToHadronic 1,081, TTToSemiLeptonic 1,102), nano 3,052. 추출·정렬은 샘플마다 condor job 하나(`~/TTHHGenCategoryTools_v15/condor_prep2024/` 의 `prep_job.sh`·`prep.sub`, 저장소 밖; batch `prep2024`, cluster 13538989, 7 job): el8 이미지에서 v15 영역의 `scramv1 runtime`, `extractTtbarIdPatch --out-tree TtNb --label <KEY>_2024` → EOS `lookup2024/ttnb_<KEY>.root`, `sortSplitExtend` → EOS `sorted2024/<sample>/`(part 를 다 올린 뒤 `index.txt` — 검증 제출기는 `index.txt` 가 있어야 정렬본이 준비됐다고 본다), 추출의 input entries 와 정렬의 행 합이 다르면 FAIL; `.out` 끝 줄 `[prep] end … RESULT=OK|FAIL`.
- **규칙(사용자).** "1-2시간 걸리는건 내가 condor로 하라고 했을텐데 왜 tmux로 했냐." — [../00_PROMPT.md](../00_PROMPT.md) §10 에 넣음: lxplus 에서 30 분을 넘길 수 있는 단계는 condor job, tmux·screen·`nohup` 에 걸어 두지 않는다. [04](04_decisions.md) D20 에 보탬.
- **저장소 위생(사용자, v15 clone 75bfa2d 의 `git status --short`).** `?? TtbarIdExtender/crab.log` — crab 명령이 그 디렉터리에 남긴 CRAB client 로그(transcript 라 커밋하지 않는다) → `.gitignore` 에 `crab.log`. `?? Validation/lookup2024/` — [../Validation/README.md](../Validation/README.md) §0.1d 의 대화형 patch 블록이 쓰는 자리라 그 블록을 앞서 돌린 흔적으로 보인다: 내용을 확인한 뒤 저장소 밖으로 옮기고, 2024 lookup 은 condor job 의 EOS `lookup2024/` 것을 쓴다.
- **코드 변경 없음**(`.gitignore` 한 줄 외). OPEN: `prep_job.sh`·`prep.sub` 를 era 인자로 일반화해 저장소에(결과 확인 뒤); condor_rm 뒤에 남은 lock(T-45); 앞 항목의 둘(`dbStatus`, `max_runtime_min`).

## 2026-10-16 (3) — O10: lookup 일곱 → TTHHAnalyzer; 검증 ⑥ 제출(preflight READY, smoke PASS, 전량 156 job); O12 신설

- **prep2024 결과(사용자 lxplus, cluster 13538989).** 일곱 job 모두 `RESULT=OK`; 입력 행·tt+nb 행·61/62/71/72 = `REPORT.txt`; md5 job = EOS `lookup2024/` = 맥 → TTHHAnalyzer `DerivedCorr/expandedTtbarId/2024/`(그쪽 801f059). 수치: [06](06_validation_results.md) '2024'.
- **대화형 추출의 흔적.** v15 clone 의 추적 안 되는 `Validation/lookup2024/`·`logs2024/`(TTbar_DiLep 63 bytes, TTbar_Hadronic 없음 — 끊긴 tmux 실행, [08](08_troubleshooting.md) T-44)는 `~/TTHHGenCategoryTools_v15/aborted_interactive_extract2024/` 로 옮김(지우지 않음).
- **검증 ⑥(사용자 lxplus).** `submit_validation_condor.py --era 2024 --preflight` READY(32 PASS; 정렬은 prep job 의 EOS `sorted2024/` 를 그대로 — `--sort-only` 안 씀) → `--smoke`(cluster 13540386, ttbb_2L2Nu chunk 0, nano 20 파일): 787,920 event 모두 matched·agree, unmatched·disagree·위반 0 → 전량 156 job(cluster 13540390). TTHHAnalyzer 의 2024 prescan(DAG cluster 13540391)과 병렬.
- **O12 신설(미래).** TTHHAnalyzer D-2026-10-16-B(Run 2 는 v9·v15 둘 다) → v15 mode 에는 2016·2017 lookup 을 중앙 NanoAODv15 와 다시 대조 — [01](01_status.md) O12.
- **코드 변경 없음.**

## 2026-10-17 — 문서: 워크스페이스의 여러 세션용 문서 체계를 가리키는 줄

- [01](01_status.md) 머리에 한 줄: 워크스페이스 전체의 진행은 맥 워크스페이스 최상단의 `coord/BOARD.md`, 공통 규칙은 `AGENTS.md`(이 저장소 밖). 이 저장소의 2024 검증 흐름 = `coord/streams/S2_tgc_validation.md`(사용자 요청 2026-10-16, 10-17 새벽 승인).
- **코드 변경 없음.**

## 2026-10-17 (2) — O10: 검증 ⑥ 의 결과(156/156 chunk), 해석과 사용 제안

- `--report` TOTAL `156 156 0 0 0`; `aggregate_validation.py --era 2024` → tt4b·ttbb_SemiLeptonic PASS, 나머지 다섯은 `unmatched == 0` 만 FAIL. matched 사건은 일곱 표본 모두 disagree 0, 위반 0, 보존 일치 — 숫자와 해석은 [06](06_validation_results.md) '2024'.
- unmatched 는 Nano 와 MiniAOD 의 VALID 파일 차이(O10 의 (i)); 셋은 Nano − MiniAOD 와 정확히 같고, TTToSemiLeptonic·TTToHadronic 은 양쪽 모두에 상대에 없는 파일이 있다. 분석 영향(tt+≥3b 의 오분류)은 표본마다 ge3 의 0.06 % 이하.
- **코드 변경 없음.** 사용 여부는 사용자 결정(워크스페이스 `coord/DECISIONS_PENDING.md` D1).

## 2026-10-17 (3) — D23: 2024 lookup 을 그대로 쓴다(사용자 결정)

- 사용자(10-17): "해당 사항을 기록해 두되 네 권고대로 2024 lookup을 그대로 쓴다." → [04](04_decisions.md) D23(근거·영향·기각한 대안), [06](06_validation_results.md)·[01](01_status.md) O10 에 표시.
- **코드 변경 없음.**
