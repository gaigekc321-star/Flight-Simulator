# Tools

Working pipeline that produced the N45BP paint. These are research scripts, not a polished tool: paths are
relative to a scratch working directory (`kit/`, `photos/`, `work/`), and the paint kit and reference photos
are not in this repository.

Requirements: Python 3.13, `numpy scipy numba pillow scikit-image pyamg psd-tools bpy`.

## Order of operations

1. `psdexport.py` — export every layer of the three kit PSDs to PNG.
2. `fbx_dump.py` — load `Global_UDIM_Model.fbx` with Blender's Python module, dump geometry, normals and UVs.
3. `posefix.py` — two parts are misplaced in the kit FBX (left stabiliser, right nose avionics door); find the
   transforms that put them back. (`data/meta.json` holds the results.)
4. `bake.py` — for each of the 13 tiles, bake a 4096² map of 3D position, normal and part ID per texel.
5. `camfit1/2/3.py` — solve a camera for each reference photo from landmarks (doors, windows, tail).
6. `photo_maps.py`, `seg_pipeline.py` — remove shading and classify each photo into the three paint tones.
7. `charts.py`, `project_photo.py` — project those classes onto unwrapped charts (fuselage cylinder, nacelles, fin sides).
8. `assemble_fus.py`, `assemble_parts.py` — clean the photo data and fill unseen areas in the same style (`camo.py`).
9. `decal_rect.py`, `decals.py` — trace the tail registration from the rectified photo, draw the flag, extract the emblem.
10. `paint.py` — paint every texel from the charts and decals.
11. `composite.py` — add the kit's Details and Weathering layers.
12. `render.py`, `make_release.py` — preview renders, thumbnails and this folder.

## `data/`

Everything needed to repaint without redoing the photo work:

- `*_labels.png` — the finished three-tone maps (palette index 0 dark, 1 mid, 2 light) for the fuselage chart,
  both fin sides, both nacelles, and the planar chart used for wing/stabiliser upper surfaces.
- `fus_known.png` — which parts of the fuselage chart came from photographs.
- `reg_mask.png`, `flag.png`, `emblem_mask.png` — decals.
- `meta.json` — decal positions in model coordinates, the pose fixes, solved cameras, and the palette.

To change a colour, edit the palette at the top of `camo.py` / `paint.py` and rerun steps 10–12.
To make the wing upper surface plain, replace `top_col(p)` in the wing section of `paint.py` with a constant.
