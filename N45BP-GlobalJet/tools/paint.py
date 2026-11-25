"""Paint all texture tiles (paint layer only, 4096^2 each) from the camo label charts + decals."""
import sys, os, numpy as np, json, time
sys.path.insert(0, 'scripts')
from raster import *
from charts import *
from camo import PAL, indicators
from PIL import Image
from scipy import ndimage as ndi
GREEN = np.array([56, 190, 162], np.float32)
REGCOL = np.array([100, 101, 108], np.float32)
WHITE = np.array([236, 237, 238], np.float32)
RES = 4096
os.makedirs('work/paint', exist_ok=True)
objs, d = load_model('work/model')
name = {o['i']: o['name'] for o in objs}; mat = {o['i']: o['mat'] for o in objs}
tile_of = {o['i']: int(np.floor(np.median(d[f"tuv{o['i']}"][:, :, 0]))) for o in objs}
STAB = {'Tail_042', 'Object031', 'Tail_040', 'Tail_043', 'Tail_Skin_002', 'Object26450090', 'Object26450204', 'Object048', 'Object26450203'}
def ind_of(f, wrap): return indicators(np.load(f), 1.3, wrap_y=wrap)
I = dict(fus=ind_of('work/charts/fus_labels.npy', True), engL=ind_of('work/charts/engL_labels.npy', True), engR=ind_of('work/charts/engR_labels.npy', True),
         finL=ind_of('work/charts/finL_labels.npy', False), finR=ind_of('work/charts/finR_labels.npy', False), top=ind_of('work/charts/top_labels.npy', False))
def camo_col(ind, cx, cy, wrap):
    H, W = ind.shape[:2]
    cx = np.clip(cx - 0.5, 0, W - 1); cy = cy - 0.5
    if not wrap: cy = np.clip(cy, 0, H - 1)
    w = np.stack([ndi.map_coordinates(ind[..., k], [cy, cx], order=1, mode='grid-wrap' if wrap else 'nearest') for k in range(3)], 1)
    order = np.argsort(w, 1); k1 = order[:, 2]; k2 = order[:, 1]
    r = np.arange(len(w)); e = w[r, k1] - w[r, k2]
    a = np.clip(0.5 + e / 0.20, 0, 1)[:, None]
    return a * PAL[k1] + (1 - a) * PAL[k2]
def top_col(p): return camo_col(I['top'], (p[:, 0] + 14.6) * PPM, (p[:, 1] + 1.6) * PPM, False)
def decal(img, u, v):
    """img (h,w[,c]) float; u,v in 0..1 -> sampled values, and inside mask"""
    h, w = img.shape[:2]
    inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
    x = np.clip(u * w - 0.5, 0, w - 1); y = np.clip(v * h - 0.5, 0, h - 1)
    if img.ndim == 2: return ndi.map_coordinates(img, [y, x], order=1, mode='nearest') * inside, inside
    return np.stack([ndi.map_coordinates(img[..., k], [y, x], order=1, mode='nearest') for k in range(img.shape[2])], 1), inside
DK = ndi.distance_transform_edt(~np.load('work/charts/fus_known.npz')['known']).astype(np.float32)
REG = np.asarray(Image.open('work/decals/reg_mask.png')).astype(np.float32) / 255; RB = np.load('work/decals/reg_bbox.npy')
FLAG = np.asarray(Image.open('work/decals/flag.png').convert('RGB')).astype(np.float32); FB = np.load('work/decals/flag_bbox.npy')
EMB = np.asarray(Image.open('work/decals/emblem_mask.png')).astype(np.float32) / 255
# wing upper-surface height maps (top view, 100 px/m)
ZT = {}
for side, sx in (('L', 1.0), ('R', -1.0)):
    P = []
    for o in objs:
        if o['mat'] != 'GLEX_Wing_' + side: continue
        i = o['i']; p = d[f'v{i}'][d[f'tv{i}']].astype(np.float64)
        P.append(np.stack([(sx * p[..., 0] - 1.0) * 100, (p[..., 1] + 1.5) * 100, -p[..., 2]], -1))
    idx, bc, zb = rasterize(np.concatenate(P), 1340, 1200)
    ZT[side] = np.where(np.isfinite(zb), -zb, -99).astype(np.float32)
def finish_tile(tname, cover, col_cov):
    img = np.zeros((RES, RES, 3), np.float32); img[cover] = col_cov
    dist, (iy, ix) = ndi.distance_transform_edt(~cover, return_indices=True)
    img = img[iy, ix]
    Image.fromarray(np.clip(np.rint(img), 0, 255).astype(np.uint8)).save(f'work/paint/{tname}.png', compress_level=3)
only = sys.argv[1:]
for k in range(7):
    tname = f'EXT_{1001 + k}'
    if only and tname not in only: continue
    t0 = time.time(); b = np.load(f'work/bake/{tname}.npz'); cover = b['cover'] > 0
    p = b['pos'][cover].astype(np.float64); n = b['nrm'][cover].astype(np.float32) / 127; ob = b['obj'][cover]
    ids = np.unique(ob); nm = np.array([name[i] if i >= 0 else '' for i in range(max(name) + 1)])
    isstab = np.isin(ob, [i for i in ids if name[i] in STAB])
    isfin = np.isin(ob, [i for i in ids if tile_of[i] == 4 and name[i] not in STAB])
    isstar = np.isin(ob, [i for i in ids if name[i] == 'x0_Starlink_Antenna'])
    isfus = ~(isstab | isfin | isstar)
    col = np.zeros((len(p), 3), np.float32)
    if isfus.any():
        q = p[isfus]; cx, cy, r = fus_coords(q)
        c = camo_col(I['fus'], cx, cy, True)
        th = cy / PPD - 180.0
        # nose cone / tail cone: the cylindrical chart pinches towards the tip, so areas without photo data use a planar (end-on) pattern there
        dk = DK[np.clip(np.rint(cy - 0.5).astype(int) % DK.shape[0], 0, DK.shape[0] - 1), np.clip(np.rint(cx - 0.5).astype(int), 0, DK.shape[1] - 1)]
        wob = 0.20 * np.sin(np.radians(3 * th) + 1.0) + 0.10 * np.sin(np.radians(7 * th))
        for sel, zoff in (((q[:, 1] < -10.35 + wob) & (dk > 25), 2.0), ((q[:, 1] > 13.9 + wob) & (dk > 25), 6.0)):
            if sel.any(): c[sel] = camo_col(I['top'], (q[sel, 0] + 14.6) * PPM, (q[sel, 2] + 1.6 + zoff) * PPM, False)
        ant = (q[:, 1] > -7.3) & (q[:, 1] < 7.3) & (r > 1.385) & (np.abs(th) < 14)
        c[ant] = WHITE
        col[isfus] = c
    if isfin.any():
        q = p[isfin]; nn = n[isfin]; cx, cy = fin_coords(q)
        left = nn[:, 0] >= 0
        c = np.where(left[:, None], camo_col(I['finL'], cx, cy, False), camo_col(I['finR'], cx, cy, False))
        flat = np.abs(nn[:, 0]) > 0.5
        # registration (reads correctly on both sides)
        u = np.where(left, (q[:, 1] - RB[0]) / (RB[1] - RB[0]), (RB[1] - q[:, 1]) / (RB[1] - RB[0])); v = (RB[3] - q[:, 2]) / (RB[3] - RB[2])
        a, ins = decal(REG, u, v); a = (a * flat)[:, None]; c = c * (1 - a) + REGCOL * a
        # flag (union forward on both sides)
        u = (q[:, 1] - FB[0]) / (FB[1] - FB[0]); v = (FB[3] - q[:, 2]) / (FB[3] - FB[2])
        fc, ins = decal(FLAG, u, v); m = ins & flat; c[m] = fc[m]
        col[isfin] = c
    if isstab.any():
        q = p[isstab]; nn = n[isstab]
        c = np.where((nn[:, 2] > 0.0)[:, None], top_col(q), GREEN)
        root = np.abs(q[:, 0]) < 0.46                      # bullet / root fairing stays camo all round
        if root.any():
            cx, cy = fin_coords(q[root]); lf = q[root][:, 0] >= 0
            c[root] = np.where(lf[:, None], camo_col(I['finL'], cx, cy, False), camo_col(I['finR'], cx, cy, False))
        col[isstab] = c
    col[isstar] = WHITE
    # small disc parts whose kit-model placement is unreliable: keep them a plain mid tone
    col[np.isin(ob, [i for i in ids if name[i] in ('Tail_004', 'Tail_005', 'Tail_025')])] = PAL[1]
    finish_tile(tname, cover, col); print(tname, 'done %.1fs' % (time.time() - t0), 'fus %d fin %d stab %d' % (isfus.sum(), isfin.sum(), isstab.sum()), flush=True)
for side in 'LR':
    tname = 'ENG_' + side
    if not only or tname in only:
        t0 = time.time(); b = np.load(f'work/bake/{tname}.npz'); cover = b['cover'] > 0
        p = b['pos'][cover].astype(np.float64)
        cx, cy, r = eng_coords(p, side)
        finish_tile(tname, cover, camo_col(I['eng' + side], cx, cy, True)); print(tname, 'done %.1fs' % (time.time() - t0), flush=True)
    sx = 1.0 if side == 'L' else -1.0
    for k in range(2):
        tname = f'WING_{side}_{1001 + k}'
        if only and tname not in only: continue
        t0 = time.time(); b = np.load(f'work/bake/{tname}.npz'); cover = b['cover'] > 0
        p = b['pos'][cover].astype(np.float64); n = b['nrm'][cover].astype(np.float32) / 127
        zx = np.clip(np.rint((sx * p[:, 0] - 1.0) * 100 - 0.5).astype(int), 0, 1339); zy = np.clip(np.rint((p[:, 1] + 1.5) * 100 - 0.5).astype(int), 0, 1199)
        zt = ZT[side][zy, zx]
        s = n[:, 2] - 0.5 * sx * n[:, 0]
        top = (zt - p[:, 2] < 0.035) & (s > 0.05)
        col = np.where(top[:, None], top_col(p), GREEN).astype(np.float32)
        # winglet emblem on the inner face
        wl = top & (sx * p[:, 0] > 13.75) & (p[:, 2] > 0.35)
        if wl.any():
            zc = 0.15 + 0.425 * (1.548 - 0.15)
            band = wl & (np.abs(p[:, 2] - zc) < 0.04)
            if band.any():
                yc = (p[band, 1].min() + p[band, 1].max()) / 2 + 0.04
                ew, eh = 0.42, 0.42 * EMB.shape[0] / EMB.shape[1] * 0.53
                slant = 1.0 / np.sqrt(max(1e-6, 1 - 0.0))   # height measured along z (winglet is near-vertical)
                u = 0.5 + sx * (-(p[:, 1] - yc)) / ew        # left winglet: image-right = forward (-y)
                v = 0.5 - (p[:, 2] - zc) / eh
                a, ins = decal(EMB, u, v); a = (a * wl)[:, None]
                col = col * (1 - a) + GREEN * a
                print('  emblem', side, 'centre y %.2f z %.2f size %.2f x %.2f m' % (yc, zc, ew, eh))
        finish_tile(tname, cover, col); print(tname, 'done %.1fs' % (time.time() - t0), 'top frac %.2f' % top.mean(), flush=True)
