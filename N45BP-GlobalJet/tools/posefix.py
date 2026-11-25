# The kit model has the right nose avionics-bay door (Fuselage_230) posed open. Find the rigid transform that closes it
# by matching it (through UV correspondence) to the mirrored left door (Fuselage_229).
import sys, numpy as np
sys.path.insert(0, 'scripts')
from raster import *
from scipy.spatial import cKDTree
objs, d = load_model('work/model'); by = {o['name']: o for o in objs}
def corners(n):
    i = by[n]['i']; return d[f'v{i}'][d[f'tv{i}']].reshape(-1, 3).astype(np.float64), d[f'tuv{i}'].reshape(-1, 2).astype(np.float64)
pA, uA = corners('Fuselage_229'); pB, uB = corners('Fuselage_230')
best = None
for flip in (False, True):
    ua = uA - uA.min(0); ub = uB - uB.min(0)
    if flip: ub = ub.copy(); ub[:, 0] = ub[:, 0].max() - ub[:, 0]
    dist, j = cKDTree(ua).query(ub)
    ok = dist < 2e-4
    src = pB[ok]; tgt = pA[j[ok]] * np.array([-1, 1, 1])
    cs, ct = src.mean(0), tgt.mean(0)
    U, S, Vt = np.linalg.svd((src - cs).T @ (tgt - ct))
    R = Vt.T @ U.T                                     # orthogonal (reflection allowed)
    t = ct - R @ cs
    res = np.linalg.norm(src @ R.T + t - tgt, axis=1)
    print('flip', flip, 'matched %.0f%%' % (100 * ok.mean()), 'det %.2f' % np.linalg.det(R), 'residual mean %.4f max %.4f' % (res.mean(), res.max()))
    if best is None or res.mean() < best[0]: best = (res.mean(), R, t)
np.savez('work/posefix.npz', R=best[1], t=best[2])
q = pB @ best[1].T + best[2]; print('closed bbox', q.min(0).round(2), q.max(0).round(2), ' (left door bbox', pA.min(0).round(2), pA.max(0).round(2), ')')
