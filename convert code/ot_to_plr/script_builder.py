import textwrap, ast
from pathlib import Path
from collections import defaultdict
from analyze import OTAnalyzer
from labware_loader import labware_json_to_plr, BUILTIN_CLASSMAP, LABWARE_CACHE
from step_converter import generate_steps
def generate_plr_script(expended_code: str, outdir: Path, ot_path: Path):
    BUILTIN_CLASSMAP.clear()
    LABWARE_CACHE.clear()

    analyzer = OTAnalyzer(expended_code)
    analyzer.visit(ast.parse(expended_code))

    # Build custom labware class code only for non‑builtin resources
    labware_defs = "\n".join(
        code for code in (
            labware_json_to_plr(load_name)  # returns "" if builtin
            for _, load_name, _ in analyzer.labware
        )
        if code  # keep only non‑empty strings
    )

    # Collect any builtin resources that labware_json_to_plr recognized
    builtin_import_line = ""
    if BUILTIN_CLASSMAP:
        imported_syms = ", ".join(sorted(set(BUILTIN_CLASSMAP.values())))
        builtin_import_line = (
            "from pylabrobot.resources.opentrons import (\n"
            f"  {imported_syms}\n)"
        )
    
    # Add constants defined in the run function
    const_lines = []
    for const_name, const_value in analyzer.run_constants.items():
        if isinstance(const_value, str):
            const_lines.append(f'{const_name} = "{const_value}"')
        else:
            const_lines.append(f'{const_name} = {const_value}')
    
    const_block = "\n".join(const_lines)
    
    # Group similar labware by load_name for better handling of multiple instances
    labware_groups = defaultdict(list)
    for var, load_name, slot in analyzer.labware:
        labware_groups[load_name].append((var, slot))
    
    # Create build_deck function content
    deck_setup_lines = []
    well_definition_lines = []
    
    # Track labware variables for deck dictionary
    deck_dict_items = {}
    
    # Process tip racks first
    tipracks_exist = False
    for load_name, instances in labware_groups.items():
        cls_name = BUILTIN_CLASSMAP.get(load_name, load_name)
        
        if any(name for name in [load_name, cls_name] if 'tiprack' in name.lower()):
            tipracks_exist = True
            # Generate tiprack specific code with a list
            slots = [slot for _, slot in instances]
            collection_name = "tipracks"  # Use consistent naming
            
            deck_setup_lines.append(f"    # Tip racks on slots {slots}")
            deck_setup_lines.append(f"    tiprack_slots = {slots}")
            deck_setup_lines.append(f"    {collection_name} = []")
            deck_setup_lines.append(f"    # Load tip racks")
            deck_setup_lines.append(f"    for slot_i in tiprack_slots:")
            deck_setup_lines.append(f"        tr = {cls_name}(name=f\"tiprack_{{slot_i}}\")")
            deck_setup_lines.append(f"        lh.deck.assign_child_at_slot(tr, slot=slot_i)")
            deck_setup_lines.append(f"        {collection_name}.append(tr)")
            
            # Add to return dictionary
            deck_dict_items["tip_racks"] = collection_name
    
    # Process plates and other labware
    for load_name, instances in labware_groups.items():
        cls_name = BUILTIN_CLASSMAP.get(load_name, load_name)
        
        # Skip tipracks as they've been handled separately
        if any(name for name in [load_name, cls_name] if 'tiprack' in name.lower()):
            continue
        
        # Process other labware
        for var, slot in instances:
            # Create descriptive comment based on labware type
            comment = ""
            dict_name = ""
            
            # Determine the type of labware and assign appropriate names based on semantic rules
            if "plate" in cls_name.lower():
                if "96" in cls_name or "96" in load_name:
                    comment = f"    # 96-well plate at slot {slot}"
                    dict_name = "working_plate"
                elif "24" in cls_name or "24" in load_name:
                    comment = f"    # 24-well plate at slot {slot}"
                    dict_name = "working_plate"
                else:
                    comment = f"    # Working plate at slot {slot}"
                    dict_name = "working_plate"
            elif "reservoir" in cls_name.lower():
                if "12" in cls_name or "12" in load_name:
                    comment = f"    # 12-channel reagent reservoir at slot {slot}"
                    dict_name = "reagent_res"
                else:
                    comment = f"    # Waste reservoir at slot {slot}"
                    dict_name = "waste_res"
            elif "tube" in cls_name.lower() or "rack" in cls_name.lower():
                comment = f"    # Tube rack at slot {slot}"
                dict_name = "tube_rack"
            else:
                comment = f"    # {cls_name} at slot {slot}"
                dict_name = var.lower().replace('-', '_')
            
            # Add to setup code
            deck_setup_lines.append(comment)
            deck_setup_lines.append(f"    {var} = {cls_name}(name=\"{var}\")")
            deck_setup_lines.append(f"    lh.deck.assign_child_at_slot({var}, slot={slot})")
            
            # Add to return dictionary
            deck_dict_items[dict_name] = var
    
    # Create return statement for deck dictionary
    return_dict = "    return {\n"
    for key, value in deck_dict_items.items():
        return_dict += f"        \"{key}\": {value},\n"
    return_dict = return_dict.rstrip(",\n") + "\n    }"
    deck_setup_lines.append("")
    deck_setup_lines.append(return_dict)
    
    # Determine reagents and volumes based on the protocol context
    # This is more semantic-based rather than hardcoded
    if "reagent_res" in deck_dict_items:
        if "plate" in deck_dict_items.get("working_plate", "").lower() or "plate" in deck_dict_items:
            well_definition_lines.append("# Set up labware contents")
            
            # Get volume constants from the analyzer
            volume_constants = [name for name in analyzer.run_constants if "vol" in name.lower()]
            medium_vol = None
            pbs_vol = None
            lysis_vol = None
            reagent_vol = None
            
            # Try to intelligently determine the meaning of each volume constant
            for name in volume_constants:
                value = analyzer.run_constants[name]
                if "medium" in name.lower() or "media" in name.lower():
                    medium_vol = name
                elif "pbs" in name.lower() or "buffer" in name.lower() or "wash" in name.lower():
                    pbs_vol = name
                elif "lysis" in name.lower():
                    lysis_vol = name
                elif "luc" in name.lower() or "reagent" in name.lower():
                    reagent_vol = name
            
            # Default to first volume constant if we couldn't determine specific meanings
            if not medium_vol and volume_constants:
                medium_vol = volume_constants[0]
            
            # Set up plate wells with volume information
            if medium_vol:
                well_definition_lines.append(f"working_plate_volumns = [('culture medium', {medium_vol})] * 12 + [(None, 0)] * (96-12)")
                well_definition_lines.append(f"deck[\"working_plate\"].set_well_liquids(working_plate_volumns)")
                well_definition_lines.append("")
            
            # Set up reagent definitions based on the protocol's needs
            # Determine reagents based on the protocol steps and constants
            reagent_res_var = deck_dict_items["reagent_res"]
            well_definition_lines.append("# Define reagent locations")
            
            # Build the reagent list based on identified volume constants
            reagent_list = []
            if pbs_vol:
                reagent_list.append(f"('PBS Buffer', 5000)")
            if lysis_vol:
                reagent_list.append(f"('Lysis Buffer', 5000)")
            if reagent_vol:
                reagent_list.append(f"('Luciferase Reagent', 5000)")
            
            # Ensure we have at least some default reagents if none were detected
            if not reagent_list:
                reagent_list = ["('Buffer 1', 5000)", "('Buffer 2', 5000)", "('Reagent', 5000)"]
            
            # Generate the reagent info line
            reagent_str = ", ".join(reagent_list)
            well_definition_lines.append(f"reagent_info = [{reagent_str}] + [(None, 0)] * (12 - {len(reagent_list)})")
            well_definition_lines.append("deck[\"reagent_res\"].set_well_liquids(reagent_info)")
            well_definition_lines.append("")
            
            # Generate well references based on the reagents we identified
            well_definition_lines.append("# Get easy references to wells")
            if pbs_vol:
                well_definition_lines.append("pbs        = deck[\"reagent_res\"][0][0]")
            if lysis_vol:
                well_definition_lines.append("lysis      = deck[\"reagent_res\"][1][0]")
            if reagent_vol:
                well_definition_lines.append("luciferase = deck[\"reagent_res\"][2][0]")
            
            # Waste reference if available
            if "waste_res" in deck_dict_items:
                well_definition_lines.append("waste_res  = deck[\"waste_res\"][0]")
            
            # Define well range for cell plate
            # Determine the range based on the protocol context
            well_count = 12  # Default
            if analyzer.run_constants.get("TOTAL_COL"):
                well_count = analyzer.run_constants["TOTAL_COL"]
            
            well_definition_lines.append("")
            well_definition_lines.append("# Define cell wells for processing")
            well_definition_lines.append(f"wells_name = [f\"A{{i}}\" for i in range(1, {well_count+1})]  # A1-A{well_count}")
            well_definition_lines.append("cells_all  = deck[\"working_plate\"][wells_name]")
    
    # Create tip generator function as a regular string, not inside an f-string
    tip_gen_func = """
def _tip_gen(tip_racks):
    \"\"\"Yield the next available tip.\"\"\"
    for rack in tip_racks:
        for tip in rack:
            yield tip
    raise RuntimeError("Out of tips!")
"""

    # Create build_deck function as a regular string
    deck_func = """
def _build_deck(lh: LiquidHandler):
    \"\"\"Load all labware on the deck and return handy shortcuts.\"\"\"
"""
    for line in deck_setup_lines:
        deck_func += line + "\n"

    # Generate protocol steps
    step_lines = generate_steps(analyzer.steps)
    
    # Convert step_lines list to a string with proper line breaks
    step_block = "\n".join(step_lines)

    # The well definition lines should also be properly joined
    well_definition_block = "\n".join(well_definition_lines)

    # Generate the template with our prepared blocks
    template = f"""
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.opentrons import OTDeck
from pylabrobot.visualizer.visualizer import Visualizer
from pylabrobot.resources import Coordinate, set_tip_tracking, set_volume_tracking
{builtin_import_line}

# Constants from Opentrons protocol
{const_block}

{labware_defs}
{tip_gen_func}
{deck_func}

# Initialize liquid handler
lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(), deck=OTDeck())
deck = _build_deck(lh)
await lh.setup()
vis = Visualizer(resource=lh)
await vis.setup()

# Enable tip and volume tracking
set_tip_tracking(True)
set_volume_tracking(True)

# Initialize tip generator
tips = _tip_gen(deck["tip_racks"]) if "tip_racks" in deck else None

{well_definition_block}

# Protocol steps
{step_block}

# Cleanup
await lh.teardown()
"""
    outdir.mkdir(exist_ok=True)
    out_path = outdir / (ot_path.stem + "_plr.py")
    out_path.write_text(textwrap.dedent(template))
    print(f"[✓] {ot_path.name} → {out_path}")