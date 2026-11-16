import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mount_diagnostics import classify, patched_path


class MountDiagnosticsTests(unittest.TestCase):
    def test_nested_archive_patch_is_applied_before_membership(self):
        evidence={'active':{'virtual':'update\\patch.rpf\\nested.rpf'},'patches':{'dlc\\old.rpf':'update\\patch.rpf\\nested.rpf'},'failures':[]}
        result=classify([{'name':'map.ymap','candidates':['dlc/old.rpf/map.ymap','update/patch.rpf/nested.rpf/map.ymap']}],evidence)['conflicts'][0]
        self.assertEqual(result['active_candidates'],['update/patch.rpf/nested.rpf/map.ymap'])
        self.assertEqual(result['status'],'one')

    def test_none_and_multiple_are_not_silently_selected(self):
        evidence={'active':{'a':'a.rpf','b':'b.rpf'},'patches':{},'failures':[]}
        groups=[{'name':'x','candidates':['c.rpf/x']},{'name':'y','candidates':['a.rpf/y','b.rpf/y']}]
        self.assertEqual([x['status'] for x in classify(groups,evidence)['conflicts']],['none','multiple'])

    def test_rejects_patch_cycles_and_failed_evidence(self):
        with self.assertRaisesRegex(ValueError,'cycle'): patched_path('a.rpf/x',{'a.rpf':'b.rpf','b.rpf':'a.rpf'})
        with self.assertRaisesRegex(ValueError,'cycle'): patched_path('a.rpf/x',{'a.rpf':'a.rpf/nested'})
        with self.assertRaisesRegex(ValueError,'errors'): classify([] ,{'failures':['bad']})
        with self.assertRaisesRegex(ValueError,'normalized'): classify([],{'active':{},'patches':{'A.rpf':'b.rpf','a.rpf':'c.rpf'},'failures':[]})
