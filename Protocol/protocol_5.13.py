text = """
 ------------- TRANSFERRING WATER ------------
Setting Temperature Module temperature to 4.0 °C (rounded off to nearest integer)

Picking up tip from A1 of Opentrons OT-2 96 Filter Tip Rack 200 µL on 6
Transferring 21.5 from A1 of Agilent 1 Well Reservoir 290 mL on 1 to A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3
        Aspirating 21.5 uL from A1 of Agilent 1 Well Reservoir 290 mL on 1 at 92.86 uL/sec
        Dispensing 21.5 uL into A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3 at 92.86 uL/sec
Dropping tip into A1 of Opentrons Fixed Trash on 12
Deactivating Temperature Module


 ------------- TRANSFERRING DNA ------------

Engaging Magnetic Module
Picking up tip from B1 of Opentrons OT-2 96 Filter Tip Rack 200 µL on 6
Transferring 10.5 from A1 of Bio-Rad 96 Well Plate 200 µL PCR on 2 to A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3
        Aspirating 10.5 uL from A1 of Bio-Rad 96 Well Plate 200 µL PCR on 2 at 92.86 uL/sec
        Dispensing 10.5 uL into A1 of Bio-Rad 96 Well Plate 200 µL PCR on 3 at 92.86 uL/sec
Dropping tip into A1 of Opentrons Fixed Trash on 12

Delaying for 5 minutes and 0.0 seconds
Disengaging Magnetic Module

 ------------- Operating the heater shaker------------

Setting Target Temperature of Heater-Shaker to 37 °C
Waiting for Heater-Shaker to reach target temperature
Setting Heater-Shaker to Shake at 200 RPM and waiting until reached
Delaying for 60 minutes and 0.0 seconds
Deactivating Heater


"""
import re
from collections import defaultdict
from typing import List, Dict, Optional, Union, Sequence, Literal  # ← 提前导入


MODULE_START_PATTERNS = [
    r"Setting Target Temperature of Heater-Shaker",
    r"Engaging Magnetic Module"
]

# Compile once for quick matching of Heater‑Shaker commands
module_start_regex = re.compile("|".join(MODULE_START_PATTERNS))

# Input: Multiline protocol text
# with open("/mnt/data/opentrons_protocol.txt", "r", encoding="utf-8") as file:
#     lines = file.readlines()
text_ = text.replace("\n        ", ";")
lines = text_.strip().split('\n')

# Strip lines, ignore indented lines (children/substeps), and filter empty lines
steps = [line.replace(";", "\n        ").strip() for line in lines if line.strip() and not line.startswith("        ") and not line.startswith("~~") and not "--" in line and not line.endswith(":")]

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

# -------- Build phases: split on Heater‑Shaker OR liquid‑logic breaks --------
grouped_phases = []
current_phase = []
aspirating_seen = False
last = ""

for step in parsed_steps:
    line_raw = step["raw"]

    # ① 如果遇到 Heater‑Shaker 指令，立即结束当前 phase
    if module_start_regex.search(line_raw):
        if current_phase:
            grouped_phases.append(current_phase)
            current_phase = []
            aspirating_seen = False    # reset for next liquid series

    # ② 维持原有移液逻辑的切割
    if (line_raw.startswith("Aspirating") and not ("Picking up tip" in last) and not ("Moving to" in last) and not ("Transferring" in last)) \
        or ("Picking up tip" in line_raw) \
        or ("Moving to" in line_raw and not ("Picking up tip" in last)):
        if aspirating_seen:
            grouped_phases.append(current_phase)
            current_phase = []
        aspirating_seen = True

    last = line_raw
    current_phase.append(line_raw)

# 别忘了收集最后一个 phase
if current_phase:
    grouped_phases.append(current_phase)
# ---------------------------------------------------------------------------
# ---------- Heater‑Shaker phase parser ----------
def build_heater_shaker_dict(step_lines: List[str]) -> Dict:
    """
    Extracts key parameters for a Heater‑Shaker phase:
    target_temperature, shake_speed, duration, wait flag, deactivate flags
    """
    data = {
        "module": "heater_shaker",
        "sources": [],
        "targets": [],
        "target_temperature": None,
        "wait_for_temp": False,
        "shake_speed": None,
        "duration_minutes": None,
        "deactivate_heater": False,
        "deactivate_shaker": False
    }
    for line in step_lines:
        if line.startswith("Setting Target Temperature of Heater-Shaker"):
            data["target_temperature"] = extract_float_after_keyword(line, "to")
        elif line.startswith("Waiting for Heater-Shaker"):
            data["wait_for_temp"] = True
        elif line.startswith("Setting Heater-Shaker to Shake at"):
            m = re.search(r'Shake at ([\d.]+) RPM', line)
            if m:
                data["shake_speed"] = float(m.group(1))
        elif line.startswith("Delaying"):
            dm = re.search(r'Delaying for (\d+) minutes', line)
            if dm:
                data["duration_minutes"] = int(dm.group(1))
        elif line.startswith("Deactivating Heater"):
            data["deactivate_heater"] = True
        elif line.startswith("Deactivating Shaker"):
            data["deactivate_shaker"] = True
    return data
# -----------------------------------------------

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
sorted_actions


import re
from typing import List, Dict, Optional, Union, Sequence, Literal

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

    # --- module flags that accompany liquid handling ---
    temperature_target = None
    temperature_deactivate = False
    magnetic_engage = False
    magnetic_delay_minutes = None
    magnetic_disengage = False
    # ---------------------------------------------------

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

        # Temperature Module commands
        elif stripped.startswith("Setting Temperature Module temperature"):
            temperature_target = extract_float_after_keyword(stripped, "to")
        elif stripped.startswith("Deactivating Temperature Module"):
            temperature_deactivate = True

        # Magnetic Module commands
        elif stripped.startswith("Engaging Magnetic Module"):
            magnetic_engage = True
        elif stripped.startswith("Disengaging Magnetic Module"):
            magnetic_disengage = True
        elif stripped.startswith("Delaying") and magnetic_engage and not magnetic_disengage:
            delay_match2 = re.search(r'Delaying for (\d+) minutes', stripped)
            if delay_match2:
                magnetic_delay_minutes = int(delay_match2.group(1))

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
        ,
        "temperature_target": temperature_target,
        "temperature_deactivate": temperature_deactivate,
        "magnetic_engage": magnetic_engage,
        "magnetic_delay_minutes": magnetic_delay_minutes,
        "magnetic_disengage": magnetic_disengage
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

 # -------- Build dicts for each phase (liquid vs HS) --------
outputs = []
for phase_lines in grouped_phases:
    if any("Heater-Shaker" in l for l in phase_lines):
        outputs.append(build_heater_shaker_dict(phase_lines))
    else:
        outputs.append(build_transfer_liquid_dict_complete(phase_lines))
# -----------------------------------------------------------

# Separate out liquid handling and non-liquid handling phases
liquid_only = [x for x in outputs if x.get("sources") and x.get("targets")]
non_liquid = [x for x in outputs if not (x["sources"] and x["targets"])]

merged_liquid = merge_same_slot_phases(liquid_only)
final_outputs = merged_liquid + non_liquid   # keep HS and other non‑liquid phases

ddf = pd.DataFrame({"Phase {}".format(i + 1): phase for i, phase in enumerate(final_outputs)})
print(ddf)