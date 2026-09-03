# 10 — (Legacy) Enriched NanoAOD 아카이브: 사실 기록

> **목적**: 폐기된 **Approach 2** (enriched NanoAOD 사설 생산)에 대해 — 남아있는 파일이 무엇이고, 무엇이 검증됐고 무엇이 검증되지 않았는지를 사실만 기록한다.
> **대상 독자**: `TtbarIdExtender/archive/enriched_nanoaod/`의 파일을 발견하고 "이게 뭐지 / 써도 되나"를 묻는 사람.
> **상태**: **DEPRECATED** (Approach 자체; [04](04_decisions.md) D-DEP1). 파일은 무수정 동결. 이 문서는 legacy 기록 — 읽기 순서상 마지막.
> **관련**: 폐기 사유는 D1, 디버깅 역사 원문은 [legacy/GenSidecar_pre-merge_ARCHITECTURE.md](legacy/GenSidecar_pre-merge_ARCHITECTURE.md) §§10–11.

> ### ⚠️ 2026-09-02 — 이 접근은 D17 로 **부분 부활**했다. 실행 가능한 현행 레시피는 [11_enriched_nanoaod.md](11_enriched_nanoaod.md) 다.
>
> 이 문서는 **첫 시도(v7.2, 2026-05)의 역사 기록**으로만 유효하다. 특히 §4 "되살리려면" 의 ②(FlatTable producer 재작성)·③(IntColumn 확인)은
> **실측으로 불필요함이 드러났다** — 릴리스의 `GlobalVariablesTableProducer` 관용구를 쓰면 새 C++ 이 없다. §1–§3 의 사실 기록은 그대로 유효하다.

## 결론 먼저 (BLUF)

Approach 2 = "중앙 NanoAODv9와 동일한 사설 NanoAOD를 만들되 `Custom_*` branch 4개를 추가"하는 방식. **v7.2(2026-05-28)에서 소규모 byte-identity가 실증**되었으나(공통 1,665개 branch 전부 ratio=1.000), storage 100배·NANO-step fragility 때문에 sidecar로 대체·폐기되었다. 아카이브의 cfg 4편은 **현 패키지에서 실행 불가능**하며(pre-v10 import 경로 + v10에서 제거된 모듈 의존) 실행이 아니라 **provenance 기록**으로 보존한다.

## 1. 아카이브 파일 목록과 각각의 정체 (`TtbarIdExtender/archive/enriched_nanoaod/`)

네 파일 모두 같은 cmsDriver 명령으로 emit된 UL17 NANO step cfg가 뿌리이고, 차이는 "injection(우리 시퀀스 부착 코드) 유무·형태"뿐이다:

| 파일 | 정체 |
|---|---|
| `run_enriched_nanoaod_cfg_v8_baseline.py` | cmsDriver emit **원본 그대로** (injection 없음) — pristine baseline |
| `run_enriched_nanoaod_cfg.py.pre-inject.bak` | v7.2 워크플로가 injection 직전에 남긴 백업 (내용상 pristine emit; 헤더의 `--python_filename`만 다름) |
| `run_enriched_nanoaod_cfg_v8.py` | pristine emit + **plain injection** (`addCustomTtbar` import·호출; 마커 주석 없는 초기 형태) |
| `run_enriched_nanoaod_cfg.py` | pristine emit + **v7.2 마커 injection** — `# === TtbbStudies/NanoExtension v7.2 ... ===` 블록과 `[ttbb-inject]` print (idempotent 재주입 방지용 마커 패턴의 최종형) |

emit에 사용된 cmsDriver 명령(파일 헤더 5행에 원문 보존, 요지):

```
cmsDriver.py nano --step NANO --mc -n 10 --no_exec
  --era Run2_2017,run2_nanoAOD_106Xv2 --conditions 106X_mc2017_realistic_v9
  --eventcontent NANOAODSIM --datatier NANOAODSIM
  --customise Configuration/DataProcessing/Utils.addMonitoring
  --filein root://xrootd-cms.infn.it//store/mc/RunIISummer20UL17MiniAODv2/
           TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/MINIAODSIM/
           106X_mc2017_realistic_v9-v1/280000/04B35B8B-....root
  --fileout file:enriched.root
```

이 옵션 세트의 출처: UL Run2 NanoAODv9 중앙 생산과 동일한 조건으로 사설 생산하기 위한 **PdmV**(Physics Data And Monte Carlo Validation) 그룹의 가이드에 따른 것이며, 실제 값(era/conditions/step)은 중앙 production request 시스템 **McM**에 기록된 NanoAODv9 request의 설정과 대조해 채웠다. ("PMMV"가 아니라 **PdmV**가 정확한 명칭; McM은 PdmV가 운영하는 Monte-Carlo request 관리 DB다.)

## 2. 검증된 사실 (v7.2, 2026-05-28 — 당시 환경에서)

- 환경: CMSSW_10_6_32_patch1, 입력 TTbb_4f_TTToHadronic UL17 MiniAODv2 1파일, **N=10 events**.
- `compareEnrichedToCentral`(전 branch 자동 열거 비교기)로 enriched 출력 vs 대응 중앙 NanoAODv9 대조:
  - **공통 1,665개 branch 전부 sum-ratio = 1.000** (관측 위상수·값 수준의 byte-identity),
  - enriched 전용 branch는 `Custom_*` 4개뿐, 중앙 전용은 (당시 명명의) 원 `genTtbarId` 1개 — 즉 "중앙 + 추가 4개" 구조가 성립.
- 이 결과가 입증하는 것: **release pin(D2) + cmsDriver-emit(무결 baseline) 조합이면 중앙과 동일한 NanoAOD를 사설 재생산할 수 있다.** 이 지식은 ttbarId-extend 시대에도 유효한 자산이다 (예: 언젠가 full enriched가 다시 필요해질 경우의 출발점).

## 3. 검증되지 **않은** 것 (경계 명시 — 과대 해석 금지)

1. **확장 카테고리 값**: v7.2 시점의 split 조건은 아직 sub-code 56 기반(→ v10에서 수정된 버그, [08](08_troubleshooting.md) T-10)이었으므로, 그 검증 run에서 `Custom_Expanded_genTtbarId`가 61/62/71/72를 실제로 만든 적이 **없다**. 1,665-branch 일치는 표준 내용에 대한 것이고, 확장값의 정당성은 이후 **ttbarId-extend 경로에서** 별도로 입증되었다 ([06](06_validation_results.md)).
2. **production 규모**: N=10 단일 파일뿐 — CRAB 규모의 enriched 생산은 수행된 적 없다 (시도 전 폐기).
3. **현재 실행 가능성**: 네 cfg 모두 `from TtbbStudies.NanoExtension.ttbarCategorySequence_cff import addCustomTtbar`를 참조 — (a) 패키지 경로가 pre-v10 (`TtbbStudies`), (b) `ttbarCategorySequence_cff.py`·`TtbarCategoryTableProducer.cc` 자체가 v10에서 패키지에서 제거됨. 따라서 **현 저장소에 대고 cmsRun 하면 ImportError로 실패하는 것이 정상**이다. 아카이브는 무수정 원칙 — "고쳐서 돌아가게" 만들면 그건 검증된 적 없는 새 구성이 된다.
4. 당시 존재했던 emit 자동화 스크립트(`gen_official_cfg.sh`: EL7 컨테이너에서 emit→inject 2-step)는 v10 정리에서 제거되어 **이 아카이브에 없다** — 위 §1의 cmsDriver 명령 원문이 그 대체 기록이다.

## 4. 되살리려면 (참고 절차 — **2026-09-02 SUPERSEDED**: 실제 부활 절차는 [11](11_enriched_nanoaod.md) §2; 아래는 당시의 추정이며 ②·③은 불필요했다)

sidecar가 요구를 못 채우는 상황(예: 확장 id를 branch로 품은 완전한 NanoAOD 파일 자체가 필요)이 오면: ① §1의 cmsDriver 명령으로 해당 era의 cfg를 **새로 emit**, ② 현행 패키지 기준의 attach 함수(현재는 sidecar용 `addTtbarIdExtend`뿐이므로 FlatTable producer를 재작성)를 inject, ③ [09](09_environment.md) §2의 FlatTable 항목(IntColumn 명시) 확인, ④ `compareEnrichedToCentral` 계열로 byte-identity 재검증. — 전부 새 검증 대상이며 v7.2 결과를 재사용할 수 없다.
