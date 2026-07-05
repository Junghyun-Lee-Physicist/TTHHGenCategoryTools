# TtbarIdHistCompare

Standalone tools to compare the **distribution** of the ttbar+HF
categorization id (`genTtbarId`) between two sources, per physics process:

* a **nano** source - central NanoAOD, or a slimmedNtuple that preserves the
  NanoAOD `genTtbarId` branch and structure, and
* a **sidecar** source - the gen-level ttbar-Id sidecar (which additionally
  carries the extended `Expanded_genTtbarId`: events with >= 3 additional b-jets have their
  sub-code reclassified into 61/62 (tt+bbb) / 71/72 (tt+4b), plus the
  `nAddBJets` / `nAddBJetsMulti` counts the reclassification is keyed on).

If both sources were run over the same event set, the `genTtbarId`
distributions must coincide bin-by-bin (ratio = 1.0 everywhere, shown as per-bin numbers). The plot also
overlays the sidecar `Expanded_genTtbarId` so the extended sub-codes are visible.

This project is **independent of any CMSSW package**: it builds with a plain
Makefile against a ROOT installation (`root-config` on `PATH`) - the same ROOT
environment you use to run the jobs.

---

## 0. Workflow at a glance

There are two separate paths. **No tool draws a plot by itself except
`plotTtbarCompare`** - the others produce ROOT files, and `plotTtbarCompare`
turns those into images. So the order is always: produce ROOT histograms ->
then plot.

**Path A - strict per-event validation (recommended for ttbb / tt4b / ttHH):**

```
make
  -> bin/matchTtbarId, bin/plotTtbarCompare, ...

bin/matchTtbarId --sidecar-filelist <S> --nano-filelist <N> --out match_<P>.root
  -> prints the numeric check to the screen (agree/disagree, nAddBJets>=3 -> 61/62/71/72
     conservation); this is the actual validation result
  -> writes histograms into match_<P>.root   (NO image yet, just a ROOT file)

bin/plotTtbarCompare --match match_<P>.root --out <P>.png
  -> reads match_<P>.root and produces the image   (the histogram is drawn here)
```

So `matchTtbarId` does NOT draw a plot; it validates (numbers on screen) and
saves histograms to a `.root`. `plotTtbarCompare --match` then draws them. The
split lets you run the heavy matching on a worker and plot later, locally.

**Path B - distribution (shape) comparison only:**

```
make
bin/makeTtbarHist --filelist <nano>    --mode nano    --out hist_nano_<P>.root
bin/makeTtbarHist --filelist <sidecar> --mode sidecar --out hist_sidecar_<P>.root
bin/plotTtbarCompare --sidecar hist_sidecar_<P>.root --nano hist_nano_<P>.root --out <P>.png
```

Path B compares whole-sample distributions (counts/shape). Path A matches event
by event and is the definitive check; it is also what validates the extended
`Expanded_genTtbarId`. For the analysis, Path A on the signal samples is the one to run.

(At full scale, `makeTtbarHist` for Path B can be parallelized with
`scripts/submit_hist_condor.py`; `matchTtbarId` for Path A is run per process,
see Sections 4 and 6b.)

---

## 0-K. 대용량 ttbar 검증 (메모리 문제 해결) — 한국어

`matchTtbarId` 는 sidecar **전체**를 메모리(map)에 올립니다. ttbb / tt4b / ttHH
처럼 작은 샘플은 문제없지만, ttbar inclusive (예: TTToHadronic 약 2.36억 event)
는 ~20GB 를 넘겨 Tier3 worker 에서 돌지 않습니다.

해결: sidecar 를 **한 번 (run, lumi, event) 로 정렬해서 작은 part 파일들로
쪼개 둡니다.** 그러면 검증할 때 전체를 메모리에 안 올리고, 각 nano event 가
속한 part 하나(약 16MB)만 열어서 비교합니다. 정렬은 external sort 라 정렬
과정에서도 메모리를 적게 씁니다 (전체를 한 번에 안 올림).

```bash
make    # bin/sortSplitSidecar, bin/matchTtbarIdSorted 포함 빌드

# 1) sidecar 를 정렬 + 분할 (한 번만; part 당 50만 event 기본)
bin/sortSplitSidecar \
    --filelist filelists/filelistEnriched/filelist_TTToHadronic.txt \
    --out-dir  sorted_TTToHadronic
# -> sorted_TTToHadronic/part00000.root, part00001.root, ... + index.txt

# 2) 정렬된 sidecar 로 검증 (메모리 ~16MB, nano 는 정렬 안 돼도 됨)
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTToHadronic \
    --nano-filelist filelists/filelistNanoAOD/filelist_TTToHadronic.txt \
    --out match_TTToHadronic.root --label TTToHadronic

# 3) 그림 (작은 샘플과 동일)
bin/plotTtbarCompare --match match_TTToHadronic.root --out TTToHadronic.png --label TTToHadronic
```

**원리 (external sort 의 2단계)**:
1. **분할 정렬**: 입력을 청크(기본 1000만 event)씩 읽어 각각 정렬해 임시 파일로
   저장. 메모리 = 청크 하나치.
2. **k-way merge**: 정렬된 청크들을 동시에 열고, 각 청크의 맨 앞만 비교하며 가장
   작은 것부터 꺼내 합칩니다. 이때 한 청크의 row 가 다른 청크의 row "사이사이"에
   자동으로 끼워지면서 전역 정렬이 완성됩니다. 메모리 = 청크 개수만큼의 row.

결과 part 들은 전역 정렬돼 있고 lumi 범위가 겹치지 않으므로, `index.txt`(각 part 의
첫/끝 (run,lumi,event))를 보고 nano event 가 어느 part 인지 binary search 로 즉시
찾습니다. 여러 condor job 이 각자 다른 part 를 열어 디스크 병목도 분산됩니다.

이 정렬·분할 산출물은 **나중에 analyzer 가 Expanded_genTtbarId 를 lookup 할 때도
그대로 재사용**할 수 있습니다 (같은 index + part 구조).

**메모리 조절** (필요시):
`--part-size`(part 당 row, 기본 50만 ~ 16MB), `--chunk-size`(정렬 청크, 기본
1000만 ~ 320MB). worker 가 작으면 chunk-size 를 줄이세요.

---

## 0-R. 전체 실행 순서 (실제 샘플 이름) — 한국어

filelist 는 `filelists/nano/filelist_<sample>.txt` 와
`filelists/sidecar/filelist_<sample>.txt` 에 동일 이름으로 있다고 가정합니다.
(경로는 본인 위치에 맞게 조정; TtbarIdHistCompare 디렉토리 안에서 실행)

ttbar stitching 7개 샘플 분류:
* **큰 것 (sorted 경로)**: `TTToHadronic`, `TTToSemiLeptonic`, `TTTo2L2Nu`
* **작은 것 (whole-map 경로)**: `tt4b`, `ttbb_Hadronic`, `ttbb_SemiLeptonic`, `ttbb_2L2Nu`

### 빌드 (한 번)

```bash
make
```

### 작은 샘플 — matchTtbarId (정렬 불필요)

```bash
for S in tt4b ttbb_Hadronic ttbb_SemiLeptonic ttbb_2L2Nu; do
  bin/matchTtbarId \
      --sidecar-filelist filelists/sidecar/filelist_${S}.txt \
      --nano-filelist    filelists/nano/filelist_${S}.txt \
      --out match_${S}.root --label ${S}
  bin/plotTtbarCompare --match match_${S}.root --out ${S}.png --label ${S}
done
```

### 큰 ttbar — sortSplitSidecar 먼저, 그 다음 matchTtbarIdSorted

```bash
for S in TTToHadronic TTToSemiLeptonic TTTo2L2Nu; do
  # (1) sidecar 정렬 + 50만씩 분할 (한 번만)
  bin/sortSplitSidecar \
      --filelist filelists/sidecar/filelist_${S}.txt \
      --out-dir  sorted_${S}
  # (2) 정렬된 sidecar 로 검증 (메모리 ~16MB)
  bin/matchTtbarIdSorted \
      --sorted-dir    sorted_${S} \
      --nano-filelist filelists/nano/filelist_${S}.txt \
      --out match_${S}.root --label ${S}
  # (3) 그림
  bin/plotTtbarCompare --match match_${S}.root --out ${S}.png --label ${S}
done
```

worker 메모리가 빠듯하면 `sortSplitSidecar` 에 `--chunk-size 5000000` 추가.

### tt4b 확장 카테고리 확인 (stitching 의 tt+nb 공급원)

```bash
bin/makeTtbarHist --filelist filelists/sidecar/filelist_tt4b.txt --mode sidecar --out hist_tt4b.root
# hist_tt4b.root 의 h_Expanded_sub 에서 61/62 (tt+bbb), 71/72 (tt+4b) 확인
```

대략 5천만 event 넘으면 sorted 경로를 쓰세요. (TTTo* 셋은 큰 쪽, ttbb·tt4b 는
작은 쪽.)

### 복붙용 — 검증 명령 전체 (그대로 실행)

```bash
# tt4b
bin/matchTtbarId \
    --sidecar-filelist filelists/sidecar/filelist_tt4b.txt \
    --nano-filelist    filelists/nano/filelist_tt4b.txt \
    --out match_tt4b.root --label tt4b
bin/plotTtbarCompare --match match_tt4b.root --out tt4b.png --label tt4b
# ttbb_Hadronic
bin/matchTtbarId \
    --sidecar-filelist filelists/sidecar/filelist_ttbb_Hadronic.txt \
    --nano-filelist    filelists/nano/filelist_ttbb_Hadronic.txt \
    --out match_ttbb_Hadronic.root --label ttbb_Hadronic
bin/plotTtbarCompare --match match_ttbb_Hadronic.root --out ttbb_Hadronic.png --label ttbb_Hadronic
# ttbb_SemiLeptonic
bin/matchTtbarId \
    --sidecar-filelist filelists/sidecar/filelist_ttbb_SemiLeptonic.txt \
    --nano-filelist    filelists/nano/filelist_ttbb_SemiLeptonic.txt \
    --out match_ttbb_SemiLeptonic.root --label ttbb_SemiLeptonic
bin/plotTtbarCompare --match match_ttbb_SemiLeptonic.root --out ttbb_SemiLeptonic.png --label ttbb_SemiLeptonic
# ttbb_2L2Nu
bin/matchTtbarId \
    --sidecar-filelist filelists/sidecar/filelist_ttbb_2L2Nu.txt \
    --nano-filelist    filelists/nano/filelist_ttbb_2L2Nu.txt \
    --out match_ttbb_2L2Nu.root --label ttbb_2L2Nu
bin/plotTtbarCompare --match match_ttbb_2L2Nu.root --out ttbb_2L2Nu.png --label ttbb_2L2Nu

# --- TTToHadronic (2.36억, 약 472 part) ---
bin/sortSplitSidecar \
    --filelist filelists/sidecar/filelist_TTToHadronic.txt \
    --out-dir  sorted_TTToHadronic
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTToHadronic \
    --nano-filelist filelists/nano/filelist_TTToHadronic.txt \
    --out match_TTToHadronic.root --label TTToHadronic
bin/plotTtbarCompare --match match_TTToHadronic.root --out TTToHadronic.png --label TTToHadronic
# --- TTToSemiLeptonic ---
bin/sortSplitSidecar \
    --filelist filelists/sidecar/filelist_TTToSemiLeptonic.txt \
    --out-dir  sorted_TTToSemiLeptonic
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTToSemiLeptonic \
    --nano-filelist filelists/nano/filelist_TTToSemiLeptonic.txt \
    --out match_TTToSemiLeptonic.root --label TTToSemiLeptonic
bin/plotTtbarCompare --match match_TTToSemiLeptonic.root --out TTToSemiLeptonic.png --label TTToSemiLeptonic
# --- TTTo2L2Nu ---
bin/sortSplitSidecar \
    --filelist filelists/sidecar/filelist_TTTo2L2Nu.txt \
    --out-dir  sorted_TTTo2L2Nu
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTTo2L2Nu \
    --nano-filelist filelists/nano/filelist_TTTo2L2Nu.txt \
    --out match_TTTo2L2Nu.root --label TTTo2L2Nu
bin/plotTtbarCompare --match match_TTTo2L2Nu.root --out TTTo2L2Nu.png --label TTTo2L2Nu
```

### analyzer 소비용 tt+nb lookup 만들기 (extractTtNb)

검증이 끝나면, analyzer 가 실제로 쓸 작은 lookup 을 만듭니다. sidecar 전체가
아니라 **tt+nb (Expanded%100 in {61,62,71,72}, 즉 nAddBJets>=3) 인 row 만** 추출
합니다. inclusive 는 수만 개, tt4b 는 약 188만 개라 파일이 작고, analyzer 는 이를
`(run,lumi,event) -> Expanded_genTtbarId` map 으로 통째 올려 멤버십 조회만 합니다
(map 에 있으면 tt+nb, 없으면 genTtbarId 그대로 — 60번 미만은 Expanded==genTtbarId
라 lookup 이 필요 없음).

```bash
for S in tt4b ttbb_Hadronic ttbb_SemiLeptonic ttbb_2L2Nu \
         TTToHadronic TTToSemiLeptonic TTTo2L2Nu; do
  bin/extractTtNb \
      --filelist filelists/sidecar/filelist_${S}.txt \
      --out ttnb_${S}.root --label ${S}
done
```

각 `ttnb_<S>.root` 의 `TtNb` 트리에 tt+nb row 만 들어갑니다. 출력 로그의
`selected tt+nb rows` 와 `tt+bbb (61+62) / tt+4b (71+72)` 개수는 같은 샘플의
`matchTtbarId` / `matchTtbarIdSorted` 검증 로그와 **정확히 일치**해야 합니다
(일치하면 추출이 정확한 것). 실제 측정값은 `docs/ARCHITECTURE.md` §8 참고.

### 의존성 두 가지

1. 검증 전에 sidecar 가 먼저 생산돼 있어야 함 (ExtendedTtbarId 패키지).
2. 큰 ttbar 는 반드시 `sortSplitSidecar` 가 먼저 → 그 출력 `sorted_<S>/` 를
   `matchTtbarIdSorted --sorted-dir` 로 넘김.

---

## 1. Build

```bash
# Set up your ROOT environment first (whatever you normally source so that
# `root-config` is on PATH).  Then:
make
# -> bin/makeTtbarHist
# -> bin/plotTtbarCompare
```

`make clean` removes `bin/`. The Makefile errors out with a clear message if
`root-config` is not found.

---

## 2. What each tool does

| Tool | Role |
|---|---|
| `bin/makeTtbarHist` | Read a filelist (one ROOT path per line), fill `genTtbarId` and sub-code (`%100`) histograms into a ROOT file. In `--mode sidecar` also fills `Expanded_genTtbarId` / `nAddBJets` / `nAddBJetsMulti`. Uses only the id branches, not run/lumi/event. |
| `bin/matchTtbarId` | Strict per-event check: load the sidecar into a `(run, lumi, event)` map and, for every nano event, verify the same key has an identical `genTtbarId`. Also validates the extended `Expanded_genTtbarId` directly against the sidecar's own `nAddBJets`: the sub-code is in 61/62/71/72 **iff** `nAddBJets >= 3`, the prefix is preserved, and the exact `(nAddBJets, nAddBJetsMulti)` -> sub-code mapping holds. Aborts (exit 9) if `run != 1`; aborts (exit 7) on a duplicate key. Optionally writes matched-event histograms. |
| `bin/matchTtbarIdSorted` | Memory-light version of `matchTtbarId` for large ttbar (e.g. TTToHadronic ~236M events). Consumes the sorted+split sidecar from `sortSplitSidecar` (parts + `index.txt`): for each nano event it finds the covering part via the index and binary-searches only that part (~16MB resident), instead of loading the whole sidecar. Same genTtbarId byte-identity + extended-id checks. |
| `bin/sortSplitSidecar` | External-sort an unordered sidecar by `(run, lumi, event)` into fixed-size part ROOT files plus `index.txt` (per-part first/last key). Two passes (chunk-sort then k-way merge) so it never holds the whole sample in memory. Feeds `matchTtbarIdSorted` and is reusable by the analysis for Expanded_genTtbarId lookup. |
| `bin/extractTtNb` | Extract only the tt+nb rows (`Expanded_genTtbarId % 100` in {61,62,71,72}, i.e. `nAddBJets >= 3`) from a sidecar into a small `TtNb` ROOT tree. This is the lookup the **analysis** consumes: load it into a `(run,lumi,event) -> Expanded_genTtbarId` map and decide per event by membership (in map -> tt+nb; not in -> use `genTtbarId`). Prints counts that must match the `matchTtbarId` validation log. |
| `bin/scanOrder` | Diagnose per-file `(run, lumi, event)` ordering of a filelist (shows whether files are globally sorted). |
| `bin/plotTtbarCompare` | Overlay sidecar vs nano `genTtbarId` sub-code; the per-bin ratio (sidecar/nano) is printed as a number above each populated bar (red if it deviates from 1) instead of a separate ratio panel. Also draws the sidecar `Expanded_genTtbarId` (shows 61/62/71/72 appearing). `--normalize` for shape-only, `--logy` for log scale. |
| `scripts/merge_hists.sh` | `hadd` wrapper: merge per-job histogram files into one file per process. |
| `scripts/submit_hist_condor.py` | Submit one HTCondor job per input ROOT file running `makeTtbarHist`, for a list of processes. |

---

## 3. Quick start (local, one file per side)

```bash
# nano side (your slimmedNtuple / central NanoAOD filelist)
bin/makeTtbarHist --filelist filelists/filelist_ttHH_nano.txt \
                  --mode nano --out hist_nano_ttHH.root --label ttHH

# sidecar side (filelist pointing at your sidecar ROOT files)
bin/makeTtbarHist --filelist filelists/filelist_ttHH_sidecar.txt \
                  --mode sidecar --out hist_sidecar_ttHH.root --label ttHH

# compare
bin/plotTtbarCompare --sidecar hist_sidecar_ttHH.root \
                     --nano    hist_nano_ttHH.root \
                     --out     ttHH_ttbarId_compare.png --label ttHH
```

`makeTtbarHist` flags: `--filelist`, `--mode {nano,sidecar}`, `--out`,
`--tree` (default `Events`), `--label`, `--max-events`.

`plotTtbarCompare` flags: `--sidecar`, `--nano`, `--out` (.png/.pdf/.root by
extension), `--label`, `--normalize`, `--logy`. It prints to stdout every
sub-code whose sidecar/nano ratio differs from 1.0 (none, if the event sets
match).

> **Tree name.** Defaults to `Events` (NanoAOD standard; the sidecar uses it
> too). If your slimmedNtuple uses a different tree name, pass `--tree NAME`.

---

## 4. Full scale on HTCondor

`scripts/submit_hist_condor.py` submits one job per input ROOT file. It is
self-contained (vanilla `condor_submit`; no analysis-framework dependency) and
ships your environment to the worker via `getenv=True`, so run it from the same
shell where ROOT and the binary are available.

Input filelists are laid out as `filelist_<process>.txt` inside a directory
(the layout produced by a `make_filelists.py`-style scan).

```bash
# nano pass
python3 scripts/submit_hist_condor.py \
    --filelist-dir filelists/nano --mode nano \
    --processes ttHH,tt4b,TTToSemiLeptonic,ttbb_SemiLeptonic \
    --work-dir condor_hist_nano --out-prefix hist_nano

# sidecar pass
python3 scripts/submit_hist_condor.py \
    --filelist-dir filelists/sidecar --mode sidecar \
    --processes ttHH,tt4b,TTToSemiLeptonic,ttbb_SemiLeptonic \
    --work-dir condor_hist_sidecar --out-prefix hist_sidecar
```

Options: `--makettbarhist /abs/path` (default `<project_root>/bin/makeTtbarHist`),
`--tree`, `--proxy` (default `$X509_USER_PROXY`), `--memory` (MB, default 2000),
`--max-files N` (smoke test), `--dry-run` (write `.sub` files but do not submit).

Per-job outputs land in `<work-dir>/outputs/hist_<prefix>_<process>_<N>.root`.

If your site needs an explicit ROOT setup line on the worker (a CVMFS source
or an LCG view) rather than relying on `getenv`, add it to the generated
`run_<process>.sh` or regenerate after editing `write_run_script` in the
submitter.

---

## 5. Merge and plot

```bash
scripts/merge_hists.sh condor_hist_nano/outputs    merged hist_nano
scripts/merge_hists.sh condor_hist_sidecar/outputs merged hist_sidecar
# -> merged/hist_nano_<process>.root, merged/hist_sidecar_<process>.root

for P in ttHH tt4b TTToSemiLeptonic ttbb_SemiLeptonic; do
  bin/plotTtbarCompare \
      --sidecar merged/hist_sidecar_${P}.root \
      --nano    merged/hist_nano_${P}.root \
      --out     ${P}_ttbarId_compare.png --label ${P}
done
```

---

## 6. Interpreting the plot

* Main pad: nano `genTtbarId` (filled), sidecar `genTtbarId` (black points),
  sidecar `Expanded_genTtbarId` (red open points).
* The black points must sit exactly on the filled nano histogram - that is the
  byte-level agreement of `genTtbarId`, shown as a distribution.
* The red points show where the extended categories appear: part of the nano
  tt+bb bucket (sub-code 53/54/55) is redistributed into 61/62/71/72 in the
  sidecar `Expanded_genTtbarId` (the events with >= 3 additional b-jets).
* Per-bin ratio numbers: the sidecar/nano ratio is printed above each populated
  bar (gray when 1.0, red when it deviates). Because the ratio is ~1.0
  everywhere, in-plot numbers are clearer than a separate ratio panel.

**Same event set is the precondition for ratio = 1.0.** If the nano and
sidecar passes cover different numbers of events (e.g. you only produced
sidecars for part of a sample), use `--normalize` to compare shapes instead of
absolute counts.

---

## 6b. Two comparison methods (distribution vs per-event)

There are two complementary ways to compare, and they answer different questions:

**Distribution comparison** (`makeTtbarHist` + `plotTtbarCompare`):
histograms each side independently and overlays them. Fast, and good for a
visual check of the shape. But the absolute counts only agree if both sides
cover the same events. In particular, a NanoAOD production often contains
*fewer* events than its parent MiniAOD (some input files dropped during
production), so the sidecar (made from MiniAOD) can legitimately have more
events than nano. That shows up as a *uniform* ratio offset across all
sub-codes (e.g. every bin ~1.027) - a tell-tale sign that the shapes match
but the populations differ. `--normalize` removes the offset and the shapes
coincide.

**Per-event comparison** (`matchTtbarId`): the strict check. It matches every
nano event to the sidecar by `(run, event)` and verifies the `genTtbarId` is
identical. Events in the sidecar but not in nano are simply never looked up,
so the MiniAOD-vs-NanoAOD count difference does not matter. This is the
definitive byte-level confirmation.

### Running matchTtbarId

```bash
bin/matchTtbarId \
    --sidecar-filelist filelists/sidecar/filelist_TTToSemiLeptonic.txt \
    --nano-filelist    filelists/nano/filelist_TTToSemiLeptonic.txt \
    --out match_TTToSemiLeptonic.root \
    --label TTToSemiLeptonic
```

It prints a summary:

```
[matchTtbarId]   matched             : <N>
[matchTtbarId]   agree               : <N>
[matchTtbarId]   disagree            : 0
[matchTtbarId] ----- extended-id (Expanded_genTtbarId) validation [v10] -----
[matchTtbarId]   matched events with nAddBJets >= 3       : <K>
[matchTtbarId]   matched events with ext sub-code (61/62/71/72): <K>
[matchTtbarId]   tt+bbb (61+62) : ...   tt+4b (71+72) : ...
[matchTtbarId]   nano sub-code of reclassified events (expect 53/54/55):
[matchTtbarId]       from sub-code 53 : ...
[matchTtbarId]   --- invariant violations (every count must be 0) ---
[matchTtbarId]   ext sub-code but nAddBJets < 3           : 0
[matchTtbarId]   nAddBJets >= 3 but not reclassified      : 0
[matchTtbarId]   reclassified with changed prefix         : 0
[matchTtbarId]   (nAddBJets,Multi) -> sub-code mismatch    : 0
[matchTtbarId]   nAddBJets <= 2 but Expanded_genTtbarId != genTtbarId  : 0
[matchTtbarId]   >>> extended-id consistent [v10]: Expanded_genTtbarId sub-code is in {61,62,71,72} iff nAddBJets>=3 ...
[matchTtbarId] >>> ALL <N> matched events have sidecar.genTtbarId == nano.genTtbarId (1:1), and Expanded_genTtbarId is consistent.
```

The extended-id block is the validation of the new categories: since NanoAOD
has no `Expanded_genTtbarId`, it cannot be checked against nano directly. Instead the tool
checks the producer's encoding rule head-on, using the sidecar's own
`nAddBJets` / `nAddBJetsMulti`: a sub-code in 61/62/71/72 appears **if and only
if** `nAddBJets >= 3`, the leading prefix digits are preserved, and the exact
`(nAddBJets, nAddBJetsMulti)` -> sub-code mapping (3 -> 61/62, >= 4 -> 71/72,
the second digit set by the multi-hadron-jet count) holds. Combined with the
genTtbarId 1:1 agreement (which confirms the upstream categorization module
reproduces the official NanoAOD), this establishes the extended id is correct:
it is built by the same module whose base output already matches nano.

> The earlier "only sub-code 56 may split" wording was the v9 model. The
> official GenTtbarCategorizer never emits sub-code 56 (>= 2 additional b-jets
> all map to 53/54/55), so the v10 producer keys the split on `nAddBJets`
> directly; this tool checks the same rule it enforces.

Exit codes: `0` all agree and Expanded_genTtbarId consistent, `5` nothing matched, `6` some
genTtbarId disagree, `7` duplicate `(run, lumi, event)` in the sidecar, `8`
extended-id consistency failed, `9` `run != 1` encountered (this tooling
assumes MC, where run is always 1). A duplicate key or `run != 1` must never
happen; `matchTtbarId` prints the offending rows to stderr and aborts, so you
can grep your condor logs for it:

```bash
grep -l "DUPLICATE (run,lumi,event)" condor_logs/*.err
grep -l "run=.* != 1"               condor_logs/*.err
```

The `--out` file holds histograms over **matched events only**:
`h_genTtbarId_sub` (nano), `h_sidecar_genTtbarId_sub` (sidecar), and
`h_sidecar_Expanded_genTtbarId_sub` (sidecar Expanded_genTtbarId). Plot them directly with
`plotTtbarCompare --match`:

```bash
bin/plotTtbarCompare --match match_TTHHto4b.root \
                     --out   TTHHto4b_validation.png --label TTHHto4b
```

The main pad overlays nano genTtbarId (filled), sidecar genTtbarId (black
points, must coincide), and sidecar Expanded_genTtbarId (red points, showing 53/54/55
partly redistributed into 61/62/71/72). The per-bin ratio numbers (sidecar/nano genTtbarId) must be 1.0 in every
populated bin - and because the histograms cover exactly the matched event
set, no `--normalize` is needed.

### Key, run, and memory

`matchTtbarId` keys on the full `(run, lumi, event)` and aborts if `run != 1`
(this tooling assumes MC). The full key matters: in a large MC sample the
event number is only unique *within a lumisection*, so event numbers are
reused across lumisections and `(run, event)` alone is NOT unique (observed
~4% collisions in the 355M-event TTToSemiLeptonic sample). The 3-key avoids
that; a genuine duplicate of the full key triggers the exit-7 abort.

Memory note: the extended categories (61/62/71/72) only ever populate for the
ttbb / tt4b / ttHH samples (samples that never reach >= 3 additional b-jets
keep Expanded_genTtbarId == genTtbarId, so their plain genTtbarId can be taken straight from
NanoAOD). Those signal samples are
small (tens of millions of events at most), so the in-memory map is only a few
GB - the 18-20 GB figure was for the 346M-event TTToSemiLeptonic, which does
not need the extended id at all. For the samples that do, raise the condor
job memory as needed; it is comfortably bounded.

---

## 7. Layout

```
TtbarIdHistCompare/
+-- Makefile                         <- standalone ROOT build (no CMSSW)
+-- src/
|   +-- makeTtbarHist.cc             <- fill genTtbarId/Expanded_genTtbarId histograms
|   +-- matchTtbarId.cc              <- per-event (run,lumi,event) match + Expanded_genTtbarId validation (whole sidecar in memory)
|   +-- matchTtbarIdSorted.cc        <- per-event match using sorted+split sidecar (memory-light; large ttbar)
|   +-- sortSplitSidecar.cc          <- external-sort sidecar by (run,lumi,event) -> part files + index.txt
|   +-- extractTtNb.cc               <- extract tt+nb rows (61/62/71/72) into a small lookup ROOT for the analyzer
|   +-- scanOrder.cc                 <- diagnose per-file (run,lumi,event) ordering
|   `-- plotTtbarCompare.cc          <- overlay plot with per-bin ratio numbers (separate files or --match)
+-- scripts/
|   +-- merge_hists.sh               <- hadd per-process
|   `-- submit_hist_condor.py        <- HTCondor submitter
+-- docs/
|   `-- ARCHITECTURE.md              <- design + validation notes
+-- filelists/                       <- (you populate: filelist_<process>.txt)
`-- README.md
```
