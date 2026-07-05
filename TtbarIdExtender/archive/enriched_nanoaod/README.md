# archive/enriched_nanoaod — 폐기된 Approach 2의 cfg 원본 (동결)

> **목적**: 폐기된 enriched-NanoAOD 접근의 cmsDriver-emit cfg 4편을 **무수정 보존**한다 (provenance 기록).
> **상태**: DEPRECATED — **실행 금지** (pre-v10 import 경로 `TtbbStudies.NanoExtension` + v10에서 제거된 모듈 의존 → 현 저장소에서 ImportError가 정상).
> **정본 문서**: 파일별 정체·cmsDriver 명령 원문·검증된 것/안 된 것의 경계는 [../../../docs/10_enriched_nanoaod_archive.md](../../../docs/10_enriched_nanoaod_archive.md) — 여기 있는 정보는 그 문서의 축약이다.

| 파일 | 한 줄 정체 |
|---|---|
| `run_enriched_nanoaod_cfg_v8_baseline.py` | cmsDriver emit 원본 (injection 없음) |
| `run_enriched_nanoaod_cfg.py.pre-inject.bak` | v7.2 injection 직전 백업 (내용상 pristine) |
| `run_enriched_nanoaod_cfg_v8.py` | pristine + plain injection (마커 없음) |
| `run_enriched_nanoaod_cfg.py` | pristine + v7.2 마커 injection (`[ttbb-inject]`) — 최종형 |

이 파일들을 고치지 말 것 — "고쳐서 돌아가게" 만든 구성은 검증된 적 없는 새 구성이다. 되살리는 절차는 docs/10 §4.
