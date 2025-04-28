
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.opentrons import OTDeck
from pylabrobot.visualizer.visualizer import Visualizer
from pylabrobot.resources.opentrons import (
  corning_96_wellplate_360ul_flat, nest_12_reservoir_15ml, nest_1_reservoir_195ml, opentrons_96_tiprack_300ul
)


lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(), deck = OTDeck())
corning_96_wellplate_360ul_flat = corning_96_wellplate_360ul_flat(name="corning_96_wellplate_360ul_flat")
lh.deck.assign_child_at_slot(corning_96_wellplate_360ul_flat, slot=6)
nest_12_reservoir_15ml = nest_12_reservoir_15ml(name="nest_12_reservoir_15ml")
lh.deck.assign_child_at_slot(nest_12_reservoir_15ml, slot=3)
nest_1_reservoir_195ml = nest_1_reservoir_195ml(name="nest_1_reservoir_195ml")
lh.deck.assign_child_at_slot(nest_1_reservoir_195ml, slot=9)
opentrons_96_tiprack_300ul = opentrons_96_tiprack_300ul(name="opentrons_96_tiprack_300ul")
lh.deck.assign_child_at_slot(opentrons_96_tiprack_300ul, slot=slot)
ctx.load_instrument('p300_multi_gen2', p300_mount, tip_racks = lh.setup_pipette(model="p300_multi_gen2", mount="tiprack")
await lh.setup()
vis = Visualizer(resource=lh)
await vis.setup()
p300.pick_up_tip()
await lh.aspirate(MEDIUM_VOL * 1.2, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(MEDIUM_VOL * 1.2, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL, pbs.bottom(z=0.5), rate=3, pipette=p300)
await lh.dispense(PBS_VOL + 20, final.top(z=-2), rate=0.3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(PBS_VOL * 1.5, final.bottom(z=0.2).move(Point(x=-2.5)), rate=0.2, pipette=p300)
await lh.dispense(PBS_VOL * 1.5, waste.top(z=-5), rate=3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LYSIS_VOL, lysis.bottom(z=0.5), rate=0.5, pipette=p300)
await lh.dispense(LYSIS_VOL, final.bottom(z=5), rate=0.3, pipette=p300)
p300.drop_tip()
p300.pick_up_tip()
await lh.aspirate(LUC_VOL, luciferase.bottom(z=0.5), rate=0.75, pipette=p300)
await lh.dispense(LUC_VOL + 20, final.top(z=-0.5), rate=0.75, pipette=p300)
await lh.mix(final.bottom(z=0.5), repetitions=3, volume=75, rate=3, pipette=p300)
p300.drop_tip()
await lh.teardown()
