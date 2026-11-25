"""Composite paint tiles with the paint kit's Details (normal) and Weathering (multiply) layers -> final ALBD tiles."""
import sys, numpy as np, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
T = 4096
SHEETS = {
 'ext': dict(det='work/layers/ext/ALBD__Details__Details.png', wth='work/layers/ext/ALBD__Weathering__Weathering.png',
             tiles={f'EXT_{1001 + k}': (k % 4, k // 4) for k in range(7)}),
 'engine': dict(det='work/layers/engine/ALBD__Details__Details.png', wth='work/layers/engine/ALBD__Weathering__Weathering.png',
             tiles={'ENG_L': (0, 0), 'ENG_R': (1, 0)}),
 'wing': dict(det='work/layers/wing/ALBD__Details.png', wth='work/layers/wing/ALBD__Weathering.png',
             tiles={'WING_L_1001': (0, 0), 'WING_L_1002': (1, 0), 'WING_R_1001': (0, 1), 'WING_R_1002': (1, 1)}),
}
only = sys.argv[1:]
for sname, S in SHEETS.items():
    if only and sname not in only: continue
    det = Image.open(S['det']); wth = Image.open(S['wth'])
    for tname, (cx, cy) in S['tiles'].items():
        box = (cx * T, cy * T, (cx + 1) * T, (cy + 1) * T)
        p = np.asarray(Image.open(f'work/paint/{tname}.png').convert('RGB')).astype(np.float32)
        dt = np.asarray(det.crop(box)).astype(np.float32); a = dt[..., 3:4] / 255
        out = p * (1 - a) + dt[..., :3] * a
        w = np.asarray(wth.crop(box)).astype(np.float32); wa = w[..., 3:4] / 255
        out = out * ((w[..., :3] / 255) * wa + (1 - wa))
        Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8)).save(f'work/final/{tname}.png', compress_level=4)
        print(tname, 'details coverage %.1f%%' % (100 * (a > 0.5).mean()), flush=True)
