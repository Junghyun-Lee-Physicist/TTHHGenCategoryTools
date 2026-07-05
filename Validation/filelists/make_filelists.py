import os

# ==============================================================================
# [설정] 경로
# ==============================================================================
SAMPLE_DIR = "/pnfs/knu.ac.kr/data/cms/store/user/junghyun/ttHH2017UL_08thApr2026_v18"
OUTPUT_DIR = "nano"

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
    """주어진 경로 아래의 slimmedNtuple*.root 파일의 절대 경로를 리스트로 반환"""
    root_files = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file.startswith("slimmedNtuple") and file.endswith(".root"):
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
