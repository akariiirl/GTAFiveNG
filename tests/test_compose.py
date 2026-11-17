import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_region import fixture
from region import run
from compose import compose
from validate_surfaces import validate
from progress_maps import generate


class CompositionTests(unittest.TestCase):
    def test_neighbors_dedup_collision_roads_and_determinism(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            (source/'toy.ydr.xml').rename(source/'sc1_rd_r_test.ydr.xml')
            p=source/'toy.ymap.xml'; p.write_text(p.read_text().replace('>toy<','>sc1_rd_r_test<'))
            (source/'road.ybn.xml').write_text('<BoundsFile><Bounds type="Geometry"><BoxMin x="0" y="0" z="0"/><BoxMax x="20" y="20" z="0"/><GeometryCenter x="0" y="0" z="0"/><Vertices>0,0,0\n20,0,0\n0,20,0</Vertices><Polygons><Triangle v1="0" v2="1" v3="2"/></Polygons></Bounds></BoundsFile>')
            a=run(source,root/'a',[0,0],10,maps=False)/'build'
            b=run(source,root/'b',[1,0],10,maps=False)/'build'
            result=compose([a,b],root/'composed')
            report=json.loads((result/'conversion_report.json').read_text())
            self.assertEqual(report['visual_instances'],3)
            self.assertEqual(report['collision_triangles'],1)
            self.assertEqual(validate(result,step=1)['within_half_meter'],3)
            objects=[json.loads(line) for line in (result/'levels/los_santos_fazes/main/MissionGroup/Geometry/items.level.json').read_text().splitlines()]
            self.assertEqual(len({o['name'] for o in objects}),len(objects))
            self.assertEqual(len({o['shapeName'] for o in objects if o['collisionType']=='None'}),1)
            summary=generate(result,source,root/'maps','synthetic-composed')
            self.assertEqual(summary['asset_completeness']['expected_instances_in_available_selected_ymaps'],4)
            second=compose([b,a],root/'reversed')
            self.assertEqual((result/'composed.zip').read_bytes(),(second/'composed.zip').read_bytes())
            self.assertEqual(compose([b,a],result),result)
            expanded=compose([result,a],root/'expanded')
            expanded_report=json.loads((expanded/'conversion_report.json').read_text())
            self.assertEqual(expanded_report['visual_instances'],3)
            self.assertEqual(expanded_report['collision_triangles'],1)
            self.assertEqual(validate(expanded,step=1)['within_half_meter'],3)

    def test_same_texture_names_and_material_names_do_not_collide(self):
        import struct
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); builds=[]
            for index in range(2):
                source=root/f'source{index}'; fixture(source)
                header=bytearray(128); header[:4]=b'DDS '
                struct.pack_into('<II',header,12,1,1); struct.pack_into('<I',header,80,2); struct.pack_into('<I',header,88,8)
                (source/'missing_paint.dds').write_bytes(header+bytes([index*255]))
                build=run(source,root/f'work{index}',[index,0],10,maps=False)/'build'
                if index:
                    shape=build/'levels/los_santos_fazes/art/shapes/toy.dae'; shape.rename(shape.with_name('other.dae'))
                    geometry=build/'levels/los_santos_fazes/main/MissionGroup/Geometry/items.level.json'
                    geometry.write_text(geometry.read_text().replace('shapes/toy.dae','shapes/other.dae'))
                builds.append(build)
            result=compose(builds,root/'combined',origin=[255,0,0])
            self.assertEqual(len(list((result/'levels/los_santos_fazes/art/textures').glob('*.dds'))),2)
            materials=json.loads((result/'levels/los_santos_fazes/art/main.materials.json').read_text())
            maps={stage['diffuseMap'] for material in materials.values() for stage in material.get('Stages',[]) if 'diffuseMap' in stage}
            self.assertEqual(len(maps),2)
            self.assertTrue(json.loads((result/'chunks.json').read_text()))
