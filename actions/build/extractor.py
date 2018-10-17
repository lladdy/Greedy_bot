"""Everything related to building logic for the extractors goes here"""
from sc2.constants import EXTRACTOR


class BuildExtractor:
    """Can be improved, the ratio mineral-vespene still sightly off"""

    def __init__(self, ai):
        self.ai = ai
        self.drone = None
        self.geyser = None

    async def should_handle(self, iteration):
        """Couldnt find another way to build the geysers its way to inefficient,
         also the logic can be improved, sometimes it over collect vespene sometime it under collect"""
        if (self.ai.vespene * 1.25 > self.ai.minerals) or (
            not (self.ai.townhalls.ready and self.ai.can_afford(EXTRACTOR))
        ):
            return False

        gas = self.ai.extractors
        gas_amount = len(gas)  # so it calculate just once per step
        vgs = self.ai.state.vespene_geyser.closer_than(10, self.ai.townhalls.ready.random)
        for geyser in vgs:
            self.drone = self.ai.select_build_worker(geyser.position)
            if not self.drone:
                return False
            if not self.ai.already_pending(EXTRACTOR):
                # if not gas and self.ai.pools:
                if not gas and self.ai.supply_used >= 14:
                    self.geyser = geyser
                    return True
            if (self.ai.time > 900 or self.ai.spires) and gas_amount < 11:
                self.geyser = geyser
                return True
            pit = self.ai.pits
            if pit and gas_amount < 8 and not self.ai.already_pending(EXTRACTOR):
                self.geyser = geyser
                return True
        return False

    async def handle(self, iteration):
        """Just finish the action of building the extractor"""
        self.ai.add_action(self.drone.build(EXTRACTOR, self.geyser))
        return True
