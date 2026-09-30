import os
from pathlib import Path

import pytest

from redstone.door_volume import (Entity, Tick, Zones, aabb_cells, bounds, cells, dims, entity_cells, head_cell,
                                  hitbox, on_shell, region, volume)
from redstone.entity_dims import BLOCKS_BUILDING, ENTITY_DIMS
from scripts import entity_dims

HALL = cells([((2, 1, 0), (2, 2, 4))])
FRAME = cells([((2, 1, 2), (2, 2, 2))])
LEVER = (4, 2, 3)


def zones(**kw) -> Zones:
    base = dict(frame=FRAME, device=frozenset({LEVER}), hallway=HALL, region=((-2, -2, -2), (6, 6, 6)),
                door_material=frozenset({"smooth_quartz"}), surface_material=frozenset({"stone"}))
    return Zones(**(base | kw))


def test_table_has_the_harness_entities():
    assert ENTITY_DIMS["minecart"] == (0.98, 0.7)
    assert ENTITY_DIMS["armor_stand"] == (0.5, 1.975)
    assert ENTITY_DIMS["mannequin"] == (0.6, 1.8)
    assert {"minecart", "armor_stand", "mannequin", "falling_block", "tnt"} <= BLOCKS_BUILDING
    assert not {"item", "marker", "text_display", "item_frame"} & BLOCKS_BUILDING


def test_parser_reads_multiline_registrations_and_inheritance(tmp_path):
    d = tmp_path / entity_dims.ENTITY_DIR
    d.mkdir(parents=True)
    (d / "EntityTypeIds.java").write_text(
        'public static final ResourceKey<EntityType<?>> CART = create("cart");\n'
        'public static final ResourceKey<EntityType<?>> BLOB = create("blob");\n')
    (d / "EntityTypes.java").write_text(
        "   public static final EntityType<Cart> CART = register(\n"
        "      EntityTypeIds.CART,\n"
        "      EntityType.Builder.of(Cart::new, MobCategory.MISC)\n"
        "         .sized(0.98F, 0.7F)\n"
        "   );\n"
        "   public static final EntityType<Outer.Blob> BLOB = register(\n"
        "      EntityTypeIds.BLOB, EntityType.Builder.of(Blob::new, MobCategory.MISC).sized(0.0F, 0.0F)\n"
        "   );\n")
    (d / "Cart.java").write_text("public class Cart extends AbstractCart {}")
    (d / "AbstractCart.java").write_text("public abstract class AbstractCart extends Entity {\n"
                                         "      this.blocksBuilding = true;\n}")
    (d / "Outer.java").write_text("public class Outer extends Entity {\n"
                                  "   public static class Blob extends Outer {}\n}")
    assert entity_dims.parse(tmp_path) == ({"blob": (0.0, 0.0), "cart": (0.98, 0.7)}, ["cart"])


@pytest.mark.skipif(not os.environ.get("MC_SRC"), reason="set MC_SRC to the decompiled source root")
def test_generated_table_is_current():
    committed = Path(entity_dims.OUT).read_text()
    assert entity_dims.render(*entity_dims.parse(Path(os.environ["MC_SRC"]))) == committed


def test_centred_minecart_occupies_one_cell():
    assert entity_cells(Entity("minecart", (0.5, 1.0625, 0.5))) == {(0, 1, 0)}


def test_hitbox_spanning_cells_counts_each_cell_it_blocks():
    # 0.98 wide at x=1.0: x from 0.51 to 1.49, into cells 0 and 1; 0.7 tall from y=1.5 reaches y=2.2.
    assert entity_cells(Entity("minecart", (1.0, 1.5, 0.5))) == {(0, 1, 0), (1, 1, 0), (0, 2, 0), (1, 2, 0)}
    assert entity_cells(Entity("minecart", (0.5, 1.5, 0.5), scale=0.5)) == {(0, 1, 0)}


def test_touching_a_cell_face_is_not_occupying_it():
    assert aabb_cells(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))) == {(0, 0, 0)}
    assert aabb_cells(((0.0, 0.0, 0.0), (1.0 + 5e-8, 1.0, 1.0))) == {(0, 0, 0)}
    assert aabb_cells(((0.0, 0.0, 0.0), (1.001, 1.0, 1.0))) == {(0, 0, 0), (1, 0, 0)}


def test_entities_that_dont_block_placement_occupy_nothing():
    assert entity_cells(Entity("item", (0.5, 1.0, 0.5))) == set()
    assert entity_cells(Entity("minecraft:text_display", (0.5, 1.0, 0.5))) == set()


def test_unknown_entity_type_is_an_error():
    with pytest.raises(KeyError):
        entity_cells(Entity("minecrat", (0.5, 1.0, 0.5)))


def test_hitbox_uses_float_dimensions():
    (x0, _, _), (x1, y1, _) = hitbox(Entity("armor_stand", (0.5, 0.0, 0.5)))
    assert (x0, x1) == (0.25, 0.75) and y1 == pytest.approx(1.975, abs=1e-6) and y1 != 1.975


def test_frame_and_device_are_excluded_and_circuitry_counts():
    closed = Tick({(2, 1, 2): "smooth_quartz", (2, 2, 2): "smooth_quartz", LEVER: "lever",
                   (3, 1, 2): "sticky_piston[facing=west]", (4, 1, 3): "redstone_wire"})
    v = volume([closed], zones())
    assert v.any == v.circ == {(3, 1, 2), (4, 1, 3)}
    assert v.v_circ == 2 * 1 * 2 and v.ok


def test_hallway_counts_only_in_the_open_state():
    poke = (2, 1, 0)
    ticks = [Tick({poke: "sticky_piston"}), Tick({poke: "moving_piston"}, open=False),
             Tick({(3, 1, 3): "redstone_wire"}, open=True)]
    assert volume(ticks, zones()).any == {(3, 1, 3)}
    ticks.append(Tick({poke: "piston_head", (3, 1, 3): "redstone_wire"}, open=True))
    v = volume(ticks, zones())
    assert v.circ == {poke, (3, 1, 3)} and dims(bounds(v.circ)) == (2, 1, 4)


def test_entity_in_hallway_counts_only_when_open():
    cart = Entity("minecart", (2.5, 1.0, 1.5))
    assert volume([Tick({}, (cart,))], zones()).any == set()
    assert volume([Tick({}, (cart,), open=True)], zones()).circ == {(2, 1, 1)}


def test_entity_hitbox_widens_the_box_over_ticks():
    wire = (3, 1, 3)
    ticks = [Tick({wire: "redstone_wire"}), Tick({wire: "redstone_wire"}, (Entity("minecart", (4.0, 1.0, 3.5)),))]
    v = volume(ticks, zones())
    assert v.circ == {wire, (4, 1, 3)} and v.v_circ == 2


def test_door_material_outside_the_hallway_splits_any_from_circ():
    ticks = [Tick({(3, 1, 3): "redstone_wire", (3, 3, 3): "smooth_quartz"})]
    v = volume(ticks, zones())
    assert (v.v_any, v.v_circ) == (3, 1)


def test_outer_surface_blocks_are_ignored_but_circuitry_in_the_surface_is_not():
    wall = frozenset({(1, 1, 0), (3, 1, 0)})
    ticks = [Tick({(1, 1, 0): "stone", (3, 1, 0): "observer", (3, 1, 1): "redstone_wire"})]
    assert volume(ticks, zones(outer_surface=wall)).any == {(3, 1, 0), (3, 1, 1)}


def test_surface_material_is_circuitry_off_the_surface():
    ticks = [Tick({(3, 1, 3): "redstone_wire", (3, 0, 3): "stone", (2, 1, 1): "stone"}, open=True)]
    assert volume(ticks, zones()).circ == {(3, 1, 3), (3, 0, 3)}


def test_exempt_entities_are_left_out():
    cart = Entity("minecart", (4.5, 1.0, 4.5), name="cart")
    assert volume([Tick({}, (cart,))], zones(exempt=frozenset({"cart"}))).any == set()
    assert volume([Tick({}, (cart,))], zones()).any == {(4, 1, 4)}


def test_anything_on_the_shell_fails_even_if_excluded():
    box = ((0, 0, 0), (4, 4, 4))
    z = zones(region=box, hallway=frozenset({(0, 2, 2)}))
    v = volume([Tick({(0, 2, 2): "piston_head", (2, 2, 2): "stone"}, (Entity("minecart", (2.5, 3.5, 2.5)),))], z)
    assert v.shell == {(0, 2, 2), (2, 4, 2)} and not v.ok


def test_empty_volume_is_zero():
    v = volume([Tick({(5, 5, 5): "air", LEVER: "lever"})], zones())
    assert (v.v_any, v.v_circ, v.ok) == (0, 0, True)


def test_region_grows_and_clamps():
    assert region([((0, 1, 0), (4, 3, 4)), ((2, 1, -3), (2, 2, 0))]) == ((-2, -1, -5), (6, 5, 6))
    assert region([((0, 1, 0), (4, 3, 4))], clamp=((-1, 0, -1), (100, 100, 100))) == ((-1, 0, -1), (6, 5, 6))
    assert on_shell((-2, 0, 0), ((-2, -2, -2), (2, 2, 2))) and not on_shell((1, 1, 1), ((-2, -2, -2), (2, 2, 2)))


def test_head_cell():
    assert head_cell((3, 1, 2), "west") == (2, 1, 2)
    assert head_cell((0, 5, 0), "down") == (0, 4, 0)
