import sys, numpy as np, json, time
sys.path.insert(0, 'scripts')
from raster import *
from scipy import ndimage as ndi
objs, d = load_model('work/model')
by = {o['name']: o for o in objs}
fix = np.load('work/stabfix.npz'); R, t = fix['R'], fix['t']
BAD = {'Object048', 'Object26450203', 'Object26450090', 'Object26450204'}   # misplaced LE strips / tiny parts (non-paintable)
RES = 4096
# tile definitions: name -> (material, u tile index)
TILES = {}
for k in range(7): TILES[f'EXT_{1001+k}'] = ('GLEX_EXT', k)
TILES['ENG_L'] = ('GLEX_ENG_L', 0); TILES['ENG_R'] = ('GLEX_ENG_R', 0)
for s in 'LR':
    for k in range(2): TILES[f'WING_{s}_{1001+k}'] = (f'GLEX_Wing_{s}', k)
# surface area per object for draw ordering (largest last)
area = {}
for o in objs:
    i = o['i']; p = d[f'v{i}'][d[f'tv{i}']].astype(np.float64)
    area[i] = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1).sum()
only = sys.argv[1:] 
for name, (mat, k) in TILES.items():
    if only and name not in only: continue
    t0 = time.time()
    P = []; POS = []; NRM = []; OBJ = []; VAL = []
    for o in sorted([o for o in objs if o['mat'] == mat], key=lambda o: area[o['i']]):
        i = o['i']
        uv = d[f'tuv{i}'].astype(np.float64)
        sel = np.floor(uv[:, :, 0].mean(1) + 1e-9).astype(int) == k
        if not sel.any(): continue
        pos = d[f'v{i}'][d[f'tv{i}']].astype(np.float64)[sel]
        nrm = d[f'tn{i}'].astype(np.float64)[sel]
        if o['name'] == 'Object031':
            pos = pos @ R.T + t; nrm = nrm @ R.T
        if o['name'] == 'Fuselage_230':
            pf = np.load('work/posefix.npz'); pos = pos @ pf['R'].T + pf['t']; nrm = nrm @ pf['R'].T
        if o['det'] < 0: nrm = nrm  # normals already world-space
        uv = uv[sel]
        scr = np.stack([(uv[..., 0] - k) * RES, (1.0 - uv[..., 1]) * RES, np.zeros(uv.shape[:2])], -1)
        P.append(scr); POS.append(pos); NRM.append(nrm); OBJ.append(np.full(len(pos), i, np.int32))
        VAL.append(np.full(len(pos), o['name'] not in BAD))
    P = np.concatenate(P); POS = np.concatenate(POS); NRM = np.concatenate(NRM); OBJ = np.concatenate(OBJ); VAL = np.concatenate(VAL)
    idx, bc, zb = rasterize(P, RES, RES, False)
    m = idx >= 0
    pos = interp(POS, idx, bc); nrm = interp(NRM, idx, bc)
    obj = np.full((RES, RES), -1, np.int16); obj[m] = OBJ[idx[m]]
    valid = np.zeros((RES, RES), bool); valid[m] = VAL[idx[m]]
    # dilate: nearest covered texel within 24 px
    dist, (iy, ix) = ndi.distance_transform_edt(~m, return_indices=True)
    grow = (~m) & (dist <= 24)
    pos[grow] = pos[iy[grow], ix[grow]]; nrm[grow] = nrm[iy[grow], ix[grow]]; obj[grow] = obj[iy[grow], ix[grow]]; valid[grow] = valid[iy[grow], ix[grow]]
    cover = m.astype(np.uint8); cover[grow] = 2
    nl = np.linalg.norm(nrm, axis=2, keepdims=True); nrm = nrm / np.maximum(nl, 1e-6)
    np.savez(f'work/bake/{name}.npz', pos=pos.astype(np.float32), nrm=(nrm * 127).astype(np.int8), obj=obj, cover=cover, valid=valid)
    print(name, 'tris', len(P), 'covered %.1f%%' % (100 * m.mean()), 'time %.1fs' % (time.time() - t0), flush=True)
