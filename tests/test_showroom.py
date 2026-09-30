from redstone.showroom import RCON_MAX, fit_rcon


def stack(i: int) -> str:
    return f'{{slot:{i},item:{{id:"minecraft:cobblestone",count:64}}}}'


def test_a_short_command_is_sent_as_it_is():
    assert fit_rcon("setblock ~ ~ ~ minecraft:stone") == ["setblock ~ ~ ~ minecraft:stone"]


def test_a_full_shulker_box_in_a_dispenser_is_placed_in_pieces():
    box = ('{Slot:0b,id:"minecraft:shulker_box",count:1,components:{"minecraft:container":['
           + ",".join(stack(i) for i in range(27)) + "]}}")
    cmd = f"setblock ~3 ~4 ~1 minecraft:dispenser[facing=south]{{Items:[{box},{{Slot:1b,id:\"minecraft:stone\",count:1}}]}}"
    assert len(cmd) > RCON_MAX
    parts = fit_rcon(cmd)
    assert parts[0] == "setblock ~3 ~4 ~1 minecraft:dispenser[facing=south]{Items:[]}"
    assert parts[1] == ('data modify block ~3 ~4 ~1 Items append value '
                        '{Slot:0b,id:"minecraft:shulker_box",count:1,components:{"minecraft:container":[]}}')
    assert parts[2:29] == [f'data modify block ~3 ~4 ~1 Items[-1].components."minecraft:container" append value {stack(i)}'
                           for i in range(27)]
    assert parts[29] == 'data modify block ~3 ~4 ~1 Items append value {Slot:1b,id:"minecraft:stone",count:1}'
    assert all(len(p) <= RCON_MAX for p in parts)
