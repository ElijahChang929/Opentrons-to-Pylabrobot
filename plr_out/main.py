import argparse
from pathlib import Path
from script_builder import generate_plr_script
import traceback
from transform import transform_explicit
def main():

    ap = argparse.ArgumentParser(description="OT-to-PLR converter")
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--outdir", default="../../plr_out", type=Path)
    args = ap.parse_args()

    for p in args.paths:

        try:
            code_expended = transform_explicit(p)
            # write the expanded code to a temporary file
            with open(args.outdir / p.name, "w") as f:
                f.write(code_expended)

            #generate_plr_script(code_expended, args.outdir, p)
        except Exception as e:
            traceback.print_exc()
            print(f"[ERROR] Failed to process {p}: {e}")

if __name__ == "__main__":
    main()


# python main.py "../../OT examples/sci-lucif-assay4.py"