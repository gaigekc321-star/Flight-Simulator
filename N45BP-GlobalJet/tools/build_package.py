#!/usr/bin/env python3
"""Build a Community-folder livery package from ../textures using the names in names.json.

Textures are written as BC7 DDS with mipmaps plus the .json flag file (the long-standing community livery
format). Needs: pip install numpy pillow etcpak
"""
import json, os, shutil, struct, sys, time
import numpy as np
from PIL import Image
import etcpak

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
cfg = json.load(open(os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else 'names.json')))
OUT = os.path.join(ROOT, 'community-package', cfg['package_folder'])
FILETIME = int((time.time() + 11644473600) * 10_000_000)

def srgb2lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lin2srgb(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.maximum(c, 0) ** (1 / 2.4) - 0.055)

def write_dds_bc7(png, dst):
    im = Image.open(png).convert('RGBA'); w, h = im.size
    a = np.asarray(im).astype(np.float32) / 255
    rgb = srgb2lin(a[..., :3]); alpha = a[..., 3:4]
    if alpha.min() < 1:                       # keep colour under transparent pixels sensible
        rgb = np.where(alpha > 0, rgb, rgb[alpha[..., 0] > 0].mean(0) if (alpha > 0).any() else rgb)
    mips = []
    while True:
        out = np.concatenate([lin2srgb(rgb), alpha], -1)
        u8 = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
        hh, ww = u8.shape[:2]; ph, pw = max(4, hh), max(4, ww)
        if (ph, pw) != (hh, ww): u8 = np.pad(u8, ((0, ph - hh), (0, pw - ww), (0, 0)), mode='edge')
        mips.append(etcpak.compress_bc7(np.ascontiguousarray(u8).tobytes(), pw, ph))
        if hh == 1 and ww == 1: break
        nh, nw = max(1, hh // 2), max(1, ww // 2)
        rgb = rgb[:nh * 2, :nw * 2].reshape(nh, 2, nw, 2, 3).mean((1, 3)) if hh > 1 and ww > 1 else rgb[:nh, :nw]
        alpha = alpha[:nh * 2, :nw * 2].reshape(nh, 2, nw, 2, 1).mean((1, 3)) if hh > 1 and ww > 1 else alpha[:nh, :nw]
    DDSD = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, DDSD, h, w, len(mips[0]), 0, len(mips))
    hdr += struct.pack('<II4sIIIII', 32, 0x4, b'DX10', 0, 0, 0, 0, 0)          # pixel format: FourCC DX10
    hdr += struct.pack('<IIIII', 0x1000 | 0x8 | 0x400000, 0, 0, 0, 0)          # caps (texture, complex, mipmap) + reserved
    hdr += struct.pack('<IIIII', 98, 3, 0, 1, 0)                               # DXGI_FORMAT_BC7_UNORM, 2D, array 1
    assert len(hdr) == 148
    with open(dst, 'wb') as f:
        f.write(hdr)
        for m in mips: f.write(m)
    with open(dst + '.json', 'w') as f:
        json.dump({"Version": 2, "SourceFileDate": FILETIME, "Flags": ["FL_BITMAP_COMPRESSION", "FL_BITMAP_MIPMAP", "FL_BITMAP_QUALITY_HIGH"]}, f)

if os.path.exists(OUT): shutil.rmtree(OUT)
primary = None
for n, ac in enumerate(cfg['aircraft_folders']):
    liv = os.path.join(OUT, 'SimObjects', 'Airplanes', ac, 'liveries', cfg['company_folder'], cfg['livery_folder'])
    tex = os.path.join(liv, cfg['texture_folder']); os.makedirs(tex)
    with open(os.path.join(liv, 'livery.cfg'), 'w', newline='\r\n') as f:
        f.write('[Version]\nmajor = 1\nminor = 0\n\n[General]\nname = "%s"\n' % cfg['livery_name'])
    fallbacks = list(cfg['base_texture_fallbacks'])
    if n == 0:
        primary = ac
        for src, names in cfg['textures'].items():
            names = [names] if isinstance(names, str) else names
            first = os.path.join(tex, names[0].upper() + '.PNG.DDS')
            write_dds_bc7(os.path.join(ROOT, 'textures', src + '.png'), first)
            for extra in names[1:]:                      # same texture under an alternative guessed name
                for ext in ('', '.json'): shutil.copy(first + ext, os.path.join(tex, extra.upper() + '.PNG.DDS') + ext)
            print('  wrote', ', '.join(names), flush=True)
    else:   # alternative spelling of the aircraft folder: reuse the primary copy's textures through a fallback
        fallbacks.insert(0, '..\\..\\..\\..\\..\\%s\\liveries\\%s\\%s\\%s' % (primary, cfg['company_folder'], cfg['livery_folder'], cfg['texture_folder']))
    with open(os.path.join(tex, 'texture.cfg'), 'w', newline='\r\n') as f:
        f.write('[fltsim]\n' + ''.join('fallback.%d=%s\n' % (i + 1, p) for i, p in enumerate(fallbacks)))
    shutil.copytree(os.path.join(ROOT, 'thumbnail'), os.path.join(liv, 'thumbnail'))
content = []; total = 0
for dp, dn, fn in os.walk(OUT):
    for f in sorted(fn):
        p = os.path.join(dp, f); s = os.path.getsize(p); total += s
        content.append({"path": os.path.relpath(p, OUT).replace(os.sep, '/'), "size": s, "date": FILETIME})
content.sort(key=lambda c: c['path'].lower())
json.dump({"content": content}, open(os.path.join(OUT, 'layout.json'), 'w'), indent=1)
json.dump({"dependencies": [], "content_type": "AIRCRAFT", "title": "N45BP livery - iniBuilds Global Jet", "manufacturer": "Bombardier",
           "creator": "community", "package_version": "0.1.0", "minimum_game_version": "1.0.0",
           "release_notes": {"neutral": {"LastUpdate": "", "OlderHistory": ""}}, "total_package_size": str(total).zfill(20)},
          open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
print('built', OUT, '%.0f MB' % (total / 1e6), len(content), 'files')
