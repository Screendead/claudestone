"""Save the routes of some nets of a door16_quart_compact build as pins (scripts/door16/<pin file>), so a later build
with other snakes or rows reuses them wherever their cells are still free.

pin_v3.pkl, the routes low_snakes.py keeps from odd_south.py (about a minute):
python -m scripts.door16.save_pins scripts/door16/odd_south.py pin_v3.pkl \
    XKE,XKO,CLOSE,STOREE,KZB,XARR,SX,ZASE,ZASO,TMR,XSPE,XSPO,XHPE,XHPO
"""
import ast
import pickle
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import ctrlq2 as ctrlq      # noqa: E402
import layout3 as L3        # noqa: E402
import timingq2 as timingq  # noqa: E402

cfg = ast.literal_eval(Path(sys.argv[1]).read_text())
ctrlq.COMPACT.update(cfg)
ctrlq.setup(8, 8)
timingq.tuned(8, start=dict(cfg.get('zas_start') or {'e': 25, 'o': 25}))
keep = sys.argv[3].split(',')
# L3.PREV holds the last tuning round's routes, before the tuned delays go on
pickle.dump({k: L3.PREV[k] for k in keep}, open(HERE / sys.argv[2], 'wb'))
print('pinned', keep)
