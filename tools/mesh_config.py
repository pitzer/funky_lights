from collections import namedtuple

MeshConfig = namedtuple(
    'MeshConfig', ['mesh', 'cluster_eps', 'start_offset', 'end_offset', 'uid_offset', 'modelled_csv', 'actual_csv'])

mesh_configs = [
    MeshConfig(
        mesh='../controller/mesh/dome.obj',
        cluster_eps=0.03,
        start_offset=0.15,
        end_offset=0.05,
        uid_offset=1,
        modelled_csv='../config/dome_modelled.csv',
        actual_csv='../config/dome_actual.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/trunk.obj',
        cluster_eps=0.005,
        start_offset=0.01,
        end_offset=0.01,
        uid_offset=10,
        modelled_csv='../config/trunk_modelled.csv',
        actual_csv='../config/trunk_actual.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/eyes.obj',
        cluster_eps=0.02,
        start_offset=0.0,
        end_offset=0.0,
        uid_offset=50,
        modelled_csv='../config/eyes_modelled.csv',
        actual_csv='../config/eyes_actual.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/head.obj',
        cluster_eps=0.03,
        start_offset=0.15,
        end_offset=0.05,
        uid_offset=60,
        modelled_csv='../config/head_modelled.csv',
        actual_csv='../config/head_actual.csv'
    ),
    MeshConfig(
        mesh='../controller/mesh/legs.obj',
        cluster_eps=0.03,
        start_offset=0.15,
        end_offset=0.05,
        uid_offset=80,
        modelled_csv='../config/legs_modelled.csv',
        actual_csv='../config/legs_actual.csv'
    )
]