"""Synthetic regressions for real-world road names and invalid vertex attributes."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from convert import drawable
from resource_cache import ResourceCache, cached_drawable
from validate_surfaces import is_drivable_road


DRAWABLE = """<Drawable><ShaderGroup><Shaders><Item><Name>default</Name><FileName>default</FileName></Item></Shaders></ShaderGroup>
<DrawableModelsHigh><Item><Geometries><Item><ShaderIndex value="0"/>
<VertexBuffer><Layout><Position/><TexCoord0/></Layout><Data>0 0 0   0 0
1 0 0   1 0
0 1 0   0 1
0 0 1   nan nan</Data></VertexBuffer>
<IndexBuffer><Data>0 1 2 0 1 3</Data></IndexBuffer>
</Item></Geometries></Item></DrawableModelsHigh></Drawable>"""


class NonfiniteDrawableTests(unittest.TestCase):
    def test_numeric_hw1_road_segments(self):
        self.assertTrue(is_drivable_road("hw1_rd_04_07"))
        self.assertFalse(is_drivable_road("hw1_rd_04_07_ovly"))

    def test_nonfinite_uv_omits_only_affected_triangle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toy.ydr.xml"
            path.write_text(DRAWABLE)
            report = {"missing_textures":set(), "degenerate_triangles_removed":0,
                      "nonfinite_attribute_triangles_removed":0}
            meshes = drawable(path, "toy", {}, {}, report)
            self.assertEqual(len(meshes), 1)
            self.assertEqual(meshes[0]["i"].tolist(), [[0,1,2]])
            self.assertTrue(np.isfinite(meshes[0]["uv"]).all())
            self.assertEqual(report["nonfinite_attribute_triangles_removed"], 1)

    def test_cache_replays_nonfinite_omission_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "toy.ydr.xml"
            path.write_text(DRAWABLE)
            cache = ResourceCache(root / "cache")
            for _ in range(2):
                report = {"missing_textures":set(), "degenerate_triangles_removed":0,
                          "nonfinite_attribute_triangles_removed":0}
                meshes = cached_drawable(cache, path, "toy", {}, {}, report, drawable)
                self.assertEqual(len(meshes[0]["i"]), 1)
                self.assertEqual(report["nonfinite_attribute_triangles_removed"], 1)
            self.assertEqual(cache.hits, 1)


if __name__ == "__main__": unittest.main()
