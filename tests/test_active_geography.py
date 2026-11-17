"""Regression checks for full active-YMAP geography selection."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from selected_region import active_ymap_paths, hd_placements, map_may_overlap, overlaps_placement
from validate_surfaces import is_drivable_road


class ActiveGeographyTests(unittest.TestCase):
    def test_all_active_names_including_other_districts(self):
        evidence={'ymap': {'1':'x64/scentral_01/a.ymap',
                           '2':'update/cityw/vinewood/b.ymap',
                           '3':'x64/desert/c.ymap'}}
        self.assertEqual(len(active_ymap_paths(evidence)), 3)
        with self.assertRaisesRegex(ValueError, 'selection is empty'):
            active_ymap_paths({'ymap': {}})

    def test_far_coordinates_and_outside_anchor_are_retained(self):
        root=ET.fromstring('''<CMapData>
          <streamingExtentsMin x="5100" y="-4100"/>
          <streamingExtentsMax x="5600" y="-3700"/>
          <entities><Item><lodLevel>LODTYPES_DEPTH_HD</lodLevel>
          <archetypeName>real_road</archetypeName>
          <position x="5300" y="-3900" z="20"/>
          <rotation x="0" y="0" z="0" w="1"/>
          </Item></entities></CMapData>''')
        box=[5120,-4000,5250,-3800]
        self.assertTrue(map_may_overlap(root,box))
        placements=hd_placements(root,'other_district.ymap')
        self.assertEqual(placements[0]['position'],[5300,-3900,20])
        archetype=ET.fromstring('''<Item><bbMin x="-100" y="-10" z="-1"/>
          <bbMax x="10" y="10" z="1"/></Item>''')
        self.assertTrue(overlaps_placement(ET.fromstring(placements[0]['xml']),archetype,box))

    def test_missing_streaming_extents_cannot_cull_map(self):
        self.assertTrue(map_may_overlap(ET.fromstring('<CMapData/>'),[0,0,256,256]))

    def test_shadow_geometry_is_not_a_drivable_road(self):
        self.assertTrue(is_drivable_road('sc1_rd_r3_12'))
        self.assertFalse(is_drivable_road('sc1_rd_rnd_tun02_shadow'))


if __name__=='__main__': unittest.main()
