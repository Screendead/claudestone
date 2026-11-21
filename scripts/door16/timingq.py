"""COMPUTED timing for ctrlq (circuit.propagate + bulb-reading comparators), against the stage-1 stand-in schedule
(MEASURED door16_quart_pairs): spits at R+56+10j from each pair's ZA kick R, the hold from R+58+10N for 40 gt."""
import ctrlq
import layout3 as L3
from timing3 import propagate

ZB_SPIT = None


def target(N):
    return dict(spit=56, hold_on=58 + 10 * N, hold_off=98 + 10 * N)


def base(c):
    m = c.marks
    xs = m['xs']
    e, o = xs['E'], xs['O']
    r = propagate(c, m['gr'])
    out = {'R_e': r[m['r_e_in']], 'R_o': r[m['r_o_in']]}
    M0 = r[m['xsm']]
    pc = lambda src, t0=2: propagate(c, src, t0)
    dS = pc(m['xs_comp'])
    dH = pc(m['xh_comp'])
    for cls, d in (('e', e), ('o', o)):
        De = pc(d['spit_comp'])[d['spit']]
        He = pc(d['hold_comp'])[d['p_t']]
        R0 = out[f'R_{cls}']
        out[f'spit_{cls}'] = M0 + dS[d['spit_bulb']] + De - R0
        out[f'hold_on_{cls}'] = r[m['tA_end']] + dH[d['hold_bulb']] + He - R0
        out[f'hold_off_{cls}'] = r[m['tB_end']] + dH[d['hold_bulb']] + He - R0
    k = propagate(c, m['gc'])
    for cls, d in (('e', e), ('o', o)):
        sp = k[m['xsm']] + dS[d['spit_bulb']] + pc(d['spit_comp'])[d['spit']]
        out[f'close_kick-spit_{cls}'] = k[d['kick']] - sp
    s = propagate(c, m['gs'])
    Rz = s[m['zbk_e_in']]
    sz = propagate(c, m['sz'], Rz + 2)
    out['gz_in-KZ_on'] = sz[m['gz_in']] - s[m['kz']]
    out['zbk-zbs_e'] = Rz - s[(4, 7, ctrlq.bq.MARKS[(1, 'B')]['spit'][2])]
    out['zbk-zbs_o'] = s[m['zbk_o_in']] - s[m['zbs_o']]
    return out


def extras(o, N):
    """Spits: the later class's ZA kick is delayed so both spit on one ladder delay; holds: tap A sets the earlier
    class, the odd class's delay line the rest; tap B ends both 40 gt later."""
    T = target(N)
    se, so = T['spit'] - o['spit_e'], T['spit'] - o['spit_o']
    zae, zao = max(0, so - se), max(0, se - so)
    lad = max(se, so)
    xe, xo = T['hold_on'] - o['hold_on_e'] + zae, T['hold_on'] - o['hold_on_o'] + zao
    ye = T['hold_off'] - o['hold_off_e'] + zae
    a = min(xe, xo)
    return {'LADF': lad, 'ZASE': zae, 'ZASO': zao, 'TAPA': a, 'XHPE': xe - a, 'XHPO': xo - a,
            'TAPB': ye - (xe - a), 'KZB': o['gz_in-KZ_on'] - 4}


def tuned(N):
    c = ctrlq.build(N)
    o = base(c)
    ex = extras(o, N)
    print('base', o)
    print('extras', ex)
    assert all(v >= 0 and v % 2 == 0 for v in ex.values()), ex
    L3.remember(c)
    c = ctrlq.build(N, delays=ex)
    return c, base(c), ex


if __name__ == '__main__':
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    ctrlq.setup(n)
    c, o, ex = tuned(n)
    print('tuned', o)
