-- Local GTA geometry streaming experiment.
local M = {}
local TAG = 'lsf_stream'
local ROOT = '/levels/los_santos_fazes/stream/'
local CELL_SIZE = 256
local CREATE_PER_FRAME = 24
local MAX_ACTIVE_CELLS = 16
local MAX_REQUESTED_OBJECTS = 20000
local KEEP_DISTANCE_CELLS = 2
local index, cells, active, refs, objects, queue
local current, failed, pausedByUs, reloads, created, deleted, queueHead
local lastReport = 0
local lastX, lastY, rejectedMotionSamples
local reportFrames, recentFps = 0, 0
local unloadCell, budgetSerial, budgetDeferred

local function say(level, message) if log then log(level, TAG, message) end end
local function setHold(on)
  if not simTimeAuthority then return end
  if on and not pausedByUs then
    simTimeAuthority.pushPauseRequest(TAG)
    pausedByUs = true
  elseif not on and pausedByUs then
    simTimeAuthority.popPauseRequest(TAG)
    pausedByUs = false
  end
end
local function cellId(x, y)
  return tostring(math.floor(x / CELL_SIZE)) .. '_' .. tostring(math.floor(y / CELL_SIZE))
end
local function parseId(id)
  local x, y = id:match('^(-?%d+)_(-?%d+)$')
  return tonumber(x), tonumber(y)
end
local function desiredIds(x, y, vx, vy)
  local px, py = x + vx * 3, y + vy * 3
  local cx, cy = math.floor(x / CELL_SIZE), math.floor(y / CELL_SIZE)
  local fx, fy = math.floor(px / CELL_SIZE), math.floor(py / CELL_SIZE)
  local wanted, order = {}, {}
  local function add(ix, iy)
    local id = tostring(ix) .. '_' .. tostring(iy)
    if cells[id] and not wanted[id] then
      wanted[id] = true
      order[#order + 1] = id
    end
  end
  add(cx, cy)
  for _, center in ipairs({{cx,cy},{fx,fy}}) do
    for dx = -1, 1 do for dy = -1, 1 do add(center[1]+dx, center[2]+dy) end end
  end
  table.sort(order, function(a,b)
    local ax,ay=parseId(a); local bx,by=parseId(b)
    local da=(ax-cx)^2+(ay-cy)^2; local db=(bx-cx)^2+(by-cy)^2
    if da == db then return a < b end
    return da < db
  end)
  return wanted, order, cx, cy
end
local function field(value)
  if type(value) == 'table' then
    local out = {}
    for i,v in ipairs(value) do out[i] = tostring(v) end
    return table.concat(out, ' ')
  end
  return tostring(value)
end
local function createOne(spec)
  if not FS:fileExists(spec.shapeName) then error('missing shape ' .. tostring(spec.shapeName)) end
  local obj = createObject('TSStatic')
  if not obj then error('TSStatic creation failed') end
  local ok, why = pcall(function()
    for _, key in ipairs({'shapeName','position','rotationMatrix','scale','collisionType','decalType','meshCulling','isRenderEnabled'}) do
      if spec[key] ~= nil then obj:setField(key, 0, field(spec[key])) end
    end
    if obj:registerObject(spec.name) == false then error('registerObject rejected ' .. spec.name) end
    local group = scenetree.findObject('Geometry')
    if not group then error('Geometry group missing') end
    group:addObject(obj)
  end)
  if not ok then pcall(function() obj:delete() end); error(why) end
  return obj
end
local function reloadCollision()
  local ok, why = pcall(function() be:reloadCollision() end)
  if not ok then failed = 'reloadCollision: ' .. tostring(why); say('E', failed); setHold(true); return false end
  reloads = reloads + 1
  return true
end
local function requestedCount(rows)
  local resident, additional = 0, 0
  for _,count in pairs(refs) do if count > 0 then resident = resident + 1 end end
  for _,spec in ipairs(rows) do if not refs[spec.name] or refs[spec.name] == 0 then additional = additional + 1 end end
  return resident + additional
end
local function beginCell(id, wanted, cx, cy)
  if active[id] or current then return false end
  local center = cx and (tostring(cx)..'_'..tostring(cy)) or ''
  local deferred = budgetDeferred[id]
  if deferred and deferred.serial == budgetSerial and deferred.center == center then return false end
  local rows = jsonReadFile(ROOT .. 'cells/' .. id .. '.json')
  if type(rows) ~= 'table' then failed = 'missing cell manifest ' .. id; say('E', failed); setHold(true); return false end
  local needed = requestedCount(rows)
  if needed > MAX_REQUESTED_OBJECTS and wanted then
    local candidates = {}
    for oldId,state in pairs(active) do
      if state == 'ready' and not wanted[oldId] then candidates[#candidates+1] = oldId end
    end
    table.sort(candidates, function(a,b)
      local ax,ay=parseId(a); local bx,by=parseId(b)
      local da=(ax-cx)^2+(ay-cy)^2; local db=(bx-cx)^2+(by-cy)^2
      if da == db then return a < b end
      return da > db
    end)
    local collisionChanged = false
    for _,oldId in ipairs(candidates) do
      if needed <= MAX_REQUESTED_OBJECTS then break end
      collisionChanged = unloadCell(oldId, true) or collisionChanged
      if failed then return false end
      needed = requestedCount(rows)
    end
    if collisionChanged and not reloadCollision() then return false end
  end
  if needed > MAX_REQUESTED_OBJECTS then
    budgetDeferred[id] = {serial=budgetSerial, center=center}
    say('W', 'deferring cell '..id..' at object budget '..tostring(needed)..'/'..MAX_REQUESTED_OBJECTS)
    return false
  end
  budgetDeferred[id] = nil
  current = {id=id, count=#rows}
  active[id] = 'loading'
  for _, spec in ipairs(rows) do
    if type(spec.name) ~= 'string' or type(spec.shapeName) ~= 'string' then
      failed = 'invalid cell object in ' .. id; say('E',failed);setHold(true);return false
    end
    local previous = refs[spec.name] or 0
    refs[spec.name] = previous + 1
    if previous == 0 then queue[#queue + 1] = spec end
  end
  say('I', 'begin cell ' .. id .. ' objects=' .. #rows .. ' unique queue=' .. tostring(#queue-queueHead+1))
  return true
end
local function finishCell()
  if not current or queueHead <= #queue then return end
  if not reloadCollision() then return end
  active[current.id] = 'ready'
  budgetSerial = budgetSerial + 1
  say('I', 'ready cell ' .. current.id .. ' activeObjects=' .. tostring(created - deleted))
  current = nil
end
local function processQueue()
  local made = 0
  while queueHead <= #queue and made < CREATE_PER_FRAME do
    local spec = queue[queueHead]
    queue[queueHead] = false
    queueHead = queueHead + 1
    if (refs[spec.name] or 0) > 0 and not objects[spec.name] then
      local ok, result = pcall(createOne, spec)
      if not ok then
        failed = 'create ' .. spec.name .. ': ' .. tostring(result)
        say('E', failed); setHold(true); return
      end
      objects[spec.name] = result
      created = created + 1
      made = made + 1
    end
  end
  if queueHead > #queue then queue = {}; queueHead = 1 end
  finishCell()
end
unloadCell = function(id, deferReload)
  if active[id] ~= 'ready' then return false end
  local rows = jsonReadFile(ROOT .. 'cells/' .. id .. '.json')
  if type(rows) ~= 'table' then failed='unload manifest missing '..id;say('E',failed);return end
  local removedCollision = false
  for _, spec in ipairs(rows) do
    local left = (refs[spec.name] or 0) - 1
    if left < 0 then failed='reference underflow '..spec.name;say('E',failed);return end
    refs[spec.name] = left
    if left == 0 and objects[spec.name] then
      if spec.collisionType == 'Collision Mesh' then removedCollision = true end
      local ok, why = pcall(function() objects[spec.name]:delete() end)
      if not ok then failed='delete '..spec.name..': '..tostring(why);say('E',failed);return end
      objects[spec.name] = nil
      deleted = deleted + 1
    end
  end
  active[id] = nil
  budgetSerial = budgetSerial + 1
  if removedCollision and not deferReload then reloadCollision() end
  say('I', 'unloaded cell '..id..' activeObjects='..tostring(created-deleted))
  return removedCollision
end
local function begin()
  if index then return end
  if getCurrentLevelIdentifier() ~= 'los_santos_fazes' then return end
  index = jsonReadFile(ROOT .. 'index.json')
  if type(index) ~= 'table' or type(index.cells) ~= 'table' or type(index.origin) ~= 'table' then
    failed = 'stream index missing or invalid'; say('E',failed);return
  end
  cells = {}; for _,id in ipairs(index.cells) do cells[id]=true end
  active, refs, objects, queue, queueHead = {}, {}, {}, {}, 1
  reloads, created, deleted = 0, 0, 0
  budgetSerial, budgetDeferred = 0, {}
  lastX, lastY, rejectedMotionSamples = nil, nil, 0
  reportFrames, recentFps = 0, 0
  setHold(true)
  beginCell(index.spawn_cell)
  say('I', 'started GTA stream; cell count='..#index.cells..' spawn='..index.spawn_cell)
end
function M.onClientStartMission() begin() end
function M.onExtensionLoaded() begin() end
function M.onUpdate(dtReal)
  if not index or failed then return end
  processQueue()
  local veh = be and be:getPlayerVehicle(0)
  if not veh then return end
  local pos, vel = veh:getPosition(), veh:getVelocity()
  local x,y = pos.x+index.origin[1],pos.y+index.origin[2]
  -- GE vehicle velocity can be stale or nonsensical while physics is held during
  -- initial loading. Derive motion from actual world-position changes instead.
  local vx, vy = 0, 0
  if lastX and dtReal and dtReal > 0.001 and dtReal < 1 then
    vx, vy = (x-lastX)/dtReal, (y-lastY)/dtReal
    if vx ~= vx or vy ~= vy or vx*vx+vy*vy > 10000 then
      vx, vy = 0, 0
      rejectedMotionSamples = rejectedMotionSamples + 1
    end
  end
  lastX, lastY = x, y
  local wanted, order, cx, cy = desiredIds(x,y,vx,vy)
  local here = cellId(x,y)
  local readyHere = active[here] == 'ready'
  local ahead = cellId(x + vx, y + vy)
  local readyAhead = active[ahead] == 'ready'
  setHold(not readyHere or (ahead ~= here and not readyAhead))
  local count = 0; for _ in pairs(active) do count=count+1 end
  if count > MAX_ACTIVE_CELLS or not current then
    local candidates = {}
    for id,state in pairs(active) do
      if state == 'ready' and not wanted[id] then candidates[#candidates+1] = id end
    end
    table.sort(candidates, function(a,b)
      local ax,ay=parseId(a); local bx,by=parseId(b)
      local da=(ax-cx)^2+(ay-cy)^2; local db=(bx-cx)^2+(by-cy)^2
      if da == db then return a < b end
      return da > db
    end)
    local collisionChanged = false
    for _,id in ipairs(candidates) do
      local ix,iy=parseId(id)
      if count >= MAX_ACTIVE_CELLS or math.max(math.abs(ix-cx),math.abs(iy-cy)) > KEEP_DISTANCE_CELLS then
        collisionChanged = unloadCell(id, true) or collisionChanged
        if failed then return end
        count = count - 1
      end
    end
    if collisionChanged and not reloadCollision() then return end
  end
  count = 0; for _ in pairs(active) do count=count+1 end
  if not current and count < MAX_ACTIVE_CELLS then
    for _,id in ipairs(order) do if not active[id] then beginCell(id,wanted,cx,cy);break end end
  end
  lastReport = lastReport + (dtReal or 0)
  reportFrames = reportFrames + 1
  if lastReport >= 5 then
    recentFps = reportFrames / lastReport
    reportFrames = 0
    lastReport = 0
    local status = M.status()
    status.player = {beamng={pos.x,pos.y,pos.z},gta={x,y,pos.z},raw_velocity={vel.x,vel.y,vel.z},observed_velocity={vx,vy},cell=here}
    if jsonWriteFile then jsonWriteFile('lsf_stream_status.json',status,true) end
    say('I','position GTA=('..math.floor(x)..','..math.floor(y)..') cell='..here..' ready='..tostring(readyHere)..' objects='..tostring(created-deleted))
  end
end
function M.status()
  local ready,loading={},{}
  for id,state in pairs(active or {}) do
    if state=='ready' then ready[#ready+1]=id else loading[#loading+1]=id end
  end
  table.sort(ready);table.sort(loading)
  return {schema=1,ready_cells=ready,loading_cells=loading,objects=(created or 0)-(deleted or 0),
          created=created or 0,deleted=deleted or 0,collision_reloads=reloads or 0,failed=failed,
          max_active_cells=MAX_ACTIVE_CELLS,max_requested_objects=MAX_REQUESTED_OBJECTS,
          rejected_motion_samples=rejectedMotionSamples or 0,
          recent_fps=recentFps,paused_by_stream=pausedByUs or false,
          lua_heap_kib=collectgarbage('count'),engine_memory_verified=false}
end
function M.onClientEndMission()
  setHold(false)
  index=nil
end
return M
