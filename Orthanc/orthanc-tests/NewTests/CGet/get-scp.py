import os

from pydicom import dcmread
from pydicom.dataset import Dataset

from pydicom.uid import ImplicitVRLittleEndian, ExplicitVRLittleEndian
from pynetdicom import AE, StoragePresentationContexts, evt, AllStoragePresentationContexts
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelGet, StudyRootQueryRetrieveInformationModelGet, MRImageStorage, CTImageStorage

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def transform_to_transfer_syntax(dataset, target_transfer_syntax):
    # Create a new dataset with the new transfer syntax
    new_dataset = Dataset()
    new_dataset.file_meta = Dataset()
    new_dataset.file_meta.TransferSyntaxUID = target_transfer_syntax
    new_dataset.update(dataset)
    return new_dataset

# Implement the handler for evt.EVT_C_GET
def handle_get(event):
    """Handle a C-GET request event."""
    ds = event.identifier
    if 'QueryRetrieveLevel' not in ds:
        # Failure
        yield 0xC000, None
        return

    # Import stored SOP Instances
    instances = []
    matching = []
    fdir = '/home/alain/o/orthanc-tests/Database/Brainix/Epi'
    for fpath in os.listdir(fdir):
        instances.append(dcmread(os.path.join(fdir, fpath)))

    if ds.QueryRetrieveLevel == 'PATIENT':
        if 'PatientID' in ds:
            matching = [
                inst for inst in instances if inst.PatientID == ds.PatientID
            ]
    elif ds.QueryRetrieveLevel == 'STUDY':
        if 'StudyInstanceUID' in ds:
            matching = [
                inst for inst in instances if inst.StudyInstanceUID == ds.StudyInstanceUID
            ]

    print(f"GET-SCP: instances to send: {len(instances)}")
    # Yield the total number of C-STORE sub-operations required
    yield len(instances)

    # Yield the matching instances
    for instance in matching:
        # Check if C-CANCEL has been received
        if event.is_cancelled:
            yield (0xFE00, None)
            return

        # Pending
        accepted_transfer_syntax = event.assoc.accepted_contexts[0].transfer_syntax

        if accepted_transfer_syntax != instance.file_meta.TransferSyntaxUID:
            transformed_instance = transform_to_transfer_syntax(instance, accepted_transfer_syntax)
            yield (0xFF00, transformed_instance)
        else:
            yield (0xFF00, instance)
        

handlers = [(evt.EVT_C_GET, handle_get)]

# Create application entity
ae = AE("PYNETDICOM")

accepted_transfer_syntaxes = [
    '1.2.840.10008.1.2',  # Implicit VR Little Endian
    '1.2.840.10008.1.2.1',  # Explicit VR Little Endian
    '1.2.840.10008.1.2.2',  # Explicit VR Big Endian
    '1.2.840.10008.1.2.4.50',  # JPEG Baseline (Process 1)
    '1.2.840.10008.1.2.4.70',  # JPEG Lossless, Non-Hierarchical (Process 14)
]

# # Add the supported presentation contexts (Storage SCU)
# ae.supported_contexts = StoragePresentationContexts

# # Accept the association requestor's proposed SCP role in the
# #   SCP/SCU Role Selection Negotiation items
# for cx in ae.supported_contexts:
#     cx.scp_role = True
#     cx.scu_role = False

# # Add a supported presentation context (QR Get SCP)
ae.add_supported_context(PatientRootQueryRetrieveInformationModelGet)
ae.add_supported_context(StudyRootQueryRetrieveInformationModelGet)
# ae.add_supported_context(MRImageStorage, accepted_transfer_syntaxes, scu_role=True, scp_role=True)
# ae.add_supported_context(CTImageStorage, accepted_transfer_syntaxes, scu_role=True, scp_role=True)


for context in AllStoragePresentationContexts:
    ae.add_supported_context(context.abstract_syntax, ImplicitVRLittleEndian)

# Start listening for incoming association requests
ae.start_server(("0.0.0.0", 11112), evt_handlers=handlers)