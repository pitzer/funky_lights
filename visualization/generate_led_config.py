import numpy as np


class WavefrontGroup:
    def __init__(self, name='default'):
        self.name = name               # group name
        # vertices as an Nx3 or Nx6 array (per vtx colors)
        self.vertices = []
        self.normals = []                 # normals
        self.texcoords = []                 # texture coordinates
        # M*Nv*3 array, Nv=# of vertices, stored as vid,tid,nid (-1 for N/A)
        self.polygons = []


class WavefrontOBJ:
    def __init__(self, default_mtl='default_mtl'):
        self.path = None               # path of loaded object
        self.mtllibs = []                 # .mtl files references via mtllib
        self.mtls = [default_mtl]    # materials referenced
        self.mtlid = []                 # indices into self.mtls for each polygon
        # vertices as an Nx3 or Nx6 array (per vtx colors)
        self.vertices = []
        self.normals = []                 # normals
        self.texcoords = []                 # texture coordinates
        # M*Nv*3 array, Nv=# of vertices, stored as vid,tid,nid (-1 for N/A)
        self.polygons = []
        self.groups = []                 # Groups


def load_obj(filename: str, default_mtl='default_mtl', triangulate=False) -> WavefrontOBJ:
    """Reads a .obj file from disk and returns a WavefrontOBJ instance

    Handles only very rudimentary reading and contains no error handling!

    Does not handle:
        - relative indexing
        - subobjects or groups
        - lines, splines, beziers, etc.
    """
    # parses a vertex record as either vid, vid/tid, vid//nid or vid/tid/nid
    # and returns a 3-tuple where unparsed values are replaced with -1
    def parse_vertex(vstr):
        vals = vstr.split('/')
        vid = int(vals[0])-1
        tid = int(vals[1])-1 if len(vals) > 1 and vals[1] else -1
        nid = int(vals[2])-1 if len(vals) > 2 else -1
        return (vid, tid, nid)

    with open(filename, 'r') as objf:
        obj = WavefrontOBJ(default_mtl=default_mtl)
        obj.path = filename
        cur_mat = obj.mtls.index(default_mtl)
        cur_group = WavefrontGroup()

        for line in objf:
            toks = line.split()
            if not toks:
                continue
            if toks[0] == 'g':
                cur_group = WavefrontGroup(name=toks[1])
                obj.groups.append(cur_group)
            if toks[0] == 'v':
                cur_group.vertices.append([float(v) for v in toks[1:]])
            elif toks[0] == 'vn':
                cur_group.normals.append([float(v) for v in toks[1:]])
            elif toks[0] == 'vt':
                cur_group.texcoords.append([float(v) for v in toks[1:]])
            elif toks[0] == 'f':
                poly = [parse_vertex(vstr) for vstr in toks[1:]]
                if triangulate:
                    for i in range(2, len(poly)):
                        obj.mtlid.append(cur_mat)
                        cur_group.polygons.append(
                            (poly[0], poly[i-1], poly[i]))
                else:
                    obj.mtlid.append(cur_mat)
                    cur_group.polygons.append(poly)
            elif toks[0] == 'mtllib':
                obj.mtllibs.append(toks[1])
            elif toks[0] == 'usemtl':
                if toks[1] not in obj.mtls:
                    obj.mtls.append(toks[1])
                cur_mat = obj.mtls.index(toks[1])
        return obj


def save_obj(obj: WavefrontOBJ, filename: str):
    """Saves a WavefrontOBJ object to a file

    Warning: Contains no error checking!

    """
    with open(filename, 'w') as ofile:
        for mlib in obj.mtllibs:
            ofile.write('mtllib {}\n'.format(mlib))
        for vtx in obj.vertices:
            ofile.write('v '+' '.join(['{}'.format(v) for v in vtx])+'\n')
        for tex in obj.texcoords:
            ofile.write('vt '+' '.join(['{}'.format(vt) for vt in tex])+'\n')
        for nrm in obj.normals:
            ofile.write('vn '+' '.join(['{}'.format(vn) for vn in nrm])+'\n')
        if not obj.mtlid:
            obj.mtlid = [-1] * len(obj.polygons)
        poly_idx = np.argsort(np.array(obj.mtlid))
        cur_mat = -1
        for pid in poly_idx:
            if obj.mtlid[pid] != cur_mat:
                cur_mat = obj.mtlid[pid]
                ofile.write('usemtl {}\n'.format(obj.mtls[cur_mat]))
            pstr = 'f '
            for v in obj.polygons[pid]:
                # UGLY!
                vstr = '{}/{}/{} '.format(v[0]+1, v[1]+1 if v[1]
                                          >= 0 else 'X', v[2]+1 if v[2] >= 0 else 'X')
                vstr = vstr.replace('/X/', '//').replace('/X ', ' ')
                pstr += vstr
            ofile.write(pstr+'\n')


scene = load_obj('dome.obj')
group =scene.groups[0]
print(group.name)

x = np.array([v[0] for v in group.vertices])
y = np.array([v[1] for v in group.vertices])
z = np.array([v[2] for v in group.vertices])


data = np.concatenate((x[:, np.newaxis], 
                       y[:, np.newaxis], 
                       z[:, np.newaxis]), 
                      axis=1)
print('data' + str(data))

# Calculate the mean of the points, i.e. the 'center' of the cloud
datamean = data.mean(axis=0)
print('mean ' + str(datamean))

# PCO to generate a line representation for each tube
mu = data.mean(0)
C = np.cov(data - mu, rowvar=False)
d, u = np.linalg.eigh(C)
U = u.T[::-1]

# Project points onto the principle axes to get min/max
Z = np.dot(data - mu, U.T)
print('min Z ' + str(Z.min()))
print('max Z ' + str(Z.max()))

# Generate LED positions
LED_SEGMENT_UID = 1
NUM_LEDS = 30
linepts = U[0] * np.mgrid[Z.min():Z.max():complex(NUM_LEDS)][:, np.newaxis]
linepts += datamean

# Dump into json
import json

json_dict = {
    'led_segments': [
        {
            'uid': LED_SEGMENT_UID,
            'name': group.name,
            'num_leds': linepts.shape[0],
            'led_positions': linepts.tolist()
        }
    ]
}
with open('led_config.json', 'w', encoding='utf-8') as f:
    json.dump(json_dict, f, ensure_ascii=False, indent=4)


# Verify that everything looks right
# import matplotlib.pyplot as plt
# import mpl_toolkits.mplot3d as m3d

# ax = m3d.Axes3D(plt.figure())
# print('x ' + str(x.min()) + ' ' + str(x.max()))
# print('y ' + str(y.min()) + ' ' + str(y.max()))
# print('z ' + str(z.min()) + ' ' + str(z.max()))
# ax.scatter3D(*data.T)
# ax.set_xlim3d(-0.1, 0.9)
# ax.set_ylim3d(-3.7, -1.7)
# ax.set_zlim3d(-0.5, 0.5)

# ax.scatter3D(*Z.T)
# ax.set_xlim3d(-0.5, 0.5)
# ax.set_ylim3d(-0.5, 0.5)
# ax.set_zlim3d(-0.5, 0.5)

# ax.plot3D(*linepts.T)
# plt.show()

