# Validation — ttbarId-extend 검증 + patch 추출 도구 (지역 README)

> **목적**: ttbarId-extend ↔ 중앙 NanoAODv9의 전량 byte-identity 검증, 분포 비교, analyzer용 patch 파일 추출의 **복붙 가능한 명령 모음**.
> **대상 독자**: 검증을 (재)수행하거나 새 샘플을 추가하는 사람. 검사 로직·설계는 [../docs/05_architecture.md](../docs/05_architecture.md) §3, 완료된 결과 수치는 [../docs/06_validation_results.md](../docs/06_validation_results.md).
> **상태**: 워크플로 DECIDED (2026-06 캠페인에서 그대로 사용). 2026-07-05: 도구 rename `extractTtNb` → `extractTtbarIdPatch` (로직 무변경, D12) — 이 문서의 명령은 신규약 기준, 구규약 재생산법 병기.
> **환경**: CMSSW 불필요. `root-config`가 PATH에 있는 아무 ROOT 6.x 환경 (KNU Tier3, lxplus 등). 소스는 `Validation/tools/`에 있고 BuildFile.xml이 없어 **scram이 건드리지 않는다**(standalone `make`). 소스를 `src/`가 아니라 `tools/`에 둔 이유는 [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) T-15.

## 0. 한눈에 보는 워크플로

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

두 개의 생성기가 있다. 각자 스크립트 상단의 `SAMPLE_DIR`를 **본인의 실제 데이터 위치로** 고친 뒤 인자 없이 실행한다(현재 값은 KNU Tier3 기준):

```bash
cd filelists
# 중앙 NanoAOD 쪽 (SAMPLE_DIR = ttHH2017UL 중앙 NanoAOD) -> filelists/nano/
python3 make_filelists.py
# ttbarId-extend 쪽 (SAMPLE_DIR = production 출력 위치) -> filelists/sidecar/
python3 make_filelists_miniAOD.py
cd ..
# 결과: filelists/nano/filelist_<S>.txt, filelists/sidecar/filelist_<S>.txt (S = 7샘플)
```

`make_filelists_miniAOD.py`는 출력 파일명이 신규(`ttbarIDExtend*.root`)든 구 production(`sidecar*.root`)이든 **둘 다 매칭**한다([03](../docs/03_changelog.md) v12).

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
- `scanOrder` — 새 샘플에서 "정렬돼 있으니 map 없이 되겠지" 같은 가정을 하기 전에 실측: `bin/scanOrder --filelist <fl> --report-every 5000000`.
- 문제 발생 시: [../docs/08_troubleshooting.md](../docs/08_troubleshooting.md) (특히 T-8 타입, T-12 2-key 중복).
