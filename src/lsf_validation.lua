-- Temporary instrumentation for the isolated development profile only.
local M = {}
local elapsed, last = 0, -1
local samples = {}
local function onUpdate(dtReal, dtSim)
  elapsed = elapsed + dtReal
  local second = math.floor(elapsed)
  if second == last then return end
  last = second
  local v = be:getPlayerVehicle(0)
  if not v then return end
  local p = v:getPosition()
  local speed = v:getVelocity():length()
  local hit = castRayStatic(vec3(p.x,p.y,100),vec3(0,0,-1),200)
  table.insert(samples, {t=elapsed,position={p.x,p.y,p.z},speed=speed,groundZ=100-hit})
  jsonWriteFile('lsf_validation.json', {level=getMissionFilename(),samples=samples}, true)
  if #samples == 5 then
    log('I','lsf_validation','Stationary vehicle sample recorded')
    require('screenshot').takeScreenShot()
  end
  if #samples == 8 then v:queueLuaCommand("input.event('throttle', 0.25, 1)") end
  if #samples == 13 then
    v:queueLuaCommand("input.event('throttle', 0, 1); input.event('brake', 1, 1)")
    require('screenshot').takeScreenShot()
  end
end
M.onUpdate = onUpdate
return M
