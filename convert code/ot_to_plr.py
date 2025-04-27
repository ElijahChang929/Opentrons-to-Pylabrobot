#!/usr/bin/env python3
"""
ot_to_plr.py  ——  Batch-convert Opentrons v2 protocols to pylabrobot scripts.

Usage
-----
$ python ot_to_plr.py my_protocol.py another_protocol.py  ...  --outdir converted/

Requirements
------------
pip install pylabrobot opentrons==7.* (for the AST grammar only, 无需接硬件)
"""

import ast, argparse, json, textwrap
from pathlib import Path
from typing import Dict, List, Tuple, Any

# ------------- 1. 解析 Opentrons 协议 -----------------------------

class OTAnalyzer(ast.NodeVisitor):
    """Walk an OT-2 protocol script and collect semantic info."""
    def __init__(self):
        self.labware: List[Tuple[str, str, str]] = []    # [(var, load_name, slot)]
        self.tipracks: Dict[str, str] = {}               # var -> slot
        self.pipettes: Dict[str, Dict[str, Any]] = {}    # var -> {...}
        self.steps: List[ast.Call] = []                  # pipetting calls

    # ------ helpers ------
    def _const(self, node):
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Str):  # For older Python versions
            return node.s
        else:
            print(f"[DEBUG] Unexpected node type in _const: {ast.dump(node)}")
            raise ValueError("Expect constant")

    # ------ visit methods ------
    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            tgt, fname = node.func.value.id, node.func.attr  # e.g. protocol.load_labware
            # 1) labware
            if tgt == "protocol" and fname == "load_labware":
                load_name  = self._const(node.args[0])
                slot       = self._const(node.args[1])
                varname    = self._const(node.keywords[0].value) if node.keywords else f"{load_name}_{slot}"
                self.labware.append((varname, load_name, slot))
            # 2) instrument
            elif tgt == "protocol" and fname == "load_instrument":
                model  = self._const(node.args[0])
                mount  = self._const(node.keywords[0].value)
                var    = ast.get_source_segment(source, node).split('=')[0].strip()
                self.pipettes[var] = {"model": model, "mount": mount, "tip_racks": []}
            # 3) tipracks稍后补 slot
            elif fname == "transfer" or fname in {"aspirate", "dispense", "mix", "pick_up_tip", "drop_tip"}:
                self.steps.append(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # 捕捉 tiprack = protocol.load_labware(...) 对象名称
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            if node.value.func.attr == "load_labware":
                load_name = self._const(node.value.args[0])
                if "tiprack" in load_name:
                    var = node.targets[0].id
                    slot = self._const(node.value.args[1])
                    self.tipracks[var] = slot
        self.generic_visit(node)

# ------------- 2. labware JSON -> pylabrobot Resource ----------------

LABWARE_CACHE: Dict[str, str] = {}

def labware_json_to_plr(load_name: str, json_dir: Path = Path(".")) -> str:
    """Return Python code that instantiates a PLR Resource for this labware."""
    if load_name in LABWARE_CACHE:      # 已经转换过
        return LABWARE_CACHE[load_name]

    # Use the 'custom_labware' folder in the same directory as the script
    custom_labware_dir = Path(__file__).parent / "custom_labware"
    json_path = next(custom_labware_dir.glob(f"**/{load_name}.json"), None)
    if not json_path:
        raise FileNotFoundError(f"Labware JSON file '{load_name}.json' not found in 'custom_labware' directory.")

    meta = json.loads(json_path.read_text())

    wells = meta["wells"]
    cols = sorted({w[1:] for w in wells})
    rows = sorted({w[0] for w in wells})
    # 简化：深度、直径 取第一个孔的值
    first = wells[next(iter(wells))]
    depth, diam = first["depth"], first["diameter"]

    code = textwrap.dedent(f"""
        class {load_name}(WellPlate):
            def __init__(self, name: str="{load_name}", size_x={meta["dimensions"]["xDimension"]},
                         size_y={meta["dimensions"]["yDimension"]}, size_z={meta["dimensions"]["zDimension"]}):
                super().__init__(name=name, size_x=size_x, size_y=size_y, size_z=size_z)
                # auto-generated wells
    """)
    for w, spec in wells.items():
        code += f'                self.add_child(Well(name="{w}", size_x={diam}, size_y={diam}, size_z={depth}, ' \
                f'location=Coordinate({spec["x"]:.2f}, {spec["y"]:.2f}, {spec["z"]:.2f})))\n'

    LABWARE_CACHE[load_name] = code
    return code

# ------------- 3. 将步骤翻译成 pylabrobot 调用 ----------------------

def generate_steps(an: OTAnalyzer) -> List[str]:
    plr_lines = []
    for call in an.steps:
        fun = call.func.attr
        tgt = call.func.value.id               # pipette var
        if fun == "transfer":
            vol = ast.unparse(call.args[2])
            src = ast.unparse(call.args[0])
            dst = ast.unparse(call.args[1])
            plr_lines.append(f'lh.transfer({src}, {dst}, volume={vol}, pipette={tgt})')
        elif fun == "aspirate":
            vol = ast.unparse(call.args[1])
            src = ast.unparse(call.args[0])
            plr_lines.append(f'lh.aspirate({src}, {vol}, pipette={tgt})')
        elif fun == "dispense":
            vol = ast.unparse(call.args[1])
            dst = ast.unparse(call.args[0])
            plr_lines.append(f'lh.dispense({dst}, {vol}, pipette={tgt})')
        elif fun == "mix":
            reps = ast.unparse(call.args[0]); vol = ast.unparse(call.args[1]); loc = ast.unparse(call.args[2])
            plr_lines.append(f'lh.mix({loc}, repetitions={reps}, volume={vol}, pipette={tgt})')
        elif fun == "pick_up_tip":
            plr_lines.append(f'{tgt}.pick_up_tip()')
        elif fun == "drop_tip":
            plr_lines.append(f'{tgt}.drop_tip()')
    return plr_lines

# ------------- 4. 组装完整 pylabrobot 脚本 -------------------------

def generate_plr_script(ot_path: Path, outdir: Path):
    global source
    source = ot_path.read_text()
    tree = ast.parse(source)
    analyzer = OTAnalyzer(); analyzer.visit(tree)

    # Build labware classes
    labware_defs = "\n".join(
        labware_json_to_plr(load_name) for _, load_name, _ in analyzer.labware
    )

    # Deck + resources
    deck_lines = ["deck = Deck()", "lh = LiquidHandler(backend=SerialOT2Backend(port=None))  # 改为真实端口"]
    for var, load_name, slot in analyzer.labware:
        deck_lines.append(f'{var} = {load_name}()')
        deck_lines.append(f'deck.assign_child_at_slot({var}, slot={slot})')

    # Tipracks
    for var, slot in analyzer.tipracks.items():
        deck_lines.append(f'{var} = TipRack(name="{var}")')
        deck_lines.append(f'deck.assign_child_at_slot({var}, slot={slot})')

    # Pipettes
    for var, info in analyzer.pipettes.items():
        deck_lines.append(f'{var} = lh.setup_pipette(model="{info["model"]}", mount="{info["mount"]}")')

    # Steps
    step_lines = generate_steps(analyzer)

    template = f"""
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import SerialOT2Backend
from pylabrobot.liquid_handling.resources import Deck, Well, WellPlate, TipRack, Coordinate

{labware_defs}

def main():
    {'; '.join(deck_lines)}
    lh.setup()

    # -- protocol steps converted automatically --
    {'; '.join(step_lines)}

    lh.teardown()

if __name__ == "__main__":
    main()
"""
    outdir.mkdir(exist_ok=True)
    out_path = outdir / (ot_path.stem + "_plr.py")
    out_path.write_text(textwrap.dedent(template))
    print(f"[✓] {ot_path.name}  →  {out_path}")

# ------------- 5. CLI wrapper --------------------------------------

if __name__ == "__main__":
    print("OT-to-pylabrobot batch converter")
    print("=========================================")
    ap = argparse.ArgumentParser(description="OT-to-pylabrobot batch converter")
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--outdir", default="../plr_out", type=Path)
    args = ap.parse_args()
    for p in args.paths:
        try:
            generate_plr_script(p, args.outdir)
        except Exception as e:
            print(f"[ERROR] Failed to process {p}: {e}")