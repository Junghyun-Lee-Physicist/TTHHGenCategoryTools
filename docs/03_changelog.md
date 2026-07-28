# 03 — Changelog (append-only)

> **목적**: 무엇이 언제 바뀌었나. 새 항목은 **아래에 추가만** 한다 (append-only).
> **대상 독자**: 최신 변경을 따라잡으려는 모든 기여자.
> **상태**: 살아있는 문서 — 마지막 항목 **2026-07-28** (v13.25).
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

