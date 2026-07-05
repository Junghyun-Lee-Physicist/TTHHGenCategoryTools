# TtbarIdHistCompare - design and validation notes

This document records why each tool exists, what was learned while validating
the ttbar+HF categorization sidecar against central NanoAOD, and how the
extended categories (61/62/71/72) are validated. It is the companion to the
usage-focused `README.md`.

## 1. Goal

The analysis needs the ttbar+HF categorization id (`genTtbarId`) and an
extended version (`Expanded_genTtbarId`). For events with >= 3 additional b-jets the
sub-code is reclassified into 61/62 (exactly 3 add b-jets, no-multi / multi)
and 71/72 (>= 4 add b-jets, no-multi / multi); events with <= 2 keep their
standard sub-code. The split is keyed on `nAddBJets`, not on a sub-code value:
the official GenTtbarCategorizer maps every event with >= 2 additional b-jets
to 53/54/55 and never emits sub-code 56, so the reclassified events come out
of the 53/54/55 bucket. These are produced by a gen-level "sidecar" (running
the standard `categorizeGenTtbar` plus the `ExtendedTtbarIdProducer` module on
MiniAOD), avoiding a full MiniAOD -> NanoAOD reproduction.

Before relying on the sidecar we must show:
1. its `genTtbarId` reproduces the official NanoAOD `genTtbarId`, and
2. its extended `Expanded_genTtbarId` is internally consistent (sub-code in 61/62/71/72 iff
   `nAddBJets >= 3`; prefix preserved; exact mapping).

This project provides the tools for both, plus the histogram comparison.

## 2. genTtbarId distribution check (makeTtbarHist + plotTtbarCompare)

`makeTtbarHist` fills the `genTtbarId` (and sub-code) distribution from a
filelist; `plotTtbarCompare` overlays sidecar vs nano with per-bin ratio numbers.

Observed result across the analysis samples:
- ttHH, tt4b, ttbb_SemiLeptonic: ratio = 1.0 in every populated sub-code.
- TTToSemiLeptonic: a *uniform* ratio offset of ~1.027 across all sub-codes.

The uniform offset is the signature of equal shape but unequal population.
DAS confirmed the cause: the MiniAODv2 dataset has 355,332,000 events while
its NanoAODv9 child has 346,052,000 - the NanoAOD production dropped ~9.28M
(2.68%) of the parent events. The sidecar (made from MiniAOD) therefore
legitimately has more events than nano. With `--normalize` the offset
disappears and the shapes coincide. This is a data-population effect, not a
code error, and it does not affect the per-event check (Section 4), which only
looks up events that exist in nano.

## 3. Why per-file lumi chunking is not possible (scanOrder)

A natural idea for matching sidecar to nano without loading everything into
memory is to process in lumisection ranges, assuming the files are laid out in
lumi order. `scanOrder` was written to test this: for each file in a filelist
it records the first/last/min/max (run, lumi, event) and whether the file is
internally sorted, then checks whether consecutive files are globally ordered
and whether their lumi ranges overlap. It streams each file (no big map), so
memory is negligible.

Finding (TTToSemiLeptonic sidecar): files are **not** internally sorted
(`sortedInFile=0` everywhere) and their lumi ranges **overlap heavily** - e.g.
one file spans lumi [338131, 355940] and the next spans [338177, 351722],
which overlap almost completely. A single lumisection's events are scattered
across many files. CRAB FileBased splitting plus the MiniAOD's own event
ordering produce this. Consequently lumi-range chunking is not safe, and
matching needs either a full in-memory index or an external sort.

### 3.1 The external-sort solution (sortSplitSidecar + matchTtbarIdSorted)

For small samples (ttbb, tt4b, ttHH) the full in-memory index in `matchTtbarId`
is fine. For ttbar inclusive it is not: TTToHadronic has ~236M events, so the
`(run,lumi,event)->Row` map needs ~20GB and does not fit on a Tier3 worker.

`sortSplitSidecar` solves this with a classic external sort:

* **Pass 1 (chunk-sort):** stream the sidecar, accumulate `--chunk-size` rows
  (default 10M ~ 320MB), sort that chunk in memory by `(run,lumi,event)`, and
  write it to a temporary ROOT file. Memory = one chunk.
* **Pass 2 (k-way merge):** open all sorted chunks at once and repeatedly emit
  the globally smallest current row (a min-heap over the chunks' heads). This
  interleaves each chunk's rows into the others, producing one globally sorted
  stream, written out as `part%05d.root` files of `--part-size` rows each
  (default 500k ~ 16MB). Memory = one row per chunk + one output part.

It also writes `index.txt`, one line per part:
`partIndex nRows firstRun firstLumi firstEvent lastRun lastLumi lastEvent`.
Because the output is globally sorted, the parts' key ranges are
non-overlapping, so a consumer can binary-search the index to find the unique
part covering any `(run,lumi,event)`.

`matchTtbarIdSorted` consumes this: it loops the (still unordered) nano events,
finds each event's covering part via the index, loads only that part (~16MB)
into a sorted vector, and binary-searches the key. It keeps one part resident
and reloads only when the needed part changes, so memory stays at one part
regardless of sample size. It performs the same genTtbarId byte-identity check
and the v10 extended-id validation as `matchTtbarId`.

Sizing for TTToHadronic (235,719,999 events) at the default 500k rows/part:
~472 parts, each ~16MB; chunk-sort uses ~24 chunks of 10M rows. Both passes fit
comfortably on a standard worker. The same sorted+split output is reusable by
the analysis itself for per-event `Expanded_genTtbarId` lookup (find the part by
`(run,lumi,event)`, load it, binary-search), which also distributes disk access
across parts and avoids a single-file bottleneck.

Note: the part boundaries are placed by row count, so one lumisection can span
two adjacent parts. That is why the index stores the full `(run,lumi,event)`
first/last key of each part (not just lumi), and lookups compare the full key.

## 4. Per-event check and the (run, lumi, event) key (matchTtbarId)

`matchTtbarId` loads the sidecar into a `(run, lumi, event)` -> (genTtbarId,
Expanded_genTtbarId) hash map and, for every nano event, looks up the same key and compares
`genTtbarId`. Events present in the sidecar but absent from nano (the ~2.68%
dropped by NanoAOD production) are never looked up, so the population
difference does not pollute the comparison.

The key must be the full `(run, lumi, event)`. An earlier 2-key `(run, event)`
version aborted on the TTToSemiLeptonic sidecar with ~15.27M duplicate keys
(4.3%). Inspection showed the collisions all had the same run and event but
*different* lumi: in a large MC sample the event number is only unique within
a lumisection and is reused across lumisections. The duplicate-detection that
caught this was a deliberate safety check (insert into the map, error on
collision) and worked as intended. The tool now also aborts if `run != 1`,
since this tooling assumes MC.

Memory: one map entry per sidecar event (~50-60 B with the hash map). For the
346M-event TTToSemiLeptonic this is ~18-20 GB - but that sample does not need
the extended id (see Section 5), so in practice matchTtbarId is run on the much
smaller signal samples where the map is a few GB.

## 5. Extended-id (Expanded_genTtbarId) validation

NanoAOD has no `Expanded_genTtbarId`, so it cannot be checked against nano directly.
Instead `matchTtbarId` checks the producer's encoding rule head-on over matched
events, using the sidecar's own `nAddBJets` / `nAddBJetsMulti` (the quantities
the producer keys on). For every matched event:

- `Expanded_genTtbarId` sub-code is in {61,62,71,72} **iff** `nAddBJets >= 3` (both
  directions: no false extension, no missed extension);
- a reclassified event preserves the leading prefix: `Expanded_genTtbarId/100 == genTtbarId/100`;
- the exact mapping holds: `nAddBJets == 3 -> 61/62`, `>= 4 -> 71/72`, with the
  second digit set by `nAddBJetsMulti` (0 -> 61/71, >= 1 -> 62/72);
- `nAddBJets <= 2 -> Expanded_genTtbarId == genTtbarId` exactly (unchanged).

The logic behind treating this as sufficient: `genTtbarId` and the extended
`Expanded_genTtbarId` come from the **same module chain**. Section 2/4 establish that the
module reproduces the official NanoAOD `genTtbarId` bit-for-bit. The extension
is a deterministic function of `(nAddBJets, nAddBJetsMulti)`, both carried in
the sidecar, so checking that function directly (plus prefix preservation and
the unchanged-below-3 case) fully validates the extended id given the base is
already correct.

> Earlier revisions stated "only sub-code 56 may move". That was the v9 model,
> before the producer was fixed: the official GenTtbarCategorizer never emits
> 56, so that check never fired and tt+bbb / tt+4b were never produced. v10
> keys the split on `nAddBJets`; this tool checks the same rule it enforces.

Only the ttbb / tt4b / ttHH samples actually populate the extended id; samples
that never reach >= 3 additional b-jets keep `Expanded_genTtbarId == genTtbarId` and can
take their plain `genTtbarId` straight from the NanoAOD branch.

## 6. Exit codes

`matchTtbarId`: `0` ok; `5` nothing matched; `6` genTtbarId disagreement;
`7` duplicate `(run, lumi, event)` in the sidecar (must not happen); `8`
extended-id consistency failure. The nonzero codes make failures visible in
condor logs (grep for `DUPLICATE (run,lumi,event)` or `run=... != 1`).

## 7. Next step (outside this project)

Once validation passes, `extractTtNb` produces the small per-sample tt+nb
lookup (`ttnb_<sample>.root`, holding only the `nAddBJets >= 3` rows, i.e.
`Expanded_genTtbarId % 100` in {61,62,71,72}; see Section 8.7). The analyzer
loads this into a `(run, luminosityBlock, event) -> Expanded_genTtbarId` map
and decides per event purely by membership:

* in the map  -> tt+nb; use the stored `Expanded_genTtbarId` (61/62/71/72),
* not in map  -> use the NanoAOD `genTtbarId` unchanged (events with
  `nAddBJets <= 2` satisfy `Expanded_genTtbarId == genTtbarId`, so no lookup is
  needed for them).

This membership-only decision means no `genTtbarId` sub-code gating is required,
so the b-hadron-vs-b-jet "boundary" subtlety never enters. The lookup is tiny
(tens of thousands of rows for inclusive ttbar, ~1.9M for tt4b), so it fits
entirely in memory with negligible lookup cost. Every ttbar sample that
participates in the tt+nb / tt+mb stitching needs its own lookup; the tt+nb
class is sourced from the dedicated tt4b sample (keep `Expanded_genTtbarId % 100`
in {61,62,71,72}) while every other ttbar sample rejects those events. That
application is part of the analysis framework, not this validation project.

## 8. Validation results (2017 UL, full statistics)

이 절은 7개 ttbar stitching 샘플 전체를 실제로 검증한 결과입니다. 어떤 명령을
썼고, 무슨 결과가 나왔으며, 그게 무엇을 뜻하는지 정리합니다.

### 8.1 사용한 명령

작은 샘플(ttbb 3종, tt4b)은 sidecar 를 통째로 메모리에 올리는 `matchTtbarId`,
큰 inclusive 3종(메모리 초과)은 `sortSplitSidecar` -> `matchTtbarIdSorted` 의
메모리-경량 경로를 썼습니다.

```bash
# 작은 샘플 (예: tt4b)
bin/matchTtbarId \
    --sidecar-filelist filelists/sidecar/filelist_tt4b.txt \
    --nano-filelist    filelists/nano/filelist_tt4b.txt \
    --out match_tt4b.root --label tt4b

# 큰 샘플 (예: TTToHadronic)
bin/sortSplitSidecar \
    --filelist filelists/sidecar/filelist_TTToHadronic.txt \
    --out-dir  sorted_TTToHadronic
bin/matchTtbarIdSorted \
    --sorted-dir    sorted_TTToHadronic \
    --nano-filelist filelists/nano/filelist_TTToHadronic.txt \
    --out match_TTToHadronic.root --label TTToHadronic
```

(전체 복붙용 명령은 README §0-R 참고.)

### 8.2 genTtbarId byte-identity — 7샘플 전량 일치

모든 샘플에서 nano event 전량이 sidecar 와 매칭됐고(unmatched 0), genTtbarId 가
완전히 일치했습니다(disagree 0).

| 샘플 | nano events | matched | agree | disagree | unmatched |
|---|---:|---:|---:|---:|---:|
| TTToHadronic     | 232,999,999 | 232,999,999 | 232,999,999 | 0 | 0 |
| TTToSemiLeptonic | 346,052,000 | 346,052,000 | 346,052,000 | 0 | 0 |
| TTTo2L2Nu        | 106,724,000 | 106,724,000 | 106,724,000 | 0 | 0 |
| tt4b             |   9,502,000 |   9,502,000 |   9,502,000 | 0 | 0 |
| ttbb_Hadronic    |   5,694,656 |   5,694,656 |   5,694,656 | 0 | 0 |
| ttbb_SemiLeptonic|   7,318,891 |   7,318,891 |   7,318,891 | 0 | 0 |
| ttbb_2L2Nu       |   3,472,503 |   3,472,503 |   3,472,503 | 0 | 0 |

합계 약 7.12억 event. **의미**: 우리가 MiniAODv2 에서 재생산한 `genTtbarId` 가
중앙 NanoAODv9 의 값과 byte 단위로 동일합니다. 즉 sidecar 의 기반(표준
genTtbarId)이 정확하며, 그 위에 얹은 확장만 검증하면 됩니다.

### 8.3 확장 카테고리(Expanded_genTtbarId) — v10 무결성 전량 통과

모든 샘플에서 다음 무결성 조건이 전부 0 이고, 보존식
(nAddBJets>=3 개수 == 61/62/71/72 개수)이 정확히 성립했습니다:
extended-but-nAddBJets<3 = 0, nAddBJets>=3-but-not-ext = 0,
prefix-changed = 0, nAddBJets<=2-changed = 0.

| 샘플 | tt+nb (nAddBJets>=3) | tt+bbb (61+62) | tt+4b (71+72) | tt+nb 비율 |
|---|---:|---:|---:|---:|
| tt4b             | 1,882,170 | 1,585,810 | 296,360 | 19.8 % |
| ttbb_SemiLeptonic|    26,544 |    23,468 |   3,076 | 0.36 % |
| ttbb_Hadronic    |    23,390 |    20,631 |   2,759 | 0.41 % |
| ttbb_2L2Nu       |    11,238 |     9,953 |   1,285 | 0.32 % |
| TTToSemiLeptonic |    32,162 |     (61+62)|  (71+72)| 0.0093 % |
| TTToHadronic     |    25,097 |     (61+62)|  (71+72)| 0.0108 % |
| TTTo2L2Nu        |     8,559 |     (61+62)|  (71+72)| 0.0080 % |

(inclusive 3종은 매칭 로그에서 tt+nb 합만 출력했고, bbb/4b 세부는 extractTtNb
로그에서 확인됩니다. tt4b 의 1,585,810 / 296,360 은 §5.3 에서 예측한
nAddBJets==3 / >=4 카운트와 정확히 일치합니다.)

### 8.4 tt4b 의 재분류 출처 — 전부 표준 tt+bb(53/54/55)에서

tt4b 에서 60번대로 재분류된 1,882,170 event 의 원래 genTtbarId sub-code:

```
from sub-code 53 : 1,458,666
from sub-code 54 :   408,116
from sub-code 55 :    15,388
```

**의미**: tt+nb event 가 전부 표준의 tt+bb 버킷(53/54/55) 안에 숨어 있었습니다.
51/52(tt+b/2b)나 다른 sub-code 에서 새어 나온 게 0 입니다. 이는 (a) 표준
GenTtbarCategorizer 가 추가 b-jet >=2 를 53/54/55 로 뭉뚱그린다는 사실,
(b) 우리가 그 안에서 nAddBJets>=3 을 정확히 끄집어낸다는 사실을 동시에
확인합니다.

### 8.5 물리적 해석 — stitching 설계의 정당화

tt+nb 비율이 dedicated tt4b 에서 19.8 %, 4FS ttbb 에서 ~0.4 %, inclusive 5FS
에서 ~0.01 % 입니다. tt4b 가 inclusive 보다 tt+nb 를 약 1,800배 높은 밀도로
담습니다. 이는 "tt+nb 는 dedicated tt4b 샘플로, 나머지(tt+mb/cc/LF)는 각자의
샘플로" 라는 stitching 결정을 데이터로 뒷받침합니다 — inclusive 로 tt+nb 를
모델링하면 통계가 절망적이기 때문입니다.

### 8.6 메모리 경량 경로의 성능

`matchTtbarIdSorted` 가 TTToSemiLeptonic 3.46억, TTToHadronic 2.33억 event 를
part 하나(~16MB)만 상주시킨 채 완주했습니다. 정렬 산출물의 part 수는
TTToHadronic 472, TTToSemiLeptonic 711, TTTo2L2Nu 214 였습니다. 전 과정에서
메모리 초과 없이 동작했고, 이는 sidecar 전체를 map 에 올리던 방식(~20GB+)으로는
불가능했던 작업입니다.

### 8.7 analyzer 소비용 lookup (extractTtNb)

검증이 끝난 뒤, analyzer 가 실제로 쓸 작은 lookup 을 `extractTtNb` 로 만듭니다.
sidecar 전체가 아니라 tt+nb(60번대) row 만 추출하므로, inclusive 는 수만 row,
tt4b 는 ~188만 row 입니다. analyzer 는 이를 `(run,lumi,event) -> Expanded`
map 으로 올려 멤버십만 조회합니다(있으면 tt+nb, 없으면 genTtbarId 그대로).
`extractTtNb` 가 출력하는 selected/61+62/71+72 개수는 위 §8.3 표와 일치해야
하며, 일치하면 추출이 정확한 것입니다.
