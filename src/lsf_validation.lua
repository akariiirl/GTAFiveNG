-- Temporary instrumentation for the isolated development profile only.
local M = {}
local elapsed, last = 0, -1
local samples = {}
local controlledId
local vehicleState={}
local frameCount,frameTime=0,0
function M.recordVehicle(data) vehicleState=data end
local function onUpdate(dtReal, dtSim)
  elapsed = elapsed + dtReal
  if #samples >= 5 and #samples < 30 then frameCount=frameCount+1; frameTime=frameTime+dtReal end
  local v = be:getPlayerVehicle(0)
  if v then
    controlledId=v:getID()
    v:queueLuaCommand("for _,k in ipairs({'throttle','brake','parkingbrake','steering'}) do input.setAllowedInputSource(k,'lsf_test',true) end")
  end
  if v then
    local drive = #samples >= 8 and #samples < 13
    v:queueLuaCommand(string.format("input.event('throttle',%f,0,nil,nil,nil,'lsf_test'); input.event('brake',%f,0,nil,nil,nil,'lsf_test'); input.event('parkingbrake',%f,0,nil,nil,nil,'lsf_test'); input.event('steering',0,0,nil,nil,nil,'lsf_test')", drive and 0.25 or 0, drive and 0 or 1, drive and 0 or 1))
  end
  if #samples >= 30 then return end
  local second = math.floor(elapsed)
  if second == last then return end
  last = second
  if not v then return end
  local p = v:getPosition()
  local speed = v:getVelocity():length()
  local hit = castRayStatic(vec3(p.x,p.y,100),vec3(0,0,-1),200)
  v:queueLuaCommand("obj:queueGameEngineLua('extensions.lsf_validation.recordVehicle(' .. serialize({throttle=input.state.throttle.val,brake=input.state.brake.val,parkingbrake=input.state.parkingbrake.val,throttleOut=electrics.values.throttle,brakeOut=electrics.values.brake,parkingOut=electrics.values.parkingbrake,gear=electrics.values.gear}) .. ')')")
  table.insert(samples, {t=elapsed,position={p.x,p.y,p.z},speed=speed,groundZ=100-hit,controls=vehicleState})
  jsonWriteFile('lsf_validation.json', {level=getMissionFilename(),samples=samples,meanGameUpdateRate=frameTime>0 and frameCount/frameTime or 0,performanceNote='Game onUpdate calls per real second, including screenshot stalls; not a full-resolution rendering benchmark.'}, true)
  if #samples == 3 then v:queueLuaCommand("controller.mainController.setGearboxMode('realistic'); controller.mainController.shiftToGearIndex(2)") end
  if #samples == 5 then
    log('I','lsf_validation','Stationary vehicle sample recorded')
    require('screenshot').takeScreenShot()
  end
  if #samples == 13 then
    require('screenshot').takeScreenShot()
  end
end
M.onUpdate = onUpdate
return M
