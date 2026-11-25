import numpy as np
from scipy import ndimage as ndi
from numba import njit
@njit(cache=True)
def local_hists(Rq, mask, cy, cx, hy, hx, nb):
    out = np.zeros((len(cy), len(cx), nb), np.float32)
    H, W = Rq.shape
    for i in range(len(cy)):
        y0 = max(0, cy[i] - hy); y1 = min(H, cy[i] + hy + 1)
        for j in range(len(cx)):
            x0 = max(0, cx[j] - hx); x1 = min(W, cx[j] + hx + 1)
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if mask[y, x]:
                        q = Rq[y, x]
                        if q >= 0 and q < nb:
                            out[i, j, q] += 1
    return out
def comb_align(R, mask, d1, d2, hy=40, hx=250, sy=16, sx=40, lo=-1.6, hi=1.4, bw=0.01, ksig=0.045):
    """Return bias (level of the MID tone) estimate + confidence on a coarse grid, upsampled."""
    H, W = R.shape
    nb = int((hi - lo) / bw)
    Rq = np.where(mask, np.floor((np.nan_to_num(R) - lo) / bw), -1).astype(np.int32)
    cy = np.arange(sy // 2, H, sy); cx = np.arange(sx // 2, W, sx)
    hist = local_hists(Rq, mask, cy, cx, hy, hx, nb)
    n = hist.sum(2)
    # comb kernel (positions relative to mid tone)
    r = (np.arange(nb) - nb // 2) * bw
    comb = sum(np.exp(-0.5 * ((r - a) / ksig) ** 2) for a in (-d1, 0.0, d2)).astype(np.float32)
    # score(b) = sum_r hist(r) comb(r - b): correlation
    from numpy.fft import rfft, irfft
    F = rfft(hist, n=2 * nb, axis=2); Fc = rfft(comb[::-1], n=2 * nb)
    corr = irfft(F * Fc[None, None, :], n=2 * nb, axis=2)   # index k <-> shift
    # shift mapping: corr[k] = sum_r hist[r] * comb_rev[k - r] = sum_r hist[r]*comb[nb-1-k+r] -> comb index = r - (k - (nb-1)) ; b_bins = k-(nb-1)+... 
    k = np.arange(2 * nb)
    b_vals = lo + (k - (nb - 1) + nb // 2) * bw + bw / 2
    valid = (b_vals > lo + 0.3) & (b_vals < hi - 0.3)
    corr = np.where(valid[None, None, :], corr, 0)
    best = corr.argmax(2)
    bs = b_vals[best]
    sc = np.take_along_axis(corr, best[..., None], 2)[..., 0]
    # alias scores at b - d1 and b + d2
    def at(bshift):
        kk = np.clip(best + int(round(bshift / bw)), 0, 2 * nb - 1)
        return np.take_along_axis(corr, kk[..., None], 2)[..., 0]
    alias = np.maximum(at(-d1), np.maximum(at(d2), np.maximum(at(-d2), at(d1))))
    conf = np.where(n > 200, (sc - alias) / np.maximum(sc, 1e-6), 0) * np.minimum(n / 3000.0, 1.0)
    return cy, cx, bs.astype(np.float32), conf.astype(np.float32), sc / np.maximum(n, 1), n
