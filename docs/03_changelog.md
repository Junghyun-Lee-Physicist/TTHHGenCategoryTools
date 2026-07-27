# 03 — Changelog (append-only)

> **목적**: 무엇이 언제 바뀌었나. 새 항목은 **아래에 추가만** 한다 (append-only).
> **대상 독자**: 최신 변경을 따라잡으려는 모든 기여자.
> **상태**: 살아있는 문서 — 마지막 항목 **2026-07-26**.
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
