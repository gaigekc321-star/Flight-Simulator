import sys, numpy as np
sys.path.insert(0, 'scripts')
from camo import *
from charts import *
from PIL import Image
pal = PAL.astype(np.uint8)
def finish(name, V, extra_unknown, seed, ppm_x, ppm_y, wrap, scale=1.3, open_r=3, min_px=300, blur=2.0, thr=0.12):
    V = np.stack([ndi.gaussian_filter(V[..., k], blur, mode=['wrap' if wrap else 'nearest', 'nearest']) for k in range(3)], -1)
    lab = V.argmax(2).astype(np.uint8); known = (V.sum(2) > thr) & ~extra_unknown
    known = ndi.binary_erosion(known, iterations=2)
    known = clean_known(lab, known, open_r=open_r, min_px=min_px)
    fl, fd = camo_fields(lab.shape, ppm_x, ppm_y, seed, wrap_y=wrap, scale=scale)
    full = classify(fl, fd, known=known, labels=lab, seed=seed, wrap_y=wrap)
    full = majority(full, 3.0, wrap_y=wrap)
    np.save(f'work/charts/{name}_labels.npy', full)
    vis = pal[full].copy(); dbg = vis.copy(); dbg[~known] = (dbg[~known] * 0.55 + np.array([90, 0, 90]) * 0.45).astype(np.uint8)
    Image.fromarray(dbg).save(f'work/{name}_labels_dbg.png')
    print(name, lab.shape, 'known %.2f' % known.mean(), 'class frac', [round(float((full == k).mean()), 3) for k in range(3)])
    return full
# ---------------- fins
H, W = FIN_H, FIN_W
yy = FIN_Y0 + (np.arange(W) + 0.5) / PPM; zz = FIN_Z1 - (np.arange(H) + 0.5) / PPM
Y, Z = np.meshgrid(yy, zz)
regbox = (Y > 10.30) & (Y < 12.20) & (Z > 2.38) & (Z < 2.90)
flagbox = (Y > 13.00) & (Y < 13.96) & (Z > 3.84) & (Z < 4.49)
o1 = np.load('work/obs1_finL.npz')['obs']
c1 = o1.argmax(2)
shadow = (Z > 3.65) & (Y > 13.3 + (5.0 - Z) * 0.7 - 0.08)
unk = (Z > 4.72) | shadow | flagbox | (regbox & (c1 == 0)) | ((Y > 12.25) & (Y < 12.62) & (Z > 3.38) & (Z < 3.60))   # last: static-port style fitting w/ shadow
unk |= ndi.binary_dilation(regbox & (c1 == 0), iterations=4)
finish('finL', o1, unk, 21, PPM, PPM, False)
o3 = np.load('work/obs3_finR.npz')['obs']; c3 = o3.argmax(2)
unk = (Z > 4.35) | flagbox | ndi.binary_dilation(regbox & (c3 == 0), iterations=4) | (Y > 14.2)
finish('finR', o3, unk, 22, PPM, PPM, False, open_r=2, min_px=200)
# ---------------- engines (chart: x = station, y = angle; 1 deg = 0.0148 m at r=0.85)
He, We = ENG_H, ENG_W
ph = (np.arange(He) + 0.5) / PPD - 180.0; ye = ENG_Y0 + (np.arange(We) + 0.5) / PPM
PH, YE = np.meshgrid(ph, ye, indexing='ij')
ends = (YE < 7.45) | (YE > 12.0)
oL = np.load('work/obs1_engL.npz')['obs']
finish('engL', oL, ends | (PH < 50) | (PH > 140), 31, PPM, PPD / 0.0148, True, open_r=2, min_px=200)
oR = np.load('work/obs2_engR.npz')['obs'] * 0.8 + np.load('work/obs3_engR.npz')['obs']
finish('engR', oR, ends | (PH < 50) | (PH > 140), 32, PPM, PPD / 0.0148, True, open_r=2, min_px=200)
# ---------------- planar top charts (procedural only): wings + stabiliser, 160 px/m, x in [-14.6,14.6], y in [-1.6,19.4]
TW, TH_ = int(29.2 * PPM), int(21.0 * PPM)
fl, fd = camo_fields((TH_, TW), PPM, PPM, 41, wrap_y=False, scale=1.3)
top = majority(classify(fl, fd), 3.0)
np.save('work/charts/top_labels.npy', top)
Image.fromarray(pal[top]).resize((TW // 4, TH_ // 4), Image.LANCZOS).save('work/top_labels_small.png')
print('top', top.shape)
