from __future__ import annotations

from typing import List, Sequence, Optional, Literal, Union, Iterator

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.resources import (
    Resource,
    TipRack,
    Container,
    Coordinate,
)





# ---------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------

def iter_tips(tip_racks: Sequence[TipRack]) -> Iterator[Resource]:
    """Yield tips from a list of TipRacks one-by-one until depleted."""
    for rack in tip_racks:
        for tip in rack:
            yield tip
    raise RuntimeError("Out of tips!")

# ---------------------------------------------------------------
# REMOVE LIQUID --------------------------------------------------
# ---------------------------------------------------------------

async def remove_liquid(
    lh: LiquidHandler,
    vols: Union[List[float], float],
    sources: Sequence[Container],
    waste: Resource,
    tip_racks: Sequence[TipRack],
    *,
    use_channels: Optional[List[int]] = None,
    flow_rates: Optional[List[Optional[float]]] = None,
    offsets: Optional[List[Coordinate]] = None,
    liquid_height: Optional[List[Optional[float]]] = None,
    blow_out_air_volume: Optional[List[Optional[float]]] = None,
    spread: Optional[Literal["wide", "tight", "custom"]] = "wide",
    is_96_well: Optional[bool] = False,
):
    """A complete *remove* (aspirate → waste) operation."""

    try:
        if is_96_well:
            if not isinstance(vols, (int, float)):
                raise ValueError("For 96‑well operations `vols` must be a scalar.")
            first_rack = next(iter(tip_racks))
            await lh.pick_up_tips96(first_rack)
            await lh.aspirate96(
                resource=sources,
                volume=vols,
                offset=Coordinate.zero(),
                flow_rate=flow_rates[0] if flow_rates else None,
                blow_out_air_volume=blow_out_air_volume[0] if blow_out_air_volume else None,
                use_channels=use_channels,
            )
            await lh.dispense(
                resources=[waste],
                vols=[vols] * 8,
                use_channels=use_channels,
                flow_rates=flow_rates,
                offsets=offsets,
                liquid_height=liquid_height,
                blow_out_air_volume=blow_out_air_volume,
                spread=spread,
            )
            await lh.discard_tips96()
        else:
            if len(vols) != len(sources):
                raise ValueError("Length of `vols` must match `sources`.")
            tip_iter = iter_tips(tip_racks)
            for src, vol in zip(sources, vols):
                tip = next(tip_iter)
                await lh.pick_up_tips(tip)
                await lh.aspirate(
                    resources=[src],
                    vols=[vol],
                    use_channels=use_channels, # only aspirate96 used, default to None
                    flow_rates=flow_rates,
                    offsets=offsets,
                    liquid_height=liquid_height,
                    blow_out_air_volume=blow_out_air_volume,
                    spread=spread,
                )
                await lh.dispense(
                    resources=[waste],
                    vols=[vol],
                    use_channels=use_channels,
                    flow_rates=flow_rates,
                    offsets=offsets,
                    liquid_height=liquid_height,
                    blow_out_air_volume=blow_out_air_volume,
                    spread=spread,
                )
                await lh.discard_tips() # For now, each of tips is discarded after use
    except Exception as e:
        raise RuntimeError(f"Liquid removal failed: {e}") from e

# ---------------------------------------------------------------
# ADD LIQUID -----------------------------------------------------
# ---------------------------------------------------------------

async def add_liquid(
    lh: LiquidHandler,
    vols: Union[List[float], float],
    reagent_sources: Sequence[Container],
    targets: Sequence[Container],
    tip_racks: Sequence[TipRack],
    *,
    use_channels: Optional[List[int]] = None,
    flow_rates: Optional[List[Optional[float]]] = None,
    offsets: Optional[List[Coordinate]] = None,
    liquid_height: Optional[List[Optional[float]]] = None,
    blow_out_air_volume: Optional[List[Optional[float]]] = None,
    spread: Literal["wide", "tight", "custom"] = "wide",
    is_96_well: bool = False,
):
    """A complete *add* (aspirate reagent → dispense into targets) operation."""

    try:
        if is_96_well:
            if not isinstance(vols, (int, float)):
                raise ValueError("For 96‑well operations `vols` must be a scalar.")
            first_rack = next(iter(tip_racks))
            await lh.pick_up_tips96(first_rack)
            await lh.aspirate(
                resources=reagent_sources,
                vols=[vols],
                use_channels=use_channels,
                flow_rates=flow_rates,
                offsets=offsets,
                liquid_height=liquid_height,
                blow_out_air_volume=blow_out_air_volume,
                spread=spread,
            )
            await lh.dispense96(
                resource=targets,
                volume=vols,
                offset=Coordinate.zero(),
                flow_rate=flow_rates[0] if flow_rates else None,
                blow_out_air_volume=blow_out_air_volume[0] if blow_out_air_volume else None,
                use_channels=use_channels,
            )
            await lh.discard_tips96()
        else:
            if len(vols) != len(targets):
                raise ValueError("Length of `vols` must match `targets`.")
            tip_iter = iter_tips(tip_racks)
            for tgt, vol in zip(targets, vols):
                tip = next(tip_iter)
                await lh.pick_up_tips(tip)
                await lh.aspirate(
                    resources=reagent_sources,
                    vols=[vol],
                    use_channels=use_channels,
                    flow_rates=flow_rates,
                    offsets=offsets,
                    liquid_height=liquid_height,
                    blow_out_air_volume=blow_out_air_volume,
                    spread=spread,
                )
                await lh.dispense(
                    resources=[tgt],
                    vols=[vol],
                    use_channels=use_channels,
                    flow_rates=flow_rates,
                    offsets=offsets,
                    liquid_height=liquid_height,
                    blow_out_air_volume=blow_out_air_volume,
                    spread=spread,
                )
                await lh.discard_tips()
    except Exception as e:
        raise RuntimeError(f"Liquid addition failed: {e}") from e

# ---------------------------------------------------------------
# TRANSFER LIQUID ------------------------------------------------
# ---------------------------------------------------------------
async def transfer_liquid(
    lh: LiquidHandler,
    vols: Union[float, List[float]],
    sources: Sequence[Container],
    targets: Sequence[Container],
    tip_racks: Sequence[TipRack],
    *,
    use_channels: Optional[List[int]] = None,
    flow_rates: Optional[List[Optional[float]]] = None,
    offsets: Optional[List[Coordinate]] = None,
    liquid_height: Optional[List[Optional[float]]] = None,
    blow_out_air_volume: Optional[List[Optional[float]]] = None,
    spread: Literal["wide", "tight", "custom"] = "wide",
    is_96_well: bool = False,
):
    """Transfer liquid from each *source* well/plate to the corresponding *target*.

    Parameters
    ----------
    lh
        An initialized :class:`~pylabrobot.liquid_handling.LiquidHandler`.
    vols
        Single volume (µL) or list matching the number of transfers.
    sources, targets
        Same‑length sequences of containers (wells or plates). In 96‑well mode
        each must contain exactly one plate.
    tip_racks
        One or more TipRacks providing fresh tips.
    is_96_well
        Set *True* to use the 96‑channel head.
    """

    try:
        # ------------------------------------------------------------------
        # 96‑channel head mode
        # ------------------------------------------------------------------
        if is_96_well:
            # Validate inputs ------------------------------------------------

            if len(sources) != 1 or len(targets) != 1:
                raise ValueError("Provide exactly one source plate and one target plate in 96‑well mode.")

            # 1) Pick up 96 tips
            first_rack = next(iter(tip_racks))
            await lh.pick_up_tips96(first_rack)

            # 2) Aspirate from source plate
            await lh.aspirate96(
                resource=sources,
                volume=vols,
                offset=Coordinate.zero(),
                flow_rate=flow_rates[0] if flow_rates else None,
                blow_out_air_volume=blow_out_air_volume[0] if blow_out_air_volume else None,
                use_channels=use_channels,
            )

            # 3) Dispense into target plate
            await lh.dispense96(
                resource=targets,
                volume=vols,
                offset=Coordinate.zero(),
                flow_rate=flow_rates[0] if flow_rates else None,
                blow_out_air_volume=blow_out_air_volume[0] if blow_out_air_volume else None,
                use_channels=use_channels,
            )

            # 4) Drop tips
            await lh.discard_tips96()
            return  # success

        # ------------------------------------------------------------------
        # Single / multi‑channel mode
        # ------------------------------------------------------------------
        # Normalize vols list ----------------------------------------------

        if not (len(vols) == len(sources) == len(targets)):
            raise ValueError("`sources`, `targets`, and `vols` must have the same length.")

        tip_iter = iter_tips(tip_racks)

        for src, tgt, vol in zip(sources, targets, vols):
            tip = next(tip_iter)
            await lh.pick_up_tips(tip)

            # Aspirate from source
            await lh.aspirate(
                resources=[src],
                vols=[vol],
                use_channels=use_channels,
                flow_rates=flow_rates,
                offsets=offsets,
                liquid_height=liquid_height,
                blow_out_air_volume=blow_out_air_volume,
                spread=spread,
            )

            # Dispense into target
            await lh.dispense(
                resources=[tgt],
                vols=[vol],
                use_channels=use_channels,
                flow_rates=flow_rates,
                offsets=offsets,
                liquid_height=liquid_height,
                blow_out_air_volume=blow_out_air_volume,
                spread=spread,
            )

            await lh.discard_tips()

    except Exception as exc:
        raise RuntimeError(f"Liquid transfer failed: {exc}") from exc
