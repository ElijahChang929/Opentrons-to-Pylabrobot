import ast
from typing import List

def generate_steps(steps: List[ast.Call]) -> List[str]:
    lines = []

    def _kw_string(call: ast.Call) -> str:
        if not call.keywords:
            return ""
        parts = [f"{kw.arg}={ast.unparse(kw.value)}" for kw in call.keywords]
        return ", " + ", ".join(parts)
    
    def _extract_rate(keywords, default_key="rate"):
        """Extract rate or flow_rate from keywords"""
        for kw in keywords:
            if kw.arg == "rate" or kw.arg == "flow_rate":
                return ast.unparse(kw.value)
        return None

    for call in steps:
        fun = call.func.attr
        tgt = ast.unparse(call.func.value)
        
        if fun == "transfer":
            src, dst, vol = map(ast.unparse, call.args[:3])
            # PyLabRobot transfer needs source, destination wells as lists
            lines.append(f"await lh.transfer({src}, [{dst}], source_vol={vol})")
            
        elif fun == "aspirate":
            # PyLabRobot aspirate expects [resources], [vols]
            src, vol = map(ast.unparse, call.args[:2])
            flow_rate = _extract_rate(call.keywords)
            
            flow_rate_arg = f", flow_rates=[{flow_rate}]" if flow_rate else ""
            
            # Check for any air_gap command which becomes blow_out_air_volume in PyLabRobot
            blow_out_vol = None
            for kw in call.keywords:
                if kw.arg == "air_gap":
                    blow_out_vol = ast.unparse(kw.value)
                    break
                    
            blow_out_arg = f", blow_out_air_volume=[{blow_out_vol}]" if blow_out_vol else ""
            
            lines.append(f"await lh.aspirate([{src}], [{vol}]{flow_rate_arg}{blow_out_arg})")
            
        elif fun == "dispense":
            # PyLabRobot dispense expects [resources], [vols]
            dst, vol = map(ast.unparse, call.args[:2])
            flow_rate = _extract_rate(call.keywords)
            
            flow_rate_arg = f", flow_rates=[{flow_rate}]" if flow_rate else ""
            
            lines.append(f"await lh.dispense([{dst}], [{vol}]{flow_rate_arg})")
            
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