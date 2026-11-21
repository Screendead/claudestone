"""COMPUTED timing for layout3 (as timing2: door16_band_ctrl's MEASURED offsets from each pair's ZA kick R)."""
import layout3
import circuit
from circuit import kind_of, prop, add

_orig_prop = circuit.propagate


def propagate(c, src, t0=0, stop=None):
    """circuit.propagate plus comparators reading a bulb (2 gt after the bulb's first toggle)."""
    best = _orig_prop(c, src, t0, stop)
    allc = {**c.fixed, **c.cells}
    changed = True
    while changed:
        changed = False
        for p, t in list(best.items()):
            if kind_of(allc.get(p, 'air')) != 'bulb':
                continue
            for d in ('east', 'west', 'north', 'south'):
                q = add(p, d)
                st = allc.get(q, '')
                if kind_of(st) == 'comp' and add(q, prop(st, 'facing')) == p and t + 2 < best.get(q, 1e9):
                    sub = _orig_prop(c, q, t + 2, stop)
                    for k, v in sub.items():
                        if v < best.get(k, 1e9):
                            best[k] = v; changed = True
    return best

TARGET = dict(spit=46, hold_on=98, hold_off=138)


def base(c):
    m = c.marks
    r = propagate(c, m['gr'])
    o = {'R_e': r[m['r_e_in']], 'R_o': r[m['r_o_in']]}
    o['zas_e'], o['zas_o'] = r[(4, 7, 3)] - o['R_e'], r[(-4, 9, 3)] - o['R_o']
    down = lambda comp, end: propagate(c, comp, 2)[end]
    De, Do = down((0, 7, 23), (2, 7, 17)), down((-8, 9, 18), (-6, 9, 15))
    He, Ho = down((0, 5, 25), (2, 5, 16)), down((-9, 7, 18), (-6, 7, 16))
    M0 = r[m['xsm']]
    dSE = propagate(c, m['xs_comp'], 2)[(0, 7, 25)]
    dSO = propagate(c, m['xs_comp'], 2)[(-8, 9, 20)]
    tA, tB = r[m['tA_end']], r[m['tB_end']]
    dE = propagate(c, m['xh_comp'], 2)[(-1, 5, 26)]
    dO = propagate(c, m['xh_comp'], 2)[(-9, 7, 20)]
    o['tB-tA'] = tB - tA
    o['spit_e'] = M0 + dSE + De - o['R_e']
    o['spit_o'] = M0 + dSO + Do - o['R_o']
    o['hold_on_e'], o['hold_off_e'] = tA + dE + He - o['R_e'], tB + dE + He - o['R_e']
    o['hold_on_o'], o['hold_off_o'] = tA + dO + Ho - o['R_o'], tB + dO + Ho - o['R_o']
    k = propagate(c, m['gc'])
    o['close_kick-spit_e'] = k[(1, 5, 20)] + 2 - (k[m['xsm']] + dSE + De)
    o['close_kick-spit_o'] = k[(-8, 7, 15)] - (k[m['xsm']] + dSO + Do)
    f = propagate(c, m['gf'])
    TR = f[(-8, 7, 15)]
    sx = propagate(c, m['sx'], TR + 2)
    o['gx_in-K_on'] = sx[m['gx_in']] - f[m['kx']]
    s = propagate(c, m['gs'])
    Rz = s[m['zbk_e_in']]
    sz = propagate(c, m['sz'], Rz + 2)
    o['gz_in-KZ_on'] = sz[m['gz_in']] - s[m['kz']]
    o['zbk-zbs_e'] = Rz - s[(4, 7, 23)]
    o['zbk-zbs_o'] = s[(-5, 7, 24)] - s[(-4, 9, 23)]
    return o


def extras(o):
    xe, xo = TARGET['hold_on'] - o['hold_on_e'], TARGET['hold_on'] - o['hold_on_o']
    a = min(xe, xo)
    ye = TARGET['hold_off'] - o['hold_off_e']
    se, so = TARGET['spit'] - o['spit_e'], TARGET['spit'] - o['spit_o']
    # spits: LADF moves both; a pair whose spit would come too late gets its ZA kick delayed by its delay bulb, which
    # moves its holds too (absorbed by TAPA/TAPB/XHPx)
    lad = min(max(0, min(se, so)), 24)                # the ladder feed's 6 repeaters, delay <= 3
    se2, so2 = se - lad, so - lad
    ze, zo = 0, 0
    xe, xo = xe + ze, xo + zo
    a = min(xe, xo)
    ye = ye + ze
    return {'TAPA': a, 'XHPE': xe - a, 'XHPO': xo - a, 'TAPB': ye - (xe - a), 'LADF': lad, 'XSPE': se2,
            'XSPO': so2, 'ZASE': ze, 'ZASO': zo, 'KX': o['gx_in-K_on'] - 2, 'KZB': o['gz_in-KZ_on'] - 4}


def tuned(N=5):
    c = layout3.build(N)
    ex = extras(base(c))
    assert all(v >= 0 and v % 2 == 0 for v in ex.values()), ex
    c = layout3.build(N, delays=ex)
    return c, base(c), ex


if __name__ == '__main__':
    c = layout3.build(5)
    print(base(c))
    print(extras(base(c)))
