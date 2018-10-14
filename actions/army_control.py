"""Everything related to controlling army units goes here"""
from sc2.constants import (
    ADEPTPHASESHIFT,
    AUTOTURRET,
    BUNKER,
    DISRUPTORPHASED,
    DRONE,
    EGG,
    INFESTEDTERRAN,
    INFESTEDTERRANSEGG,
    LARVA,
    MUTALISK,
    PHOTONCANNON,
    PLANETARYFORTRESS,
    PROBE,
    SCV,
    SPINECRAWLER,
    ZERGLING,
    ZERGLINGATTACKSPEED,
)

from .micro import Micro


class ArmyControl(Micro):
    """Can be improved"""

    def __init__(self, ai):
        self.ai = ai
        self.retreat_units = set()
        self.rally_point = None
        self.zergling_atk_speed = False

    async def should_handle(self, iteration):
        """Requirements to run handle"""
        return self.ai.zerglings | self.ai.ultralisks | self.ai.mutalisks

    async def handle(self, iteration):
        """It surrounds and target low hp units, also retreats when overwhelmed,
         it can be improved a lot but is already much better than a-move
        Name army_micro because it is in army.py."""
        targets = None
        combined_enemies = None
        enemy_building = self.ai.known_enemy_structures

        if not self.zergling_atk_speed and self.ai.hives:
            self.zergling_atk_speed = self.ai.already_pending_upgrade(ZERGLINGATTACKSPEED) == 1

        if self.ai.townhalls:
            self.rally_point = self.ai.townhalls.closest_to(self.ai.game_info.map_center).position.towards(
                self.ai.game_info.map_center, 10
            )

        if self.ai.known_enemy_units:
            excluded_units = {
                ADEPTPHASESHIFT,
                DISRUPTORPHASED,
                EGG,
                LARVA,
                INFESTEDTERRANSEGG,
                INFESTEDTERRAN,
                AUTOTURRET,
            }
            filtered_enemies = self.ai.known_enemy_units.not_structure.exclude_type(excluded_units)
            static_defence = self.ai.known_enemy_units.of_type({SPINECRAWLER, PHOTONCANNON, BUNKER, PLANETARYFORTRESS})
            combined_enemies = filtered_enemies.exclude_type({DRONE, SCV, PROBE}) | static_defence
            targets = static_defence | filtered_enemies.not_flying
        atk_force = self.ai.zerglings | self.ai.ultralisks | self.ai.mutalisks
        # enemy_detection = self.ai.known_enemy_units.not_structure.of_type({OVERSEER, OBSERVER})
        for attacking_unit in atk_force:
            if attacking_unit.type_id == MUTALISK and enemy_building.flying:
                self.ai.add_action(attacking_unit.attack(enemy_building.flying.closest_to(attacking_unit.position)))
                continue
            if attacking_unit.tag in self.retreat_units and self.ai.townhalls:
                self.has_retreated(attacking_unit)
                continue
            if (
                targets
                and targets.closer_than(17, attacking_unit.position)
                and await self.ai._client.query_pathing(
                    attacking_unit.position, targets.closest_to(attacking_unit.position).position
                )
            ):

                if self.retreat_unit(attacking_unit, combined_enemies):
                    continue

                if attacking_unit.type_id == ZERGLING:
                    if self.micro_zerglings(targets, attacking_unit):
                        continue
                else:
                    self.ai.add_action(attacking_unit.attack(targets.closest_to(attacking_unit.position)))
                    continue

            elif enemy_building.closer_than(30, attacking_unit.position):
                self.ai.add_action(attacking_unit.attack(enemy_building.closest_to(attacking_unit.position)))
                continue
            elif self.ai.time < 1000 and not self.ai.close_enemies_to_base:
                self.idle_unit(attacking_unit)
                continue
            else:
                if not self.retreat_units or self.ai.close_enemies_to_base or self.ai.time >= 1000:
                    if enemy_building:
                        self.ai.add_action(attacking_unit.attack(enemy_building.closest_to(attacking_unit.position)))
                        continue
                    elif targets:
                        self.ai.add_action(attacking_unit.attack(targets.closest_to(attacking_unit.position)))
                        continue
                    else:
                        self.attack_startlocation(attacking_unit)
                elif self.ai.townhalls:
                    self.move_to_rallying_point(attacking_unit)

    def move_to_rallying_point(self, unit):
        """Set the point where the units should gather"""
        if unit.position.distance_to_point2(self.rally_point) > 5:
            self.ai.add_action(unit.move(self.rally_point))

    def has_retreated(self, unit):
        """Identify if the unit has retreated"""
        if self.ai.townhalls.closer_than(15, unit.position):
            self.retreat_units.remove(unit.tag)

    def retreat_unit(self, unit, combined_enemies):
        """Tell the unit to retreat when overwhelmed"""
        if (
            self.ai.townhalls
            and not self.ai.close_enemies_to_base
            and not self.ai.units.structure.closer_than(7, unit.position)
            and self.is_overwhelmed(unit, combined_enemies)
        ):
            self.move_to_rallying_point(unit)
            self.retreat_units.add(unit.tag)
            return True
        return False

    def is_overwhelmed(self, unit, combined_enemies):
        return len(combined_enemies.closer_than(15, unit.position)) >= self.army_strength_around(unit)

    def army_strength_around(self, unit):
        return len(self.ai.zerglings.closer_than(20, unit.position))
        + len(self.ai.ultralisks.closer_than(20, unit.position)) * 6

    def micro_zerglings(self, targets, unit):
        """Target low hp units smartly, and surrounds when attack cd is down"""
        if self.zergling_atk_speed:  # more than half of the attack time with adrenal glands (0.35)
            if unit.weapon_cooldown <= 0.25:
                if self.attack_close_target(unit, targets):
                    return True
            else:
                if self.move_to_next_target(unit, targets):
                    return True
        elif unit.weapon_cooldown <= 0.35:  # more than half of the attack time with adrenal glands (0.35)
            if self.attack_close_target(unit, targets):
                return True
        else:
            if self.move_to_next_target(unit, targets):
                return True

        self.ai.add_action(unit.attack(targets.closest_to(unit.position)))
        return True

    def idle_unit(self, unit):
        """Control the idle units, by gathering then or telling then to attack"""
        if (
            len(self.ai.ultralisks.ready) < 4
            and self.ai.supply_used not in range(198, 201)
            and len(self.ai.zerglings.ready) < 41
            and self.ai.townhalls
            and self.retreat_units
        ):
            self.move_to_rallying_point(unit)
            return True
        enemy_building = self.ai.known_enemy_structures
        if enemy_building and self.ai.townhalls:
            self.attack_closest_building(unit)
        else:
            self.attack_startlocation(unit)
        return False

    def attack_closest_building(self, unit):
        """Attack the starting location"""
        enemy_building = self.ai.known_enemy_structures.not_flying
        if enemy_building:
            self.ai.add_action(
                unit.attack(enemy_building.closest_to(self.ai.townhalls.furthest_to(self.ai.game_info.map_center)))
            )

    def attack_startlocation(self, unit):
        """It tell to attack the starting location"""
        if self.ai.enemy_start_locations:
            self.ai.add_action(unit.attack(self.ai.enemy_start_locations[0]))
