import ast
from typing import List

def generate_steps(steps: List[ast.Call]) -> List[str]:
    lines = []

    def _kw_string(call: ast.Call) -> str:
        if not call.keywords:
            return ""
        parts = [f"{kw.arg}={ast.unparse(kw.value)}" for kw in call.keywords]
        return ", " + ", ".join(parts)

    for call in steps:
        fun = call.func.attr
        tgt = ast.unparse(call.func.value)
        kw = _kw_string(call)

        if fun == "transfer":
            src, dst, vol = map(ast.unparse, call.args[:3])
            lines.append(f"await lh.transfer({src}, {dst}, volume={vol}{kw}, pipette={tgt})")
        elif fun == "aspirate":
            src, vol = map(ast.unparse, call.args[:2])
            lines.append(f"await lh.aspirate({src}, {vol}{kw}, pipette={tgt})")
        elif fun == "dispense":
            dst, vol = map(ast.unparse, call.args[:2])
            lines.append(f"await lh.dispense({dst}, {vol}{kw}, pipette={tgt})")
        elif fun == "mix":
            reps, vol, loc = map(ast.unparse, call.args[:3])
            lines.append(f"await lh.mix({loc}, repetitions={reps}, volume={vol}{kw}, pipette={tgt})")
        elif fun == "pick_up_tip":
            lines.append(f"{tgt}.pick_up_tip({kw.lstrip(', ')})")
        elif fun == "drop_tip":
            lines.append(f"{tgt}.drop_tip({kw.lstrip(', ')})")
    return lines