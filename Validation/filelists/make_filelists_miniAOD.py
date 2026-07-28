import os
import re

# ==============================================================================
# [설정] 경로
# ==============================================================================
# NOTE (v12 rename): the 2026-06 검증에 쓴 production sidecar 데이터는 rename 이전 경로
#   .../ExtendedTtbarId/sidecar/2017 에 물리적으로 그대로 있습니다. rename 은 코드/설정
#   문자열만 바꿀 뿐 Tier3 데이터를 옮기지 않으므로, 기존 검증 filelist 를 재생성할 때는
#   이 SAMPLE_DIR 을 실제 데이터 위치(구 경로)로 둡니다. 앞으로 TtbarIdExtender 로 새로
#   제출하는 CRAB job 의 출력은 site_config.yaml 의 새 LFN(.../TTHHGenCategoryTools/ttbarIdExtend)
#   으로 저장되므로, 그때는 이 값을 새 경로로 바꾸세요.
# 2026-07-26: era(연도) 인자 추가. 이전에는 OUTPUT_DIR="sidecar" 고정이어서 다른
# 연도로 실행하면 커밋된 2017 filelist 를 덮어썼다.
#   python make_filelists_miniAOD.py            # 2017 (기존 동작: sidecar/)
#   python make_filelists_miniAOD.py 2018       # sidecar2018/
#   python make_filelists_miniAOD.py 2018 /pnfs/.../<다른_경로>
import sys

# -----------------------------------------------------------------------------
# stdout encoding safety net (2026-07-27)
# -----------------------------------------------------------------------------
# lxplus runs with LANG=C, which makes sys.stdout's encoding ASCII. ANY print()
# of a non-ASCII character then raises UnicodeEncodeError -- and this script does
# real work (writes filelists sample by sample), so such a crash leaves a
# HALF-FINISHED output directory. That is exactly what happened on 2026-07-27:
# a box-drawing character in the "Split into folder" line killed the run right
# after filelist_TTTo2L2Nu.txt was written, with 6 samples still to go.
#
# Two layers:
#   1) every printed string in this file is now pure ASCII  <- the real fix
#   2) this shim degrades a future stray non-ASCII to '?' instead of aborting
# NOTE: making the SOURCE ascii-clean is not sufficient by itself -- a literal
# "\u2514" escape is ascii in the file but still non-ascii at print() time.
# py3.6-compatible (sys.stdout.reconfigure() is 3.7+).
try:
    import io as _io
    _enc = (getattr(sys.stdout, "encoding", None) or "").lower().replace("-", "_")
    if _enc in ("ascii", "us_ascii", "ansi_x3.4_1968"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="ascii",
                                       errors="replace", line_buffering=True)
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="ascii",
                                       errors="replace", line_buffering=True)
except Exception:
    pass        # never let the safety net itself break the script

SAMPLE_DIR_BY_ERA = {
    # 2017: rename 이전 경로에 실데이터가 그대로 있음 (위 NOTE 참조)
    "2017": "/pnfs/knu.ac.kr/data/cms/store/user/junghyun/ExtendedTtbarId/sidecar/2017",
    # 2018: TtbarIdExtender 신규 제출의 출력 = site_config.yaml 의 out_lfn_base + /2018
    #       (submit_ttbarIdExtend.py 가 outLFNDirBase = <base>/<era> 로 만든다)
    # ⚠ 아래 기본값은 **KNU T3 마운트 경로**를 가정한다. 현재
    #   TtbarIdExtender/crab/site_config.yaml 의 storage_site 는 "T3_CH_CERNBOX" 이므로
    #   실제 stage-out 은 CERN EOS(/eos/user/<i>/<user>/...) 로 간다. 제출 site 를
    #   바꾸지 않았다면 2번째 인자로 실제 경로를 넘길 것:
    #     python make_filelists_miniAOD.py 2018 /eos/user/j/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2018
    "2018": "/pnfs/knu.ac.kr/data/cms/store/user/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2018",
}

ERA = sys.argv[1] if len(sys.argv) > 1 else "2017"
if ERA not in SAMPLE_DIR_BY_ERA:
    sys.exit("FATAL: unsupported era '%s' (expected one of %s)"
             % (ERA, sorted(SAMPLE_DIR_BY_ERA)))
SAMPLE_DIR = sys.argv[2] if len(sys.argv) > 2 else SAMPLE_DIR_BY_ERA[ERA]
OUTPUT_DIR = "sidecar" if ERA == "2017" else "sidecar%s" % ERA
print("[make_filelists_miniAOD] era=%s  SAMPLE_DIR=%s  OUTPUT_DIR=%s"
      % (ERA, SAMPLE_DIR, OUTPUT_DIR))

# ==============================================================================
# [샘플 매핑] 디렉토리 이름 -> 출력 short name
#   - Data 샘플은 short_name 을 None 으로 두면 Run2017 period 별로 분할 처리됨.
#   - MC 샘플은 short_name 을 그대로 filelist 파일명에 사용함.
# ==============================================================================
sample_mapping = {

    # ttbar (Powheg inclusive)
    "TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8":        "TTTo2L2Nu",
    "TTToHadronic_TuneCP5_13TeV-powheg-pythia8":     "TTToHadronic",
    "TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8": "TTToSemiLeptonic",

    # ttbb (4F dedicated)
    "TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8":     "ttbb_Hadronic",
    "TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8": "ttbb_SemiLeptonic",
    "TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8":        "ttbb_2L2Nu",

    # tt4b
    "TT4b_TuneCP5_13TeV_madgraph_pythia8": "tt4b",
}


def find_root_files(start_path):
    """주어진 경로 아래의 ttbarIDExtend*/sidecar*.root 절대 경로 리스트를 반환
    (이 스크립트는 extend/sidecar 산출물 전용 — ntuple 쪽은 make_filelists.py)"""
    root_files = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if (file.startswith("ttbarIDExtend") or file.startswith("sidecar")) and file.endswith(".root"):  # 신규 출력명 + 구 production(sidecar*) 둘 다 매칭
                absolute_path = os.path.abspath(os.path.join(root, file))
                root_files.append(absolute_path)
    return root_files


CRAB_TS_RE = re.compile(r"/(\d{6}_\d{6})/")


def check_single_crab_submission(short_name, paths):
    """CRAB timestamp 디렉토리가 샘플당 1개인지 확인하고, 여러 개면 FATAL.

    왜 필요한가 (2026-07-27 실사고):
      CRAB LFN 은 <primary>/<outputDatasetTag>/<TIMESTAMP>/0000/ 이다. 같은 dataset 을
      두 번 제출하면(예: --max-files 로 부분 task 를 돌린 뒤 다시 전체 제출, 또는 task 를
      kill 하지 않고 project dir 만 지운 뒤 재제출) timestamp 디렉토리가 2개가 되고,
      os.walk 는 **둘 다** 주워온다. 그러면 겹치는 event 가 filelist 에 두 번 들어가
      한참 뒤에야 `matchTtbarId` 가 exit 7 (3-key 중복) 로 죽는다 — 원인 추적이 매우 번거롭다.
      여기서 즉시 잡는 편이 훨씬 싸다.

    의도적으로 여러 제출을 합치려면 환경변수로 우회:
      ALLOW_MULTI_CRAB_SUBMISSION=1 python make_filelists_miniAOD.py 2018 ...
    """
    stamps = sorted({m.group(1) for p in paths for m in [CRAB_TS_RE.search(p)] if m})
    if len(stamps) <= 1:
        return stamps
    print("")
    print("=" * 78)
    print(f"[FATAL] {short_name}: found {len(stamps)} CRAB timestamp dir(s) -> {stamps}")
    print("        The same dataset was submitted twice. Using this list would give")
    print("        duplicate events -> matchTtbarId dies with exit 7 (3-key duplicate).")
    print("        ACTION: delete the unwanted timestamp dir(s), then re-run. e.g.")
    for st in stamps:
        ex = next(p for p in paths if f"/{st}/" in p)
        root = ex.split(f"/{st}/")[0]
        n = sum(1 for p in paths if f"/{st}/" in p)
        print(f"          rm -rf {root}/{st}     # files={n}")
    print("        Keep exactly ONE timestamp dir per sample.")
    print("        If the overlap is intentional, re-run with")
    print("          ALLOW_MULTI_CRAB_SUBMISSION=1 python3 make_filelists_miniAOD.py ...")
    print("=" * 78)
    if os.environ.get("ALLOW_MULTI_CRAB_SUBMISSION") != "1":
        sys.exit(3)
    print("[WARN] ALLOW_MULTI_CRAB_SUBMISSION=1 -> continuing despite duplicate risk")
    return stamps


def create_split_files(filename, paths):
    """
    1. filelist_NAME.txt -> NAME 디렉토리 생성
    2. 경로 리스트를 하나씩 쪼개서 file_NAME_0.txt 등으로 저장
    """
    base_name = os.path.splitext(filename)[0]

    if base_name.startswith("filelist_"):
        core_name = base_name.replace("filelist_", "")
    else:
        core_name = base_name

    split_dir_path = os.path.join(OUTPUT_DIR, core_name)

    if not os.path.exists(split_dir_path):
        os.makedirs(split_dir_path)

    for i, path in enumerate(paths):
        individual_filename = f"file_{core_name}_{i}.txt"
        individual_filepath = os.path.join(split_dir_path, individual_filename)

        with open(individual_filepath, 'w') as f:
            f.write(path + '\n')

    return core_name, len(paths)


def write_and_split(filename, paths):
    """Master List 작성 후 바로 Split 수행"""
    if not paths:
        print(f"    [WARNING] skipping '{filename}': 0 files found")
        return

    # 1. Master List 작성
    output_path = os.path.join(OUTPUT_DIR, filename)
    with open(output_path, 'w') as f:
        for path in paths:
            f.write(path + '\n')

    # 2. Split 수행
    core_name, count = create_split_files(filename, paths)

    print(f"    [SUCCESS] {filename} ({count} files)")
    print(f"       \\_ Split into folder: {OUTPUT_DIR}/{core_name}/ (file_{core_name}_0.txt ...)")


def main():
    print("=" * 60)
    print(f"Start scanning in: {SAMPLE_DIR}")
    print(f"Output Directory : {OUTPUT_DIR}")
    print("=" * 60)

    if not os.path.exists(SAMPLE_DIR):
        print(f"[CRITICAL ERROR] SAMPLE_DIR does not exist: '{SAMPLE_DIR}'")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for dirname, short_name in sample_mapping.items():
        full_dir_path = os.path.join(SAMPLE_DIR, dirname)

        if not os.path.exists(full_dir_path):
            print(f"[MISSING] Directory not found: {dirname}")
            continue

        print(f"-> [PROCESSING] {dirname} ...")

        # Data: Run2017 period(B/C/D/E/F)별로 분할
        if short_name is None:
            process_prefix = dirname
            try:
                subdirs = [d for d in os.listdir(full_dir_path)
                           if os.path.isdir(os.path.join(full_dir_path, d))]
            except Exception:
                subdirs = []

            data_found = False
            for subdir in subdirs:
                if "Run2017" in subdir:
                    period = subdir[-1]
                    output_filename = f"filelist_{process_prefix}_{period}.txt"
                    paths = find_root_files(os.path.join(full_dir_path, subdir))
                    if paths:
                        write_and_split(output_filename, paths)
                        data_found = True

            if not data_found:
                print(f"    [WARNING] {dirname}: no valid Data subfolder found")

        # MC: 단일 filelist
        else:
            output_filename = f"filelist_{short_name}.txt"
            paths = find_root_files(full_dir_path)
            if paths:
                stamps = check_single_crab_submission(short_name, paths)
                if stamps:
                    print(f"    [crab] {short_name}: submission timestamp {stamps[0]}")
            write_and_split(output_filename, paths)

    print("\n" + "=" * 60)
    print("All tasks finished. Check the output directory.")
    print("=" * 60)


if __name__ == "__main__":
    main()
