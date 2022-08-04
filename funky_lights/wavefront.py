

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