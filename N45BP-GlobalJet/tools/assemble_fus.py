import sys, numpy as np
sys.path.insert(0, 'scripts')
from camo import *
from charts import *
from camlib import YP0, YP1
from PIL import Image
o1 = np.load('work/obs1_fus.npz')['obs']; o2 = np.load('work/obs2_fus.npz')['obs']; o3 = np.load('work/obs3_fus.npz')['obs']
H, W = o1.shape[:2]
th = (np.arange(H) + 0.5) / PPD - 180.0
yy = FUS_Y0 + (np.arange(W) + 0.5) / PPM
TH, YY = np.meshgrid(th, yy, indexing='ij')
rng0 = np.random.default_rng(5)
wob = smooth_noise((H, W), 60, 30, rng0, True) * 5.0            # wavy reliability limits (deg)
relL = (TH >= 12 + wob) & (TH <= 112 + wob); relR = (TH <= -60 + wob) & (TH >= -112 + wob)
ok_y = (YY > -11.0) & (YY < 12.5)
V = o1 * relL[..., None] + (o2 * 1.0 + o3 * 0.6) * relR[..., None]
V = V * ok_y[..., None]
V = np.stack([ndi.gaussian_filter(V[..., k], 3.0, mode=['wrap', 'nearest']) for k in range(3)], -1)
lab = V.argmax(2).astype(np.uint8); known = V.sum(2) > 0.15
known &= ~((YY > YP0 - 0.03) & (YY < YP1 + 0.03))          # 6000-only fuselage plug: no real-world data
known = ndi.binary_erosion(known, iterations=3)
known = clean_known(lab, known, open_r=4, min_px=700)
np.savez_compressed('work/charts/fus_known.npz', lab=lab, known=known)
seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
# circumference varies; use PPD-> metres at mid radius 1.345 m: 1 deg = 0.0235 m -> 4 px/deg = 170 px/m
fl, fd = camo_fields((H, W), PPM, PPD / 0.0235, seed, wrap_y=True, scale=1.3)
full = classify(fl, fd, known=known, labels=lab, seed=seed, wrap_y=True)
full = majority(full, 3.0, wrap_y=True)
np.save('work/charts/fus_labels.npy', full)
pal = PAL.astype(np.uint8)
vis = pal[full].copy()
Image.fromarray(vis).save('work/charts/fus_labels.png')
dbg = vis.copy(); dbg[~known] = (dbg[~known] * 0.55 + np.array([90, 0, 90]) * 0.45).astype(np.uint8)
Image.fromarray(dbg).resize((W // 2, H // 2), Image.LANCZOS).save('work/fus_labels_dbg.png')
Image.fromarray(vis).resize((W // 2, H // 2), Image.LANCZOS).save('work/fus_labels_small.png')
print('known frac', known.mean(), 'class frac', [(full == k).mean().round(3) for k in range(3)], 'known class frac', [(lab[known] == k).mean().round(3) for k in range(3)])
