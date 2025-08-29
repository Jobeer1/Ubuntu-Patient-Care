#if 0
          /**
           * TODO - Decide which tags are safe (i.e. what is supposed to
           * be constant?)
           **/
          
          // Those tags are necessary for "DicomImageInformation" in
          // the Orthanc core (for Stone)
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_BITS_ALLOCATED);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_BITS_STORED);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_COLUMNS);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_HIGH_BIT);
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_NUMBER_OF_FRAMES);  // => Already in main DICOM tags
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_PHOTOMETRIC_INTERPRETATION);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_PIXEL_REPRESENTATION);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_PLANAR_CONFIGURATION);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_ROWS);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_SAMPLES_PER_PIXEL);

          // Those tags are necessary for "DicomInstanceParameters" in Stone
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_SOP_CLASS_UID);
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_WINDOW_CENTER);  // varies over each instance
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_WINDOW_WIDTH);  // varies over each instance
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_GRID_FRAME_OFFSET_VECTOR);  // TODO => probably unsafe!
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_FRAME_INCREMENT_POINTER);  // TODO => probably unsafe!
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_SLICE_THICKNESS);
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_IMAGE_POSITION_PATIENT);  // => Already in main DICOM tags
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_IMAGE_ORIENTATION_PATIENT);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_RESCALE_INTERCEPT);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_RESCALE_SLOPE);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_DOSE_GRID_SCALING);  // TODO => probably unsafe!

          // SeriesMetadataLoader
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_SOP_INSTANCE_UID);  // => Already in main DICOM tags
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_STUDY_INSTANCE_UID);  // => Already in main DICOM tags
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_SERIES_INSTANCE_UID);  // => Already in main DICOM tags
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_REFERENCED_SOP_INSTANCE_UID_IN_FILE);  // => Meaningless at series level

          // SeriesOrderedFrames
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_INSTANCE_NUMBER);  // => Already in main DICOM tags
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_IMAGE_INDEX);  // => Already in main DICOM tags

          // SeriesFramesLoader
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_SMALLEST_IMAGE_PIXEL_VALUE); => throws "Exception while invoking plugin service 23: Internal error" in Orthanc 
          //instances.MinorityReport(dicom, Orthanc::DICOM_TAG_LARGEST_IMAGE_PIXEL_VALUE);  // varies over each instance
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_REFERENCED_FILE_ID);
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_PATIENT_ID);

          // GeometryToolbox
          instances.MinorityReport(dicom, Orthanc::DICOM_TAG_PIXEL_SPACING);
#endif
