"""Chart definitions + baking of chart position maps (surface point per chart pixel)."""
import sys, numpy as np, json
sys.path.insert(0, 'scripts')
from raster import *
PPM = 160.0           # px per metre along the aircraft
PPD = 4.0             # px per degree around cylinders
FUS_Y0, FUS_Y1 = -11.8, 15.0
ENG_Y0, ENG_Y1 = 7.0, 12.4
ENG_XC, ENG_ZC = 2.282, 1.471
FIN_Y0, FIN_Y1, FIN_Z0, FIN_Z1 = 8.2, 17.2, 1.5, 6.1
_zc = None
def fus_zc(y):
    """fuselage centreline height as function of station"""
    global _zc
    if _zc is None: _zc = np.load('work/charts/fus_zc.npy')
    return np.interp(y, _zc[0], _zc[1])
def fus_coords(p):
    y = p[..., 1]; zc = fus_zc(y)
    th = np.degrees(np.arctan2(p[..., 0], p[..., 2] - zc))
    r = np.hypot(p[..., 0], p[..., 2] - zc)
    return (y - FUS_Y0) * PPM, (th + 180.0) * PPD, r
def eng_coords(p, side):
    s = 1.0 if side == 'L' else -1.0
    dx = s * p[..., 0] - ENG_XC; dz = p[..., 2] - ENG_ZC
    ph = np.degrees(np.arctan2(dx, dz))        # 0 top, +90 outboard, -90 inboard
    return (p[..., 1] - ENG_Y0) * PPM, (ph + 180.0) * PPD, np.hypot(dx, dz)
def fin_coords(p):
    return (p[..., 1] - FIN_Y0) * PPM, (FIN_Z1 - p[..., 2]) * PPM
FUS_W, FUS_H = int((FUS_Y1 - FUS_Y0) * PPM), int(360 * PPD)
ENG_W, ENG_H = int((ENG_Y1 - ENG_Y0) * PPM), int(360 * PPD)
FIN_W, FIN_H = int((FIN_Y1 - FIN_Y0) * PPM), int((FIN_Z1 - FIN_Z0) * PPM)
def sample(chart, cx, cy, wrap_y=False):
    """nearest lookup with clamping (and vertical wrap for cylinders)"""
    H, W = chart.shape[:2]
    ix = np.clip(np.rint(cx).astype(np.int64), 0, W - 1)
    iy = np.rint(cy).astype(np.int64)
    iy = iy % H if wrap_y else np.clip(iy, 0, H - 1)
    return chart[iy, ix]
if __name__ == '__main__':
    from model_side import gather_fixed, objs, d
    from scipy import ndimage as ndi
    area = {}
    for o in objs:
        i = o['i']; p = d[f'v{i}'][d[f'tv{i}']].astype(np.float64)
        area[i] = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1).sum()
    by = {o['name']: o for o in objs}
    # centreline table (station, z) - nose droop, constant cylinder, aft upsweep
    tab = np.array([[-11.8,0.26],[-11.66,0.26],[-11.0,0.36],[-10.4,0.49],[-10.0,0.56],[-9.5,0.68],[-9.0,0.80],[-8.5,0.89],[-8.0,0.94],[-7.5,0.955],[7.0,0.955],[8.5,1.10],[10.0,1.15],[12.5,1.17],[14.2,1.23],[15.0,1.25]])
    ys = np.linspace(-11.8, 15.0, 600); zc = ndi.gaussian_filter1d(np.interp(ys, tab[:,0], tab[:,1]), 6, mode='nearest')
    np.save('work/charts/fus_zc.npy', np.stack([ys, zc]))
    def tile_of(o):
        uv = d[f"tuv{o['i']}"]; return int(np.floor(np.median(uv[:, :, 0])))
    def bake(name, sel, coord_fn, W, H, wrap=False):
        P = []; POS = []; NRM = []
        fix = np.load('work/stabfix.npz')
        for o in objs:
            if not sel(o): continue
            i = o['i']; p = d[f'v{i}'][d[f'tv{i}']].astype(np.float64); n = d[f'tn{i}'].astype(np.float64)
            c = coord_fn(p)
            if len(c) == 3: cx, cy, r = c; dep = -r
            else: cx, cy = c; dep = None
            P.append((cx, cy, dep)); POS.append(p); NRM.append(n)
        cx = np.concatenate([a[0] for a in P]); cy = np.concatenate([a[1] for a in P])
        dep = np.concatenate([a[2] for a in P])
        POS = np.concatenate(POS); NRM = np.concatenate(NRM)
        if wrap:
            span = cy.max(1) - cy.min(1)
            wrapm = span > H / 2
            cyw = cy.copy(); cyw[wrapm] = np.where(cy[wrapm] < H / 2, cy[wrapm] + H, cy[wrapm])
            S1 = np.stack([cx, cyw, dep], -1); S2 = S1.copy(); S2[..., 1] -= H
            S = np.concatenate([S1, S2[wrapm]]); POS = np.concatenate([POS, POS[wrapm]]); NRM = np.concatenate([NRM, NRM[wrapm]])
        else:
            S = np.stack([cx, cy, dep], -1)
        idx, bc, zb = rasterize(S, W, H)
        pos = interp(POS, idx, bc); nrm = interp(NRM, idx, bc); m = idx >= 0
        dist, (iy, ix) = ndi.distance_transform_edt(~m, return_indices=True)
        g = (~m) & (dist < 6); pos[g] = pos[iy[g], ix[g]]; nrm[g] = nrm[iy[g], ix[g]]
        np.savez(f'work/charts/{name}.npz', pos=pos.astype(np.float32), nrm=nrm.astype(np.float32), cover=m | g)
        print(name, W, H, 'cover %.1f%%' % (100 * (m | g).mean()))
    fus_sel = lambda o: o['mat'] == 'GLEX_EXT' and tile_of(o) <= 3 and area[o['i']] > 0.2 and o['name'] not in ('Object022',)
    bake('fus', fus_sel, fus_coords, FUS_W, FUS_H, wrap=True)
    for side in 'LR':
        sel = lambda o, side=side: o['mat'] == 'GLEX_ENG_' + side and area[o['i']] > 0.3
        bake('eng' + side, sel, lambda p, side=side: eng_coords(p, side), ENG_W, ENG_H, wrap=True)
    fin_names = lambda o: o['mat'] == 'GLEX_EXT' and tile_of(o) == 4 and area[o['i']] > 0.2
    for side, s in (('L', 1.0), ('R', -1.0)):
        bake('fin' + side, fin_names, lambda p, s=s: (*fin_coords(p), s * p[..., 0]), FIN_W, FIN_H)
