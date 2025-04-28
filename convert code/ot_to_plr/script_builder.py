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

    deck_lines = [
        "lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(), deck = OTDeck())"
    ]
    
    # Group similar labware by load_name for better handling of multiple instances
    labware_groups = defaultdict(list)
    for var, load_name, slot in analyzer.labware:
        labware_groups[load_name].append((var, slot))
    
    # First process regular labware (non-tipracks)
    for load_name, instances in labware_groups.items():
        cls_name = BUILTIN_CLASSMAP.get(load_name, load_name)
        
        # Handle tip racks specially if there are multiple instances
        if any(name for name in [load_name, cls_name] if 'tiprack' in name.lower()) and len(instances) > 1:
            # Generate tiprack specific code with a list
            slots = [slot for _, slot in instances]
            collection_name = f"{cls_name.lower().replace('_', '')}_racks"
            
            deck_lines.append(f"# Setup {len(slots)} tip racks")
            deck_lines.append(f"tiprack_slots = {slots}")
            deck_lines.append(f"{collection_name} = []")
            deck_lines.append(f"for slot_i in tiprack_slots:")
            deck_lines.append(f"    tr = {cls_name}(name=f\"tiprack_{{slot_i}}\")")
            deck_lines.append(f"    lh.deck.assign_child_at_slot(tr, slot=slot_i)")
            deck_lines.append(f"    {collection_name}.append(tr)")
        else:
            # Process normal labware
            for var, slot in instances:
                deck_lines.append(f'{var} = {cls_name}(name="{var}")')
                deck_lines.append(f'lh.deck.assign_child_at_slot({var}, slot={slot})')
                
                # Handle wells if needed
                if 'wells' in var:
                    well_var_name = var.split('.')[-1]  # e.g., 'pbs' from 'reagent_stock.wells()[0]'
                    deck_lines.append(f'{well_var_name} = {var}.wells()[0]')  # Example: pbs = reagent_stock.wells()[0]
    
    # Process tipracks separately if they exist in analyzer.tipracks
    for var, slot in analyzer.tipracks.items():
        deck_lines.append(f'{var} = TipRack(name="{var}")')
        deck_lines.append(f'lh.deck.assign_child_at_slot({var}, slot={slot})')

        if 'wells' in var:
            well_var_name = var.split('.')[-1]  # e.g., 'pbs' from 'reagent_stock.wells()[0]'
            deck_lines.append(f'{well_var_name} = {var}.wells()[0]')  # Example: pbs = reagent_stock.wells()[0]
            

    step_lines = generate_steps(analyzer.steps)

    # Pretty‑print blocks with one statement per line
    deck_block = "\n".join(deck_lines)
    step_block = "\n".join(step_lines)

    # Generate the template
    template = f"""
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.opentrons import OTDeck
from pylabrobot.visualizer.visualizer import Visualizer
{builtin_import_line}

# Constants from Opentrons protocol
{const_block}

{labware_defs}
{deck_block}
await lh.setup()
vis = Visualizer(resource=lh)
await vis.setup()

# For tip racks created in a loop
if 'tiprack_slots' in locals():
    for tr in tiprack_racks:
        tr.fill()
else:
    # Fall back to the old behavior
    try:
        tip_rack.fill()
    except NameError:
        pass

{step_block}
await lh.teardown()
"""
    outdir.mkdir(exist_ok=True)
    out_path = outdir / (ot_path.stem + "_plr.py")
    out_path.write_text(textwrap.dedent(template))
    print(f"[✓] {ot_path.name} → {out_path}")