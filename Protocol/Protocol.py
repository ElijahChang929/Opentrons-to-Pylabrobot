import re
from collections import defaultdict
from typing import List, Dict, Optional, Union, Sequence, Literal
import os
import json


def process_log_file(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        text = f.read()
    # 下面是你原有的处理逻辑，可以直接用text变量
    text_ = text.replace("\n        ", ";")
    lines = text_.strip().split('\n')
    # Strip lines, ignore indented lines (children/substeps), and filter empty lines
    excluded_patterns = [
        "/Users",
        "Congratulations!",
        "Caught exception:",
        "Deck calibration",
        "WARNING",
        "Protocol complete",
        "Seal and shake",
        "Pausing robot operation",
        "TRANSFERRING",
        "Centrifuge"
    ]
    steps = [line.replace(";", "\n        ").strip() for line in lines if line.strip() and 
             not line.startswith("        ") and not line.startswith("~~") and 
             not "--" in line and not line.endswith(":") and
             not sum([line.startswith(patt) for patt in excluded_patterns])]

    # Define prepositions to split on
    PREPOSITIONS = [' from ', ' to ', ' on ', ' of ', ' into ']

    # Structure for collecting parsed results
    parsed_steps = []

    # Parse each line
    for line in steps:
        tokens = [line]
        for prep in PREPOSITIONS:
            new_tokens = []
            for token in tokens:
                new_tokens.extend(token.split(prep))
            tokens = new_tokens
        parsed_steps.append({
            "raw": line,
            "tokens": [t.strip() for t in tokens if t.strip()]
        })

    # Group steps into phases based on "Aspirating"
    grouped_phases = []
    current_phase = []
    aspirating_seen = False

    last = ""
    for step in parsed_steps:
        if (step["raw"].startswith("Aspirating") and not ("Picking up tip" in last) and not ("Moving to" in last) and not ("Transferring" in last)) \
            or ("Picking up tip" in step["raw"]) or ("Moving to" in step["raw"] and not ("Picking up tip" in last)):
            if aspirating_seen:
                grouped_phases.append(current_phase)
                current_phase = []
            aspirating_seen = True
        last = step["raw"]
        current_phase.append(step["raw"])

    # Append the last batch
    if current_phase:
        grouped_phases.append(current_phase)

    # Output the grouped phases
    import pandas as pd

    grouped_dict = {"Phase {}".format(i + 1): phase for i, phase in enumerate(grouped_phases)}
    df = pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in grouped_dict.items() ]))

    # Also, extract all distinct actions (first word in each step)
    actions = set()
    for step in parsed_steps:
        action = step["raw"].split()[0]
        actions.add(action)

    sorted_actions = sorted(actions)


    def extract_float_after_keyword(text: str, keyword: str) -> Optional[float]:
        match = re.search(fr'{keyword} ([\d.]+)', text)
        return float(match.group(1)) if match else None

    def extract_container_from_line(line: str, keyword: str) -> Optional[Dict[str, Union[str, int, float]]]:
        # 匹配 from 模式
        match = re.search(fr'{keyword} [\d.]+ uL .*?from ([A-H]\d+) of (.*?) on (\d+).*?at ([\d.]+) uL/sec', line)
        if not match:
            # 匹配 into 模式
            match = re.search(fr'{keyword} [\d.]+ uL .*?into ([A-H]\d+) of (.*?) on (\d+).*?at ([\d.]+) uL/sec', line)
        if match:
            return {
                "well": match.group(1),
                "labware": match.group(2).strip(),
                "slot": int(match.group(3))
            }
        return None

    def is_full_row(wells: List[str]) -> bool:
        """Returns True if all wells in a row (e.g., A1 to A12) are included"""
        if len(wells) < 12:
            return False
        row = wells[0][0]
        indices = sorted([int(w[1:]) for w in wells if w[0] == row])
        return indices == list(range(1, 13))

    def build_transfer_liquid_dict_complete(step_lines: List[str]) -> Dict:
        asp_vols = []
        dis_vols = []
        sources = []
        targets = []
        tip_rack_info = None
        asp_flow_rate = None
        dis_flow_rate = None
        blow_out_air_volume = 0.0
        mix_times = 0
        mix_vol = None
        mix_rate = None
        touch_tip = False
        delays = None
    
        aspirate_index = None
        dispense_index = None
        mixing_indices = []
    
        # First pass: gather line indices for logic
        for i, line in enumerate(step_lines):
            if line.startswith(" "):  # ignore indented substeps
                continue
            stripped = line.strip()
            if stripped.startswith("Aspirating") and "from" in stripped and aspirate_index is None:
                aspirate_index = i
            elif stripped.startswith("Dispensing") and "into" in stripped and dispense_index is None:
                dispense_index = i
            elif stripped.startswith("Mixing"):
                mixing_indices.append(i)
            elif stripped.startswith("Picking up tip"):
                tip_match = re.search(r'from ([A-H]\d+) of (.*?) on (\d+)', stripped)
                if tip_match:
                    tip_rack_info = {
                        "well": tip_match.group(1),
                        "type": tip_match.group(2).strip(),
                        "slot": int(tip_match.group(3))
                    }
    
        # Determine mix_stage
        mix_stage = "none"
        for idx in mixing_indices:
            if aspirate_index is not None and idx < aspirate_index:
                mix_stage = "before" if mix_stage == "none" else "both"
            elif dispense_index is not None and idx > dispense_index:
                mix_stage = "after" if mix_stage == "none" else "both"
    
        # Second pass: parse actual values
        for i, line in enumerate(step_lines):
            if line.startswith(" "):  # ignore indented substeps
                continue
            stripped = line.strip()
    
            if stripped.startswith("Aspirating") and "from" in stripped:
                asp_vols = extract_float_after_keyword(stripped, "Aspirating")
                source = extract_container_from_line(stripped, "Aspirating")
                if source:
                    sources.append(source)
                asp_flow_rate = extract_float_after_keyword(stripped, "at")
            elif stripped.startswith("Dispensing") and "into" in stripped:
                dis_vols = extract_float_after_keyword(stripped, "Dispensing")
                target = extract_container_from_line(stripped, "Dispensing")
                if target:
                    targets.append(target)
                dis_flow_rate = extract_float_after_keyword(stripped, "at")
            
            elif stripped.startswith("Transferring"):
                asp_vols = extract_float_after_keyword(stripped, "Aspirating")
                dis_vols = extract_float_after_keyword(stripped, "Dispensing")
                source = extract_container_from_line(stripped, "Aspirating")
                if source:
                    sources.append(source)
                target = extract_container_from_line(stripped, "Dispensing")
                if target:
                    targets.append(target)    
                    # 新增：分别提取Aspirating和Dispensing的流速
                asp_match = re.search(r"Aspirating.*?at ([\d.]+)", stripped)
                dis_match = re.search(r"Dispensing.*?at ([\d.]+)", stripped)
                asp_flow_rate = float(asp_match.group(1)) if asp_match else None
                dis_flow_rate = float(dis_match.group(1)) if dis_match else None
    
            elif stripped.startswith("Air gap"):
                blow_out_air_volume = extract_float_after_keyword(stripped, "Aspirating")
            elif stripped.startswith("Mixing"):
                mix_match = re.search(r'Mixing (\d+) times.*?(\d+\.?\d*)', stripped)
                if mix_match:
                    mix_times = [int(mix_match.group(1))]
                    mix_vol = float(mix_match.group(2))
                    mix_rate = extract_float_after_keyword(stripped, "at")
            elif "Touching tip" in stripped:
                touch_tip = True
            elif stripped.startswith("Delaying"):
                delay_match = re.search(r'Delaying for \d+ minutes and ([\d.]+)', stripped)
                if delay_match:
                    delays = [int(float(delay_match.group(1)))]
    
        # Determine 96-well multichannel use
        source_wells = [s['well'] for s in sources]
        target_wells = [t['well'] for t in targets]
        is_96_well = is_full_row(source_wells) and is_full_row(target_wells)
    
        return {
            "asp_vols": asp_vols,
            "disp_vols": dis_vols,
            "sources": sources,
            "targets": targets,
            "tip_racks": [tip_rack_info] if tip_rack_info else [],
            "use_channels": None,
            "asp_flow_rates": [asp_flow_rate] if asp_flow_rate else None,
            "dis_flow_rates": [dis_flow_rate] if dis_flow_rate else None,
            "offsets": None,
            "touch_tip": touch_tip,
            "liquid_height": None,
            "blow_out_air_volume": [blow_out_air_volume] if blow_out_air_volume else [0.0],
            "spread": "wide",
            "is_96_well": is_96_well,
            "mix_stage": mix_stage,
            "mix_times": mix_times,
            "mix_vol": mix_vol,
            "mix_rate": mix_rate,
            "mix_liquid_height": None,
            "delays": delays
        }
    
    
    def merge_same_slot_phases(param_dicts: List[Dict]) -> List[Dict]:
        merged = []
        cache = {}
        last_key = None
        last_block = None
    
        for d in param_dicts:
            if not d["sources"] or not d["targets"]:
                continue
            # 定义用于合并的唯一标识 key，注意引用第一个 blow_out_air_volume 可能为 None
            key = (
                d["sources"][0]["slot"],
                d["targets"][0]["slot"],
                d.get("mix_stage"),
                d.get("is_96_well"),
                d.get("touch_tip"),
                d.get("blow_out_air_volume", [0])[0]
            )
    
            if (last_key == key and last_block):
                # 合并到上一个 block 中
                for field in ['vols', 'sources', 'targets', 'tip_racks', 'flow_rates', 'blow_out_air_volume', 'delays']:
                    if field in d:
                        if not isinstance(last_block[field], list):
                            last_block[field] = [last_block[field]]
                        if isinstance(d[field], list):
                            last_block[field].extend(d[field])
                        else:
                            last_block[field].append(d[field])
            else:
                # 启动新的 merge block
                merged.append(d)
                last_block = d
                last_key = key
    
        return merged
    
    
    outputs = [build_transfer_liquid_dict_complete(steps) for phase, steps in grouped_dict.items()]
    o = merge_same_slot_phases(outputs)
    ddf = pd.DataFrame({"Phase {}".format(i + 1): phase for i, phase in enumerate(o)})
    
    return ddf.to_dict(orient="list")


# if __name__ == "__main__":
#     success_dir = "success"
#     json_dir = "json"
#     os.makedirs(json_dir, exist_ok=True)
#     for filename in os.listdir(success_dir):
#         if filename.endswith(".log"):
#             log_path = os.path.join(success_dir, filename)
#             result = process_log_file(log_path)
#             json_path = os.path.join(json_dir, filename.replace(".log", ".json"))
#             with open(json_path, "w", encoding="utf-8") as jf:
#                 json.dump(result, jf, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    success_dir = "success"
    json_dir = "json"
    os.makedirs(json_dir, exist_ok=True)
    count = 0
    for filename in os.listdir(success_dir):
        if filename.endswith(".log"):
            log_path = os.path.join(success_dir, filename)
            result = process_log_file(log_path)
            json_path = os.path.join(json_dir, filename.replace(".log", ".json"))
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(result, jf, ensure_ascii=False, indent=2)
            count += 1
            if count >= 5:
                break