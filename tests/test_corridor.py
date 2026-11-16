"""Original small fixtures for overlap selection and checkpoint preservation."""
import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from selected_region import overlaps_placement
from corridor_job import reuse,checked
from convert import build
from test_region import fixture
from prepare_selected import prepare
from extraction import export_name

class CorridorTests(unittest.TestCase):
    def test_prepared_maps_preserve_only_selected_indices(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            r=Path(d);(r/'catalog').mkdir();(r/'snapshot').mkdir();(r/'snapshot/inventory.jsonl').write_text('')
            (r/'catalog/bootstrap.json').write_text(json.dumps({'snapshot':str(r/'snapshot')}))
            w=r/'work';source=w/'extracted';source.mkdir(parents=True)
            name=export_name('base.rpf/map.ymap');raw=b'<CMapData><entities><Item><archetypeName>first</archetypeName></Item><Item><archetypeName>second</archetypeName></Item></entities></CMapData>'
            (source/name).write_bytes(raw)
            (source/(name[:-4]+'.receipt.json')).write_text(json.dumps({'Fingerprint':'synthetic','Files':{name:hashlib.sha256(raw).hexdigest().upper()}}))
            (w/'tasks.json').write_text(json.dumps({'tasks':[{'path':'base.rpf/map.ymap','export':name}]}))
            (w/'placements.json').write_text(json.dumps([{'map':name,'index':1}]))
            prepare(r,w)
            self.assertEqual((source/name).read_bytes(),raw)
            self.assertEqual([x.text for x in ET.parse(w/'prepared'/name).findall('entities/Item/archetypeName')],['second'])

    def test_outside_anchor_rotated_bounds(self):
        item=ET.fromstring('<Item><position x="12" y="0" z="0"/><rotation x="0" y="0" z="0.7071067811865476" w="0.7071067811865476"/><scaleXY value="2"/></Item>')
        archetype=ET.fromstring('<Item><bbMin x="-1" y="-3" z="0"/><bbMax x="1" y="3" z="1"/></Item>')
        self.assertTrue(overlaps_placement(item,archetype,[0,-3,10,3]))
        self.assertFalse(overlaps_placement(item,archetype,[0,10,10,20]))
        with self.assertRaisesRegex(ValueError,'bounds unavailable'):overlaps_placement(item,ET.fromstring('<Item/>'),[0,0,1,1])

    def test_preselected_keeps_outside_anchors(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            r=Path(d);fixture(r/'source')
            ordinary=build(r/'source',r/'ordinary',bbox=[-1,-1,1,1])
            selected=build(r/'source',r/'selected',bbox=[-1,-1,1,1],preselected=True)
            self.assertEqual(ordinary['visual_instances'],1)
            self.assertEqual(selected['visual_instances'],3)

    def test_receipt_copy_verifies_and_preserves(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);s=r/'source';s.mkdir();name='toy.ydr.xml';data=b'synthetic'
            (s/name).write_bytes(data)
            (s/'toy.ydr.receipt.json').write_text(json.dumps({'Files':{name:hashlib.sha256(data).hexdigest().upper()}}))
            tasks={'tasks':[{'export':name}]}
            self.assertEqual(reuse(tasks,r/'out',[s]),1)
            self.assertEqual(reuse(tasks,r/'out',[s]),0)
            (s/name).write_bytes(b'corrupt')
            self.assertEqual(reuse(tasks,r/'second',[s]),0)
            self.assertEqual((r/'out'/name).read_bytes(),data)

    def test_checkpoint_changed_fails(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'output').write_bytes(b'ok')
            marker=r/'complete.json';marker.write_text(json.dumps({'files':{'output':hashlib.sha256(b'ok').hexdigest()}}))
            self.assertIsNotNone(checked(marker))
            (r/'output').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'Checkpoint changed'):checked(marker)
