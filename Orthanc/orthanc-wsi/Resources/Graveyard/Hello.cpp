
#include <stdint.h>
#include <boost/noncopyable.hpp>
#include <string>
#include <vector>
#include <json/reader.h>
#include <json/value.h>
#include <boost/thread/mutex.hpp>

#include "../../Framework/Inputs/DicomPyramid.h"
#include "../../Applications/ApplicationToolbox.h"
#include "../../Resources/Orthanc/Plugins/Samples/Common/OrthancHttpConnection.h"
#include "../../Resources/Orthanc/Plugins/Samples/Common/DicomDatasetReader.h"
#include "../../Resources/Orthanc/Plugins/Samples/Common/FullOrthancDataset.h"
#include "../../Resources/Orthanc/Plugins/Samples/Common/SimplifiedOrthancDataset.h"

#include <stdio.h>

namespace OrthancPlugins
{
  void Run()
  {
    OrthancHttpConnection orthanc;

#if 0
    //DicomDatasetReader reader(new SimplifiedOrthancDataset(orthanc, "/instances/2791b060-6ff103b3-8078bed0-5abbd75a-a5c675f7/tags?simplify"));
    DicomDatasetReader reader(new FullOrthancDataset(orthanc, "/instances/2791b060-6ff103b3-8078bed0-5abbd75a-a5c675f7/tags"));

    std::cout << reader.GetIntegerValue(DICOM_TAG_TOTAL_PIXEL_MATRIX_COLUMNS) << "x"
              << reader.GetIntegerValue(DICOM_TAG_TOTAL_PIXEL_MATRIX_ROWS) << std::endl;
    
    std::string s;
    printf("%d ", reader.GetDataset().GetStringValue(s, DICOM_TAG_SOP_CLASS_UID));
    printf("[%s]\n", s.c_str());

    size_t c;

    {
      DicomPath p(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE);
      printf("%d ", reader.GetDataset().GetSequenceSize(c, p));
      printf("%d\n", c);    
    }

    for (size_t i = 0; i < c; i++)
    {
      /*DicomPath p(DICOM_TAG_COLUMN_POSITION_IN_TOTAL_IMAGE_PIXEL_MATRIX);
        p.AddToPrefix(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE, i);
        p.AddToPrefix(DICOM_TAG_PLANE_POSITION_SLIDE_SEQUENCE, 0);

        std::string x, y;
        printf("%d %d ", i, reader.GetDataset().GetStringValue(x, p));
        p.SetFinalTag(DICOM_TAG_ROW_POSITION_IN_TOTAL_IMAGE_PIXEL_MATRIX);
        printf("%d ", reader.GetDataset().GetStringValue(y, p));
        printf("[%s,%s]\n", x.c_str(), y.c_str());*/
      
      std::cout << i << ": [" 
                << reader.GetMandatoryStringValue(
                  DicomPath(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE, i,
                            DICOM_TAG_PLANE_POSITION_SLIDE_SEQUENCE, 0,
                            DICOM_TAG_COLUMN_POSITION_IN_TOTAL_IMAGE_PIXEL_MATRIX)) << ","
                << reader.GetMandatoryStringValue(
                  DicomPath(DICOM_TAG_PER_FRAME_FUNCTIONAL_GROUPS_SEQUENCE, i,
                            DICOM_TAG_PLANE_POSITION_SLIDE_SEQUENCE, 0,
                            DICOM_TAG_ROW_POSITION_IN_TOTAL_IMAGE_PIXEL_MATRIX))
                << "]" << std::endl;
    }

#else
    OrthancWSI::DicomPyramid pyramid(orthanc, "09d0cca4-a8f0cd78-5480c690-ed14eb3b-a6614d14", true);
    //OrthancWSI::DicomPyramid pyramid(orthanc, "4fdff9b9-8b81bc8f-04a3f903-4d44bd57-cc3bf42c");
#endif
  }

}




int main()
{
  OrthancWSI::ApplicationToolbox::GlobalInitialize();
  OrthancPlugins::Run();
  OrthancWSI::ApplicationToolbox::GlobalFinalize();
  return 0;
}
