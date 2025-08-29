=========================
Source of the test images
=========================

------
OsiriX
------

Many of the images that are used by the integration tests of Orthanc
come from the OsiriX samples available at:
http://www.osirix-viewer.com/datasets/

WARNING: The datasets from OsiriX are exclusively available for
research and teaching! You are not authorized to redistribute or sell
them, or use them for commercial purposes.


----
GDCM
----

Some images were collected by the GDCM project. They can be downloaded
courtesy of Jean-Pierre Roux at the following URL:
http://www.creatis.insa-lyon.fr/~jpr/PUBLIC/gdcm/gdcmSampleData


---------------
Sébastien Barré
---------------

Some images are provided courtesy of Sébastien Barré:
http://www.barre.nom.fr/medical/samples/


---------------------------
NEMA - DICOM working groups
---------------------------

Some images come from the sample images of DICOM WG04:
ftp://medical.nema.org/medical/Dicom/DataSets/WG04/


---------------------------------
The Cancer Imaging Archive (TCIA)
---------------------------------

Some images come from the "TCGA-GBM" data collection:
https://wiki.cancerimagingarchive.net/display/Public/TCGA-GBM

Scarpace, L., Mikkelsen, T., Cha, S., Rao, S., Tekchandani, S.,
Gutman, D., Saltz, J. H., Erickson, B. J., Pedano, N., Flanders,
A. E., Barnholtz-Sloan, J., Ostrom, Q., Barboriak, D., & Pierce,
L. J. (2016). Radiology Data from The Cancer Genome Atlas Glioblastoma
Multiforme [TCGA-GBM] collection [Data set]. The Cancer Imaging
Archive. https://doi.org/10.7937/K9/TCIA.2016.RNYFUYE9


-------------
Other sources
-------------

Other images were publicly posted by external contributors to the
Orthanc project, or were generated manually by the Orthanc team.


-------
Content
-------

Here is the source of each set of sample images:

- 2020-09-12-ELSCINT1-PMSCT_RLE1.dcm: Anonymized from https://discourse.slicer.org/t/fail-to-load-pet-ct-gemini/8158
- 2020-11-16-SalimKanounAnonymization.dcm: From https://groups.google.com/g/orthanc-users/c/T0IokiActrI/m/L9K0vfscAAAJ
- Beaufix/* : From OsiriX, "BEAUFIX" (sample of JPEG2000).
- Brainix/* : From OsiriX, "BRAINIX" (sample of uncompressed data).
- ColorTestImageJ.dcm : From ImageJ, http://imagej.nih.gov/ij/images/cardio.dcm
- ColorTestMalaterre.dcm : From Mathieu Malaterre <mathieu.malaterre@gmail.com>, Debian bug #698417
- Comunix/* : From OsiriX, "COMUNIX" (sample of PET/CT study).
- DicomSeg.dcm : From TCIA, "TCGA-GBM" collection, "TCGA-08-0360" patient.
- DummyCT.dcm : From Osirix, "KNIX" with PixelData removed.
- HierarchicalAnonymization/RTH/* : From https://wiki.cancerimagingarchive.net/display/Public/Lung+CT+Segmentation+Challenge+2017
- HierarchicalAnonymization/StructuredReports/* : Courtesy of Collective Minds Radiology AB
- Issue16.dcm : From Chris Hafey on Google Code (AT VR's are not returned properly as JSON)
- Issue19.dcm : From Chris Hafey on Google Code (YBR_FULL are not decoded incorrectly)
- Issue22.dcm : From Emsy Chan on Google Code (Error decoding multi-frame instances)
- Issue32.dcm : From aceberg93 on Google Code (Cyrillic symbols)
- KarstenHilbertRF.dcm : From Karsten Hilbert <karsten.hilbert@gmx.net>.
- Knee/* : From OsiriX, "KNEE" (sample of JPEG2000).
- Knix/* : From OsiriX, "KNIX" (sample of lossless JPEG).
- Lena.png : Lena/Lenna test image (as downloaded from Wikipedia). MD5 = 814a0034f5549e957ee61360d87457e5
- LenaTwiceWithFragments.dcm: One image with 2 JPEG frames containing Lena (from Orthanc)
- MarekLatin2.dcm : From Marek Święcicki <mswiecicki@archimedic.pl>.
- Multiframe.dcm : From GDCM, "images_of_interest/PHILIPS_Integris_H-8-MONO2-Multiframe.dcm"
- Phenix/* : From OsiriX, "PHENIX" (sample of uncompressed data).
- PilatesArgenturGEUltrasoundOsiriX.dcm: From https://groups.google.com/d/msg/orthanc-users/m3zQLyl_jNc/TUrR462UKSMJ
- PNG16RGBATest.png : From http://www.schaik.com/pngsuite/#basic, License http://www.schaik.com/pngsuite/PngSuite.LICENSE
- PrivateMDNTags.dcm : From University Hospital of Liege
- PrivateTags.dcm : From GDCM, "images_of_interest/494APG9K.dcm"
- SignedCT.dcm : From Sébastien Jodogne.
- TransferSyntaxes/1.2.840.10008.1.2.1.dcm : From Sébastien Barré (US-RGB-8-esopecho)
- TransferSyntaxes/1.2.840.10008.1.2.2.dcm : From Sébastien Barré (US-RGB-8-epicard)
- TransferSyntaxes/1.2.840.10008.1.2.4.50.dcm : From GDCM, "US_DataSet/Philips_US/3EAF5680_8b_YBR_jpeg.dcm"
- TransferSyntaxes/1.2.840.10008.1.2.4.51.dcm : From DICOM WG04 (IMAGES/JPLY/MG1_JPLY)
- TransferSyntaxes/1.2.840.10008.1.2.4.57.dcm : From Sébastien Barré (MR-MONO2-12-shoulder)
- TransferSyntaxes/1.2.840.10008.1.2.4.70.dcm : From Sébastien Barré (CT-MONO2-16-chest)
- TransferSyntaxes/1.2.840.10008.1.2.4.80.dcm : From DICOM WG04 (IMAGES/JLSL/NM1_JLSL)
- TransferSyntaxes/1.2.840.10008.1.2.4.81.dcm : From DICOM WG04 (IMAGES/JLSN/CT2_JLSN)
- TransferSyntaxes/1.2.840.10008.1.2.4.90.dcm : From DICOM WG04 (IMAGES/J2KR/NM1_J2KR)
- TransferSyntaxes/1.2.840.10008.1.2.4.91.dcm : From DICOM WG04 (IMAGES/J2KI/CT1_J2KI)
- TransferSyntaxes/1.2.840.10008.1.2.5.dcm : From DICOM WG04 (IMAGES/RLE/NM1_RLE)
- TransferSyntaxes/1.2.840.10008.1.2.dcm : From Sébastien Barré (MR-MONO2-12-an2)
- UnknownSopClassUid.dcm : Same as "ColorTestMalaterre.dcm", with arbitrary SOP class UID.

Sample images that are not listed above, were submitted by Orthanc
users, either in the "Orthanc Users" public discussion group or in the
Orthanc bug tracker.
