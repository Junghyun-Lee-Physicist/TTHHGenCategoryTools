# Validation — ttbarId-extend 검증 + patch 추출 도구 (지역 README)

> **목적**: ttbarId-extend ↔ 중앙 NanoAODv9의 전량 byte-identity 검증, 분포 비교, analyzer용 patch 파일 추출의 **복붙 가능한 명령 모음**.
> **대상 독자**: 검증을 (재)수행하거나 새 샘플을 추가하는 사람. 검사 로직·설계는 [../docs/05_architecture.md](../docs/05_architecture.md) §3, 완료된 결과 수치는 [../docs/06_validation_results.md](../docs/06_validation_results.md).
> **상태**: 워크플로 DECIDED (2026-06 캠페인에서 그대로 사용). 2026-07-05: 도구 rename `extractTtNb` → `extractTtbarIdPatch` (로직 무변경, D12) — 이 문서의 명령은 신규약 기준, 구규약 재생산법 병기.
> **환경**: CMSSW 불필요. `root-config`가 PATH에 있는 아무 ROOT 6.x 환경 (KNU Tier3, lxplus 등). 소스는 `Validation/tools/`에 있고 BuildFile.xml이 없어 **scram이 건드리지 않는다**(standalone `make`). 소스를 `src/`가 아니라 `tools/`에 둔 이유는 [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-15.

## 한눈에 보는 워크플로 (번호 없음 — 아래 §0부터가 실행 순서)

```
filelists/{nano,sidecar}/filelist_<S>.txt        (검증 캠페인 실사용본 동봉)
        │
        ├── 소샘플(≲5천만 evt): matchTtbarId ──────────────┐
        ├── 대샘플: sortSplitExtend → matchTtbarIdSorted ──┤→ match_<S>.root → plotTtbarCompare
        │                                                   │   (byte-identity + 확장 무결성 판정)
        └── 검증 통과 후: extractTtbarIdPatch → ttbarIdPatch_<S>.root  (analyzer 소비, ../docs/07)
```

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

### 4.1 다른 연도(2018 UL) 복붙용 — 검증 + patch 추출 한 번에

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
