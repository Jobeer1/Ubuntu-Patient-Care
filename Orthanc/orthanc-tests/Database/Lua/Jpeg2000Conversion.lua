-- https://groups.google.com/d/msg/orthanc-users/Rc-Beb42xc8/JUgdzrmCAgAJ

function OnStoredInstance(instanceId, tags, metadata, origin)
   -- Do not compress twice the same file
   if origin['RequestOrigin'] ~= 'Lua' then

      -- Retrieve the incoming DICOM instance from Orthanc
      local dicom = RestApiGet('/instances/' .. instanceId .. '/file')

      -- Write the DICOM content to some temporary file
      local uncompressed = '/tmp/uncompressed-' .. instanceId .. '.dcm'
      local target = assert(io.open(uncompressed, 'wb'))
      target:write(dicom)
      target:close()

      -- Compress to JPEG2000 using gdcm
      local compressed = '/tmp/compressed-' .. instanceId .. '.dcm'
      os.execute('gdcmconv -U --j2k ' .. uncompressed .. ' ' .. compressed)

      -- Generate a new SOPInstanceUID for the JPEG2000 file, as
      -- gdcmconv does not do this by itself
      os.execute('dcmodify --no-backup -m "SOPInstanceUID=' ..
                    tags['SOPInstanceUID'] .. '" ' .. compressed)

      local source = assert(io.open(compressed, 'rb'))
      local jpeg2k = source:read("*all")
      source:close()

      -- Upload the JPEG2000 file and remove the uncompressed file
      RestApiDelete('/instances/' .. instanceId)
      RestApiPost('/instances', jpeg2k)
      
      -- Remove the temporary DICOM files
      os.remove(uncompressed)
      os.remove(compressed)
   end
end
