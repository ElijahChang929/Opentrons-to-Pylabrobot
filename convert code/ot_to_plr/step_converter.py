import ast
import re
from typing import List, Tuple, Optional, Dict, Any, Set

def extract_position_modifiers(src_expr: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Extract base well, offset, and liquid_height from an OT position expression."""
    offset_x = 0
    offset_y = 0
    offset_z = 0
    liquid_height = None
    # Extract .top(z=...)
    top_match = re.search(r'\.top\(z=([+-]?[0-9.]+)\)', src_expr)
    if top_match:
        offset_z = float(top_match.group(1))
        src_expr = re.sub(r'\.top\(z=[+-]?[0-9.]+\)', '', src_expr)
    # Extract .bottom(z=...)
    bottom_match = re.search(r'\.bottom\(z=([+-]?[0-9.]+)\)', src_expr)
    if bottom_match:
        liquid_height = bottom_match.group(1)
        src_expr = re.sub(r'\.bottom\(z=[+-]?[0-9.]+\)', '', src_expr)
    # Extract .move(Point(...))
    point_match = re.search(r'\.move\(Point\((.*?)\)\)', src_expr)
    if point_match:
        point_args = point_match.group(1)
        x_match = re.search(r'x=([+-]?[0-9.]+)', point_args)
        if x_match:
            offset_x = float(x_match.group(1))
        y_match = re.search(r'y=([+-]?[0-9.]+)', point_args)
        if y_match:
            offset_y = float(y_match.group(1))
        z_match = re.search(r'z=([+-]?[0-9.]+)', point_args)
        if z_match:
            offset_z = float(z_match.group(1))
        src_expr = re.sub(r'\.move\(Point\(.*?\)\)', '', src_expr)
    src_expr = re.sub(r'\.(top|bottom)\(\)', '', src_expr)
    base_well = src_expr.split('.')[0].strip()
    offset = f"Coordinate({offset_x}, {offset_y}, {offset_z})" if (offset_x != 0 or offset_y != 0 or offset_z != 0) else None
    print(f"[DEBUG] extract_position_modifiers: src_expr={src_expr}, base_well={base_well}, offset={offset}, liquid_height={liquid_height}")
    return base_well, offset, liquid_height

def extract_call_args(call: ast.Call) -> Tuple[str, str]:
    """Extracts the first two positional arguments as strings."""
    if len(call.args) < 2:
        return '', ''
    return ast.unparse(call.args[0]), ast.unparse(call.args[1])

def build_plr_call(
    func: str,
    well: str,
    vol: str,
    flow_rate: Optional[str] = None,
    offset: Optional[str] = None,
    liquid_height: Optional[str] = None,
    blow_out_vol: Optional[str] = None
) -> str:
    """Builds a PLR call string for aspirate/dispense."""
    args = [f'[{well}]', f'[{vol}]']
    if flow_rate:
        args.append(f'flow_rates=[{flow_rate}]')
    if offset:
        args.append(f'offsets=[{offset}]')
    if liquid_height:
        args.append(f'liquid_height=[{liquid_height}]')
    if blow_out_vol:
        args.append(f'blow_out_air_volume=[{blow_out_vol}]')
    call_str = f"await lh.{func}({', '.join(args)})"
    print(f"[DEBUG] build_plr_call: {call_str}")
    return call_str

def handle_variable_assignment(call, lines, variable_mappings, defined_variables):
    target_name = call.targets[0].id
    value = ast.unparse(call.value)
    variable_mappings[target_name] = value
    if target_name not in defined_variables:
        lines.append(f"{target_name} = {value}")
        defined_variables.add(target_name)

def generate_steps(steps: List[ast.Call]) -> List[str]:
    lines = []
    variable_mappings: Dict[str, str] = {}
    defined_variables: Set[str] = set()
    loop_variables: Dict[str, List[str]] = {}

    # 1. 变量赋值和循环变量处理
    for call in steps:
        if isinstance(call, ast.Assign) and isinstance(call.targets[0], ast.Name):
            handle_variable_assignment(call, lines, variable_mappings, defined_variables)
            continue
        if hasattr(call, 'target') and hasattr(call, 'value'):
            if isinstance(call.target, ast.Name) and isinstance(call.value, ast.Subscript):
                handle_variable_assignment(call, lines, variable_mappings, defined_variables)
                continue

    # 2. 处理所有的函数调用
    for call in steps:
        if isinstance(call, ast.Assign) or hasattr(call, 'target'):
            continue
        if not hasattr(call, 'func') or not hasattr(call.func, 'attr'):
            continue
        fun = call.func.attr
        print(f"[DEBUG] Processing function: {fun}")
        if fun in ("aspirate", "dispense"):
            pos_arg, vol_arg = extract_call_args(call)
            print(f"[DEBUG] {fun} pos_arg={pos_arg}, vol_arg={vol_arg}")
            well, offset, liquid_height = extract_position_modifiers(pos_arg)
            if well in variable_mappings:
                well = variable_mappings[well]
            flow_rate = None
            blow_out_vol = None
            for kw in call.keywords:
                if kw.arg in ("rate", "flow_rate"):
                    flow_rate = ast.unparse(kw.value)
                if kw.arg == "air_gap":
                    blow_out_vol = ast.unparse(kw.value)
            plr_call = build_plr_call(fun, well, vol_arg, flow_rate, offset, liquid_height, blow_out_vol)
            lines.append(plr_call)
        elif fun == "pick_up_tip":
            lines.append("await lh.pick_up_tips(next(tips))")
        elif fun == "drop_tip":
            lines.append("await lh.discard_tips()")
        # ... 其他操作同理 ...
    return lines