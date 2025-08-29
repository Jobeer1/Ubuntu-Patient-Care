function OnStoredInstance(instanceId, tags, metadata)
   Delete(SendToModality(instanceId, 'orthanctest'))
end
