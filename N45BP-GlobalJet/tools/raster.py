import numpy as np, json
from numba import njit, prange

@njit(cache=True)
def rasterize(P, W, H, use_depth=True):
    """P: (T,3,3) float64 screen coords (x,y,depth; smaller depth = nearer).
    Returns tri index map (H,W) int32 (-1 empty), barycentric (H,W,3) float32."""
    idx = np.full((H, W), -1, np.int32)
    zb = np.full((H, W), np.inf, np.float64)
    bc = np.zeros((H, W, 3), np.float32)
    T = P.shape[0]
    for t in range(T):
        x0, y0, z0 = P[t, 0, 0], P[t, 0, 1], P[t, 0, 2]
        x1, y1, z1 = P[t, 1, 0], P[t, 1, 1], P[t, 1, 2]
        x2, y2, z2 = P[t, 2, 0], P[t, 2, 1], P[t, 2, 2]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12:
            continue
        minx = int(max(0, np.floor(min(x0, x1, x2))))
        maxx = int(min(W - 1, np.ceil(max(x0, x1, x2))))
        miny = int(max(0, np.floor(min(y0, y1, y2))))
        maxy = int(min(H - 1, np.ceil(max(y0, y1, y2))))
        if maxx < minx or maxy < miny:
            continue
        inv = 1.0 / den
        for py in range(miny, maxy + 1):
            cy = py + 0.5
            for px in range(minx, maxx + 1):
                cx = px + 0.5
                a = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) * inv
                b = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) * inv
                c = 1.0 - a - b
                e = -1e-4
                if a >= e and b >= e and c >= e:
                    z = a * z0 + b * z1 + c * z2
                    if (not use_depth) or z < zb[py, px]:
                        zb[py, px] = z
                        idx[py, px] = t
                        bc[py, px, 0] = a
                        bc[py, px, 1] = b
                        bc[py, px, 2] = c
    return idx, bc, zb

def load_model(prefix):
    objs = json.load(open(prefix + '.json'))
    d = np.load(prefix + '.npz')
    return objs, d

def gather(objs, d, select=None):
    """Concatenate triangles of selected objects. Returns dict with
    pos (T,3,3), uv (T,3,2), nrm (T,3,3), obj (T,) object index."""
    P = []; U = []; N = []; O = []
    for o in objs:
        if select is not None and not select(o):
            continue
        i = o['i']
        v = d[f'v{i}']; tv = d[f'tv{i}']
        P.append(v[tv]); U.append(d[f'tuv{i}']); N.append(d[f'tn{i}']); O.append(np.full(len(tv), i, np.int32))
    return dict(pos=np.concatenate(P).astype(np.float64), uv=np.concatenate(U).astype(np.float64),
                nrm=np.concatenate(N).astype(np.float64), obj=np.concatenate(O))

def interp(attr, idx, bc):
    """attr (T,3,C) -> (H,W,C) using idx/bc; empty pixels are 0."""
    m = idx >= 0
    out = np.zeros(idx.shape + (attr.shape[2],), np.float32)
    a = attr[idx[m]]
    out[m] = (a * bc[m][:, :, None]).sum(1)
    return out
