function OnStoredInstance(instanceId, tags, metadata, origin)
   -- The "origin" is only available since Orthanc 0.9.4
   PrintRecursive(origin)

   -- Extract the value of the "PatientName" DICOM tag
   local patientName = string.lower(tags['PatientName'])

   if string.find(patientName, 'knee') ~= nil then
      -- Only send patients whose name contains "Knee"
      Delete(SendToModality(instanceId, 'orthanctest'))

   else
      -- Delete the patients that are not called "Knee"
      Delete(instanceId)
   end
end
