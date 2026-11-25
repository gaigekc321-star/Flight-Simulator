"""Full segmentation of camo tones in a photo given model maps (pm npz).
usage: seg_pipeline.py photo pm.npz out_prefix y0 y1 angle_deg [T]"""
import sys, numpy as np, json, time
sys.path.insert(0, 'scripts')
from seg_lib import *
from seg_comb import local_hists
from PIL import Image
from skimage import color
from skimage.transform import rotate, resize
photo, pmf, out = sys.argv[1], sys.argv[2], sys.argv[3]
Y0, Y1 = int(sys.argv[4]), int(sys.argv[5]); ANG = float(sys.argv[6]); T = float(sys.argv[7]) if len(sys.argv) > 7 else 0.016
CHROMA = float(sys.argv[8]) if len(sys.argv) > 8 else 11
MINBIN = int(sys.argv[9]) if len(sys.argv) > 9 else 300
objs = json.load(open('work/model.json'))
rgb = np.asarray(Image.open(photo).convert('RGB'))[Y0:Y1]
pm = np.load(pmf); obj = pm['obj'][Y0:Y1]; nrm = pm['nrm'][Y0:Y1]; pos = pm['pos'][Y0:Y1]
H, W = obj.shape
gmap = {}
for o in objs:
    g = 0
    if o['mat'] == 'GLEX_EXT': g = 1
    if o['mat'].startswith('GLEX_ENG'): g = 2
    if o['name'] == 'Tail_003': g = 3
    if o['name'] in ('Tail_042', 'Object031', 'Tail_040', 'Tail_043', 'Tail_Skin_002'): g = 4
    if o['name'] in ('Tail_000', 'Tail_001', 'Tail_Skin_000', 'Tail_Skin_001'): g = 5
    gmap[o['i']] = g
lut = np.zeros(max(gmap) + 2, np.int8)
for k, v in gmap.items(): lut[k] = v
grp = np.zeros((H, W), np.int8); grp[obj >= 0] = lut[obj[obj >= 0]]
lab = color.rgb2lab(rgb.astype(np.float32) / 255); chroma = np.hypot(lab[..., 1] - np.median(lab[..., 1][grp == 1]), lab[..., 2] - np.median(lab[..., 2][grp == 1]))
Yl = luminance(rgb); logY = np.log(np.maximum(Yl, 1e-4)).astype(np.float32)
mask = ndi.binary_erosion(grp > 0, iterations=3) & (chroma < CHROMA) & (lab[..., 0] > 10)
mask = ndi.binary_opening(mask, iterations=1)
# --- model-based shading normalisation: f(theta) per group (theta from surface normal)
theta = np.degrees(np.arctan2(np.abs(nrm[..., 0]), nrm[..., 2]))        # 0 top .. 180 bottom
flat = logY.copy()
for g in (1, 2):
    mg = mask & (grp == g)
    if g == 1: mg_fit = mg & (pos[..., 1] > -6.5) & (pos[..., 1] < 7.0) & (np.abs(nrm[..., 1]) < 0.12)
    else: mg_fit = mg & (np.abs(nrm[..., 1]) < 0.15)
    if mg_fit.sum() < 5000: continue
    tb = np.clip(theta[mg_fit].astype(int), 0, 179); v = logY[mg_fit]
    curve = np.full(180, np.nan)
    for b in range(180):
        s = v[tb == b]
        if len(s) > MINBIN: curve[b] = np.percentile(s, 88)
    ok = np.isfinite(curve); xs = np.arange(180)
    if ok.sum() < 20: continue
    curve = np.interp(xs, xs[ok], curve[ok])
    curve = ndi.gaussian_filter1d(curve, 2.0, mode='nearest')
    print('group', g, 'shading curve (every 15deg):', curve[::15].round(2))
    sel = grp == g
    flat[sel] = logY[sel] - np.interp(theta[sel], xs + 0.5, curve).astype(np.float32)
t0 = time.time()
R, E = retinex(flat, mask, T=T)
print('retinex %.1fs' % (time.time() - t0))
# --- local rank classification in rotated frame
def rot(a, order=1): return rotate(a.astype(np.float32), ANG, resize=True, order=order, preserve_range=True)
Rr = rot(np.nan_to_num(R)); mr = rot(mask) > 0.999; gr = np.rint(rot(grp, 0)).astype(np.int8)
Hr, Wr = Rr.shape
lo_v, bw, nb = -2.5, 0.01, 500
LO = np.zeros((Hr, Wr), np.float32); HI = np.zeros((Hr, Wr), np.float32)
sy, sx = 12, 30
cy = np.arange(sy // 2, Hr, sy); cx = np.arange(sx // 2, Wr, sx)
for g, (hy, hx) in {1: (70, 230), 2: (70, 170), 3: (150, 150), 4: (60, 150), 5: (160, 200)}.items():
    mg = mr & (gr == g)
    if mg.sum() < 500: continue
    Rq = np.where(mg, np.floor((Rr - lo_v) / bw), -1).astype(np.int32)
    hist = local_hists(Rq, mg, cy, cx, hy, hx, nb)
    n = hist.sum(2); cs = np.cumsum(hist, 2)
    pct = lambda p: lo_v + ((cs >= (p * n)[..., None]).argmax(2) + 0.5) * bw
    up = lambda a: resize(a.astype(np.float32), (len(cy) * sy, len(cx) * sx), order=1, preserve_range=True)
    lo_u = np.zeros((Hr + sy, Wr + sx), np.float32); hi_u = lo_u.copy()
    a = up(pct(0.05)); lo_u[:a.shape[0], :a.shape[1]] = a
    a = up(pct(0.95)); hi_u[:a.shape[0], :a.shape[1]] = a
    sel = gr == g
    LO[sel] = lo_u[:Hr, :Wr][sel]; HI[sel] = hi_u[:Hr, :Wr][sel]
rng = HI - LO
t = (Rr - LO) / np.maximum(rng, 0.05)
C = np.where(t < 0.27, 0, np.where(t > 0.73, 2, 1)).astype(np.int8)
Rf = np.where(mr, Rr, 0); a = np.array([-0.27, 0.0, 0.25])
for it in range(12):
    b = np.zeros_like(Rf); resid = Rf - a[C]
    for g in (1, 2, 3, 4, 5):
        mg = mr & (gr == g)
        if mg.sum() < 100: continue
        bg = nconv(resid, mg, 28); b[gr == g] = bg[gr == g]
    Cn = np.abs((Rf - b)[..., None] - a[None, None, :]).argmin(2).astype(np.int8)
    changed = (Cn != C)[mr].mean(); C = Cn
    vals = [np.median((Rf - b)[mr & (C == k)]) for k in range(3)]
    a = 0.5 * a + 0.5 * (np.array(vals) - vals[1])
    if changed < 0.001: break
print('iters', it, 'a', a.round(3), 'frac', [round(float((C[mr] == k).mean()), 3) for k in range(3)])
def unrot(aimg):
    u = rotate(aimg.astype(np.float32), -ANG, resize=True, order=0, preserve_range=True)
    oy = (u.shape[0] - H) // 2; ox = (u.shape[1] - W) // 2
    return u[oy:oy + H, ox:ox + W]
Cb = np.rint(unrot(C)).astype(np.int8); mask2 = mask & (unrot(mr) > 0.5)
np.savez_compressed(out + '_classes.npz', C=Cb, mask=mask2, a=a, y0=Y0, y1=Y1)
pal = np.array([[70, 70, 78], [140, 140, 148], [225, 225, 230]], np.uint8)
vis = pal[Cb]; vis[~mask2] = (90, 0, 90)
Image.fromarray(vis).save(out + '_C.png')
im = rgb.copy()
e = ((Cb != np.roll(Cb, 1, 0)) | (Cb != np.roll(Cb, 1, 1))) & mask2 & np.roll(mask2, 1, 0) & np.roll(mask2, 1, 1)
im[e] = (255, 0, 0)
Image.fromarray(im).save(out + '_edges.jpg', quality=90)
