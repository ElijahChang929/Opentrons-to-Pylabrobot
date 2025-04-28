
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.opentrons import OTDeck
from pylabrobot.visualizer.visualizer import Visualizer
from pylabrobot.resources import Coordinate, set_tip_tracking, set_volume_tracking
from pylabrobot.resources.opentrons import (
  corning_96_wellplate_360ul_flat, nest_12_reservoir_15ml, nest_1_reservoir_195ml, opentrons_96_tiprack_300ul
)

# Constants from Opentrons protocol
TOTAL_COl = 12
MEDIUM_VOL = 100
PBS_VOL = 50
LYSIS_VOL = 30
LUC_VOL = 100



def _tip_gen(tip_racks):
    """Yield the next available tip."""
    for rack in tip_racks:
        for tip in rack:
            yield tip
    raise RuntimeError("Out of tips!")


def _build_deck(lh: LiquidHandler):
    """Load all labware on the deck and return handy shortcuts."""
    # Tip racks on slots [8, 11, 1, 4]
    tiprack_slots = [8, 11, 1, 4]
    tipracks = []
    # Load tip racks
    for slot_i in tiprack_slots:
        tr = opentrons_96_tiprack_300ul(name=f"tiprack_{slot_i}")
        lh.deck.assign_child_at_slot(tr, slot=slot_i)
        tipracks.append(tr)
    # 96-well plate at slot 6
    corning_96_wellplate_360ul_flat = corning_96_wellplate_360ul_flat(name="corning_96_wellplate_360ul_flat")
    lh.deck.assign_child_at_slot(corning_96_wellplate_360ul_flat, slot=6)
    # 12-channel reagent reservoir at slot 3
    nest_12_reservoir_15ml = nest_12_reservoir_15ml(name="nest_12_reservoir_15ml")
    lh.deck.assign_child_at_slot(nest_12_reservoir_15ml, slot=3)
    # Waste reservoir at slot 9
    nest_1_reservoir_195ml = nest_1_reservoir_195ml(name="nest_1_reservoir_195ml")
    lh.deck.assign_child_at_slot(nest_1_reservoir_195ml, slot=9)

    return {
        "tip_racks": tipracks,
        "working_plate": corning_96_wellplate_360ul_flat,
        "reagent_res": nest_12_reservoir_15ml,
        "waste_res": nest_1_reservoir_195ml
    }


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

# Set up labware contents
working_plate_volumns = [('culture medium', MEDIUM_VOL)] * 12 + [(None, 0)] * (96-12)
deck["working_plate"].set_well_liquids(working_plate_volumns)

# Define reagent locations
reagent_info = [('PBS Buffer', 5000), ('Lysis Buffer', 5000), ('Luciferase Reagent', 5000)] + [(None, 0)] * (12 - 3)
deck["reagent_res"].set_well_liquids(reagent_info)

# Get easy references to wells
pbs        = deck["reagent_res"][0][0]
lysis      = deck["reagent_res"][1][0]
luciferase = deck["reagent_res"][2][0]
waste_res  = deck["waste_res"][0]

# Define cell wells for processing
wells_name = [f"A{i}" for i in range(1, 13)]  # A1-A12
cells_all  = deck["working_plate"][wells_name]

# Protocol steps
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()

# Cleanup
await lh.teardown()
