import numpy as np
from scipy import ndimage as ndi
PAL = np.array([[143, 141, 144], [170, 169, 169], [203, 202, 198]], np.float32)   # dark, mid, light (sRGB albedo)
GREEN = np.array([56, 192, 156], np.float32)
REGCOL = np.array([100, 101, 108], np.float32)
def smooth_noise(shape, sx, sy, rng, wrap_y=False):
    n = rng.standard_normal(shape).astype(np.float32)
    mode = ['wrap' if wrap_y else 'reflect', 'reflect']
    n = ndi.gaussian_filter(n, [sy, sx], mode=mode)
    return (n - n.mean()) / n.std()
def camo_fields(shape, ppm_x, ppm_y, seed, wrap_y=False, scale=1.0):
    """two blob fields (light, dark), unit std; features elongated along x (aircraft axis)"""
    rng = np.random.default_rng(seed)
    H, W = shape
    out = []
    for k in range(2):
        base = smooth_noise(shape, 0.40 * scale * ppm_x, 0.21 * scale * ppm_y, rng, wrap_y)
        det = smooth_noise(shape, 0.16 * scale * ppm_x, 0.10 * scale * ppm_y, rng, wrap_y)
        f = base + 0.32 * det
        # domain warp for lobes
        wx = smooth_noise(shape, 0.30 * scale * ppm_x, 0.30 * scale * ppm_y, rng, wrap_y) * 0.22 * scale * ppm_x
        wy = smooth_noise(shape, 0.30 * scale * ppm_x, 0.30 * scale * ppm_y, rng, wrap_y) * 0.14 * scale * ppm_y
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        f = ndi.map_coordinates(f, [yy + wy, xx + wx], order=1, mode='wrap' if wrap_y else 'reflect')
        out.append((f - f.mean()) / f.std())
    return out
def classify(fl, fd, frac_light=0.40, frac_dark=0.32, known=None, labels=None, lam_px=30.0, seed=0, wrap_y=False):
    """returns label map (0 dark,1 mid,2 light). If known mask+labels given, known blobs are extended organically
    (warped nearest-label lookup, spatially varying reach) and fade into the procedural pattern."""
    tl = np.quantile(fl, 1 - frac_light)
    td = np.quantile(fd[fl <= tl], 1 - frac_dark / (1 - frac_light))
    gl, gd = fl, fd
    if known is not None and known.any():
        H, W = fl.shape
        rng = np.random.default_rng(seed + 991)
        d, (iy, ix) = ndi.distance_transform_edt(~known, return_indices=True)
        dx = smooth_noise((H, W), 22, 22, rng, wrap_y) * 16; dy = smooth_noise((H, W), 22, 22, rng, wrap_y) * 16
        yy, xx = np.mgrid[0:H, 0:W]
        fade = np.clip(d / 20.0, 0, 1)                      # no warp right at the border
        py = np.clip(np.rint(yy + dy * fade).astype(np.int64), 0, H - 1) if not wrap_y else np.rint(yy + dy * fade).astype(np.int64) % H
        px = np.clip(np.rint(xx + dx * fade).astype(np.int64), 0, W - 1)
        nn = labels[iy[py, px], ix[py, px]]
        lam = lam_px * (0.55 + 0.9 * (0.5 + 0.5 * np.tanh(smooth_noise((H, W), 40, 40, rng, wrap_y))))
        w = np.exp(-d / lam).astype(np.float32)
        Tl = np.where(nn == 2, tl + 2.5, tl - 2.5); Td = np.where(nn == 0, td + 2.5, td - 2.5)
        gl = (1 - w) * fl + w * Tl; gd = (1 - w) * fd + w * Td
    lab = np.where(gl > tl, 2, np.where(gd > td, 0, 1)).astype(np.uint8)
    if known is not None: lab[known] = labels[known]
    return lab
def majority(lab, sigma=2.0, wrap_y=False):
    mode = ['wrap' if wrap_y else 'nearest', 'nearest']
    ind = np.stack([ndi.gaussian_filter((lab == k).astype(np.float32), sigma, mode=mode) for k in range(3)], -1)
    return ind.argmax(2).astype(np.uint8)
def clean_known(lab, known, open_r=3, min_px=400):
    """drop thin structures and small specks from known labels (set unknown)"""
    yy, xx = np.ogrid[-open_r:open_r + 1, -open_r:open_r + 1]; disk = (yy * yy + xx * xx) <= open_r * open_r
    keep = np.zeros_like(known)
    for k in range(3):
        m = known & (lab == k)
        # opening relative to the known domain: treat unknown as "same class" to avoid eroding at domain borders
        mo = ndi.binary_opening(m | ~known, structure=disk) & m
        l, n = ndi.label(mo)
        if n:
            sizes = ndi.sum(mo, l, np.arange(1, n + 1))
            small = np.isin(l, 1 + np.where(sizes < min_px)[0])
            mo &= ~small
        keep |= mo
    return keep
def indicators(lab, sigma=1.3, wrap_y=False):
    mode = ['wrap' if wrap_y else 'nearest', 'nearest']
    return np.stack([ndi.gaussian_filter((lab == k).astype(np.float32), sigma, mode=mode) for k in range(3)], -1)
