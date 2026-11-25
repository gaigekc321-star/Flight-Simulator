import numpy as np, json
from scipy.spatial.transform import Rotation as Rot
YP0, YP1 = -5.55, -4.77      # fuselage plug present on the 6000 but not on the 5000 (model coords); YP1-YP0 ~= dL
def to5000(P, dL):
    """Map Global 6000 model coords to the (shorter) Global 5000 airframe: everything forward of the plug is shifted aft by dL."""
    Q = np.array(P, float, copy=True)
    y = Q[..., 1]
    Q[..., 1] = np.where(y < YP1, y + dL, y)
    return Q
def in_plug(P):
    y = np.asarray(P)[..., 1]
    return (y > YP0) & (y < YP1)
def project(params, X, persp=True, side='L'):
    """X (...,3) in 5000-airframe coords -> (u, v, depth)"""
    s, rx, ry, rz, tu, tv, dL, invd = params
    R = Rot.from_euler('xyz', [rx, ry, rz]).as_matrix()
    if side == 'L': B = np.array([[0, 1, 0], [0, 0, -1], [-1, 0, 0]], float)
    else:           B = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], float)
    C = (X.reshape(-1, 3) @ R.T) @ B.T
    w = 1.0 / (1.0 + invd * C[:, 2]) if persp else np.ones(len(C))
    out = np.stack([s * C[:, 0] * w + tu, s * C[:, 1] * w + tv, C[:, 2]], 1)
    return out.reshape(X.shape[:-1] + (3,))
