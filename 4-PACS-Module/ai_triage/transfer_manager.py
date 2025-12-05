import logging
import heapq
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from audit_service import AuditService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransferPriority(Enum):
    CRITICAL = 0  # Highest priority (min heap)
    HIGH = 1
    NORMAL = 2
    LOW = 3

class TransferStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass(order=True)
class TransferItem:
    priority: int
    timestamp: float
    study_id: str = field(compare=False)
    instance_id: str = field(compare=False)
    instance_path: Optional[str] = field(compare=False, default=None)
    size_bytes: int = field(compare=False, default=0)
    retry_count: int = field(compare=False, default=0)

class TransferManager:
    """
    Manages the transfer of DICOM instances with priority queuing.
    Prioritizes critical slices identified by AI Triage.
    """

    def __init__(self, max_retries: int = 3, destination_peer: str = "cloud_pacs"):
        self.queue = []  # Priority Queue (heap)
        self.processing = {}  # Map of instance_id -> TransferItem
        self.completed = set() # Set of completed instance_ids
        self.failed = {} # Map of instance_id -> error_message
        self.study_sizes = {} # Map of study_id -> total_size_bytes
        self.max_retries = max_retries
        self.destination_peer = destination_peer
        self.is_running = False
        self.audit_service = AuditService()

    def queue_study(self, study_id: str, instances: List[Dict[str, Any]], triage_results: Dict[str, Any]):
        """
        Queues instances from a study based on triage results.
        
        Args:
            study_id: The StudyInstanceUID or Orthanc ID.
            instances: List of dicts containing {'id': str, 'instance_number': int, 'path': str}.
            triage_results: Dictionary returned by TriageEngine.
        """
        logger.info(f"Queueing study {study_id} for transfer")
        
        critical_numbers = set(triage_results.get('critical_slices', []))
        status = triage_results.get('status', 'normal')
        
        # Determine base priority for the study
        if status == 'critical':
            study_priority = TransferPriority.HIGH
        elif status == 'failed':
            # If AI failed, we might want to prioritize it to get human review, or treat as normal
            study_priority = TransferPriority.NORMAL
        else:
            study_priority = TransferPriority.LOW

        # Calculate total study size
        total_size = sum(inst.get('size', 0) for inst in instances)
        self.study_sizes[study_id] = total_size

        count = 0
        for inst in instances:
            inst_id = inst.get('id')
            inst_num = inst.get('instance_number')
            inst_path = inst.get('path')
            inst_size = inst.get('size', 0)
            
            if not inst_id:
                continue
                
            if inst_id in self.completed or inst_id in self.processing:
                continue

            # Determine priority for this instance
            if inst_num in critical_numbers:
                priority = TransferPriority.CRITICAL
            else:
                priority = study_priority

            # Create item
            item = TransferItem(
                priority=priority.value,
                timestamp=time.time(),
                study_id=study_id,
                instance_id=inst_id,
                instance_path=inst_path,
                size_bytes=inst_size
            )
            
            heapq.heappush(self.queue, item)
            count += 1
            
        logger.info(f"Queued {count} instances for study {study_id}")

    def request_full_study(self, study_id: str, instances: List[Dict[str, Any]]):
        """
        Manually requests immediate transfer of a full study.
        Elevates priority of all instances to HIGH.
        """
        logger.info(f"Manual request for full study {study_id}")
        
        # In a real implementation, we might need to find items already in queue and update them.
        # Heaps don't support efficient updates. 
        # Strategy: Add them again with higher priority. 
        # The processor needs to handle duplicates (check if already completed).
        
        for inst in instances:
            inst_id = inst.get('id')
            if inst_id in self.completed:
                continue
                
            item = TransferItem(
                priority=TransferPriority.HIGH.value,
                timestamp=time.time(),
                study_id=study_id,
                instance_id=inst_id,
                instance_path=inst.get('path')
            )
            heapq.heappush(self.queue, item)

    def process_queue(self, batch_size: int = 5):
        """
        Processes the top N items from the queue.
        """
        processed_count = 0
        
        while self.queue and processed_count < batch_size:
            item = heapq.heappop(self.queue)
            
            if item.instance_id in self.completed:
                continue
                
            # Check if we are already processing this ID (due to duplicate queuing)
            # If so, ignore this one (or maybe it's a retry?)
            # For simplicity, if it's in processing, skip.
            # But wait, processing map is for currently active transfers.
            
            self.processing[item.instance_id] = item
            
            try:
                success = self._execute_transfer(item)
                if success:
                    self.completed.add(item.instance_id)
                    del self.processing[item.instance_id]
                else:
                    self._handle_failure(item)
            except Exception as e:
                logger.error(f"Unexpected error transferring {item.instance_id}: {e}")
                self._handle_failure(item)
            
            processed_count += 1

        return processed_count

    def _execute_transfer(self, item: TransferItem) -> bool:
        """
        Executes the actual transfer.
        Mocked for now. In production, this would call Orthanc API.
        """
        logger.info(f"Transferring {item.instance_id} (Priority: {item.priority}) to {self.destination_peer}")
        
        # Simulate network delay
        # time.sleep(0.1)
        
        # Simulate random failure
        # if random.random() < 0.1:
        #     return False
            
        # Here we would use:
        # orthanc.RestApiPost(f'/peers/{self.destination_peer}/store', item.instance_id)
        
        # Log audit event
        total_size = self.study_sizes.get(item.study_id, 0)
        self.audit_service.log_transfer(
            study_instance_uid=item.study_id,
            total_size_bytes=total_size,
            transferred_size_bytes=item.size_bytes,
            priority=TransferPriority(item.priority).name
        )

        return True

    def _handle_failure(self, item: TransferItem):
        """
        Handles transfer failure with retry logic.
        """
        del self.processing[item.instance_id]
        
        if item.retry_count < self.max_retries:
            item.retry_count += 1
            # Backoff?
            # Re-queue with same priority (or lower?)
            # Let's keep priority but update timestamp to put it at back of same priority level
            item.timestamp = time.time()
            heapq.heappush(self.queue, item)
            logger.warning(f"Retrying {item.instance_id} (Attempt {item.retry_count})")
        else:
            self.failed[item.instance_id] = "Max retries exceeded"
            logger.error(f"Failed to transfer {item.instance_id} after {self.max_retries} attempts")

    def get_queue_status(self) -> Dict[str, int]:
        """Returns counts of items in queue by priority"""
        counts = {p.name: 0 for p in TransferPriority}
        for item in self.queue:
            # This is O(N), but queue shouldn't be massive in this context
            try:
                p_name = TransferPriority(item.priority).name
                counts[p_name] += 1
            except:
                pass
        return counts
