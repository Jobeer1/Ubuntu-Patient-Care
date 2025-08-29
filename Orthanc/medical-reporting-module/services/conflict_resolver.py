"""
Conflict Resolver for Medical Reporting Module
Handles data conflicts during synchronization
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import json
import difflib

from config.offline_config import OfflineConfig

logger = logging.getLogger(__name__)

class ConflictType(Enum):
    """Types of data conflicts"""
    CONTENT_MODIFIED = "content_modified"
    STATUS_CHANGED = "status_changed"
    METADATA_UPDATED = "metadata_updated"
    TEMPLATE_CHANGED = "template_changed"
    LAYOUT_MODIFIED = "layout_modified"
    VOICE_DATA_CONFLICT = "voice_data_conflict"

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    USE_LOCAL = "use_local"
    USE_REMOTE = "use_remote"
    MERGE = "merge"
    USER_PROMPT = "user_prompt"
    SKIP = "skip"

class ConflictResolver:
    """Resolves data conflicts during synchronization"""
    
    def __init__(self):
        self.config = OfflineConfig()
        self.resolution_strategy = self.config.CONFLICT_RESOLUTION_STRATEGY
        self.auto_resolve_minor = self.config.AUTO_RESOLVE_MINOR_CONFLICTS
        
        # Conflict resolution handlers
        self._handlers = {
            ConflictType.CONTENT_MODIFIED: self._resolve_content_conflict,
            ConflictType.STATUS_CHANGED: self._resolve_status_conflict,
            ConflictType.METADATA_UPDATED: self._resolve_metadata_conflict,
            ConflictType.TEMPLATE_CHANGED: self._resolve_template_conflict,
            ConflictType.LAYOUT_MODIFIED: self._resolve_layout_conflict,
            ConflictType.VOICE_DATA_CONFLICT: self._resolve_voice_conflict
        }
    
    def detect_conflicts(self, local_data: Dict[str, Any], 
                        remote_data: Dict[str, Any], 
                        data_type: str) -> List[Dict[str, Any]]:
        """Detect conflicts between local and remote data"""
        conflicts = []
        
        try:
            # Check modification timestamps
            local_modified = self._parse_timestamp(local_data.get('modified_at'))
            remote_modified = self._parse_timestamp(remote_data.get('modified_at'))
            
            if not local_modified or not remote_modified:
                logger.warning("Missing modification timestamps, cannot detect conflicts")
                return conflicts
            
            # If remote is newer, check for conflicts
            if remote_modified > local_modified:
                conflicts.extend(self._detect_specific_conflicts(local_data, remote_data, data_type))
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Failed to detect conflicts: {e}")
            return []
    
    def _detect_specific_conflicts(self, local_data: Dict[str, Any], 
                                 remote_data: Dict[str, Any], 
                                 data_type: str) -> List[Dict[str, Any]]:
        """Detect specific types of conflicts"""
        conflicts = []
        
        if data_type == 'report':
            conflicts.extend(self._detect_report_conflicts(local_data, remote_data))
        elif data_type == 'template':
            conflicts.extend(self._detect_template_conflicts(local_data, remote_data))
        elif data_type == 'layout':
            conflicts.extend(self._detect_layout_conflicts(local_data, remote_data))
        elif data_type == 'voice_session':
            conflicts.extend(self._detect_voice_conflicts(local_data, remote_data))
        
        return conflicts
    
    def _detect_report_conflicts(self, local_data: Dict[str, Any], 
                               remote_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect conflicts in report data"""
        conflicts = []
        
        # Check content changes
        local_content = local_data.get('content', {})
        remote_content = remote_data.get('content', {})
        
        if local_content != remote_content:
            conflicts.append({
                'type': ConflictType.CONTENT_MODIFIED,
                'field': 'content',
                'local_value': local_content,
                'remote_value': remote_content,
                'severity': 'high'
            })
        
        # Check status changes
        local_status = local_data.get('status')
        remote_status = remote_data.get('status')
        
        if local_status != remote_status:
            conflicts.append({
                'type': ConflictType.STATUS_CHANGED,
                'field': 'status',
                'local_value': local_status,
                'remote_value': remote_status,
                'severity': 'medium'
            })
        
        # Check metadata changes
        local_metadata = local_data.get('metadata', {})
        remote_metadata = remote_data.get('metadata', {})
        
        if local_metadata != remote_metadata:
            conflicts.append({
                'type': ConflictType.METADATA_UPDATED,
                'field': 'metadata',
                'local_value': local_metadata,
                'remote_value': remote_metadata,
                'severity': 'low'
            })
        
        return conflicts
    
    def _detect_template_conflicts(self, local_data: Dict[str, Any], 
                                 remote_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect conflicts in template data"""
        conflicts = []
        
        # Check template structure changes
        local_structure = local_data.get('structure', {})
        remote_structure = remote_data.get('structure', {})
        
        if local_structure != remote_structure:
            conflicts.append({
                'type': ConflictType.TEMPLATE_CHANGED,
                'field': 'structure',
                'local_value': local_structure,
                'remote_value': remote_structure,
                'severity': 'high'
            })
        
        return conflicts
    
    def _detect_layout_conflicts(self, local_data: Dict[str, Any], 
                               remote_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect conflicts in layout data"""
        conflicts = []
        
        # Check layout configuration changes
        local_config = local_data.get('configuration', {})
        remote_config = remote_data.get('configuration', {})
        
        if local_config != remote_config:
            conflicts.append({
                'type': ConflictType.LAYOUT_MODIFIED,
                'field': 'configuration',
                'local_value': local_config,
                'remote_value': remote_config,
                'severity': 'medium'
            })
        
        return conflicts
    
    def _detect_voice_conflicts(self, local_data: Dict[str, Any], 
                              remote_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect conflicts in voice session data"""
        conflicts = []
        
        # Check transcription differences
        local_transcription = local_data.get('transcription', '')
        remote_transcription = remote_data.get('transcription', '')
        
        if local_transcription != remote_transcription:
            conflicts.append({
                'type': ConflictType.VOICE_DATA_CONFLICT,
                'field': 'transcription',
                'local_value': local_transcription,
                'remote_value': remote_transcription,
                'severity': 'high'
            })
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: List[Dict[str, Any]], 
                         local_data: Dict[str, Any], 
                         remote_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Resolve detected conflicts"""
        resolved_data = local_data.copy()
        resolution_log = []
        
        try:
            for conflict in conflicts:
                conflict_type = conflict['type']
                
                if conflict_type in self._handlers:
                    resolution, log_message = self._handlers[conflict_type](
                        conflict, local_data, remote_data
                    )
                    
                    if resolution == ConflictResolution.USE_REMOTE:
                        resolved_data[conflict['field']] = conflict['remote_value']
                        resolution_log.append(f"Used remote value for {conflict['field']}: {log_message}")
                    
                    elif resolution == ConflictResolution.USE_LOCAL:
                        # Keep local value (no change needed)
                        resolution_log.append(f"Kept local value for {conflict['field']}: {log_message}")
                    
                    elif resolution == ConflictResolution.MERGE:
                        merged_value = self._merge_values(
                            conflict['local_value'], 
                            conflict['remote_value'], 
                            conflict['field']
                        )
                        resolved_data[conflict['field']] = merged_value
                        resolution_log.append(f"Merged values for {conflict['field']}: {log_message}")
                    
                    elif resolution == ConflictResolution.USER_PROMPT:
                        # For now, default to local value and log for user review
                        resolution_log.append(f"User review required for {conflict['field']}: {log_message}")
                    
                    elif resolution == ConflictResolution.SKIP:
                        resolution_log.append(f"Skipped conflict for {conflict['field']}: {log_message}")
                
                else:
                    logger.warning(f"No handler for conflict type: {conflict_type}")
                    resolution_log.append(f"No handler for conflict type: {conflict_type}")
            
            return resolved_data, resolution_log
            
        except Exception as e:
            logger.error(f"Failed to resolve conflicts: {e}")
            return local_data, [f"Error resolving conflicts: {str(e)}"]
    
    def _resolve_content_conflict(self, conflict: Dict[str, Any], 
                                local_data: Dict[str, Any], 
                                remote_data: Dict[str, Any]) -> Tuple[ConflictResolution, str]:
        """Resolve content modification conflicts"""
        local_content = conflict['local_value']
        remote_content = conflict['remote_value']
        
        # Check if changes are minor (whitespace, formatting)
        if self.auto_resolve_minor and self._is_minor_content_change(local_content, remote_content):
            return ConflictResolution.MERGE, "Minor content changes merged automatically"
        
        # Check if one is empty (likely new content)
        if not local_content and remote_content:
            return ConflictResolution.USE_REMOTE, "Local content empty, using remote"
        
        if local_content and not remote_content:
            return ConflictResolution.USE_LOCAL, "Remote content empty, keeping local"
        
        # For significant content changes, use configured strategy
        if self.resolution_strategy == 'latest_wins':
            return ConflictResolution.USE_REMOTE, "Using latest (remote) content"
        elif self.resolution_strategy == 'merge':
            return ConflictResolution.MERGE, "Attempting to merge content changes"
        else:
            return ConflictResolution.USER_PROMPT, "Significant content changes require user review"
    
    def _resolve_status_conflict(self, conflict: Dict[str, Any], 
                               local_data: Dict[str, Any], 
                               remote_data: Dict[str, Any]) -> Tuple[ConflictResolution, str]:
        """Resolve status change conflicts"""
        local_status = conflict['local_value']
        remote_status = conflict['remote_value']
        
        # Status progression rules
        status_priority = {
            'draft': 1,
            'in_review': 2,
            'reviewed': 3,
            'final': 4,
            'signed': 5
        }
        
        local_priority = status_priority.get(local_status, 0)
        remote_priority = status_priority.get(remote_status, 0)
        
        # Use higher priority status
        if remote_priority > local_priority:
            return ConflictResolution.USE_REMOTE, f"Remote status '{remote_status}' has higher priority"
        elif local_priority > remote_priority:
            return ConflictResolution.USE_LOCAL, f"Local status '{local_status}' has higher priority"
        else:
            return ConflictResolution.USE_REMOTE, "Same priority, using remote status"
    
    def _resolve_metadata_conflict(self, conflict: Dict[str, Any], 
                                 local_data: Dict[str, Any], 
                                 remote_data: Dict[str, Any]) -> Tuple[ConflictResolution, str]:
        """Resolve metadata conflicts"""
        # Metadata conflicts are usually minor, merge them
        return ConflictResolution.MERGE, "Merging metadata changes"
    
    def _resolve_template_conflict(self, conflict: Dict[str, Any], 
                                 local_data: Dict[str, Any], 
                                 remote_data: Dict[str, Any]) -> Tuple[ConflictResolution, str]:
        """Resolve template conflicts"""
        # Template changes are significant, require user review
        return ConflictResolution.USER_PROMPT, "Template structure changes require user review"
    
    def _resolve_layout_conflict(self, conflict: Dict[str, Any], 
                               local_data: Dict[str, Any], 
                               remote_data: Dict[str, Any]) -> Tuple[ConflictResolution, str]:
        """Resolve layout conflicts"""
        # Layout changes are user-specific, prefer local
        return ConflictResolution.USE_LOCAL, "Layout changes are user-specific, keeping local"
    
    def _resolve_voice_conflict(self, conflict: Dict[str, Any], 
                              local_data: Dict[str, Any], 
                              remote_data: Dict[str, Any]) -> Tuple[ConflictResolution, str]:
        """Resolve voice data conflicts"""
        # Voice transcription conflicts need user review
        return ConflictResolution.USER_PROMPT, "Voice transcription differences require user review"
    
    def _is_minor_content_change(self, local_content: Any, remote_content: Any) -> bool:
        """Check if content changes are minor (whitespace, formatting)"""
        try:
            if isinstance(local_content, dict) and isinstance(remote_content, dict):
                # For structured content, check if only formatting differs
                local_text = json.dumps(local_content, sort_keys=True)
                remote_text = json.dumps(remote_content, sort_keys=True)
            else:
                local_text = str(local_content)
                remote_text = str(remote_content)
            
            # Remove whitespace and compare
            local_normalized = ''.join(local_text.split())
            remote_normalized = ''.join(remote_text.split())
            
            return local_normalized == remote_normalized
            
        except Exception as e:
            logger.error(f"Failed to check minor content change: {e}")
            return False
    
    def _merge_values(self, local_value: Any, remote_value: Any, field: str) -> Any:
        """Merge local and remote values"""
        try:
            if isinstance(local_value, dict) and isinstance(remote_value, dict):
                # Merge dictionaries
                merged = local_value.copy()
                for key, value in remote_value.items():
                    if key not in merged:
                        merged[key] = value
                    elif merged[key] != value:
                        # For nested conflicts, prefer remote
                        merged[key] = value
                return merged
            
            elif isinstance(local_value, list) and isinstance(remote_value, list):
                # Merge lists (remove duplicates)
                merged = local_value.copy()
                for item in remote_value:
                    if item not in merged:
                        merged.append(item)
                return merged
            
            elif isinstance(local_value, str) and isinstance(remote_value, str):
                # For text, try to merge using diff
                return self._merge_text(local_value, remote_value)
            
            else:
                # For other types, prefer remote
                return remote_value
                
        except Exception as e:
            logger.error(f"Failed to merge values: {e}")
            return remote_value
    
    def _merge_text(self, local_text: str, remote_text: str) -> str:
        """Merge text content using diff algorithm"""
        try:
            # Simple merge: if texts are similar, combine them
            local_lines = local_text.splitlines()
            remote_lines = remote_text.splitlines()
            
            # Use difflib to find common and different parts
            differ = difflib.unified_diff(local_lines, remote_lines, lineterm='')
            diff_lines = list(differ)
            
            # If diff is small, try to merge
            if len(diff_lines) < 10:  # Arbitrary threshold
                merged_lines = []
                for line in difflib.ndiff(local_lines, remote_lines):
                    if line.startswith('  '):  # Common line
                        merged_lines.append(line[2:])
                    elif line.startswith('+ '):  # Added in remote
                        merged_lines.append(line[2:])
                    elif line.startswith('- '):  # Removed in remote
                        # Skip removed lines for now
                        pass
                
                return '\n'.join(merged_lines)
            else:
                # Too many differences, return remote
                return remote_text
                
        except Exception as e:
            logger.error(f"Failed to merge text: {e}")
            return remote_text
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None
        
        try:
            # Try different timestamp formats
            formats = [
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse timestamp: {e}")
            return None
    
    def get_conflict_summary(self, conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of conflicts"""
        if not conflicts:
            return {'total': 0, 'by_type': {}, 'by_severity': {}}
        
        by_type = {}
        by_severity = {}
        
        for conflict in conflicts:
            conflict_type = conflict['type'].value
            severity = conflict.get('severity', 'unknown')
            
            by_type[conflict_type] = by_type.get(conflict_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            'total': len(conflicts),
            'by_type': by_type,
            'by_severity': by_severity
        }