import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from predictive_streaming import plan


class PredictiveTests(unittest.TestCase):
    def test_prediction_dependencies_budget_hysteresis_and_collision_gate(self):
        chunks = {'near': {'bounds':[0,0,10,10], 'collision_available':True},
                  'ahead': {'bounds':[20,-5,40,5], 'dependencies':['near'], 'collision_available':False},
                  'far': {'bounds':[100,0,110,10]}}
        result = plan(chunks, (0,0), 10, 0, lookahead=3, radius=1, previous=['near'], load_budget=1)
        self.assertEqual(result['predicted_xy'], (30.0, 0.0))
        self.assertIn('ahead', result['visual_chunks'])
        self.assertIn('near', result['collision_ready'])
        self.assertEqual(result['drivable_chunks'], [])
        self.assertEqual(result['load_now'], ['ahead'])
        self.assertEqual(result['deferred'], [])
        self.assertEqual(result['unload'], [])

    def test_unknown_dependency_and_bad_bounds(self):
        result = plan({'a': {'bounds':[0,0,1,1], 'dependencies':['missing']}}, (0,0), 0, 1)
        self.assertEqual(result['missing_dependencies'], ['missing'])
        with self.assertRaises(ValueError): plan({'x': {'bounds':[1,0,0,1]}}, (0,0), 0, 0)

    def test_motion_modes_turn_teleport_boundary_budget_and_safe_unload(self):
        chunks={f'{x}_0':{'bounds':[x*10,0,(x+1)*10,10], 'collision_available':x<3,
                            'dependencies':['bad'] if x==3 else []} for x in range(40)}
        stopped=plan(chunks,(9,5),0,0,radius=1,previous=['0_0'],hysteresis=3)
        self.assertIn('0_0',stopped['visual_chunks'])
        reversing=plan(chunks,(25,5),5,math.pi,radius=10,lookahead=2)
        self.assertLess(reversing['predicted_xy'][0],25)
        turning=plan(chunks,(25,5),5,math.pi/2,radius=15,lookahead=2)
        self.assertGreater(turning['predicted_xy'][1],5)
        fast=plan(chunks,(0,5),100,0,radius=1,lookahead=3,load_budget=1)
        self.assertEqual(len(fast['load_now']),1)
        self.assertGreater(len(fast['deferred']),0)
        teleport=plan(chunks,(1000,5),0,0,previous=['0_0'])
        self.assertEqual(teleport['unload'],['0_0'])
        bounded=plan(chunks,(35,5),0,0,radius=20)
        self.assertNotIn('3_0',bounded['collision_ready'])
        self.assertEqual(bounded['drivable_chunks'],[])
        self.assertEqual(plan(chunks,(35,5),0,0,radius=20,load_budget=0)['load_now'],[])


if __name__ == '__main__': unittest.main()
