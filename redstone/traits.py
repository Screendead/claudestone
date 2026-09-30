"""What a design is good for. Some traits are facts about the blocks and are checked
against the build (CHECKS); the rest are the designer's claims, explained in VOCABULARY."""

from .fileformat import Spec
from .harness import parse_state

VOCABULARY = {
    # checked
    "silent": "no block or entity in it makes a sound when the circuit runs",
    "lightless": "no light level changes while it runs: no torches, lamps, bulbs or moving blocks",
    "pistonless": "no pistons",
    "entityless": "no entities",
    "uses_entities": "relies on entities (minecarts, item frames, ...)",
    "flat": "at most two blocks tall, base included",
    "one_wide": "one block wide in x or z, so copies can sit side by side",
    "instant": "a test declares delay: 0, zero game ticks from input to output (a zero in delays does not count)",
    "tileable": "copies can be laid next to each other to make a wider version: a tile test with a level offset",
    "stackable": "copies can be stacked vertically: a tile test with a vertical offset",
    # claimed
    "ultracompact": "smallest known volume for this function in the library",
    "compact": "small volume, not necessarily the smallest",
    "ultrafast": "fewest ticks known for this function in the library",
    "fast": "few ticks, not necessarily the fewest",
    "horizontal": "signal enters and leaves on the same layer",
    "vertical": "signal travels or is processed up or down",
    "analog": "works with signal strengths, not just on/off",
    "torch_based": "logic from redstone torches",
    "comparator_based": "logic from comparators",
    "observer_based": "logic from observers",
    "piston_based": "logic from pistons moving blocks",
    "rail_based": "logic from rails",
    "container_based": "logic from comparators reading containers",
    "tick_accurate": "its delay is exact and part of its interface",
    "reset_safe": "starts in a known state after placement",
    "lockable": "has a lock or hold input",
    "survival_friendly": "every block is obtainable and placeable in survival",
}

LIGHT = {"redstone_torch", "redstone_wall_torch", "redstone_lamp", "redstone_ore", "deepslate_redstone_ore",
         "sculk_sensor", "calibrated_sculk_sensor", "piston", "sticky_piston", "moving_piston"}
SOUND = {"piston", "sticky_piston", "moving_piston", "dispenser", "dropper", "note_block", "bell", "crafter",
         "sculk_sensor", "calibrated_sculk_sensor", "sculk_shrieker", "tripwire", "tripwire_hook", "lever"}
SOUND_SUFFIXES = ("_door", "_trapdoor", "_fence_gate", "_button", "_pressure_plate", "copper_bulb")
LIGHT_SUFFIXES = ("copper_bulb",)
NOISY_ENTITIES = ("minecart",)


def design_blocks(spec: Spec) -> dict:
    """The blocks that make up the design: every block but the fixtures."""
    return {p: s for p, s in spec.build.blocks.items() if p not in spec.fixtures}


def block_names(spec: Spec) -> set[str]:
    return {parse_state(s)[0].removeprefix("minecraft:") for s in design_blocks(spec).values()}


def dimensions(spec: Spec) -> tuple[int, int, int]:
    cells = set(design_blocks(spec)) | spec.reserved
    if not cells:
        return 0, 0, 0
    xs, ys, zs = zip(*cells)
    return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, max(zs) - min(zs) + 1


def _tiles(spec: Spec) -> list[list[int]]:
    return [t["tile"] for t in spec.tests if "tile" in t]


def _entity_ids(spec):
    return [e.removeprefix("minecraft:") for _, e, _ in spec.build.entities]


CHECKS = {
    "silent": lambda s: not any(n in SOUND or n.endswith(SOUND_SUFFIXES) for n in block_names(s))
    and not any(e.endswith(NOISY_ENTITIES) for e in _entity_ids(s)),
    "lightless": lambda s: not any(n in LIGHT or n.endswith(LIGHT_SUFFIXES) for n in block_names(s)),
    "pistonless": lambda s: not block_names(s) & {"piston", "sticky_piston"},
    "entityless": lambda s: not s.build.entities,
    "uses_entities": lambda s: bool(s.build.entities),
    "flat": lambda s: dimensions(s)[1] <= 2,
    "one_wide": lambda s: min(dimensions(s)[0], dimensions(s)[2]) == 1,
    "instant": lambda s: any(t.get("delay") == 0 for t in s.tests),
    "tileable": lambda s: s.name in UNTILED or any(dy == 0 for _, dy, _ in _tiles(s)),
    "stackable": lambda s: s.name in UNTILED or any(dy != 0 for _, dy, _ in _tiles(s)),
}

NEEDS = {"tileable": "no truth-table test has tile: [dx, 0, dz]",
         "stackable": "no truth-table test has tile: with dy != 0"}

# Claimed tileable or stackable before tile tests existed, proved (if at all) by a
# separate multi-copy file. Each leaves this list when it gains a tile test.
UNTILED = frozenset({
    'add_carry_cancel_cell', 'add_carry_cancel_chain_x4', 'add_full_comparator_lightless',
    'add_full_comparator_lightless_x2', 'add_half_comparator_flat', 'add_half_comparator_flat_x2',
    'analog_lift_down', 'analog_lift_up', 'and_comparator_lightless', 'and_comparator_lightless_x2',
    'and_torch_1wide_x2', 'clock_comparator_stack', 'clock_observer_pair', 'clock_observer_vertical',
    'count_bulb_ripple_bus', 'count_bulb_ripple_down', 'cross_alternating_bus', 'cross_diode_grid',
    'cross_instant_bus', 'cross_instant_column', 'cross_underpass', 'cross_underpass_bus',
    'cross_underpass_stack', 'dec_enc_4to2_instant', 'dec_prio_4to2', 'delay_observer_line',
    'delay_observer_tower', 'delay_pulse_preserving', 'delay_repeater_line', 'dl_dff_hopper_register',
    'dl_dff_hopper_register_x2', 'dl_hopper_register', 'dl_hopper_register_x3', 'dl_lock_stack',
    'mux_torch_lane', 'mux_torch_lane_x2', 'not_bus_staggered', 'not_bus_tileable', 'not_comparator_stack',
    'not_comparator_subtract', 'not_torch_tower', 'or_nor_wide_lightless', 'or_nor_wide_torch',
    'or_vertical_spiral', 'or_wide_instant', 'or_wide_repeater', 'pulse_dual_observer',
    'pulse_dual_observer_repeater', 'rs_comparator_ring', 'rs_dropper_bus', 'rs_dropper_pair',
    'rs_ring_reset_priority', 'rs_ring_stack', 'seg_bulb_3x5', 'seg_lamp_3x5', 'seg_lamp_3x5_x2',
    'seg_lamp_5x9', 'seg_piston_3x5', 'seg_trapdoor_3x5', 'shift_hopper_bus2', 'shift_pulse_lock_x2',
    'shift_reg4_lock', 'tff_bulb_counter', 'tff_copper_bulb', 'vwire_observer_bulb_down',
    'vwire_observer_down', 'vwire_observer_up', 'vwire_spiral', 'vwire_staircase_bus',
    'vwire_torch_ladder_down', 'vwire_torch_tower_bus', 'vwire_torch_tower_up', 'wire_checker_bus',
    'wire_flat_bus', 'wire_observer_bus', 'wire_rail_pulse_bus', 'wire_spaced_bus', 'xor_comparator_bridge',
    'xor_comparator_bridge_stack2', 'xor_observer_bulb', 'xor_observer_bulb_bus2', 'xor_piston_switch',
    'xor_piston_switch_stack2', 'xor_torch_flat', 'xor_torch_flat_stack2', 'xor_xnor_observer_bulb',
})


def violations(spec: Spec) -> list[str]:
    bad = [f"unknown trait {t!r}" for t in spec.traits if t not in VOCABULARY]
    bad += [f"claims {t!r} but " + NEEDS.get(t, "the build does not satisfy it")
            for t in spec.traits if t in CHECKS and not CHECKS[t](spec)]
    return bad
