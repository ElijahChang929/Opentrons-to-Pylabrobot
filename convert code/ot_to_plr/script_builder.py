import textwrap, ast
from pathlib import Path
from analyze import OTAnalyzer
from labware_loader import labware_json_to_plr, BUILTIN_CLASSMAP, LABWARE_CACHE
from step_converter import generate_steps
def generate_plr_script(ot_path: Path, outdir: Path):
    BUILTIN_CLASSMAP.clear()
    LABWARE_CACHE.clear()

    source = ot_path.read_text()
    analyzer = OTAnalyzer(source)
    analyzer.visit(ast.parse(source))

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

    deck_lines = [
        "lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(), deck = OTDeck())"
    ]
    
    # Add labware to the deck and make sure `assign_child_at_slot` is added
    for var, load_name, slot in analyzer.labware:
    
        cls_name = BUILTIN_CLASSMAP.get(load_name, load_name)
        deck_lines.append(f'{var} = {cls_name}(name="{var}")')
        #print(var, load_name)
        deck_lines.append(f'lh.deck.assign_child_at_slot({var}, slot={slot})')  # Ensure this is included

        # Handling wells or rows: Add assignment for well variables (e.g., pbs, lysis)
        if 'wells' in var:
            well_var_name = var.split('.')[-1]  # e.g., 'pbs' from 'reagent_stock.wells()[0]'
            deck_lines.append(f'{well_var_name} = {var}.wells()[0]')  # Example: pbs = reagent_stock.wells()[0]

    for var, slot in analyzer.tipracks.items():
        deck_lines.append(f'{var} = TipRack(name="{var}")')
        deck_lines.append(f'lh.deck.assign_child_at_slot({var}, slot={slot})')

        if 'wells' in var:
            well_var_name = var.split('.')[-1]  # e.g., 'pbs' from 'reagent_stock.wells()[0]'
            deck_lines.append(f'{well_var_name} = {var}.wells()[0]')  # Example: pbs = reagent_stock.wells()[0]
            
    for var, info in analyzer.pipettes.items():
        deck_lines.append(f'{var} = lh.setup_pipette(model="{info["model"]}", mount="{info["mount"]}")')

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

{labware_defs}
{deck_block}
await lh.setup()
vis = Visualizer(resource=lh)
await vis.setup()
{step_block}
await lh.teardown()
"""
    outdir.mkdir(exist_ok=True)
    out_path = outdir / (ot_path.stem + "_plr.py")
    out_path.write_text(textwrap.dedent(template))
    print(f"[✓] {ot_path.name} → {out_path}")