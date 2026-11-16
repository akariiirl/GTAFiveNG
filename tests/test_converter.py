import sys, unittest, tempfile, struct
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from convert import valid_mesh, quat_matrix, dae, NS, normalized_dds

class GeometryTests(unittest.TestCase):
    def test_truncated_compressed_mip_tail(self):
        header=bytearray(128); header[:4]=b'DDS '; header[84:88]=b'DXT1'
        struct.pack_into('<II',header,12,8,8); struct.pack_into('<I',header,28,4)
        data=bytes(header)+bytes(32+8+3)
        repaired,changed=normalized_dds(data)
        self.assertTrue(changed); self.assertEqual(struct.unpack_from('<I',repaired,28)[0],2)
        self.assertEqual(len(repaired),168)
        self.assertEqual(normalized_dds(repaired),(repaired,False))
    def test_reject_invalid_vertices(self):
        with self.assertRaises(ValueError): valid_mesh([[0,0,float('nan')]],[[0,0,0]])
        with self.assertRaises(ValueError): valid_mesh([[0,0,0]],[[0,1,2]])
    def test_remove_zero_area(self):
        idx,n=valid_mesh([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2],[0,0,1]])
        self.assertEqual(n,1); self.assertEqual(idx.tolist(),[[0,1,2]])
    def test_inverse_quaternion(self):
        e=ET.fromstring('<Item><rotation x="0" y="0" z="0.7071067811865476" w="0.7071067811865476"/></Item>')
        np.testing.assert_allclose(quat_matrix(e)@np.array([1,0,0]),[0,-1,0],atol=1e-10)
        self.assertAlmostEqual(np.linalg.det(quat_matrix(e)),1)
    def test_collada_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.dae'; dae(p,[{'v':np.array([[0,0,0],[1,0,0],[0,1,0]]),'i':np.array([[0,1,2]]),'material':'test'}])
            root=ET.parse(p).getroot(); ns={'c':NS}
            self.assertEqual(root.findtext('c:asset/c:up_axis',namespaces=ns),'Z_UP')
            self.assertEqual(root.find('.//c:triangles',ns).get('count'),'1')

if __name__=='__main__': unittest.main()
