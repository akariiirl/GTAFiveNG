import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from progress_maps import mask_triangles
import numpy as np
from PIL import Image

class ProgressAreaTests(unittest.TestCase):
    def test_overlap_is_union_and_vertical_wall_excluded(self):
        mask=Image.new('1',(20,20))
        triangle=np.array([[[2,2,0],[10,2,0],[2,10,0]]],dtype=float)
        mask_triangles(mask,triangle,np.array([0,0]),1)
        count=np.array(mask).sum()
        mask_triangles(mask,triangle,np.array([0,0]),1)
        self.assertEqual(np.array(mask).sum(),count)
        wall=np.array([[[15,2,0],[15,10,0],[15,10,20]]],dtype=float)
        mask_triangles(mask,wall,np.array([0,0]),1)
        self.assertEqual(np.array(mask).sum(),count)

if __name__=='__main__': unittest.main()
