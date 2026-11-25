import sys
from psd_tools import PSDImage
p=PSDImage.open(sys.argv[1])
print(sys.argv[1], p.size, p.color_mode, p.depth, 'channels',p.channels)
def walk(l,d=0):
    for c in l:
        ext=''
        try: ext=f" bbox={c.bbox}"
        except Exception: pass
        print('  '*d+f"[{c.kind}] {c.name!r} vis={c.visible} op={c.opacity} blend={c.blend_mode.name}{ext}" + (f" mask" if c.mask else '') + (f" clip" if getattr(c,"clipping",False) else ''))
        if c.is_group(): walk(c,d+1)
walk(p)
