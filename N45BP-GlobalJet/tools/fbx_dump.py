# Export every mesh object: world-space verts, normals, triangles, UVs (channel 1), material, name -> npz
import bpy, sys, numpy as np, json
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[-2])
out=sys.argv[-1]
objs=[]; data={}
dg=bpy.context.evaluated_depsgraph_get()
for i,o in enumerate(sorted([o for o in bpy.data.objects if o.type=='MESH'], key=lambda o:o.name)):
    me=o.data
    me.calc_loop_triangles()
    n=len(me.vertices)
    co=np.empty(n*3,dtype=np.float32); me.vertices.foreach_get('co',co); co=co.reshape(-1,3)
    M=np.array(o.matrix_world,dtype=np.float64)
    w=(co@M[:3,:3].T+M[:3,3]).astype(np.float32)
    nt=len(me.loop_triangles)
    tri_loops=np.empty(nt*3,dtype=np.int32); me.loop_triangles.foreach_get('loops',tri_loops); tri_loops=tri_loops.reshape(-1,3)
    tri_verts=np.empty(nt*3,dtype=np.int32); me.loop_triangles.foreach_get('vertices',tri_verts); tri_verts=tri_verts.reshape(-1,3)
    uvl=me.uv_layers.get('UVChannel_1') or me.uv_layers[0]
    uv=np.empty(len(me.loops)*2,dtype=np.float32); uvl.data.foreach_get('uv',uv); uv=uv.reshape(-1,2)
    # loop normals
    ln=np.empty(len(me.loops)*3,dtype=np.float32)
    try:
        me.corner_normals.foreach_get('vector',ln)
    except Exception:
        me.loops.foreach_get('normal',ln)
    ln=ln.reshape(-1,3)
    N=np.linalg.inv(M[:3,:3]).T
    lnw=(ln@N.T); lnw/= (np.linalg.norm(lnw,axis=1,keepdims=True)+1e-12)
    mat=o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ''
    det=float(np.linalg.det(M[:3,:3]))
    data[f'v{i}']=w; data[f'tv{i}']=tri_verts; data[f'tuv{i}']=uv[tri_loops]; data[f'tn{i}']=lnw[tri_loops].astype(np.float32)
    objs.append(dict(i=i,name=o.name,mat=mat,parent=o.parent.name if o.parent else None,parent_type=o.parent_type if o.parent else None,det=det,nv=n,nt=nt,uvname=uvl.name,loc=list(M[:3,3]),uvlayers=[l.name for l in me.uv_layers]))
np.savez_compressed(out+'.npz',**data)
json.dump(objs,open(out+'.json','w'),indent=1)
print('dumped',len(objs))
