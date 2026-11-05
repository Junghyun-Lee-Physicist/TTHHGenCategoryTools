# 07 — Analyzer integration: patch 파일 소비 계약

> **목적**: 분석 프레임워크(tempTTHH의 `ttHHanalyzer_unified`)가 이 저장소의 산출물을 어떻게 읽어 per-event 확장 id와 stitch weight로 바꾸는지 — 계약과 실제 구현.
> **대상 독자**: analyzer 쪽을 만지는 사람; patch 파일 명명을 바꾸려는 사람(필독).
> **상태**: 소비 방식 DECIDED (D9) · 구현은 tempTTHH에 반영 완료(2026-06) · **명명 rename의 analyzer측 반영은 PROPOSED** (§4) · **2026-11-05: format 2 — key 에 NanoAOD dataset (TTHHAnalyzer STEP 45, §5)**: 2022–23 은 format 2 만, Run 2·2024 는 format 1 그대로.
> **관련**: 개념·검증 논리의 원전은 tempTTHH `docs/ttbarCategorization.md` §9–§11 (분석 저장소); 생산측 규칙은 [02](02_physics.md) §5, 수치는 [06](06_validation_results.md).

## 결론 먼저 (BLUF)

analyzer는 per-sample patch 파일 하나를 `(run, luminosityBlock, event) → {Expanded_genTtbarId, genTtbarId}` map으로 올리고, event마다 **membership만으로** 판정한다: map에 있으면 저장된 확장값(61/62/71/72)으로 override, 없으면 NanoAOD `genTtbarId` 그대로. 이 값(`expandedTtbarId`)이 출력 branch와 stitching multiplier의 key가 된다.

## 1. 계약 (파일 → analyzer)

**입력 파일** (본 저장소 `Validation/bin/extractTtbarIdPatch` 산출):
- TTree(신규 기본 `TtbarIdPatch`; 구 규약 `TtNb`) — branch: `run/i, luminosityBlock/i, event/l, genTtbarId/I, Expanded_genTtbarId/I, nAddBJets/I, nAddBJetsMulti/I`.
- **구성상 보장**: 모든 row가 `Expanded%100 ∈ {61,62,71,72}` ⇔ `nAddBJets ≥ 3` (추출기가 불일치 시 abort하므로, 존재하는 파일은 내부 일관).
- 파일명 규약: 신규 `ttbarIdPatch_<sample>.root` / 구 `ttnb_<sample>.root` (D12; §4).

**소비 의미론** (tempTTHH `ExpandedTtbarId` 클래스, standalone ROOT-only):
- `loadFromDir(dir, sampleKey)` — `<dir>/<접두><sampleKey>.root` 정확명 → 없으면 프로세스 토큰(가장 구체적인 것부터: ttbb_SemiLeptonic, …, tt4b) fallback → 그래도 없으면 **INACTIVE** (시도 경로를 크게 로그; fatal 아님 — patch 없는 샘플·Data는 NanoAOD 값 사용이 올바른 동작). dir 기본 `DerivedCorr/expandedTtbarId/`, env `EXPANDED_TTBARID_DIR`로 override.
- `resolve(run, lumi, event, nanoGenTtbarId)` — hit이면 저장된 `Expanded_genTtbarId` 반환, miss/INACTIVE면 `nanoGenTtbarId` 그대로. hit/miss·61/62/71/72 카운터 집계, `printSummary()`로 종료 보고.

**안전장치** (전부 fail-loud):
| 검사 | 동작 |
|---|---|
| load: chain add 실패 / tree 비어있음 | exit 41 / 42 |
| load: 동일 key 중복 — 값까지 다르면 | exit 43 (동일값 중복은 무시+집계) |
| load: sub-code ⇔ nAddBJets≥3 불일치 row | 카운트 후 경고 (추출기 보장상 0이어야 함) |
| **hit 시 genId self-check**: 저장된 `genTtbarId` ≠ 이 event의 NanoAOD `genTtbarId` | **exit 44** — "샘플에 맞지 않는 patch 파일 로드"의 결정적 신호 (`setAbortOnGenIdMismatch(false)`로 완화 가능) |
| 샘플이 stitch plan에 있는데 lookup INACTIVE | analyzer가 시작 단계에서 거부 (MISCONFIG 안내 출력) |
| 키 해시 | FNV, `matchTtbarId`와 **byte-identical** — analyzer의 membership이 검증된 매칭을 그대로 재현 ([00_PROMPT](../00_PROMPT.md) §8) |

## 2. per-event 적용 흐름 (tempTTHH `process()` 내 MC 블록)

```cpp
_genTtbarIdNano  = _ev->genTtbarId;                                  // raw NanoAOD
_expandedTtbarId = _expTtbarId.resolve(_ev->run, _ev->luminosityBlock,
                                       _ev->event, _ev->genTtbarId); // 61/62/71/72 or unchanged
// stitch multiplier — resolve 직후, selectObjects(SF 체인 시드) 이전에 적용
if (_stitch.inPlan()) {
    const double m = _stitch.factor(_expandedTtbarId, _evtWeight);
    _evtWeight   *= m;
    _stitchWeight = m;                                               // 출력 branch
}
```

- 출력 Events tree에 `genTtbarId/I`와 `expandedTtbarId/I` **둘 다** 기록 (MC/Data로만 게이팅, mode 무관) — 미적용 원값이 항상 함께 남아 사후 검증 가능.
- **keep/reject([02](02_physics.md) §5)는 multiplier로 구현**: dedicated tt4b는 소유 카테고리(61–72)에 r, 그 외 0; inclusive/ttbb는 소유 카테고리에 1(또는 factor), 61–72에 0. multiplier 0 = 그 샘플에서 event 제거 → double-count/gap 없음. b-tag normalization reweight도 `expandedTtbarId%100` 카테고리를 key로 사용.

## 3. prescan(정규화 분모)에서의 사용

`--mode prescan`에서 같은 `resolve()`로 event의 **generator weight 합(ΣgenW)** 을 라우팅: tt+nb event의 무게가 53/54/55 bin에서 **61/62/71/72 bin으로 이동**하므로, 이후 53/54/55는 순수 tt+2b 잔여가 된다. prescan tree에 `sumGenW_id_{61,62,71,72}`, `n_id_{61,62,71,72}` 8개 branch 추가. per-event branch(선택 통과 event의 분자)와 prescan 합(무선택 전량의 분모)은 **역할이 다르며 서로 대체 불가** — 이 구분의 상세 논의는 tempTTHH `docs/ttbarCategorization.md` §9.5.

## 4. OPEN — 명명 rename의 analyzer측 반영 (D12 후속) · **다음 업데이트 항목**

> **2026-07-28 결정**: 지금은 **구규약 `ttnb_<KEY>.root` / tree `TtNb` 를 유지**한다. 2018 patch 도
> `extractTtbarIdPatch --out ttnb_<KEY>.root --out-tree TtNb` 로 뽑는다. 즉 이 플래그는 임시
> 우회가 아니라 **현행 정식 규약**이다. 아래는 **다음 정리 작업**으로 남긴다.
>
> **권장 방식은 기본값 교체가 아니라 fallback 추가다.** 2017 patch 7편(`Validation/lookup/`)은
> **파일 안의 tree 이름이 `TtNb`** 이므로 파일명을 바꿔도 해결되지 않는다 — loader 기본값을
> `TtbarIdPatch` 로 뒤집으면 2017 을 못 읽고 KNU Tier3 에서 **재추출**해야 한다. 대신 loader 가
> `TtbarIdPatch` 를 먼저 시도하고 없으면 `TtNb` 로 **fallback** 하게 하면, flag day 없이
> 마이그레이션되고 2017·2018 모두 동작한다.
>
> **지금 하지 않는 이유**: (1) 2018 control plots 의 크리티컬 패스가 아니다 — tempTTHH 는 별도
> repo·별도 릴리스(CMSSW_14_2_1)이고 C++ 수정 + 재빌드 + 테스트가 병목이 된다. (2) era 별 규약
> 혼재가 플래그 하나보다 나쁜 함정이다. (3) 틀렸을 때의 실패가 **조용하다** — loader 가 INACTIVE 로
> 떨어져 fatal 없이 NanoAOD 원값을 쓰므로, 확장 id 가 적용 안 된 플롯이 나온다.
>
> 상대편 기록: `tempTTHH/docs/STATUS.md` "Pending / next steps (OPEN)".

### 4.1 (참고) 기본값을 교체하는 경우의 4개 토큰

도구측 기본값은 `ttbarIdPatch_*` / `TtbarIdPatch`로 변경 완료(2026-07-05). analyzer가 신규 규약을 읽게 하려면 tempTTHH에서 **정확히 아래 4개 토큰**을 바꾸면 된다 (로직 무변경):

```diff
--- include/ExpandedTtbarId.h
-  void load(const std::string& path, const std::string& label = "",
-            const std::string& treeName = "TtNb");
+  void load(const std::string& path, const std::string& label = "",
+            const std::string& treeName = "TtbarIdPatch");
-  void loadFromDir(const std::string& dir, const std::string& sampleKey,
-                   const std::string& treeName = "TtNb");
+  void loadFromDir(const std::string& dir, const std::string& sampleKey,
+                   const std::string& treeName = "TtbarIdPatch");
--- src/ExpandedTtbarId.cc  (loadFromDir 내부 2곳)
-  const std::string path = dir + sep + "ttnb_" + sampleKey + ".root";
+  const std::string path = dir + sep + "ttbarIdPatch_" + sampleKey + ".root";
-    const std::string p2 = dir + sep + "ttnb_" + std::string(tk) + ".root";
+    const std::string p2 = dir + sep + "ttbarIdPatch_" + std::string(tk) + ".root";
```

**적용 전까지의 현행 계약 = 구 규약.** `Validation/lookup/`의 기존 7편(ttnb_*/TtNb)이 그대로 유효하다. 신규 규약으로 재추출하려면: `bin/extractTtbarIdPatch --filelist filelists/ttbarId-extend/filelist_<S>.txt --out ttbarIdPatch_<S>.root --label <S>` (구 규약 재생산은 `--out ttnb_<S>.root --out-tree TtNb`). 두 규약을 섞지 말 것 — loader의 정확명 매칭이 접두로 갈리기 때문. 사용자가 어느 쪽을 확정하면 이 항목을 DECIDED로 승격하고 [01_status.md](01_status.md) O2를 닫는다.

## 5. format 2 — key 에 NanoAOD dataset (2026-11-05, TTHHAnalyzer STEP 45)

> **왜**: 2022·2022EE 의 ttbar 표본은 main 과 ext1 두 NanoAOD dataset 을 읽는데, 두 dataset 이 **같은 (run, luminosityBlock, event) 를
> 다른 사건에** 쓴다(여섯 표본에 공유 key 350,885 개, 예: 2022EE TTbar_SemiLep 231,401 — TTHHAnalyzer
> `docs/claude-remote/daily/lxplus/files/2026-11-04_dup_scan/main_ext_overlap.tsv`). key 가 (run, lumi, event) 이면 ext1 사건이 main 사건의
> 범주를 받거나, 값이 다른 중복 key 로 load 가 멈춘다(E72). 또 2022–23 lookup 은 NanoAOD dataset 하나에 CRAB 출력 여럿 — MiniAODv4(main,
> ext1)와 판 A 의 MiniAODv3 — 에서 뽑는다(TTHHAnalyzer `docs/DECISIONS.md` D-2026-11-04-E/F, D-2026-11-05-B). §1–§3 의 key 3 개 규약
> (00_PROMPT §8, docs/04 D7)은 **format 1 의 것**이고 그대로다; format 2 는 dataset 을 key 의 넷째 칸으로 더한다.

### 5.1 파일 (생산: `extractTtbarIdPatch --input`, [Validation/README.md](../Validation/README.md) §4.2)

| 항목 | format 1 (지금까지, `--filelist`) | format 2 (`--input`) |
|---|---|---|
| 파일 이름·tree | `ttnb_<sample>.root` / `TtNb` (`--out`, `--out-tree TtNb`) | 같다 |
| branch | `run/i luminosityBlock/i event/l genTtbarId/I Expanded_genTtbarId/I nAddBJets/I nAddBJetsMulti/I` | 같은 일곱 + **`datasetIdx/I`** |
| TNamed `lookup_format` | 없음 | `"tthh-ttnb/2"` |
| TNamed `nano_datasets` | 없음 | 추출이 처리한 NanoAOD dataset 모두(tt+nb 행이 0 인 것도), 한 줄에 하나, 이름 순; `datasetIdx` = 줄 번호(0 부터) |
| TNamed `sources` | 없음 | 입력마다 한 줄(TSV): datasetIdx, dataset, priority, filelist, 파일 수, entries, 낮은 번호에 밀린 행, 쓴 tt+nb 행; 끝에 공유 key·conflict 수 |
| 행 | 입력 순서, 중복 그대로 | `(datasetIdx, run, lumi, event)` 순 정렬, dataset 안에서 key 하나에 한 행 |

**우선순위 규칙**: 한 NanoAOD dataset 안에서 같은 key 가 두 입력에 있으면 **priority 숫자가 낮은 입력의 행**을 쓴다(MiniAODv4 = 0 이
MiniAODv3 = 1 을 이긴다; 같은 숫자면 먼저 준 `--input`). **모든 행을 비교한다** — 두 입력의 행끼리도, **한 입력 안의 두 행**끼리도, 범주와
무관하게(v4 의 53 과 v3 의 61 은 conflict), 어느 입력이 메모리에 들든 흘려 읽히든. genTtbarId 나 Expanded_genTtbarId 가 다르면 **멈춘다**(exit 8,
아무것도 쓰지 않음); 같은 두 행은 하나로. `--on-conflict report` 는 세기만 하고(RESULT WARN) 기본값이 아니다. 다른 dataset 의 같은 key 는 두 행이다.
입력마다 entries 가 있어야 하고(0 이면 exit 6), `--expect <dataset>=<entries>` 를 주면 그 dataset 의 entries 합과 견준다(다르면 exit 6); sidecar 파일
하나가 두 입력에(또는 한 입력에 두 번) 있으면 exit 2(정규화한 경로로 비교). 출력은 임시 파일에 쓰고 성공할 때만 `--out` 으로 이름을 바꾼다(있는
`--out` 은 `--replace` 로만). 0 이 아닌 모든 exit 는 마지막 줄 `RESULT FAIL … (exit N)`.
메모리·읽기: dataset 마다 가장 큰 입력(v4)을 흘려 읽고(그 key 의 Bloom filter — 입력 안에서 되풀이될 수 있는 key 가 있으면 그 입력을 한 번 더 읽어
정확히 비교), 나머지(v3)는 모든 행을 32 B 씩 메모리에.

### 5.2 analyzer 계약 (TTHHAnalyzer `include/ExpandedTtbarId.h`, `src/ExpandedTtbarId.cc`, STEP 45)

- **load**: TNamed `lookup_format` 이 없으면 format 1(§1 그대로; `nano_datasets`·`datasetIdx` 가 있으면 E79), `"tthh-ttnb/2"` 이면 format 2,
  다른 값은 E79. format 2 는 `nano_datasets`(빈 줄·중복·`/<primary>/<processed>/NANOAODSIM` 이 아닌 줄 없음)와 `datasetIdx/I`(모든 행이
  범위 안)가 있어야 한다(아니면 E79). map 의 key = `(datasetIdx, run, lumi, event)` — **한 dataset 안의 값이 다른 중복이 E72**, 다른
  dataset 의 같은 (run, lumi, event) 는 중복이 아니다. format 1 의 FNV 해시는 그대로(byte-identical, 00_PROMPT §8); format 2 만 dataset 을 섞는다.
- **era 규칙**: NanoAODv12 era(2022, 2022EE, 2023, 2023BPix)는 format 2 만 — format 1 lookup 은 **E79** 로 멈춘다(`setRequireDatasetKey`).
  Run 2 와 2024 는 format 1 을 지금처럼 읽는다(format 2 도 읽을 수 있다).
- **입력 파일의 dataset**: event loop 전에 job 의 입력 파일마다 NanoAOD dataset 을 정한다(`bindInputs`) — TTHHAnalyzer `include/TtbarVetoKey.h`
  `inputOrigins`, STEP 43 의 event veto 와 **같은 대응**: lxplus wrapper 의 `TTHH_INPUT_LFNS`(복사 방식의 지역 사본), 없으면 입력 경로의
  `/store/mc/<campaign>/<primary>/NANOAODSIM/<processed>/…` 부분 → `/<primary>/<campaign>-<processed>/NANOAODSIM`. dataset 을 정할 수 없거나
  `nano_datasets` 에 없으면 **E78**(job 시작에서).
- **사건마다**: analyzer 가 입력 파일이 바뀔 때마다(`itreestream::number()`) 그 파일을 알리고(`selectInput`), `resolve(run, lumi, event,
  genTtbarId)` 는 지금 파일의 dataset 으로 찾는다 — main·btagtrig·debug(`loop()`)와 prescan(`runPrescan()`) 모두. hit → 저장된
  Expanded_genTtbarId, miss → NanoAOD genTtbarId(§1 과 같다). **genTtbarId self-check(E73)는 그대로**.
- **로그**: `format = 2 (tthh-ttnb/2) ...` 와 dataset 목록, 입력의 dataset 분포 한 줄, 파일이 바뀔 때마다 `input i (<LFN>) -> dataset [d]`, 끝에
  `[TTNB_COVERAGE]`(그대로)와 dataset 마다 `[TTNB_COVERAGE_DS] sample=… ds=d rows=… hits=… calls=…`.

| 검사 (format 2) | 동작 |
|---|---|
| format 1 lookup 을 NanoAODv12 era 에서 / `lookup_format` 이 다른 값 / `nano_datasets`·`datasetIdx` 결함 | exit **79** |
| 입력 파일의 dataset 을 정할 수 없음 / `nano_datasets` 에 없음 / `TTHH_INPUT_LFNS` 가 입력과 다름 | exit **78** |
| 한 dataset 안의 값이 다른 중복 key | exit 72 (format 1 과 같은 번호) |
| hit 의 genTtbarId ≠ NanoAOD | exit 73 (그대로) |

### 5.3 판 A·B 의 입력 (TTHHAnalyzer `tools/lxplus/README.md` §18)

판 A = MiniAODv4(main, ext1; priority 0) + MiniAODv3(main 만, lumi mask; priority 1), 판 B = MiniAODv4 만. MiniAODv3 출력의 사건은 main
NanoAOD dataset 의 사건이므로 `--input` 왼쪽은 **main 의 NanoAOD dataset**. dataset 대응표: TTHHAnalyzer
`docs/claude-remote/daily/lxplus/files/2026-11-04_ttbar_parents/ttbar_crab_table.tsv`(nano_dataset, v4_dataset, v3_dataset). 판의 lookup
디렉터리(`DerivedCorr/expandedTtbarId/<era>_A`, `_B`)의 sha256 은 STEP 43 의 veto index 가 고정한다.

### 5.4 시험

- 생산: `Validation/tests/test_extract_format2.sh <new tool> --old <format 2 전의 도구>`(22 check) — 합성 extend 파일로 v4 우선(v4 가 큰
  입력·작은 입력일 때 모두, 명령줄 순서와 무관), 두 dataset 의 같은 key, 두 입력의 conflict 셋(exit 8, 출력 없음)과 `--on-conflict report`, **한
  입력 안의 같은 key**(tt+nb 둘·tt+nb 와 아닌 것·tt+nb 아닌 둘 — 그 입력이 흘려 읽힐 때와 메모리에 들 때 모두 exit 8; 같은 두 행은 하나), 0 인
  입력과 `--expect`(6), `--replace` 와 임시 파일(4), 같은 sidecar 파일(`..`·`//`·symlink, 한 입력에 두 번; 2), 잘못된 사용·입력(2/3/5/7) — 실패마다
  `RESULT FAIL … (exit N)`, **format 1 = format 2 전의 도구**(stdout·exit code·출력 파일의 md5 — ROOT 의 `?reproducible=` 모드).
- analyzer: TTHHAnalyzer `test/test_ExpandedTtbarId.cc`(단위), `test/offline_smoke/run_offline_smoke.sh` 의 STEP 45 블록(main·ext1 이 같은
  key 를 다른 사건에 쓰는 2022 표본 — 출력이 파일의 dataset 을 따르고 입력 순서와 무관), `run_regression.sh`(Run 2·2024 의 format 1
  lookup 으로 base 와 같음).
