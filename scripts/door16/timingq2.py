"""COMPUTED timing for ctrlq (circuit.propagate + bulb-reading comparators), against the stage-1 stand-in schedule
(MEASURED door16_quart_pairs): spits at R+56+10j from each pair's ZA kick R, the hold from R+58+10N for 40 gt."""
import ctrlq2 as ctrlq
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
    """Taps A and B carry the holds' common delay and set the hold length (B 40 gt after A); each class's ZA kick is
    delayed (d) just enough that the shared ladder feed (LADF) and the per-class lines (XSP*, XHP*) only add delay."""
    T = target(N)
    g = (o['hold_off_e'] - o['hold_on_e']) - (T['hold_off'] - T['hold_on'])
    d = {c: max(0, o[f'spit_{c}'] - T['spit'], o[f'hold_on_{c}'] + max(0, g) - T['hold_on']) for c in 'eo'}
    sp = {c: T['spit'] - o[f'spit_{c}'] + d[c] for c in 'eo'}
    ho = {c: T['hold_on'] - o[f'hold_on_{c}'] + d[c] for c in 'eo'}
    lad, a = min(sp.values()), min(ho.values())
    return {'LADF': lad, 'XSPE': sp['e'] - lad, 'XSPO': sp['o'] - lad, 'ZASE': d['e'], 'ZASO': d['o'], 'TAPA': a,
            'TAPB': a - g, 'XHPE': ho['e'] - a, 'XHPO': ho['o'] - a, 'KZB': o['gz_in-KZ_on'] - 4}


def tuned(N, rounds=5, start=None):
    """ZA delays become fixed extra repeaters (ctrlq2.ZAS_EXTRA): rebuild until no ZA delay is asked for."""
    if start:
        ctrlq.ZAS_EXTRA.update(start)
    for r in range(rounds):
        c = ctrlq.build(N)
        o = base(c)
        ex = extras(o, N)
        print('base', o)
        print('extras', ex, 'zas_extra', ctrlq.ZAS_EXTRA)
        short = 8 - min(o['close_kick-spit_e'], o['close_kick-spit_o'])
        if short > 0 and ctrlq.N > 5:   # the close kick must follow the close spit: longer close-kick snake
            ctrlq.CLOSEK_LINES[0] += -(-short // 20)
            L3.PREV.pop('CLOSEK', None)
        if not ex['ZASE'] and not ex['ZASO'] and short <= 0:
            break
        ctrlq.ZAS_EXTRA['e'] += ex['ZASE'] // 2
        ctrlq.ZAS_EXTRA['o'] += ex['ZASO'] // 2
        L3.remember(c)              # keep every other route, so only the ZA spit lines move
        for k in ('ZASE', 'ZASO'):
            L3.PREV.pop(k, None)
    else:
        raise RuntimeError('ZA delays did not settle')
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
