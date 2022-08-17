from collections import namedtuple

MeshConfig = namedtuple(
    'MeshConfig', ['mesh', 'cluster_eps', 'start_offset', 'end_offset', 'uid_offset', 'output_csv'])

mesh_configs = [
    MeshConfig(
        mesh='../controller/mesh/dome.obj',
        cluster_eps=0.03,
        start_offset=0.10,
        end_offset=0.10,
        uid_offset=1,
        output_csv='../config/dome.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/trunk.obj',
        cluster_eps=0.005,
        start_offset=0.01,
        end_offset=0.01,
        uid_offset=10,
        output_csv='../config/trunk.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/head.obj',
        cluster_eps=0.03,
        start_offset=0.05,
        end_offset=0.05,
        uid_offset=60,
        output_csv='../config/head.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/legs.obj',
        cluster_eps=0.03,
        start_offset=0.05,
        end_offset=0.05,
        uid_offset=80,
        output_csv='../config/legs.csv'
    )
]