# Validation — ttbarId-extend 검증 + patch 추출 도구 (지역 README)

> **목적**: ttbarId-extend ↔ 중앙 NanoAODv9의 전량 byte-identity 검증, 분포 비교, analyzer용 patch 파일 추출의 **복붙 가능한 명령 모음**.
> **대상 독자**: 검증을 (재)수행하거나 새 샘플을 추가하는 사람. 검사 로직·설계는 [../docs/05_architecture.md](../docs/05_architecture.md) §3, 완료된 결과 수치는 [../docs/06_validation_results.md](../docs/06_validation_results.md).
> **상태**: 워크플로 DECIDED. 2026-07-28: **HTCondor 전량 검증 경로 신설·실동작 확인**(§4.0) — 스모크가 인터랙티브와 전 카운터 일치. 2026-06 캠페인(2017)은 인터랙티브 경로로 완료. 2026-07-05: 도구 rename `extractTtNb` → `extractTtbarIdPatch` (로직 무변경, D12) — 이 문서의 명령은 신규약 기준, 구규약 재생산법 병기.
> **환경**: CMSSW 불필요. `root-config`가 PATH에 있는 아무 ROOT 6.x 환경 (KNU Tier3, lxplus 등). 소스는 `Validation/tools/`에 있고 BuildFile.xml이 없어 **scram이 건드리지 않는다**(standalone `make`). 소스를 `src/`가 아니라 `tools/`에 둔 이유는 [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-15.

## 한눈에 보는 워크플로 (번호 없음 — 아래 §0부터가 실행 순서)

```
filelists/{nano,sidecar}<era>/                   (§0 에서 생성)
        │
        ├── ★ 전량 검증 = HTCondor (§4.0, 권장 · 실동작 확인)
        │     sortSplitExtend (전 샘플) → submit_validation_condor.py (job = nano chunk)
        │       → 각 job: matchTtbarIdSorted --json → xrdcp → EOS results/
        │       → aggregate_validation.py: 합산 + DAS 대조 → 샘플별 PASS/FAIL
        │
        ├── 스팟체크 = 인터랙티브 (§1, §3, §4.1)
        │     소샘플: matchTtbarId ─────────────┐
        │     대샘플: sortSplitExtend → Sorted ─┤→ match_<S>.root → plotTtbarCompare
        │                                        │  (byte-identity + 확장 무결성)
        └── 검증 통과 후: extractTtbarIdPatch → ttbarIdPatch_<S>.root  (analyzer 소비, ../docs/07)
```

**전량이면 §4.0 (HTCondor)** 로 간다 — 인터랙티브 직렬은 ~38시간이고 condor 는 ~1.7시간이다.
§1·§3 의 인터랙티브 명령은 샘플 1~2개를 손으로 확인할 때만 쓴다.

의존 순서 두 가지: (1) ttbarId-extend 파일이 먼저 생산돼 있어야 함([../TtbarIdExtender/README.md](../TtbarIdExtender/README.md)); (2) 대샘플은 반드시 `sortSplitExtend` 먼저 → 그 출력 `sorted_<S>/`를 `matchTtbarIdSorted --sorted-dir`로.

> **디렉토리명 주의**: 검증 입력 filelist는 `filelists/nano/`(중앙 NanoAOD)와 `filelists/sidecar/`(이 패키지의 ttbarId-extend 출력)로 나뉜다. `sidecar/`라는 이름은 **v12 rename에서 의도적으로 유지**한 것 — 이 디렉토리의 filelist가 가리키는 실제 Tier3 데이터가 `.../ExtendedTtbarId/sidecar/2017`에 있기 때문이다(rename은 데이터를 옮기지 않는다). 아래 명령의 `filelists/sidecar/` 경로는 오타가 아니다.

## 0. filelist 생성 (검증 캠페인 filelist가 이미 동봉돼 있으면 건너뛴다)

두 개의 생성기가 있다. 둘 다 **`era [SAMPLE_DIR]`** 를 인자로 받는다 (스크립트 상단의
`SAMPLE_DIR_BY_ERA` 가 era별 기본값이며, 2번째 인자로 덮어쓴다). era 를 생략하면 2017 이고
출력은 `nano/`·`sidecar/` 다 — 자세한 규칙은 §0.1. 아래는 2017 기본값(KNU Tier3) 재생성:

```bash
cd filelists
# 중앙 NanoAOD 쪽 (2017 기본 SAMPLE_DIR = ttHH2017UL 중앙 NanoAOD) -> filelists/nano/
python3 make_filelists.py 2017
# ttbarId-extend 쪽 (2017 기본 SAMPLE_DIR = production 출력 위치) -> filelists/sidecar/
python3 make_filelists_miniAOD.py 2017
cd ..
# 결과: filelists/nano/filelist_<S>.txt, filelists/sidecar/filelist_<S>.txt (S = 7샘플)
```

`make_filelists_miniAOD.py`는 출력 파일명이 신규(`ttbarIDExtend*.root`)든 구 production(`sidecar*.root`)이든 **둘 다 매칭**한다([03](../docs/03_changelog.md) v12).

### 0.1 연도 인자 (2026-07-26 신설) — 2017 목록을 덮어쓰지 않는다

두 생성기 모두 **era 를 첫 인자로** 받는다. 인자를 생략하면 2017 이고 출력 디렉토리도
기존과 같다(`nano/`, `sidecar/`). **다른 연도로 돌릴 때 era 를 빼먹으면 커밋된 2017
filelist 를 덮어쓴다** — 그래서 인자를 도입했다.

```bash
cd filelists
# (a) extend 쪽: CRAB 출력 위치를 2번째 인자로 준다 -> sidecar2018/
#     site_config 의 storage_site 가 T3_CH_CERNBOX 이면 실제 위치는 CERN EOS 다.
python3 make_filelists_miniAOD.py 2018 /eos/user/j/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2018

# (b) nano 쪽: 로컬 사본이 없으면 **DAS 에서 직접** 만든다 (7샘플 일괄) -> nano2018/
./make_nano_filelists_das.sh 2018
cd ..
```

`make_nano_filelists_das.sh`(신설)는 master filelist + per-job split +
`nano2018/summary_2018.log` 를 만들고 디렉토리도 스스로 만든다. `matchTtbarId` 는 nano 쪽에서
`run/luminosityBlock/event/genTtbarId` 만 읽으므로 **중앙 NanoAODv9 를 그대로 써도 된다** —
즉 자체 ntuple 생산을 기다리지 않고 새 연도를 검증할 수 있다.

> **`make_filelists.py 2018` 은 2번째 인자가 필수다**: `SAMPLE_DIR_BY_ERA["2018"]` 는 의도적으로
> 빈 문자열이라(로컬 2018 NanoAOD 사본이 없다) 경로 없이 부르면 FATAL 로 멈춘다. 2018 nano
> filelist 는 위 (b) 의 `make_nano_filelists_das.sh 2018` 로 만든다. 로컬 사본이 생기면
> `python3 make_filelists.py 2018 /path/to/local/nanoaod` 로 쓸 수 있다.

> **중복 제출 가드**: `make_filelists_miniAOD.py` 는 샘플별로 CRAB timestamp 디렉토리
> (`<primary>/<tag>/<YYMMDD_HHMMSS>/0000/`)가 **2개 이상이면 즉시 FATAL(exit 3)** 하고 지울
> 경로와 각 파일 수를 출력한다. 같은 dataset 을 두 번 제출하면(부분 task 후 재제출 등) event 가
> 중복돼 한참 뒤 `matchTtbarId` **exit 7** 로만 드러나기 때문이다. 의도적이면
> `ALLOW_MULTI_CRAB_SUBMISSION=1` 로 우회한다.

### 0.2 로컬 산출물 빠른 점검 (grid 전/후 공통)

`scripts/check_extend_invariants.C` (신설)는 ttbarId-extend 파일 하나에 대해 인코딩 계약
7개를 검사한다 — `nAddBJets<=2` 불변 / `==3`→61,62 / `>=4`→71,72 / **sub-code 56 부재** /
prefix 보존 / 원 sub-code∈{53,54,55} / `run==1`, 그리고 61·62·71·72 카운트.

```bash
root -l -b -q 'scripts/check_extend_invariants.C("<ttbarIDExtend 파일>.root")'
```

**PyROOT 를 쓰지 않는 이유**: CMSSW_10_6_32_patch1 의 ROOT 6.14 는 python2 빌드라 python3 에서
`import ROOT` 가 `ImportError: ... (PyInit_libPyROOT)` 로 죽는다(2026-07-27 확인). 매크로는
어느 환경에서든 돈다.

## 1. 빌드 (한 번)

```bash
# root-config 가 PATH 에 오도록 평소 ROOT 환경을 source 한 뒤:
make
# -> bin/makeTtbarHist bin/plotTtbarCompare bin/matchTtbarId bin/matchTtbarIdSorted
#    bin/sortSplitExtend bin/extractTtbarIdPatch bin/scanOrder
```

Makefile은 `tools/*.cc` 와일드카드 — 파일 하나 추가 = 도구 하나 추가.

### 가장 먼저 — 실제로 도는 최소 예시 하나 (tt4b)

빌드가 끝나면 이 한 줄로 파이프라인이 동작하는지 바로 확인한다. `tt4b`는 확장 카테고리(61/62/71/72)가 실제로 채워지는 샘플이라 첫 검증 대상으로 가장 적합하다. **동봉된 filelist를 그대로 쓰므로 경로 수정 없이 복붙 가능**하다(단, filelist 안의 파일들이 실제로 접근 가능한 위치여야 한다):

```bash
# ttbarId-extend ↔ 중앙 NanoAOD per-event byte-identity 검증 (정렬 불필요)
bin/matchTtbarId \
    --extend-filelist filelists/sidecar/filelist_tt4b.txt \
    --nano-filelist   filelists/nano/filelist_tt4b.txt \
    --out match_tt4b.root --label tt4b

# 결과 플롯 (nano vs extend 겹쳐 그리고 per-bin ratio 숫자 표시)
bin/plotTtbarCompare --match match_tt4b.root --out tt4b.png --label tt4b
```

성공 신호: `matchTtbarId` 종료 코드 `0`, 로그에 `disagree = 0` / `unmatched = 0`, 확장 무결성 위반 0. 0이 아니면 §2 표의 exit code로 원인을 안다(5 unmatched / 6 mismatch / 7 dup / 8 확장위반). tt4b 플롯의 `h_extend_Expanded_sub`에서 61/62·71/72 bin이 채워져 있으면 확장이 제대로 된 것.

나머지 6개 샘플로 확장하는 전체 명령은 §3.

## 2. 도구 요약 (무엇이 언제 필요한가)

| 도구 | 역할 | 실패 신호 (exit) |
|---|---|---|
| `matchTtbarId` | **결정판 검증(소샘플)**: ttbarId-extend 전체를 3-key map으로, nano 전 event lookup — id byte-identity + 확장 무결성 | 0 ok / 5 unmatched / 6 mismatch / 7 dup / 8 확장 위반 / 9 run≠1 |
| `sortSplitExtend` | 대샘플 전처리: external sort → `part%05d.root`(50만 row≈16 MB)+`index.txt` | — |
| `matchTtbarIdSorted` | 대샘플용 matchTtbarId (part 1개만 상주) | matchTtbarId와 동일 계약 |
| `extractTtbarIdPatch` | tt+nb row만 추출한 per-sample patch (analyzer 소비용) | 0 / 2 args / 3 filelist / 7 selection 불일치 |
| `makeTtbarHist`+`plotTtbarCompare` | 분포·shape 비교 (per-bin ratio 숫자, 1 이탈은 red) | ratio≠1 sub-code를 stdout 나열 |
| `scanOrder` | filelist 정렬/키범위 진단 (스트리밍) | — |
| `scripts/submit_validation_condor.py` | **전량 검증 오케스트레이션** (§4.0): 정렬 → preflight → 스모크 → 49 job 제출 | preflight 가 FAIL 나열 / job exit 는 §4.0 표 |
| `scripts/aggregate_validation.py` | chunk JSON 합산 + **DAS nevents 대조** → 샘플별 PASS/FAIL 1장 | 0 = 전 샘플 PASS / 1 = 하나 이상 FAIL |

## 3. 복붙용 — 2017 UL 7샘플 검증 전체 (2026-06 캠페인과 동일)

```bash
# ---- 소샘플 4종: matchTtbarId (정렬 불필요) ----
# tt4b
bin/matchTtbarId \
    --extend-filelist filelists/sidecar/filelist_tt4b.txt \
    --nano-filelist    filelists/nano/filelist_tt4b.txt \
    --out match_tt4b.root --label tt4b
bin/plotTtbarCompare --match match_tt4b.root --out tt4b.png --label tt4b
# ttbb_Hadronic
bin/matchTtbarId \
    --extend-filelist filelists/sidecar/filelist_ttbb_Hadronic.txt \
    --nano-filelist    filelists/nano/filelist_ttbb_Hadronic.txt \
    --out match_ttbb_Hadronic.root --label ttbb_Hadronic
bin/plotTtbarCompare --match match_ttbb_Hadronic.root --out ttbb_Hadronic.png --label ttbb_Hadronic
# ttbb_SemiLeptonic
bin/matchTtbarId \
    --extend-filelist filelists/sidecar/filelist_ttbb_SemiLeptonic.txt \
    --nano-filelist    filelists/nano/filelist_ttbb_SemiLeptonic.txt \
    --out match_ttbb_SemiLeptonic.root --label ttbb_SemiLeptonic
bin/plotTtbarCompare --match match_ttbb_SemiLeptonic.root --out ttbb_SemiLeptonic.png --label ttbb_SemiLeptonic
# ttbb_2L2Nu
bin/matchTtbarId \
    --extend-filelist filelists/sidecar/filelist_ttbb_2L2Nu.txt \
    --nano-filelist    filelists/nano/filelist_ttbb_2L2Nu.txt \
    --out match_ttbb_2L2Nu.root --label ttbb_2L2Nu
bin/plotTtbarCompare --match match_ttbb_2L2Nu.root --out ttbb_2L2Nu.png --label ttbb_2L2Nu

# ---- 대샘플 3종: sortSplitExtend 먼저 → matchTtbarIdSorted ----
# TTToHadronic (2.33억 evt, 약 472 part)
bin/sortSplitExtend \
    --filelist filelists/sidecar/filelist_TTToHadronic.txt \
    --out-dir  sorted_TTToHadronic
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTToHadronic \
    --nano-filelist filelists/nano/filelist_TTToHadronic.txt \
    --out match_TTToHadronic.root --label TTToHadronic
bin/plotTtbarCompare --match match_TTToHadronic.root --out TTToHadronic.png --label TTToHadronic
# TTToSemiLeptonic (3.46억 evt, 약 711 part)
bin/sortSplitExtend \
    --filelist filelists/sidecar/filelist_TTToSemiLeptonic.txt \
    --out-dir  sorted_TTToSemiLeptonic
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTToSemiLeptonic \
    --nano-filelist filelists/nano/filelist_TTToSemiLeptonic.txt \
    --out match_TTToSemiLeptonic.root --label TTToSemiLeptonic
bin/plotTtbarCompare --match match_TTToSemiLeptonic.root --out TTToSemiLeptonic.png --label TTToSemiLeptonic
# TTTo2L2Nu (1.07억 evt, 약 214 part)
bin/sortSplitExtend \
    --filelist filelists/sidecar/filelist_TTTo2L2Nu.txt \
    --out-dir  sorted_TTTo2L2Nu
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTTo2L2Nu \
    --nano-filelist filelists/nano/filelist_TTTo2L2Nu.txt \
    --out match_TTTo2L2Nu.root --label TTTo2L2Nu
bin/plotTtbarCompare --match match_TTTo2L2Nu.root --out TTTo2L2Nu.png --label TTTo2L2Nu
```

기대 결과(전 샘플): `disagree = 0, unmatched = 0`, 확장 무결성 위반 0 — 측정 원본은 [../docs/06_validation_results.md](../docs/06_validation_results.md). tt4b 플롯의 `h_Expanded_sub`에서 61/62(tt+bbb)·71/72(tt+4b) bin이 실제로 채워져 있는지 확인 (stitching의 tt+nb 공급원).

## 4. analyzer 소비용 patch 파일 만들기 (extractTtbarIdPatch)

검증이 끝난 ttbarId-extend 파일에서 **tt+nb row만** (`Expanded%100 ∈ {61,62,71,72}` ⇔ `nAddBJets≥3`) 추출한다 — inclusive는 수만, tt4b는 약 188만 row라 파일이 작고, analyzer는 이를 map으로 올려 membership 조회만 한다 (계약: [../docs/07_analyzer_integration.md](../docs/07_analyzer_integration.md)).

```bash
# 신규 규약 (2026-07-05 기본값): ttbarIdPatch_<S>.root, tree "TtbarIdPatch"
for S in tt4b ttbb_Hadronic ttbb_SemiLeptonic ttbb_2L2Nu \
         TTToHadronic TTToSemiLeptonic TTTo2L2Nu; do
  bin/extractTtbarIdPatch \
      --filelist filelists/sidecar/filelist_${S}.txt \
      --out ttbarIdPatch_${S}.root --label ${S}
done

# 구 규약 재생산 (analyzer 가 아직 ttnb_*/TtNb 를 기대하는 경우 — 현행 계약):
#   --out ttnb_${S}.root --out-tree TtNb
```

출력 로그의 `selected tt+nb rows`와 `tt+bbb(61+62) / tt+4b(71+72)` 개수는 같은 샘플의 match 검증 로그와 **정확히 일치**해야 한다 (일치 = 추출 정확). 2026-06에 산출된 7편(구 규약)은 [`lookup/`](lookup/README.txt)에 보존 — 두 규약을 한 디렉토리에 섞지 말 것.

### 4.0 ★ 권장 경로 — HTCondor 전량 검증 (2026-07-28 실동작 확인)

**동작이 실증된 절차다.** 스모크 1 job 이 `matchTtbarIdSorted` 로 `ttbb_2L2Nu` 전량을 검증해
인터랙티브 `matchTtbarId` 와 **모든 카운터가 일치**했다(수치·성능은
[../docs/06_validation_results.md](../docs/06_validation_results.md)). 아래 명령은 그때 실제로 쓴 것이다.

전량을 인터랙티브로 돌리면 **직렬 ~38시간**이다(실측 외삽). 병목은 CPU 가 아니라 중앙 NanoAOD
**~1.2 TB WAN 읽기**이므로 nano chunk 단위로 쪼개면 **49 job 동시 → ~1.7시간**이 된다.

#### 구조 — 무엇이 어디서 도는가

```
[제출: EL9 호스트]                      [실행: EL7 컨테이너 (워커)]
submit_validation_condor.py             run_match.sh  (자동 생성)
  --sort-only  → sortSplitExtend          ├ cvmfs 에서 cmsenv
      (컨테이너 안, 로컬·직렬)             ├ matchTtbarIdSorted --json
  --preflight  → 쓰기 없는 점검            └ xrdcp 로 결과를 EOS 에 직접 올림
  --smoke      → 1샘플 1 chunk                    │
  (플래그 없음) → 49 job                          ▼
                                        EOS: valout2018/results/*.json
                                                 │
aggregate_validation.py  ◀───────────────────────┘
  chunk JSON 합산 + DAS 대조 → 샘플별 PASS/FAIL 1장
```

| 위치 | 이유 |
|---|---|
| `make`, `--sort-only` | **컨테이너 안** (`cmssw-el7` + `cmsenv`) — 바이너리를 빌드·실행 |
| `--preflight`, `--smoke`, 전량 제출 | **EL9 호스트** (`exit` 로 나온 뒤) — `condor_submit` 이 거기 있음 |
| job 실행 | 자동으로 **EL7 컨테이너** (`MY.SingularityImage`, 실측 `os=CentOS 7.9.2009`) |
| condor 스캐폴딩 (`condor_val<era>/`) | **AFS** — submit 파일에 `/eos` 가 있으면 schedd 가 거부 |
| 결과 (`valout<era>/results/`) | **EOS** — job 이 `xrdcp` 로 직접 올림 |

함정의 근거는 [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) **T-23 (6대 함정)**.

#### 0단계 — grid proxy (세션당 1회, 필수)

job 이 nano 를 `root://cms-xrd-global.cern.ch//store/...` 로 읽으므로 proxy 가 **필수**다.
`voms-proxy-init` 의 기본 출력 위치 `/tmp` 는 **노드 로컬이라 schedd 가 못 읽는다** → job 이 HOLD 된다.
그래서 현 디렉토리에 만들고 환경변수로 가리킨다:

```bash
cd $CMSSW_BASE/src/TTHHGenCategoryTools/Validation
voms-proxy-init -voms cms -rfc --valid 192:00 --out $PWD/proxy.cert
export X509_USER_PROXY=$PWD/proxy.cert
```

`proxy.cert` 는 `.gitignore` 에 있다 — **자격증명이므로 커밋하지 않는다.** submitter 는 proxy 를
어디로도 **자동 복사하지 않고**, 없거나 `/tmp` 거나 수명 <1 h 이면 **제출을 거부**하고 위 명령을
출력한다. 컨테이너를 드나들면 `export` 가 초기화되므로 호스트에서 다시 해준다.

#### 1단계 — 빌드 + 정렬 (컨테이너 안)

```bash
cmssw-el7
cd ~/TTHHGenCategoryTools/CMSSW_10_6_32_patch1/src && cmsenv
cd TTHHGenCategoryTools/Validation && make -j4
./bin/matchTtbarIdSorted --help | grep -A1 -- --json     # 새 바이너리 확인

python3 scripts/submit_validation_condor.py --era 2018 --sort-only
#   이미 정렬된 샘플은 index.txt 존재로 SKIP (재실행 안전)
#   실측: 소형 4개 수 초 / TTToHadronic ~26분 / TTToSemiLeptonic ~36분
exit
```

정렬 결과(`sorted<era>/`)는 **입력이므로 지우지 않는다** — 재생성에 ~1시간이 든다.

#### 2단계 — preflight (호스트, 쓰기 없음)

```bash
cd ~/TTHHGenCategoryTools/CMSSW_10_6_32_patch1/src/TTHHGenCategoryTools/Validation
export X509_USER_PROXY=$PWD/proxy.cert
python3 scripts/submit_validation_condor.py --era 2018 --preflight
```

**FAIL 0** 이어야 진행한다. `worker must see EOS (POSIX)` WARN 1건은 정상이다(스모크가 확인한다).
바이너리·filelist·정렬본·proxy 수명·컨테이너 이미지·job 수(49)를 모두 보고한다.

#### 3단계 — 스모크 (1 job) → 소형 4샘플 (4 jobs) → 전량 (49 jobs)

```bash
# 스모크: ttbb_2L2Nu 1 chunk = 샘플 전체. ~21분
python3 scripts/submit_validation_condor.py --era 2018 --smoke
condor_q

# 소형 4샘플: 각 nano <20파일이라 샘플당 1 chunk = 샘플 전체
python3 scripts/submit_validation_condor.py --era 2018 \
    --samples tt4b,ttbb_Hadronic,ttbb_SemiLeptonic,ttbb_2L2Nu

# 전량 49 jobs
python3 scripts/submit_validation_condor.py --era 2018
```

`--dry-run` 을 붙이면 `condor_submit` 없이 `condor_val<era>/match.sub` 만 만든다.

#### 4단계 — 결과 확인

```bash
# job 상태 / 실측 성능
condor_q
condor_history <clusterid> -limit 1 -af RemoteWallClockTime MemoryUsage ExitCode

# job 로그는 AFS (condor 관리), 결과는 EOS (job 이 xrdcp)
grep -E "os=|root-config|parts in index|part loads|matched|unmatched|disagree|exit=" \
     condor_val2018/logs/<label>.*.out
ls /eos/user/j/junghyun/TTHHGenCategoryTools/valout2018/results/

# 합산 + 판정 (샘플별 PASS/FAIL 1장)
# DAS nevents 기준은 이 repo 안에 있다 (data/das_nevents_<era>.json) — 추가 인자 불필요.
python3 scripts/aggregate_validation.py --era 2018 --json-out ~/val_summary_2018.json
```

> **판정 기준 (전부 통과해야 PASS)**: `all chunks present` · **`nano total == DAS nevents`** ·
> `unmatched 0` · `disagree 0` · 보존식(`nAddBJets≥3 == Expanded sub∈{61,62,71,72}`) · 불변식 4종 0 ·
> 전 chunk exit 0.
>
> **`unmatched 0` 만으로는 완결성이 증명되지 않는다** — 데이터 손실에 대해 단조 감소하므로 nano
> 입력을 잃으면 오히려 좋아 보인다(T-21 에서 13% 로 clean pass 가 나왔다). 그래서 **DAS 대조**가
> 1급 기준이고, chunk JSON 이 하나라도 없으면 `all chunks present` 에서 FAIL 한다.
>
> 2017 수치(tt+nb 1,882,170)는 2018 의 기준이 **아니다** — event 수가 다르다.
>
> **DAS 기준값은 `data/das_nevents_<era>.json` 에 이 repo 안에 커밋돼 있다.** 처음엔 다른 repo(`tempTTHH/data/samples_<era>UL.json`)에서 읽었는데, 그건 lxplus 에 체크아웃돼 있지도 않아서 **기준이 조용히 SKIP 되고 PASS 가 났다**(T-23 ⑦). 검증 도구는 자기 기준 데이터를 들고 있어야 한다. `--xsec-db` 로 다른 파일을 줄 수 있지만, **주면 그 파일만 쓴다**(없으면 fallback 없이 FAIL). 불일치가 나면 **그 파일을 고치지 말고** 검증 실행이 불완전한 것으로 봐야 한다.

#### 진단 — exit code 로 원인을 안다

| exit | 의미 | 대응 |
|---|---|---|
| 0 | 정상 | — |
| 4 | nano 파일을 재시도 후에도 못 읽음 | 해당 chunk 재제출 (transient AAA) |
| 6 / 8 | `genTtbarId` 불일치 / 확장 무결성 위반 | **실제 물리 문제** — 조사 필요 |
| 122 | 계산은 정상, EOS 전송 3회 실패 | 숫자는 `.out` 의 `BEGIN/END JSON` 에 있음. 재제출 |
| 123 | `root-config` 없음 (cvmfs/scram 세팅 실패) | `.err` 확인 |
| 124–127 | CMSSW src / sorted `index.txt` / chunk / 바이너리 부재 | 해당 경로 확인 |

job 이 어디서 죽어도 `trap` 이 **스텁 JSON** 을 남기므로, 합산기가 그 chunk 를 **FAILED**(누락이
아니라)로 표시한다. 그리고 각 job 은 JSON 을 stdout 에도 찍으므로 **EOS 전송이 실패해도 숫자는
`.out` 에서 복구된다**.

#### 성능 실측 (2026-07-28, `ttbb_2L2Nu` 1 chunk)

| | 값 |
|---|---|
| wall clock | 1,245 s = **20.8분** (4,792,850 event) |
| peak memory | **489 MB** (request 2000) |
| `part_loads` | **347** (index part 수 = 10) |
| 처리율 | **231 k event/분** |

`part_loads` 가 이상값의 34.7배인 것은 **nano 가 키 순서로 저장돼 있지 않다**는 뜻이다. 감당
가능하다 — event 당 부하가 **part 총개수와 무관하게** 일정하므로(1 load / 13,800 event) 대형에도
같은 처리율을 외삽할 수 있다. 대형 chunk 당 1.3–1.7 h → 49 job 동시 **~1.7 h**.

---


### 4.1 다른 연도(2018 UL) 복붙용 — 인터랙티브 (스팟체크용)

> **전량 검증에는 §4.0 을 쓴다.** 아래는 샘플 1~2개를 손으로 확인할 때만.

§0.1 로 `filelists/sidecar2018/`·`filelists/nano2018/` 를 만든 뒤 실행한다.
`ALLOW_MULTI_CRAB_SUBMISSION` 가드가 통과했다는 것은 샘플마다 CRAB 제출이 하나뿐임을
확인했다는 뜻이다.

```bash
mkdir -p sorted2018 lookup2018 logs2018

# ---- 소샘플 4종 (in-memory) ----
for S in tt4b ttbb_Hadronic ttbb_SemiLeptonic ttbb_2L2Nu; do
  bin/matchTtbarId \
      --extend-filelist filelists/sidecar2018/filelist_${S}.txt \
      --nano-filelist   filelists/nano2018/filelist_${S}.txt \
      --out logs2018/match_${S}_2018.root --label ${S}_2018 \
      2>&1 | tee logs2018/match_${S}_2018.log
  echo "[$S] exit=${PIPESTATUS[0]}" | tee -a logs2018/match_summary_2018.log
done

# ---- 대샘플 3종 (external sort) — 2018 은 2017 대비 최대 +38% ----
#      SemiLep 476M / Hadronic 334M / DiLep 145M (nano 기준)
for S in TTToSemiLeptonic TTToHadronic TTTo2L2Nu; do
  bin/sortSplitExtend --filelist filelists/sidecar2018/filelist_${S}.txt \
      --out-dir sorted2018/${S} 2>&1 | tee logs2018/sort_${S}_2018.log
  bin/matchTtbarIdSorted --sorted-dir sorted2018/${S} \
      --nano-filelist filelists/nano2018/filelist_${S}.txt \
      --out logs2018/match_${S}_2018.root --label ${S}_2018 \
      2>&1 | tee logs2018/match_${S}_2018.log
  echo "[$S] exit=${PIPESTATUS[0]}" | tee -a logs2018/match_summary_2018.log
done

cat logs2018/match_summary_2018.log      # 전부 exit=0 이어야 한다

# ---- patch 추출: analyzer 가 읽는 **구규약 이름**으로 ----
#      loader 는 ttnb_<프로젝트키>.root / tree TtNb 를 찾는다 (src/ExpandedTtbarId.cc).
#      <프로젝트키> 는 짧은 이름이 아니라 NtupleForge sample key 다 → 매핑 필요.
for PAIR in tt4b:TT4b \
            ttbb_Hadronic:TTbb_Hadronic \
            ttbb_SemiLeptonic:TTbb_SemiLep \
            ttbb_2L2Nu:TTbb_DiLep \
            TTToHadronic:TTbar_Hadronic \
            TTToSemiLeptonic:TTbar_SemiLep \
            TTTo2L2Nu:TTbar_DiLep ; do
  S="${PAIR%%:*}"; KEY="${PAIR#*:}"
  bin/extractTtbarIdPatch \
      --filelist filelists/sidecar2018/filelist_${S}.txt \
      --out lookup2018/ttnb_${KEY}.root --out-tree TtNb --label ${KEY}_2018 \
      2>&1 | tee logs2018/patch_${KEY}_2018.log
done
ls -lh lookup2018/

# analyzer 가 보는 위치로 복사 (tempTTHH 는 다른 CMSSW 릴리스이므로 절대경로로)
TEMPTTHH=/afs/cern.ch/user/j/junghyun/CMSSW_14_2_1/src/tempTTHH   # ← 실제 경로로
mkdir -p "$TEMPTTHH/DerivedCorr/expandedTtbarId/2018"
cp lookup2018/ttnb_*.root "$TEMPTTHH/DerivedCorr/expandedTtbarId/2018/"
```

**합격 기준**: 모든 샘플 `exit=0` (= disagree 0 / unmatched 0 / 확장 무결성 위반 0).
**2017 의 tt+nb 기대 수치(1,882,170 = 61/62 1,585,810 + 71/72 296,360)는 2018 의 기준이
아니다** — event 수 자체가 다르다. 결과 수치는 [`../docs/06_validation_results.md`](../docs/06_validation_results.md)
에 **append** 한다.

> **MiniAOD ⊃ NanoAOD**: 중앙 NanoAOD 는 부모 MiniAOD event 의 일부를 떨어뜨린다
> (실측 2018: TTbar_Hadronic 343,248,000 → 334,206,000, 2.6%). extend 는 MiniAOD 기반이라
> nano 보다 row 가 많고, `matchTtbarId` 는 nano 를 순회하므로 `unmatched 0` 기준은 그대로
> 유효하다(남는 extend row 는 조회되지 않음). 다만 **완결성 점검 기준 수치**는 extend=MiniAOD,
> ntuple/prescan=NanoAOD 로 구분해야 한다.

## 5. 분포 비교 (선택) — 로컬 또는 HTCondor

```bash
# 로컬 (한 샘플, filelist 한 쌍)
bin/makeTtbarHist --filelist filelists/nano/filelist_tt4b.txt \
                  --mode nano --out hist_nano_tt4b.root --label tt4b
bin/makeTtbarHist --filelist filelists/sidecar/filelist_tt4b.txt \
                  --mode extend --out hist_extend_tt4b.root --label tt4b
bin/plotTtbarCompare --extend hist_extend_tt4b.root --nano hist_nano_tt4b.root \
                     --out tt4b_ttbarId_compare.png --label tt4b

# HTCondor 병렬 (파일 단위 job) + 병합
python3 scripts/submit_hist_condor.py \
    --filelist-dir filelists/nano --mode nano \
    --processes tt4b,TTToSemiLeptonic,ttbb_SemiLeptonic \
    --work-dir condor_hist_nano --out-prefix hist_nano
python3 scripts/submit_hist_condor.py \
    --filelist-dir filelists/sidecar --mode extend \
    --processes tt4b,TTToSemiLeptonic,ttbb_SemiLeptonic \
    --work-dir condor_hist_extend --out-prefix hist_extend
scripts/merge_hists.sh condor_hist_nano/outputs    merged hist_nano
scripts/merge_hists.sh condor_hist_extend/outputs merged hist_extend
for P in tt4b TTToSemiLeptonic ttbb_SemiLeptonic; do
  bin/plotTtbarCompare --extend merged/hist_extend_${P}.root \
      --nano merged/hist_nano_${P}.root --out ${P}_ttbarId_compare.png --label ${P}
done
```

분포 비교는 **보조 지표**다 — 모집단 차이(예: TTToSemiLeptonic의 NanoAOD production drop 2.68% → 균일 1.027 offset)가 ratio에 섞이므로, 판정은 per-event match가 한다.

## 6. 부속

- `scripts/das_lineage.py` — DAS file-level parent/child lineage 조회 (grid proxy + dasgoclient 필요). **사용 이력 미확인**([../docs/01_status.md](../docs/01_status.md) O3) — 신뢰 전 1회 동작 확인.
- `scanOrder` — 새 샘플에서 "정렬돼 있으니 map 없이 되겠지" 같은 가정을 하기 전에 실측:
  `bin/scanOrder --filelist <fl> [--tree Events] [--max-files N] [--csv out.csv]`.
  (인식하는 플래그는 이 4개 + `-h` 뿐이다. 모르는 플래그를 주면 `ERROR: unknown arg` 로 exit 2.)
- 문제 발생 시: [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) (특히 T-8 타입, T-12 2-key 중복).
