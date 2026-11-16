import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from lupa import LuaRuntime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_region import fixture
from region import run
from compose import compose
from runtime_plan import export_runtime_plan


class RuntimePrototypeTests(unittest.TestCase):
    def test_lua_mock_load_unload_reload_budget_and_missing(self):
        lua=LuaRuntime(); lua.globals().loader=lua.execute((Path(__file__).resolve().parents[1]/'src/chunk_prototype.lua').read_text())
        lua.execute('''
        local loads,unloads,logs=0,0,{}
        local adapter={exists=function(path) return not path:find('missing') end,
          load=function(id) loads=loads+1; return {id=id} end,
          unload=function(object) unloads=unloads+1; return true end,
          log=function(level,message) logs[#logs+1]=message end}
        local prefix='/levels/los_santos_fazes/experimental/chunks/'
        local plan={schema=1,experimental=true,max_active_chunks=3,max_estimated_bytes=100,
          chunks={a={filename=prefix..'a.prefab.json',estimated_bytes=10,dependencies={}},
                  b={filename=prefix..'b.prefab.json',estimated_bytes=20,dependencies={'a'}},
                  missing={filename=prefix..'missing.prefab.json',estimated_bytes=10}}}
        local c=loader.new(plan,adapter)
        assert(c.transition({'b'})); assert(loads==2 and c.stats().active_chunks==2)
        assert(c.transition({'b'})); assert(loads==2)
        assert(not c.transition({'missing'})); assert(c.stats().active_chunks==2)
        assert(not c.transition({'unknown'})); assert(c.stats().active_chunks==2)
        assert(c.reload('b')); assert(loads==3)
        plan.max_estimated_bytes=1; assert(not c.transition({'b'})); plan.max_estimated_bytes=100
        assert(c.shutdown()); assert(c.stats().active_chunks==0 and unloads==3)
        plan.chunks.a.dependencies={'b'}; assert(not c.transition({'b'}))
        assert(#logs>0 and c.stats().engine_verified==false)
        plan.chunks.a.dependencies={}
        local failedCleanup={exists=adapter.exists,load=adapter.load,unload=function() return false end,log=adapter.log}
        local leaking=loader.new(plan,failedCleanup)
        assert(not leaking.transition({'a','missing'})); assert(leaking.stats().active_chunks==1)
        assert(not leaking.shutdown()); assert(leaking.stats().active_chunks==1)
        ''')

    def test_prefab_ownership_and_dependencies_are_separate_from_level(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            root=Path(d); source=root/'source'; fixture(source)
            path=source/'toy.ymap.xml'; path.write_text(path.read_text().replace('<position x="0"','<position x="255"').replace('<position x="10"','<position x="256"').replace('<position x="11"','<position x="257"'))
            build=run(source,root/'regions',[256,0],5,maps=False)/'build'
            composed=compose([build],root/'composed')
            before=(composed/'composed.zip').read_bytes()
            manifest=export_runtime_plan(composed,root/'experiment')
            plan=json.loads(manifest.read_text()); self.assertFalse(plan['in_game_verified'])
            self.assertIn('0_0',plan['chunks']['1_0']['dependencies'])
            names=[]
            for record in plan['chunks'].values():
                prefab=root/'experiment'/record['filename'].lstrip('/')
                rows=[json.loads(line) for line in prefab.read_text().splitlines()]
                self.assertEqual(rows[0]['class'],'SimGroup'); names.extend(row['name'] for row in rows[1:])
            self.assertEqual(len(names),len(set(names)))
            self.assertEqual((composed/'composed.zip').read_bytes(),before)
