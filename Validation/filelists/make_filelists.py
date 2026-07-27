import os
import sys

# ==============================================================================
# [설정] 경로  —  2026-07-26: era(연도) 인자 추가
# ==============================================================================
# 사용법:
#   python make_filelists.py            # 2017 (기존 동작과 동일: nano/ 에 출력)
#   python make_filelists.py 2018       # nano2018/ 에 출력 (2017 파일 보존)
#   python make_filelists.py 2018 /pnfs/.../<다른_소스_디렉토리>
#
# 왜 era 인자가 필요한가: 이전에는 OUTPUT_DIR="nano" 가 고정이어서 다른 연도로
# 실행하면 커밋된 2017 filelist 를 **덮어썼다**. 연도별 디렉토리로 분리한다.
#
# 주의: nano 쪽 입력은 중앙 NanoAOD 가 아니라 사용자 ntuple(forgedNtuple*.root,
# 구 생산은 slimmedNtuple*.root — 둘 다 매칭한다)
# 이다. matchTtbarId 는 run/luminosityBlock/event/genTtbarId 만 읽으므로 중앙
# NanoAODv9 파일 목록을 그대로 써도 동작한다 — 2018 은 아직 자체 ntuple 이 없으면
# 중앙 NanoAOD 경로를 SAMPLE_DIR 로 주거나 filelist 를 직접 작성할 것.
# ==============================================================================
SAMPLE_DIR_BY_ERA = {
    "2017": "/pnfs/knu.ac.kr/data/cms/store/user/junghyun/ttHH2017UL_08thApr2026_v18",
    # 2018: NtupleForge campaign_ttHH2018UL_prescanSlim_v1 (또는 본생산) 출력 경로.
    #       실제 경로 확인 후 수정할 것 — 미확인이므로 기본값은 비워 둔다.
    "2018": "",
}

ERA = sys.argv[1] if len(sys.argv) > 1 else "2017"
if ERA not in SAMPLE_DIR_BY_ERA:
    sys.exit("FATAL: unsupported era '%s' (expected one of %s)"
             % (ERA, sorted(SAMPLE_DIR_BY_ERA)))

SAMPLE_DIR = sys.argv[2] if len(sys.argv) > 2 else SAMPLE_DIR_BY_ERA[ERA]
if not SAMPLE_DIR:
    sys.exit("FATAL: no SAMPLE_DIR for era %s — pass it as the 2nd argument "
             "(python make_filelists.py %s /pnfs/.../<dir>)" % (ERA, ERA))
OUTPUT_DIR = "nano" if ERA == "2017" else "nano%s" % ERA
print("[make_filelists] era=%s  SAMPLE_DIR=%s  OUTPUT_DIR=%s" % (ERA, SAMPLE_DIR, OUTPUT_DIR))

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


# NtupleForge 산출 ntuple 파일명 prefix (analyzer 측 make_filelists.py 와 동일 규약):
#   forgedNtuple  : 2026-07-26 이후 생산 (NtupleForge D-F rename)
#   slimmedNtuple : 그 이전 생산 — 이미 Tier-3 에 있는 파일들의 실제 이름
NTUPLE_PREFIXES = ("forgedNtuple", "slimmedNtuple")


def find_root_files(start_path):
    """주어진 경로 아래의 forgedNtuple*/slimmedNtuple*.root 절대 경로 리스트를 반환"""
    root_files = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file.startswith(NTUPLE_PREFIXES) and file.endswith(".root"):
                absolute_path = os.path.abspath(os.path.join(root, file))
                root_files.append(absolute_path)
    return root_files


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
        print(f"    [WARNING] '{filename}' 생성을 건너뜁니다. (파일 0개)")
        return

    # 1. Master List 작성
    output_path = os.path.join(OUTPUT_DIR, filename)
    with open(output_path, 'w') as f:
        for path in paths:
            f.write(path + '\n')

    # 2. Split 수행
    core_name, count = create_split_files(filename, paths)

    print(f"    [SUCCESS] {filename} ({count} files)")
    print(f"       └─ Split into folder: {OUTPUT_DIR}/{core_name}/ (file_{core_name}_0.txt ...)")


def main():
    print("=" * 60)
    print(f"Start scanning in: {SAMPLE_DIR}")
    print(f"Output Directory : {OUTPUT_DIR}")
    print("=" * 60)

    if not os.path.exists(SAMPLE_DIR):
        print(f"[CRITICAL ERROR] '{SAMPLE_DIR}' 경로가 없습니다.")
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
                print(f"    [WARNING] {dirname} 내부에서 유효한 Data 폴더를 찾지 못했습니다.")

        # MC: 단일 filelist
        else:
            output_filename = f"filelist_{short_name}.txt"
            paths = find_root_files(full_dir_path)
            write_and_split(output_filename, paths)

    print("\n" + "=" * 60)
    print("All tasks finished. Check the output directory.")
    print("=" * 60)


if __name__ == "__main__":
    main()
