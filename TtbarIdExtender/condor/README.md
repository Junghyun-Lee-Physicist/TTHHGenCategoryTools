# condor/ — enriched NanoAOD 검증 배치 (D17 gate 3 · 4 · 5)

lxplus 에서 손으로 돌리던 검증(`docs/11_enriched_nanoaod.md` §3)을 HTCondor 로 한 번에 돌린다.
입력·출력·로그는 전부 **EOS** (`/eos/user/j/junghyun/ttHH/`) — lxplus `/tmp` 는 노드별이라 쓰지 않는다.

```
config.sh          경로·이벤트 수·Condor 자원. 편집은 여기만.
submit.sh          lxplus 호스트 셸(컨테이너 밖)에서 실행. proxy 확인 → TT4b MiniAOD 파일 DAS 해석 →
                   MiniAOD 를 EOS miniaod/ 에 선(先)복사 → JDL 렌더 → condor_submit
runTask.sh         worker. 입력을 scratch 로 → cmsDriver/cmsRun → 비교·판정 → EOS 로 결과 복사
check_expanded.py  Expanded_genTtbarId 규칙(02_physics §3) 검사 + 71/72 존재 확인   (gate 3)
judge_compare.py   NtupleForge compare_v9_v15.py --json 요약을 PASS/FAIL 로 판정
submissions/<TAG>/ 제출마다 스크립트 사본·JDL·proxy 사본·condor .out/.err/.log  (git 제외)
```

## 태스크

| task | 릴리스 | 하는 일 | PASS 조건 |
|---|---|---|---|
| `control_v15_200` | 15_0_18 | **음성 대조군**: 같은 TTbb 200 ev 를 **같은 노드에서** 중앙 cfg(plain)와 우리 cfg(ours)로 연달아 | (b) plain 대 ours(같은 노드) **비트 동일**, 우리 3 컬럼만 추가 · (a) plain 대 중앙 v15: 스키마 동일, 값 차이는 허용 부류에만 · (c) plain 대 lxplus smoke(다른 머신): NN 출력의 마지막 ULP 만 |
| `timing_v15_2k` | 15_0_18 | 우리 cfg, TTbb 2000 ev, 시간 측정 (gate 4 입력) | 09-02 lxplus 의 2k 파일과 NN 출력 ULP 외 동일(다른 머신) · 중앙 v15 와 허용 부류 외 불일치 0 (gate 5, 2000 ev) |
| `tt4b_v9_2k` | 10_6_32_patch1 | 우리 v9 cfg, TT4b 2000 ev | 규칙 위반 0, 71/72 존재 (gate 3) |
| `tt4b_v15_2k` | 15_0_18 | 같은 TT4b 파일, v15 | 같음 (15_0_X 에서도 71/72) |

**허용 부류** (`config.sh` `ALLOW_REPRO` / `ALLOW_XMACHINE`; 근거 docs/11 §4, docs/08 T-35) — 값이 다를 수 있는 곳은 세 가지뿐이다:

| 부류 | 원인 | 언제 나오나 |
|---|---|---|
| `*_area` (`Jet/FatJet/SubJet/CorrT1METJet`) | FastJet ghost-area 난수 — job 의 event 이력을 따른다 | 다른 job 이력(중앙 생산)과 비교할 때. 같은 event 순서면 다른 노드라도 동일 |
| `HTXS_{Mjj,V_pt,dPhijj,ptHjj}` | 수학적 0 의 float 잔차 (0 vs 3×10⁻⁵) | 위와 같음 |
| `Tau_rawDeepTau*`, `boostedTau_rawBoostedDeepTau*` | NN 추론의 마지막 비트가 CPU 종류(lxplus/중앙 vs lxbatch)에 따라 다름; 저장 정밀도(10-bit mantissa) 한 칸을 넘는 값만 보임 | **다른 머신**에서 만든 파일과 비교할 때 (2000 ev 중 3 값) |

2026-09-03 (lxplus, 2000 ev 대 중앙: 정수 불일치 0, area/HTXS 만 38 ev) 과 2026-09-07 (lxbatch: DeepTau 3 값 추가)
의 실측이다. **같은 노드·같은 cfg·같은 event 는 비트 동일이어야 하고 예외를 두지 않는다** — 그것이 (b) 이고,
이 부류 밖의 불일치가 하나라도 나오면 FAIL 이다. 정수 branch 는 어떤 비교에서도 다르면 안 된다.

## 실행

```bash
# lxplus 호스트 (컨테이너 밖). 두 CMSSW 영역은 이미 scram b 되어 있어야 한다.
voms-proxy-init --voms cms --valid 72:00
cd ~/TTHHGenCategoryTools/CMSSW_10_6_32_patch1/src/TTHHGenCategoryTools/TtbarIdExtender/condor
./submit.sh -n            # dry run: proxy, DAS 해석, EOS 참조 파일, JDL 까지만
./submit.sh               # 제출 (기본 4 task). -T "tt4b_v9_2k" 로 부분 제출, -t TAG 로 태그 지정
condor_q -nobatch
```

전제: `$TTHH_EOS/central/central_ttbb_v15_e10ceebb.root`, `$TTHH_EOS/enriched/enriched_v15_smoke.root`,
`$TTHH_EOS/enriched/enriched_v15_2k.root` 가 있어야 한다 (09-03 에 복사해 둔 것). submit.sh 가 확인한다.

OS: v15 task 는 `MY.WantOS="el8"` 위에서 바로 cmsenv (TopCPVGenCategorizer/condor 와 같은 방식).
v9 task 는 el9 호스트로 보내고 `runTask.sh` 가 자기 OS 가 el7 이 아니면 `/cvmfs/cms.cern.ch/common/cmssw-el7`
안에서 자신을 다시 실행한다 — lxplus 에서 쓰는 wrapper 그대로.

## 결과 읽기

```
$TTHH_EOS/logs/<TAG>/<task>.summary.txt   PASS/FAIL 한 줄씩 + verdict  ← 먼저 본다
$TTHH_EOS/logs/<TAG>/<task>.log           worker 전체 로그: 환경(host, CPU, CMSSW, repo commit), 입력 staging,
                                          cmsDriver 명령, cmsRun exit/%MSG-e/%MSG-w 요약과 tail, Timing 요약,
                                          스키마, 비교기 출력, 판정
$TTHH_EOS/logs/<TAG>/<task>.cmsRun.log    cmsRun 원문 로그
$TTHH_EOS/logs/<TAG>/<task>_cfg.py        실제로 돈 cfg (provenance)
$TTHH_EOS/json/<TAG>/*.json               compare_v9_v15.py 요약 (문서 11 §3 의 증거로 붙일 것)
$TTHH_EOS/enriched/<TAG>/*.root           출력 NanoAOD
submissions/<TAG>/logs/<task>.*.out       condor stdout — job 이 끝난 뒤에 쓰인다 (아래 '주의')
```

exit code: 0 = 전부 PASS, 1 = 어떤 검사 FAIL, 2 = 인프라 오류(staging·cmsenv 실패 등).
gate 4 숫자는 `timing_v15_2k.log` 의 `Event Throughput` / `Total loop` / `loop rate` 줄이다
(startup 을 뺀 event-loop 처리율; `units_per_job` 산정에 이것을 쓴다).

## 주의 — CERN batch (2026-09-07 실측, docs/08 T-33)

- **stdout/err 스트리밍 금지.** `stream_output`/`stream_error = True` 는 2025-11 말부터 `condor_submit` 이
  거부한다 (schedd·파일시스템 부하). 다른 repo 의 JDL 을 복사하기 전에
  [batchdocs changelog](https://batchdocs.web.cern.ch/changelog/index.html) 를 본다.
  실행 중 진행 상황은 condor `.out` 이 아니라 worker 가 EOS 로 복사하는 로그로 본다.
- OS 는 `MY.WantOS = "el8" | "el9"`. el7 이 필요한 v9 job 은 el9 호스트로 보내고 job 안에서
  `/cvmfs/cms.cern.ch/common/cmssw-el7 --command-to-run` 으로 자기를 다시 실행한다.
- `submit.sh -n` 은 JDL 렌더까지만 검사한다 — schedd 정책 위반은 `condor_submit` 이 되어서야 드러나고,
  submit.sh 는 첫 JDL 이 거부되면 멈추므로 뒤 OS 그룹도 제출되지 않는다. 고친 뒤 그대로 재실행하면
  새 TAG 로 다시 렌더한다 (선복사는 캐시).
- 로그·JDL 은 AFS(`submissions/<TAG>/`)에, 데이터·결과는 EOS 에. EOS 쓰기는 proxy 로 `xrdcp`(eosuser),
  실패하면 fuse `cp` 로 넘어간다.

## 태스크 추가

`runTask.sh` 의 task table(`case "$TASK"`)에 한 줄(OS·영역·conditions·이벤트 수·customise·출력명), 필요하면
`3. checks per task` 에 판정 블록, `submit.sh` 의 OS 그룹 분류에 이름 추가. 입력 파일은 LFN 으로 주고
`stage_lfn` 이 EOS 캐시를 먼저 본다.
