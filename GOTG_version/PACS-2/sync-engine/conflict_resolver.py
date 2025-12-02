#!/usr/bin/env python3
"""
GOTG PACS - Automatic Conflict Resolution
Handle sync conflicts when multiple sites modify same data
PRODUCTION-READY - No manual intervention needed
"""

import logging
import hashlib
from datetime import datetime
from pathlib import Path
import pydicom
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConflictResolver:
    """Automatically resolve sync conflicts"""
    
    # Conflict resolution strategies
    STRATEGIES = {
        'latest_wins': 'Use most recently modified version',
        'largest_wins': 'Use version with most data',
        'merge': 'Merge non-conflicting changes',
        'keep_both': 'Keep both versions with different IDs'
    }
    
    def __init__(self, strategy='latest_wins', conflict_dir=None):
        """
        Initialize conflict resolver
        
        Args:
            strategy: Resolution strategy
            conflict_dir: Directory to store conflict logs
        """
        self.strategy = strategy
        self.conflict_dir = Path(conflict_dir or '/app/conflicts')
        self.conflict_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'conflicts_failed': 0
        }
    
    def detect_conflict(self, local_file, remote_file):
        """
        Detect if two files are in conflict
        
        Args:
            local_file: Path to local file
            remote_file: Path to remote file
            
        Returns:
            bool: True if conflict detected
        """
        try:
            # Check if files are different
            local_hash = self._calculate_hash(local_file)
            remote_hash = self._calculate_hash(remote_file)
            
            if local_hash == remote_hash:
                return False  # Files are identical
            
            # Check modification times
            local_mtime = Path(local_file).stat().st_mtime
            remote_mtime = Path(remote_file).stat().st_mtime
            
            # If modified at different times, it's a conflict
            if abs(local_mtime - remote_mtime) > 1:  # 1 second tolerance
                logger.warning(f"Conflict detected: {Path(local_file).name}")
                self.stats['conflicts_detected'] += 1
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting conflict: {e}")
            return False
    
    def resolve_conflict(self, local_file, remote_file, metadata=None):
        """
        Resolve conflict between local and remote files
        
        Args:
            local_file: Path to local file
            remote_file: Path to remote file
            metadata: Optional metadata about the conflict
            
        Returns:
            Path: Path to resolved file
        """
        try:
            logger.info(f"Resolving conflict: {Path(local_file).name}")
            
            # Log conflict
            self._log_conflict(local_file, remote_file, metadata)
            
            # Apply resolution strategy
            if self.strategy == 'latest_wins':
                resolved = self._resolve_latest_wins(local_file, remote_file)
            elif self.strategy == 'largest_wins':
                resolved = self._resolve_largest_wins(local_file, remote_file)
            elif self.strategy == 'merge':
                resolved = self._resolve_merge(local_file, remote_file)
            elif self.strategy == 'keep_both':
                resolved = self._resolve_keep_both(local_file, remote_file)
            else:
                resolved = self._resolve_latest_wins(local_file, remote_file)
            
            self.stats['conflicts_resolved'] += 1
            logger.info(f"Conflict resolved: {Path(resolved).name}")
            
            return resolved
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            self.stats['conflicts_failed'] += 1
            # Return local file as fallback
            return local_file
    
    def _resolve_latest_wins(self, local_file, remote_file):
        """Use most recently modified version"""
        local_mtime = Path(local_file).stat().st_mtime
        remote_mtime = Path(remote_file).stat().st_mtime
        
        if remote_mtime > local_mtime:
            logger.info("Remote version is newer, using remote")
            return remote_file
        else:
            logger.info("Local version is newer, using local")
            return local_file
    
    def _resolve_largest_wins(self, local_file, remote_file):
        """Use version with most data"""
        local_size = Path(local_file).stat().st_size
        remote_size = Path(remote_file).stat().st_size
        
        if remote_size > local_size:
            logger.info("Remote version is larger, using remote")
            return remote_file
        else:
            logger.info("Local version is larger, using local")
            return local_file
    
    def _resolve_merge(self, local_file, remote_file):
        """
        Merge non-conflicting changes
        For DICOM files, this means merging metadata while keeping pixel data from newer version
        """
        try:
            # Read both files
            local_ds = pydicom.dcmread(local_file)
            remote_ds = pydicom.dcmread(remote_file)
            
            # Use pixel data from newer version
            local_mtime = Path(local_file).stat().st_mtime
            remote_mtime = Path(remote_file).stat().st_mtime
            
            if remote_mtime > local_mtime:
                merged_ds = remote_ds
                logger.info("Using remote pixel data (newer)")
            else:
                merged_ds = local_ds
                logger.info("Using local pixel data (newer)")
            
            # Merge metadata (prefer non-empty values)
            for elem in local_ds:
                tag = elem.tag
                if tag not in merged_ds or not merged_ds[tag].value:
                    merged_ds[tag] = elem
            
            # Save merged file
            merged_file = Path(local_file).with_suffix('.merged.dcm')
            merged_ds.save_as(merged_file)
            
            logger.info("Merged local and remote versions")
            return merged_file
            
        except Exception as e:
            logger.error(f"Merge failed: {e}, falling back to latest_wins")
            return self._resolve_latest_wins(local_file, remote_file)
    
    def _resolve_keep_both(self, local_file, remote_file):
        """
        Keep both versions with different identifiers
        Useful when both versions might be valid
        """
        try:
            # Read remote file
            remote_ds = pydicom.dcmread(remote_file)
            
            # Generate new SOPInstanceUID for remote version
            import pydicom.uid
            remote_ds.SOPInstanceUID = pydicom.uid.generate_uid()
            
            # Save with new UID
            kept_file = Path(local_file).with_name(
                f"{Path(local_file).stem}_remote{Path(local_file).suffix}"
            )
            remote_ds.save_as(kept_file)
            
            logger.info(f"Kept both versions: {local_file} and {kept_file}")
            
            # Return local file (keep original)
            return local_file
            
        except Exception as e:
            logger.error(f"Keep both failed: {e}, falling back to latest_wins")
            return self._resolve_latest_wins(local_file, remote_file)
    
    def _calculate_hash(self, file_path):
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _log_conflict(self, local_file, remote_file, metadata=None):
        """Log conflict for audit trail"""
        try:
            conflict_log = {
                'timestamp': datetime.now().isoformat(),
                'local_file': str(local_file),
                'remote_file': str(remote_file),
                'local_size': Path(local_file).stat().st_size,
                'remote_size': Path(remote_file).stat().st_size,
                'local_mtime': Path(local_file).stat().st_mtime,
                'remote_mtime': Path(remote_file).stat().st_mtime,
                'local_hash': self._calculate_hash(local_file),
                'remote_hash': self._calculate_hash(remote_file),
                'strategy': self.strategy,
                'metadata': metadata or {}
            }
            
            # Save log
            log_file = self.conflict_dir / f"conflict_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, 'w') as f:
                json.dump(conflict_log, f, indent=2)
            
            logger.info(f"Conflict logged to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log conflict: {e}")
    
    def get_stats(self):
        """Get conflict resolution statistics"""
        return self.stats
    
    def get_conflict_history(self, limit=100):
        """
        Get recent conflict history
        
        Args:
            limit: Maximum number of conflicts to return
            
        Returns:
            list: List of conflict logs
        """
        try:
            conflict_files = sorted(
                self.conflict_dir.glob('conflict_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )[:limit]
            
            conflicts = []
            for conflict_file in conflict_files:
                with open(conflict_file, 'r') as f:
                    conflicts.append(json.load(f))
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Failed to get conflict history: {e}")
            return []

def main():
    """CLI interface for conflict resolution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GOTG PACS Conflict Resolver')
    parser.add_argument('local', help='Local file')
    parser.add_argument('remote', help='Remote file')
    parser.add_argument('--strategy', 
                       choices=['latest_wins', 'largest_wins', 'merge', 'keep_both'],
                       default='latest_wins',
                       help='Resolution strategy')
    parser.add_argument('--conflict-dir', default='/app/conflicts',
                       help='Directory for conflict logs')
    
    args = parser.parse_args()
    
    resolver = ConflictResolver(strategy=args.strategy, conflict_dir=args.conflict_dir)
    
    # Check for conflict
    if resolver.detect_conflict(args.local, args.remote):
        print(f"Conflict detected between {args.local} and {args.remote}")
        
        # Resolve conflict
        resolved = resolver.resolve_conflict(args.local, args.remote)
        print(f"Resolved to: {resolved}")
        print(f"Strategy used: {args.strategy}")
    else:
        print("No conflict detected - files are identical or compatible")
    
    # Show stats
    stats = resolver.get_stats()
    print(f"\nStatistics:")
    print(f"  Conflicts detected: {stats['conflicts_detected']}")
    print(f"  Conflicts resolved: {stats['conflicts_resolved']}")
    print(f"  Conflicts failed: {stats['conflicts_failed']}")

if __name__ == '__main__':
    main()
