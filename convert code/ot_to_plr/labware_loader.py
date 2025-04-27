import json, textwrap
from pathlib import Path
from typing import Dict, Any
from importlib import import_module

LABWARE_CACHE: Dict[str, str] = {}

# NOTE: 不再需要人工维护映射表，保留一个自动记录用
BUILTIN_CLASSMAP: Dict[str, str] = {}

# ------------- helper: runtime probe ---------------------------------
def _probe_builtin(load_name: str) -> str | None:
    """
    返回在 pylabrobot.resources.opentrons 里对应的符号名；
    若不存在返回 None。
    """
    mod = import_module("pylabrobot.resources.opentrons")
    # Opentrons labware 名字通常都是小写，下划线分隔；同时做一次“安全化”
    cand = load_name.replace("-", "_").replace(" ", "_")
    if hasattr(mod, cand):
        return cand
    # 有时文件名里带版本，pylabrobot 侧可能只有前缀，例如 "nest_12_reservoir_15ml_v1"
    # 你可以在这里再加更多花式规则
    return None
# ---------------------------------------------------------------------

def labware_json_to_plr(load_name: str, json_dir: Path = Path(".")) -> str:
    # 缓存
    if load_name in LABWARE_CACHE:
        return LABWARE_CACHE[load_name]

    # 1️⃣ 先探测 pylabrobot 内置器材
    builtin_symbol = _probe_builtin(load_name)
    if builtin_symbol:
        BUILTIN_CLASSMAP[load_name] = builtin_symbol   # 记录给 script_builder 用
        LABWARE_CACHE[load_name] = ""                  # 空串代表“已解决，且不需自定义类”
        return ""

    # 2️⃣ 若内置里没有，再去找 JSON
    custom_dir = Path(__file__).parent / "custom_labware"
    candidates = list(custom_dir.glob(f"**/{load_name}.json")) + list(json_dir.glob(f"**/{load_name}.json"))
    if candidates:
        meta = json.loads(candidates[0].read_text())
    else:
        # 3️⃣ 最后用 opentrons 官方包在线抓取
        from opentrons.protocol_api.labware import get_labware_definition
        try:
            meta = get_labware_definition(load_name)
        except Exception as e:
            raise FileNotFoundError(f"Labware '{load_name}' not found locally or online: {e}")

    # ……以下保持不变：生成 WellPlate 子类代码
    wells = meta["wells"]
    first = wells[next(iter(wells))]
    depth = first["depth"]
    if "diameter" in first:
        size_x = size_y = first["diameter"]
    else:
        size_x = first["xDimension"]
        size_y = first["yDimension"]

    code = textwrap.dedent(f"""
class {load_name}(WellPlate):
    def __init__(self, name: str="{load_name}", size_x={meta["dimensions"]["xDimension"]},
                 size_y={meta["dimensions"]["yDimension"]}, size_z={meta["dimensions"]["zDimension"]}):
        super().__init__(name=name, size_x=size_x, size_y=size_y, size_z=size_z)
""")
    for w, spec in wells.items():
        code += f'        self.add_child(Well(name="{w}", size_x={size_x}, size_y={size_y}, size_z={depth}, ' \
                f'location=Coordinate({spec["x"]:.2f}, {spec["y"]:.2f}, {spec["z"]:.2f}))\\n'
    
    LABWARE_CACHE[load_name] = code
    return code