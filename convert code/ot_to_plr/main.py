import argparse
from pathlib import Path
from script_builder import generate_plr_script
import traceback
def main():
    ap = argparse.ArgumentParser(description="OT-to-PLR converter")
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--outdir", default="../../plr_out", type=Path)
    args = ap.parse_args()

    for p in args.paths:
        try:
            generate_plr_script(p, args.outdir)
        except Exception as e:
            traceback.print_exc()
            print(f"[ERROR] Failed to process {p}: {e}")

if __name__ == "__main__":
    main()


# python main.py "../../OT examples/sci-lucif-assay4.py"