import bpy, sys, json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[-1])
print('objects',len(bpy.data.objects),'meshes',len(bpy.data.meshes),'materials',len(bpy.data.materials),'images',len(bpy.data.images))
print('unit scale',bpy.context.scene.unit_settings.scale_length)
for img in bpy.data.images: print('IMG',img.name,img.filepath)
for m in bpy.data.materials:
    texs=[]
    if m.node_tree:
        for n in m.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image: texs.append(n.image.name)
    print('MAT',m.name,texs)
import numpy as np
allmin=np.array([1e9]*3); allmax=-allmin
for o in bpy.data.objects:
    if o.type!='MESH': 
        print('OBJ',o.type,o.name, 'parent',o.parent.name if o.parent else None); continue
    me=o.data
    n=len(me.vertices)
    co=np.empty(n*3); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)
    M=np.array(o.matrix_world)
    w=co@M[:3,:3].T+M[:3,3]
    mn,mx=w.min(0),w.max(0)
    allmin=np.minimum(allmin,mn); allmax=np.maximum(allmax,mx)
    uvn=[l.name for l in me.uv_layers]
    # uv range
    uvr=''
    if me.uv_layers:
        uv=np.empty(len(me.loops)*2); me.uv_layers[0].data.foreach_get('uv',uv); uv=uv.reshape(-1,2)
        uvr=f"uv[{uv[:,0].min():.2f},{uv[:,0].max():.2f}]x[{uv[:,1].min():.2f},{uv[:,1].max():.2f}]"
    mats=[s.material.name if s.material else None for s in o.material_slots]
    print(f"MESH {o.name!r} v={n} f={len(me.polygons)} bbox=({mn[0]:.2f},{mn[1]:.2f},{mn[2]:.2f})-({mx[0]:.2f},{mx[1]:.2f},{mx[2]:.2f}) uvs={uvn} {uvr} mats={mats} parent={o.parent.name if o.parent else None}")
print('TOTAL bbox',allmin,allmax)
