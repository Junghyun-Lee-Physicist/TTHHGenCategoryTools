# 07 — Analyzer integration: patch 파일 소비 계약

> **목적**: 분석 프레임워크(tempTTHH의 `ttHHanalyzer_unified`)가 이 저장소의 산출물을 어떻게 읽어 per-event 확장 id와 stitch weight로 바꾸는지 — 계약과 실제 구현.
> **대상 독자**: analyzer 쪽을 만지는 사람; patch 파일 명명을 바꾸려는 사람(필독).
> **상태**: 소비 방식 DECIDED (D9) · 구현은 tempTTHH에 반영 완료(2026-06) · **명명 rename의 analyzer측 반영은 PROPOSED** (§4).
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
