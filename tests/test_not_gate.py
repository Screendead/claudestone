from redstone.build import Build

LEVER, STONE, TORCH, LAMP = (0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)


def not_gate() -> Build:
    return (
        Build()
        .place(LEVER, "lever[face=wall,facing=west,powered=false]")
        .place(STONE, "stone")
        .place(TORCH, "redstone_wall_torch[facing=east]")
        .place(LAMP, "redstone_lamp")
    )


def test_lamp_lit_at_rest(rig):
    rig.load(not_gate())
    rig.step(4)
    assert rig.is_(TORCH, "redstone_wall_torch[lit=true]")
    assert rig.is_(LAMP, "redstone_lamp[lit=true]")


def test_lever_turns_lamp_off_and_back_on(rig):
    rig.load(not_gate())
    rig.step(4)
    rig.use(LEVER)
    rig.step(6)
    assert rig.is_(TORCH, "redstone_wall_torch[lit=false]")
    assert rig.is_(LAMP, "redstone_lamp[lit=false]")
    rig.use(LEVER)
    rig.step(6)
    assert rig.is_(LAMP, "redstone_lamp[lit=true]")


def test_button_pulse_releases_after_20_ticks(rig):
    b = not_gate()
    b.place(LEVER, "stone_button[face=wall,facing=west,powered=false]")
    rig.load(b)
    rig.step(4)
    rig.use(LEVER)
    rig.step(6)  # torch turns off after 2 ticks, lamp 4 ticks after that
    assert rig.is_(LAMP, "redstone_lamp[lit=false]")
    rig.step(13)
    assert rig.is_(LEVER, "stone_button[powered=true]")
    rig.step(11)
    assert rig.is_(LEVER, "stone_button[powered=false]")
    assert rig.is_(LAMP, "redstone_lamp[lit=true]")
