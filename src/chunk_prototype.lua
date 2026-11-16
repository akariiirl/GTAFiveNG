-- Isolated experimental loader. Mock-tested only; BeamNG behavior is unverified.
local M = {}
local current
local function engineAdapter()
  return {
    exists=function(path) return FS and FS:fileExists(path) end,
    load=function(id, record)
      if type(createObject) ~= 'function' then error('createObject binding unavailable') end
      local object=createObject('Prefab')
      if not object then error('Prefab creation failed') end
      local ok,err=pcall(function()
        object:setField('filename',0,record.filename)
        object:setField('loadMode',0,'Automatic')
        object:setField('position',0,'0 0 0')
        object:setField('scale',0,'1 1 1')
        if object:registerObject('ls_chunk_'..id:gsub('[^%w_]','_')) == false then error('Prefab registration rejected') end
      end)
      if not ok then pcall(function() object:delete() end); error(err) end
      return object
    end,
    unload=function(object) object:delete(); return true end,
    log=function(level,message) if type(log)=='function' then log(level,'lsf_chunkPrototype',message) end end
  }
end
function M.new(plan,adapter)
  assert(plan.schema==1 and plan.experimental==true and type(plan.chunks)=='table','Experimental chunk plan required')
  adapter=adapter or engineAdapter()
  local active={}
  local controller={}
  local function emit(level,message) if adapter.log then adapter.log(level,message) end end
  function controller.stats()
    local count,estimated=0,0
    for id in pairs(active) do count=count+1; estimated=estimated+plan.chunks[id].estimated_bytes end
    return {active_chunks=count,estimated_file_bytes=estimated,lua_heap_kib=collectgarbage('count'),engine_verified=false}
  end
  function controller.planTransition(requested)
    local needed,visiting={},{}
    local function visit(id)
      if visiting[id] then error('Dependency cycle: '..id) end
      if needed[id] then return end
      local record=plan.chunks[id]
      if not record then error('Missing chunk: '..id) end
      if type(record.filename)~='string' or not record.filename:match('^/levels/los_santos_fazes/experimental/chunks/') or record.filename:find('..',1,true) then error('Unsafe prefab path') end
      if type(record.estimated_bytes)~='number' or record.estimated_bytes<0 or record.estimated_bytes>=math.huge then error('Invalid size estimate') end
      visiting[id]=true
      for _,dependency in ipairs(record.dependencies or {}) do visit(dependency) end
      visiting[id]=nil; needed[id]=true
    end
    for _,id in ipairs(requested) do visit(id) end
    local load,unload,union={},{},{}
    for id in pairs(active) do union[id]=true; if not needed[id] then unload[#unload+1]=id end end
    for id in pairs(needed) do union[id]=true; if not active[id] then load[#load+1]=id end end
    local count,bytes=0,0
    for id in pairs(union) do count=count+1; bytes=bytes+plan.chunks[id].estimated_bytes end
    if next(needed)~=nil and (count>plan.max_active_chunks or bytes>plan.max_estimated_bytes) then error('Peak file/chunk budget exceeded; unload first') end
    table.sort(load); table.sort(unload)
    return {load=load,unload=unload,needed=needed,peak_estimated_bytes=bytes}
  end
  function controller.transition(requested)
    local ok,transition=pcall(controller.planTransition,requested)
    if not ok then emit('E',tostring(transition)); return false end
    local staged={}
    local function rollback()
      for key,object in pairs(staged) do
        local removed,result=pcall(adapter.unload,object)
        if not removed or result==false then active[key]=object; emit('E','Rollback cleanup failed: '..key) end
      end
    end
    for _,id in ipairs(transition.load) do
      local record=plan.chunks[id]
      if not adapter.exists(record.filename) then
        emit('E','Missing prefab: '..record.filename)
        rollback()
        return false
      end
      local loaded,object=pcall(adapter.load,id,record)
      if not loaded or not object then
        emit('E','Load failed: '..id..' '..tostring(object))
        rollback()
        return false
      end
      staged[id]=object; emit('I','Loaded experimental chunk '..id)
    end
    for key,value in pairs(staged) do active[key]=value end
    local success=true
    for _,id in ipairs(transition.unload) do
      local removed,result=pcall(adapter.unload,active[id])
      if removed and result~=false then active[id]=nil; emit('I','Unloaded '..id) else success=false; emit('E','Unload failed: '..id) end
    end
    local stats=controller.stats(); emit('I','Lua heap KiB='..stats.lua_heap_kib..' estimated file bytes='..stats.estimated_file_bytes)
    return success
  end
  function controller.reload(id)
    if not active[id] then return controller.transition({id}) end
    local ok,result=pcall(adapter.unload,active[id])
    if not ok or result==false then emit('E','Reload unload failed: '..id); return false end
    active[id]=nil
    local requested={id}; for key in pairs(active) do requested[#requested+1]=key end
    return controller.transition(requested)
  end
  function controller.shutdown() return controller.transition({}) end
  return controller
end
function M.start(path)
  if type(jsonReadFile)~='function' then return false end
  local plan=jsonReadFile(path); if not plan then return false end
  if current and not current.shutdown() then return false end
  local ok,result=pcall(M.new,plan)
  if not ok then if type(log)=='function' then log('E','lsf_chunkPrototype',tostring(result)) end; return false end
  current=result; return true
end
function M.transition(ids) return current and current.transition(ids) or false end
function M.reload(id) return current and current.reload(id) or false end
function M.stats() return current and current.stats() or {engine_verified=false} end
function M.onExtensionUnloaded() if current then current.shutdown() end end
return M
