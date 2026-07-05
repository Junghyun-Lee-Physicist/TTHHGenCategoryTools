# 08 — Troubleshooting: 증상 → 원인 → 해결

> **목적**: 개발·운영 중 실제로 발생했던 문제의 전 목록. 같은 문제를 두 번 디버깅하지 않기 위함.
> **대상 독자**: 빌드/실행/CRAB/검증에서 뭔가 깨진 사람.
> **상태**: 살아있는 문서 — 항목은 해결 시마다 추가. 마지막 갱신 2026-07-05.
> **관련**: 환경 기인 항목의 일반화는 [09_environment.md](09_environment.md), 원 기록은 [legacy/](legacy/) 동결 문서들.

형식: **T-n | 증상 | 원인 | 해결** (+ 재발 방지가 코드에 어떻게 박혔는지).

## 생산 (GenSidecar / 그 전신)

- **T-1** | cmsRun 콘솔이 `JetPtMismatch`/`MissingJetConstituent`/`NullTransverseMomentum` 경고로 도배 | `prunedGenParticles` 기반 재클러스터링 — miniAOD `slimmedGenJets`는 constituent가 일부 truncate됨 | 재클러스터링 자체를 중단하고 miniAOD의 pre-stored `slimmedGenJetsFlavourInfos` 사용 → 경고 원천 소멸.
- **T-2** | 자릿수 분해에서 10000자리(c-from-W)만 38% 일치 | 직접 재구현이 `cHadFromTopWeakDecay` flag를 단독 신뢰 — 표준 plugin은 mother-chain으로 W ancestor를 재추적 | 재구현 포기, 표준 `categorizeGenTtbar` 호출 (D3) → 전 자릿수 100%.
- **T-3** | `ModuleNotFoundError: ...GenTtbarCategorizer_cfi` / InputTag 불일치 | cfi 파일명은 lowercase `categorizeGenTtbar_cfi`; 출력은 라벨된 `("categorizeGenTtbar","genTtbarId")` | `PhysicsTools.NanoAOD.ttbarCategorization_cff` 통째 import (canonical 경로).
- **T-4** | 10_6_X에서만 터지는 5종: non-ASCII SyntaxError / `Process has no attribute MessageLogger` / MessageLogger 새 category 무시 / `tuple has no attribute find` / `-Werror=unused-variable` | Python 2 + 옛 cmssw의 규약 차이 | PEP 263 헤더, `process.load("FWCore.MessageService.MessageLogger_cfi")`, `categories.append(...)`(hasattr 가드), 명시적 `cms.InputTag(...)`, unused 변수 제거. 일반화 표: [09](09_environment.md) §2.
- **T-5** | hand-written NANO cfg에서 `ProductNotFound`(jetCorrFactorsAK8 → finalBoostedTaus → bitmapVIDForEle)가 **연쇄** 발생, 이후 `unsupported type`의 원인 판별 불능 | customizer/era-modifier 적용 시점·등록 순서를 손으로 재현하는 것의 본질적 fragility | **cmsDriver-emit + inject 패턴**으로 전환 (같은 customizer가 cmsDriver cfg에서는 정상). ttbarId-extend(Approach 3)로 이행하면서 이 failure class 자체가 소멸 (D1). `addColumnValue<int>`의 10_6_X 함정(4번째 인자 `IntColumn` 명시 필요)은 enriched 계열에만 해당 — [10](10_enriched_nanoaod_archive.md).
- **T-6** | TrigReport "Unrunnable schedule" | Sequence `+=`로 task 결합 시도 | `Task.associate()` 사용 (10_6_X scheduling 규약).
- **T-7** | ttbarId-extend tree가 `ttbarIdSidecar/Events`에 생김 → 비교기 default 실패, friend-tree prefix 필요 | TFileService의 모듈-label 디렉토리 격리 | analyzer가 자기 TFile을 열어 top-level `Events` 생성 (D5). 부수: `tree->Write(); file->Write();` 순서가 tree를 **두 번**(cycle 2개) 쓰던 것도 `Write("",kOverwrite)`로 해결.
- **T-8** | 비교기 join이 0 entries | `event` branch를 `uint64_t` 등으로 SetBranchAddress — ROOT는 `ULong64_t`(type-id 'l')를 엄격 구분 | `ULong64_t` 명시. [00_PROMPT](../00_PROMPT.md) §8의 타입 계약으로 고정.
- **T-9** | GenJet η 일치도가 ~86%로 낮음 | NanoAOD `GenJet_eta`는 precision=12 mantissa 양자화(상대 step ~2.44e-4) — 절대 tol 1e-4가 그보다 빡빡 | relative-aware tol `5e-4·max(1,|a|)` → 즉시 100%. (pT는 precision=-1이라 절대 tol 충분.)
- **T-10** | tt+bbb/tt+4b가 **한 번도** 생성 안 됨 (통계 부족으로 오인) | split 조건이 `genTtbarId%100==56`에 결합 — 표준은 56을 절대 만들지 않음 (TWiki Example 2 혼동) | tt4b 950만 event cross-tab으로 확정(56=0건, nAddBJets≥3=188만 건) 후 조건을 `nAddBJets>=3`으로 교체 (D4). 검증 도구도 같은 규칙(iff)을 검사하도록 갱신됨.
- **T-11** | CRAB 제출이 `'year' not registered / Unknown variable`로 즉사 | enriched용 submitter를 복사하며 `pyCfgParams=["year=..."]`가 남음 — ttbarId-extend cfg는 `year` 미등록 | `pyCfgParams=["outputFile=ttbarIDExtend.root"]` + `JobType.outputFiles=["ttbarIDExtend.root"]` 선언. (VarParsing의 `_numEventN` suffix 우려는 이후 7샘플 production 성공으로 실증 해소 — 산출 filelist가 `Validation/filelists/ttbarId-extend/`에 존재.)

## 검증 (Validation)

- **T-12** | 2-key(run,event) map 적재가 duplicate abort — TTToSemiLeptonic에서 15.27M건 | MC event 번호는 lumisection 내에서만 유일 (같은 run·event, 다른 lumi) | 3-key `(run,lumi,event)` (D7). 중복 감지 abort는 설계된 안전장치 — 끄지 말 것. / 대용량 map ~20 GB 초과 → external sort 경로 (D8, T와 별개 성능 항목). / lumi-범위 chunking 아이디어는 `scanOrder` 실측(파일 내부 미정렬 + lumi 범위 중첩)으로 기각.

## 병합·rename 이후 (v11, 예방적 항목)

- **T-13** | (예상) 구 `crab_*` 프로젝트에 `--resubmit`이 실패하거나 엉뚱한 cfg를 집음 | CRAB 프로젝트 디렉토리는 제출 당시의 pset 경로(`.../NanoExtension/...`)를 기억 | 구(pre-v11) 태스크의 resubmit은 구 체크아웃에서 수행; 신규 제출은 새 경로로. `requestName`이 겹치면 `site_config.yaml`의 `request_name_tag`를 bump.
- **T-14** | (예상) `preflight.py`가 "plugin .so missing" | rename 후 stale build area | `scram b clean && scram b -j8` — plugin lib 이름이 `pluginTTHHGenCategoryToolsTtbarIdExtender*`로 재생성되는지 확인 ([01](01_status.md) O1).

## v12 첫 lxplus 빌드 (실측)

- **T-15** | `scram b`가 `Validation/`을 컴파일하려다 `fatal error: TChain.h / TCanvas.h: No such file or directory`로 전량 실패 (2026-07-05 첫 빌드) | scram은 `<Package>/src/*.cc`를 **BuildFile.xml이 없어도** 자동으로 패키지 라이브러리로 컴파일하려 든다. `Validation/src/`가 바로 그 특수 경로에 걸려, scram이 ROOT include 경로(`root-config --cflags`) 없이 컴파일 → ROOT 헤더 못 찾음. (로그의 `Entering library rule at TTHHGenCategoryTools/Validation` + `.../Validation/src/TTHHGenCategoryToolsValidation/*.cc.o`가 증거.) | **소스 디렉토리를 `Validation/src/` → `Validation/tools/`로 rename**하고 Makefile의 `SRCDIR := tools`로 변경. `tools/`는 scram의 자동 컴파일 대상이 아니므로 scram이 완전히 무시하고, standalone `make`만 `tools/*.cc`를 빌드한다. 이것이 [04](04_decisions.md) D14에서 예고한 fallback의 실제 적용. — plugin 패키지(`TtbarIdExtender/`)는 정상 컴파일됐으므로 subsystem/패키지/plugin-lib 이름 자체는 문제 없음이 이 빌드로 확인됨.
- **T-15 부수**: 같은 빌드에서 `-Wcomment`(multi-line comment) 경고가 여러 도구에서 발생 — `//` 주석 줄 끝의 `\`(예시 명령 줄바꿈)를 컴파일러가 comment continuation으로 해석. 무해하나, 주석 예시에서 줄 끝 `\`를 제거해 정리함.
- **T-16** | 첫 CRAB 제출이 `Cannot find CMSSW configuration file .../run_ttbarIdExtend_cfg.py`로 전량 실패, 이후 재제출은 `[skip] project dir already exists` / `--status`·`--resubmit`은 `Cannot find .requestcache file` | (1) `psetName`이 CWD-상대 경로여서 `src/`가 아닌 데서 실행 시 못 찾음(v12.2에서 절대경로로 수정). (2) 실패한 제출도 `crab_projects/crab_<req>/` 껍데기(`crab.log`·`inputs`·`results`만, `.requestcache` 없음)를 만들고, submit은 이 디렉토리가 있으면 skip, status/resubmit은 `.requestcache`가 없어 실패 | psetName 절대경로 수정본으로 교체 후: **빈 프로젝트 디렉토리 삭제** `rm -rf crab_projects/crab_*_2017_extend` → `source /cvmfs/cms.cern.ch/common/crab-setup.sh`(세션당 1회, `CRABClient` 로드) → `python3 crab/submit_ttbarIdExtend.py --process TT4b --max-files 5`로 스모크. `.requestcache`가 생겨야 제출 성공 = 이후 `--status`/`--resubmit` 동작.
- **T-17** | CRAB `--status`가 전 태스크 `Status on the CRAB server: SUBMITREFUSED` + `Permission denied ... write check at destination site fails` + `gfal-copy ... davs://eoscms.cern.ch:443/eos/cms/store/user/... HTTP 403 : Permission refused` | `storage_site: T2_CH_CERN` + `out_lfn_base: /store/user/...` 조합이 목적지를 **CMS 실험 EOS** `/eos/cms/store/user/`로 보냈고, 그 영역은 별도 CMS-EOS 쓰기 활성화가 필요해 stageout 사전 write-check가 403으로 거부됨. (task는 CRAB 서버까지 등록됐으나 grid로 안 나감 = SUBMITREFUSED. `--status`가 이 정보를 정상 조회한 것이므로 `[status ok]`는 맞음.) | lxplus **개인 EOS**(`/eos/user/<u>/<user>/`)로 보내려면 `storage_site: T3_CH_CERNBOX` 로 바꾼다(v12.4). 제출 전 `crab checkwrite --site=T3_CH_CERNBOX --lfn=/store/user/<user>`로 권한 확인. SUBMITREFUSED된 task의 프로젝트 디렉토리(`crab_projects/crab_*`)는 재제출 전에 지운다(`rm -rf crab_projects/crab_*_2017_extend`) — 안 지우면 submit이 skip. CMS EOS(`/eos/cms/...`)가 꼭 필요하면 `crab checkwrite`로 확인 후 활성화를 CMS computing에 요청.
