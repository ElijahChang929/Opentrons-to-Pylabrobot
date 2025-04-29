import ast
import re
from typing import List

def generate_steps(steps: List[ast.Call]) -> List[str]:
    lines = []

    def _extract_rate(keywords, default_key="rate"):
        """Extract rate or flow_rate from keywords"""
        for kw in keywords:
            if kw.arg == "rate" or kw.arg == "flow_rate":
                return ast.unparse(kw.value)
        return None

    for call in steps:
        fun = call.func.attr if hasattr(call.func, 'attr') else None
        if fun is None:
            continue
            
        tgt = ast.unparse(call.func.value)
        
        if fun == "transfer":
            src, dst, vol = map(ast.unparse, call.args[:3])
            # PyLabRobot transfer needs source, destination wells as lists
            lines.append(f"await lh.transfer({src}, [{dst}], source_vol={vol})")
            
        elif fun == "aspirate" and len(call.args) >= 2:
            # Opentrons aspirate顺序: (volume, location, rate=...)
            # 正确的顺序是 call.args[0] = 体积, call.args[1] = 位置
            vol = ast.unparse(call.args[0])  # 体积是第一个参数
            location_expr = ast.unparse(call.args[1])  # 位置是第二个参数
            
            # 提取基本位置（井名）
            base_location = location_expr.split('.')[0]
            
            # 提取偏移量
            offsets = {}
            
            # 检查z偏移量
            z_match = re.search(r'(?:top|bottom)\(z\s*=\s*(-?\d+\.?\d*)\)', location_expr)
            if z_match:
                offsets['z'] = z_match.group(1)
            
            # 检查x,y偏移量
            if '.move(Point(' in location_expr:
                x_match = re.search(r'x\s*=\s*(-?\d+\.?\d*)', location_expr)
                if x_match:
                    offsets['x'] = x_match.group(1)
                
                y_match = re.search(r'y\s*=\s*(-?\d+\.?\d*)', location_expr)
                if y_match:
                    offsets['y'] = y_match.group(1)
            
            # 构建偏移参数
            offset_arg = ""
            if offsets:
                coords_parts = []
                for axis in ['x', 'y', 'z']:
                    if axis in offsets:
                        coords_parts.append(f"{axis}={offsets[axis]}")
                
                if coords_parts:
                    offset_arg = f", offsets=[Coordinate({', '.join(coords_parts)})]"
            
            # 提取流速
            flow_rate = _extract_rate(call.keywords)
            flow_rate_arg = f", flow_rates=[{flow_rate}]" if flow_rate else ""
            
            # 检查air_gap
            blow_out_vol = None
            for kw in call.keywords:
                if kw.arg == "air_gap":
                    blow_out_vol = ast.unparse(kw.value)
            
            blow_out_arg = f", blow_out_air_volume=[{blow_out_vol}]" if blow_out_vol else ""
            
            # 生成最终的PLR命令 - PyLabRobot的参数顺序是(resources, volumes, offsets, ...)
            # 注意: PyLabRobot期望的是 lh.aspirate([volume], [location], ...)，所以我们需要把参数放在列表中
            lines.append(f"await lh.aspirate([{base_location}], [{vol}]{offset_arg}{flow_rate_arg}{blow_out_arg})")
            
        elif fun == "dispense" and len(call.args) >= 2:
            # Opentrons dispense顺序: (volume, location, rate=...)
            # 正确的顺序是 call.args[0] = 体积, call.args[1] = 位置
            vol = ast.unparse(call.args[0])  # 体积是第一个参数
            location_expr = ast.unparse(call.args[1])  # 位置是第二个参数
            
            # 提取基本位置（井名）- 修复为正确的井名，例如从waste.top(z=-5)提取waste
            base_location = location_expr.split('.')[0]
            
            # 提取偏移量
            offsets = {}
            
            # 检查z偏移量
            z_match = re.search(r'(?:top|bottom)\(z\s*=\s*(-?\d+\.?\d*)\)', location_expr)
            if z_match:
                offsets['z'] = z_match.group(1)
            
            # 检查x,y偏移量
            if '.move(Point(' in location_expr:
                x_match = re.search(r'x\s*=\s*(-?\d+\.?\d*)', location_expr)
                if x_match:
                    offsets['x'] = x_match.group(1)
                
                y_match = re.search(r'y\s*=\s*(-?\d+\.?\d*)', location_expr)
                if y_match:
                    offsets['y'] = y_match.group(1)
            
            # 构建偏移参数
            offset_arg = ""
            if offsets:
                coords_parts = []
                for axis in ['x', 'y', 'z']:
                    if axis in offsets:
                        coords_parts.append(f"{axis}={offsets[axis]}")
                
                if coords_parts:
                    offset_arg = f", offsets=[Coordinate({', '.join(coords_parts)})]"
            
            # 提取流速
            flow_rate = _extract_rate(call.keywords)
            flow_rate_arg = f", flow_rates=[{flow_rate}]" if flow_rate else ""
            
            # 检查blow_out
            blow_out_vol = None
            for kw in call.keywords:
                if kw.arg == "blow_out":
                    blow_out_vol = "20"  # 默认值
            
            blow_out_arg = f", blow_out_air_volume=[{blow_out_vol}]" if blow_out_vol else ""
            
            # 生成最终的PLR命令 - PyLabRobot的参数顺序是(resources, volumes, offsets, ...)
            # 注意: PyLabRobot期望的是 lh.dispense([volume], [location], ...)，所以我们需要把参数放在列表中
            lines.append(f"await lh.dispense([{base_location}], [{vol}]{offset_arg}{flow_rate_arg}{blow_out_arg})")
            
        elif fun == "mix":
            if len(call.args) >= 3:
                reps, vol, loc = map(ast.unparse, call.args[:3])
                flow_rate = _extract_rate(call.keywords)
                flow_rate_arg = f", flow_rates=[{flow_rate}]" if flow_rate else ""
                
                lines.append(f"await lh.mix([{loc}], repetitions={reps}, volume={vol}{flow_rate_arg})")
            else:
                # Handle case with fewer arguments
                lines.append(f"# WARNING: Incomplete mix command: {ast.unparse(call)}")
                
        elif fun == "pick_up_tip":
            # For pick_up_tip, we need to use next(tips) for tip tracking
            lines.append(f"await lh.pick_up_tips(next(tips))")
            
        elif fun == "drop_tip":
            lines.append(f"await lh.discard_tips()")
            
        elif fun == "blow_out":
            # Handle blow_out if needed
            if call.args:
                dst = ast.unparse(call.args[0])
                lines.append(f"# Blow out to {dst} - handled in dispense")
            else:
                lines.append("# Blow out - handled in dispense")
                
        elif fun == "touch_tip":
            # Touch tip doesn't have a direct equivalent - could be converted to a comment
            lines.append("# touch_tip operation (not directly supported in PyLabRobot)")
            
        elif fun == "delay" or fun == "comment":
            # Handle delays - convert ctx.delay to await asyncio.sleep
            if fun == "delay" and call.args:
                time_val = None
                for kw in call.keywords:
                    if kw.arg in ["seconds", "minutes", "hours"]:
                        multiplier = 1
                        if kw.arg == "minutes":
                            multiplier = 60
                        elif kw.arg == "hours":
                            multiplier = 3600
                        time_val = f"{ast.unparse(kw.value)} * {multiplier}"
                        break
                
                if time_val:
                    lines.append(f"await asyncio.sleep({time_val})")
                else:
                    lines.append(f"# WARNING: Unsupported delay: {ast.unparse(call)}")
            elif fun == "comment":
                # Fix the problematic f-string with backslash
                if call.args:
                    comment_val = ast.unparse(call.args[0])
                    # Replace double and single quotes but without using backslash in f-string
                    comment_val = comment_val.replace('"', '').replace("'", '')
                    lines.append(f"# {comment_val}")
                else:
                    lines.append("# Empty comment")
        else:
            # Add comments for unhandled operations
            lines.append(f"# WARNING: Unhandled operation: {ast.unparse(call)}")
            
    return lines