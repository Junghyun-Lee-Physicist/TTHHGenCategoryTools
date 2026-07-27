# 03 — Changelog (append-only)

> **목적**: 무엇이 언제 바뀌었나. 새 항목은 **아래에 추가만** 한다 (append-only).
> **대상 독자**: 최신 변경을 따라잡으려는 모든 기여자.
> **상태**: 살아있는 문서 — 마지막 항목 **2026-07-27** (v13.7).
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
  2,097 jobs / job 당 ~9분.
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
