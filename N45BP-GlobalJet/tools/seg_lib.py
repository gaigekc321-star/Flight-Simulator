import numpy as np, json
from scipy import ndimage as ndi, sparse
from scipy.sparse import linalg as sla
from skimage import color
def srgb2lin(c):
    c = c.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def luminance(rgb):
    l = srgb2lin(rgb)
    return 0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]
def retinex(logY, mask, T=0.022, sigma=1.2, dil=2, lam=1e-5):
    """Gradient-thresholded Poisson reconstruction of log reflectance inside mask."""
    import pyamg
    H, W = logY.shape
    sm = ndi.gaussian_filter(logY, sigma)
    gx = np.zeros_like(sm); gy = np.zeros_like(sm)
    gx[:, :-1] = sm[:, 1:] - sm[:, :-1]
    gy[:-1, :] = sm[1:, :] - sm[:-1, :]
    mag = np.hypot(ndi.sobel(sm, 1) / 8, ndi.sobel(sm, 0) / 8)
    E = ndi.binary_dilation(mag > T, iterations=dil)
    # keep gradients only at edge zones
    ex = E.copy(); ex[:, :-1] &= E[:, 1:]
    ey = E.copy(); ey[:-1, :] &= E[1:, :]
    gx = np.where(E | np.roll(E, -1, 1), gx, 0); gy = np.where(E | np.roll(E, -1, 0), gy, 0)
    idx = -np.ones((H, W), np.int64); n = int(mask.sum()); idx[mask] = np.arange(n)
    # horizontal pairs
    mh = mask[:, :-1] & mask[:, 1:]; mv = mask[:-1, :] & mask[1:, :]
    p = idx[:, :-1][mh]; q = idx[:, 1:][mh]; gh = gx[:, :-1][mh]
    p2 = idx[:-1, :][mv]; q2 = idx[1:, :][mv]; gv = gy[:-1, :][mv]
    P = np.concatenate([p, p2]); Q = np.concatenate([q, q2]); G = np.concatenate([gh, gv]).astype(np.float64)
    m = len(P)
    A = sparse.coo_matrix((np.concatenate([-np.ones(m), np.ones(m)]), (np.concatenate([np.arange(m)] * 2), np.concatenate([P, Q]))), shape=(m, n)).tocsr()
    L = (A.T @ A + lam * sparse.identity(n)).tocsr()
    rhs = A.T @ G
    ml = pyamg.smoothed_aggregation_solver(L, max_coarse=500)
    x = ml.solve(rhs, tol=1e-7, maxiter=60, accel='cg')
    R = np.full((H, W), np.nan, np.float32); R[mask] = x
    return R, E
def nconv(v, m, sigma):
    """normalized convolution of v within mask m"""
    num = ndi.gaussian_filter(np.where(m, v, 0).astype(np.float32), sigma)
    den = ndi.gaussian_filter(m.astype(np.float32), sigma)
    return num / np.maximum(den, 1e-6)
