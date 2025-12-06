import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

class AuditService:
    """
    Service to log audit events, specifically tracking bandwidth savings.
    """

    def __init__(self, log_file: str = "audit.log"):
        self.logger = logging.getLogger("AuditService")
        self.logger.setLevel(logging.INFO)
        
        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_transfer(self, study_instance_uid: str, total_size_bytes: int, transferred_size_bytes: int, priority: str):
        """
        Log a transfer event with bandwidth saving metrics.
        """
        savings_bytes = total_size_bytes - transferred_size_bytes
        savings_percent = (savings_bytes / total_size_bytes * 100) if total_size_bytes > 0 else 0

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "TRANSFER_COMPLETE",
            "study_uid": study_instance_uid,
            "priority": priority,
            "metrics": {
                "total_size_bytes": total_size_bytes,
                "transferred_size_bytes": transferred_size_bytes,
                "savings_bytes": savings_bytes,
                "savings_percent": round(savings_percent, 2)
            }
        }

        self.logger.info(json.dumps(event))

    def get_stats(self) -> Dict[str, Any]:
        """
        Parses the log file to calculate aggregate statistics.
        (In a real production system, this would query a DB)
        """
        total_saved = 0
        total_original = 0
        count = 0

        # This is a naive implementation for the prototype. 
        # For high volume, we would use a database.
        log_path = self.logger.handlers[0].baseFilename
        if not os.path.exists(log_path):
             return {"count": 0, "total_saved_mb": 0, "total_original_mb": 0}

        with open(log_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("event_type") == "TRANSFER_COMPLETE":
                        metrics = data.get("metrics", {})
                        total_saved += metrics.get("savings_bytes", 0)
                        total_original += metrics.get("total_size_bytes", 0)
                        count += 1
                except json.JSONDecodeError:
                    continue
        
        return {
            "count": count,
            "total_saved_mb": round(total_saved / (1024 * 1024), 2),
            "total_original_mb": round(total_original / (1024 * 1024), 2)
        }
