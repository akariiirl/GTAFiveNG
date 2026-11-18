"""Layered ground materials use original GTA vertex weights and UVs."""
from pathlib import Path
import sys
import tempfile
import unittest
import json

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from convert import drawable
from terrain import triangle_layers
from terrain_package import terrain_geometry
from dependencies import TextureCatalog
import xml.etree.ElementTree as ET


class TerrainTests(unittest.TestCase):
    def test_four_layer_weights(self):
        import numpy as np
        colours=np.array([[0,0,0,255],[0,0,255,255],[0,255,0,255],[0,255,255,255]])
        self.assertEqual(triangle_layers(colours,[[0,0,0],[1,1,1],[2,2,2],[3,3,3]]).tolist(),[0,1,2,3])

    def test_triangle_uses_integrated_four_layer_weights(self):
        import numpy as np
        colours=np.array([[0,60,204,255],[0,81,15,255],[0,204,37,255]])
        self.assertEqual(triangle_layers(colours,[[0,1,2]]).tolist(),[0])

    def test_layered_mesh_preserves_triangles_and_uv(self):
        names=''.join('<Item name="TextureSampler_layer%d"><Name>layer%d</Name></Item>'%(i,i) for i in range(4))
        xml='''<Drawable><ShaderGroup><Shaders><Item><FileName>terrain_cb_w_4lyr.sps</FileName><Parameters>%s</Parameters></Item></Shaders></ShaderGroup>
<DrawableModelsHigh><Item><Geometries><Item><ShaderIndex value="0"/><VertexBuffer><Layout><Position/><Colour1/><TexCoord0/></Layout><Data>
0 0 0   0 0 0 255   0 0
1 0 0   0 0 0 255   1 0
0 1 0   0 0 0 255   0 1
2 0 0   0 255 255 255   0 0
3 0 0   0 255 255 255   1 0
2 1 0   0 255 255 255   0 1
</Data></VertexBuffer><IndexBuffer><Data>0 1 2 3 4 5</Data></IndexBuffer></Item></Geometries></Item></DrawableModelsHigh></Drawable>'''%names
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'terrain.ydr.xml'; path.write_text(xml)
            materials={}; textures={f'layer{i}':{'path':path,'used':False} for i in range(4)}
            report={'missing_textures':set(),'degenerate_triangles_removed':0,'nonfinite_attribute_triangles_removed':0}
            meshes=drawable(path,'ground',materials,textures,report)
            self.assertEqual([len(m['i']) for m in meshes],[1,1])
            self.assertEqual([m['material'].rsplit('_',1)[-1] for m in meshes],['0','3'])
            self.assertEqual(report['terrain_layered_triangles'],2)
            self.assertEqual(report['terrain_textured_triangles'],2)
            self.assertEqual(sum(v['used'] for v in textures.values()),2)
            self.assertEqual(meshes[0]['uv'][0].tolist(),[0,1])

    def test_package_geometry_requires_original_colour_layout(self):
        geometry=ET.fromstring('''<Item><VertexBuffer><Layout><Position/><Colour1/><TexCoord0/></Layout><Data>
0 0 0   0 0 0 255   0 0
1 0 0   0 0 0 255   1 0
0 1 0   0 0 0 255   0 1
</Data></VertexBuffer><IndexBuffer><Data>0 1 2</Data></IndexBuffer></Item>''')
        shader=ET.fromstring('<Item><Parameters>'+''.join('<Item name="TextureSampler_layer%d"><Name>layer%d</Name></Item>'%(i,i) for i in range(4))+'</Parameters></Item>')
        faces,layers,names=terrain_geometry(geometry,shader)
        self.assertEqual(faces.tolist(),[[0,1,2]])
        self.assertEqual(layers.tolist(),[0])
        self.assertEqual(len(names),4)
        geometry.find('VertexBuffer/Layout/Colour1').clear()
        geometry.find('VertexBuffer/Layout').remove(geometry.find('VertexBuffer/Layout/Colour1'))
        self.assertIsNone(terrain_geometry(geometry,shader))

    def test_missing_dictionary_uses_only_identical_shader_donors(self):
        shader=('<Drawable><ShaderGroup><Shaders><Item><FileName>terrain_cb_w_4lyr.sps</FileName><Parameters>'+
                ''.join('<Item name="TextureSampler_layer%d"><Name>layer%d</Name></Item>'%(i,i) for i in range(4))+
                '</Parameters></Item></Shaders></ShaderGroup></Drawable>')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('target','donor','conflict'):
                (root/('base.rpf_'+name+'.ydr.xml')).write_text(shader)
            for index in range(4): (root/('layer%d.dds'%index)).write_bytes(bytes([index]))
            (root/'different.dds').write_bytes(b'different')
            policy={'scoped_textures':True,'asset_txds':{'donor':'good','conflict':'other'},
                    'textures':{'good':{'layer%d'%i:'layer%d.dds'%i for i in range(4)},
                                'other':{'layer%d'%i:'layer%d.dds'%i for i in range(4)}}}
            (root/'dependency-policy.json').write_text(json.dumps(policy))
            catalog=TextureCatalog(root)
            self.assertEqual(set(catalog.for_asset('target')),{'layer0','layer1','layer2','layer3'})
            self.assertEqual(catalog.diagnostics['target']['matching_shader_donors'],['conflict','donor'])
            policy['textures']['other']['layer2']='different.dds'
            (root/'dependency-policy.json').write_text(json.dumps(policy))
            catalog=TextureCatalog(root)
            self.assertNotIn('layer2',catalog.for_asset('target'))
            self.assertEqual(catalog.diagnostics['target']['ambiguous_terrain_textures'],['layer2'])


if __name__=='__main__': unittest.main()
