"""SDOH Timeline, ICS, and Export Helpers
=========================================
Mixin providing timeline management, calendar (.ics) export, and
Patient Passport generation for SDOHContinuityAgent.

All exports are local-first — nothing leaves the patient device unless
the patient explicitly approves the share.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


class SDOHTimelineMixin:

    def _recent_history_text(self, history):
        lines = []
        for msg in (history or [])[-8:]:
            role = 'Patient' if msg.get('role') == 'user' else 'Navigator'
            content = (msg.get('content') or '').strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _is_urgent(self, text):
        urgent_terms = [
            'chest pain', 'shortness of breath', 'stroke', 'severe bleeding',
            'fainting', 'confusion', 'seizure', 'unresponsive', 'emergency',
        ]
        text_lower = (text or '').lower()
        return any(term in text_lower for term in urgent_terms)

    def _classify_barrier(self, text):
        text_lower = (text or '').lower()
        if any(t in text_lower for t in ['ride', 'transport', 'car', 'lift', 'bus', 'taxi']):
            return 'transport'
        if any(t in text_lower for t in ['cost', 'money', 'afford', 'expensive', 'payment']):
            return 'financial'
        if any(t in text_lower for t in ['confused', 'overwhelmed', 'forget', 'memory']):
            return 'cognitive'
        if any(t in text_lower for t in ['wife', 'husband', 'family', 'caregiver', 'someone to go with', 'alone']):
            return 'social'
        if any(t in text_lower for t in ['offline', 'no signal', 'rural', 'internet', 'device']):
            return 'infrastructure'
        if any(t in text_lower for t in ['schedule', 'appointment', 'booking', 'reschedule']):
            return 'scheduling'
        return None

    def _severity_from_text(self, text):
        text_lower = (text or '').lower()
        if any(t in text_lower for t in ['suspected cancer', 'malignant', 'oncology', 'stroke', 'urgent', 'critical', 'biopsy', 'mass']):
            return 'critical'
        if any(t in text_lower for t in ['stat', 'same day', 'asap', 'within 48 hours', 'within 72 hours', 'follow-up pet', 'follow up pet']):
            return 'high'
        if any(t in text_lower for t in ['mri', 'ct', 'x-ray', 'ultrasound', 'moderate']):
            return 'moderate'
        return 'low'

    def _priority_from_severity(self, severity):
        return {
            'critical': 'critical',
            'high': 'high',
            'moderate': 'medium',
            'low': 'low',
        }.get(severity, 'low')

    def _build_timeline_item(self, label, status='upcoming', severity='low', barrier_type=None):
        return {
            'label': label,
            'status': status,
            'severity': severity,
            'priority': self._priority_from_severity(severity),
            'barrier_type': barrier_type,
        }

    def _clinician_continuity_summary(self, source_paragraph=None, extracted_task=None, barrier_type=None, severity='low'):
        parts = []
        if severity:
            parts.append(f'Severity {severity}')
        if barrier_type:
            parts.append(f'barrier={barrier_type}')
        if extracted_task:
            parts.append(f'task={extracted_task}')
        if source_paragraph:
            excerpt = source_paragraph[:180].replace('\n', ' ')
            parts.append(f'source="{excerpt}"')
        if not parts:
            parts.append('no structured continuity summary available')
        return 'Care continuity snapshot: ' + '; '.join(parts)

    def _apply_missed_window_reclamation(self, text, timeline_items, severity):
        text_lower = (text or '').lower()
        missed_terms = [
            'missed', 'no-show', 'no show', 'offline', 'woke the screen', 'woke up',
            'device was off', 'could not schedule', "couldn't schedule", 'lost reminder',
        ]
        triggered = any(term in text_lower for term in missed_terms)
        if severity in {'critical', 'high'} and triggered:
            reclaimed_items = []
            for item in timeline_items:
                reclaimed_items.append({
                    'label': item['label'],
                    'status': 'blocked' if item.get('status') == 'upcoming' else item.get('status', 'upcoming'),
                    'severity': item.get('severity', severity),
                    'priority': item.get('priority', self._priority_from_severity(severity)),
                    'barrier_type': item.get('barrier_type'),
                })
            return {
                'triggered': True,
                'message': (
                    'A high-risk follow-up appears to have been missed while the device or node was offline. '
                    'Reclaiming it now with priority.'
                ),
                'timeline_items': reclaimed_items,
            }
        return {'triggered': False, 'message': None, 'timeline_items': timeline_items}

    def _timeline_offset_hours(self, timeline_text, severity):
        timeline_lower = (timeline_text or '').lower()
        if 'today' in timeline_lower:
            return 6
        if 'tomorrow' in timeline_lower:
            return 24
        match = re.search(r'within\s+(\d+)\s+(hours|hour|days|day|weeks|week)', timeline_lower)
        if match:
            quantity = int(match.group(1))
            unit = match.group(2)
            if 'hour' in unit:
                return max(1, quantity)
            if 'day' in unit:
                return max(1, quantity * 24)
            if 'week' in unit:
                return max(1, quantity * 24 * 7)
        if severity == 'critical':
            return 12
        if severity == 'high':
            return 24 * 2
        if severity == 'moderate':
            return 24 * 7
        return 24 * 14

    def _ics_escape(self, text):
        value = text or ''
        return (
            value.replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\n', '\\n')
        )

    def _calendar_events_from_timeline(self, user_alias, timeline_items, source_paragraph=None,
                                        extracted_task=None, timeline=None, severity='low'):
        if not timeline_items:
            return []
        now = datetime.now(timezone.utc)
        offset_hours = self._timeline_offset_hours(timeline, severity)
        events = []
        for index, item in enumerate(timeline_items):
            due_at = now + timedelta(hours=offset_hours + index * 2)
            duration = timedelta(minutes=15)
            summary = item.get('label') or extracted_task or 'SDOH follow-up'
            description_parts = [
                f'Patient alias: {user_alias}',
                f'Severity: {item.get("severity", severity)}',
                f'Priority: {item.get("priority")}',
            ]
            if item.get('barrier_type'):
                description_parts.append(f'Barrier: {item["barrier_type"]}')
            if extracted_task:
                description_parts.append(f'Extracted task: {extracted_task}')
            if source_paragraph:
                description_parts.append(f'Source paragraph: {source_paragraph}')
            events.append({
                'uid': f'sdoh-{int(now.timestamp())}-{index}',
                'summary': summary,
                'description': '\n'.join(description_parts),
                'dtstamp': now.isoformat().replace('+00:00', 'Z'),
                'start': due_at.isoformat().replace('+00:00', 'Z'),
                'end': (due_at + duration).isoformat().replace('+00:00', 'Z'),
                'status': item.get('status', 'upcoming'),
                'severity': item.get('severity', severity),
                'priority': item.get('priority', self._priority_from_severity(severity)),
                'barrier_type': item.get('barrier_type'),
                'approved': True,
            })
        return events

    def _build_ics_content(self, calendar_events):
        if not calendar_events:
            return None

        def fmt(value):
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed.strftime('%Y%m%dT%H%M%SZ')

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//SDOH Continuity Agent//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
        ]
        for event in calendar_events:
            lines.extend([
                'BEGIN:VEVENT',
                f'UID:{self._ics_escape(event["uid"])}',
                f'DTSTAMP:{fmt(event["dtstamp"])}',
                f'DTSTART:{fmt(event["start"])}',
                f'DTEND:{fmt(event["end"])}',
                f'SUMMARY:{self._ics_escape(event["summary"])}',
                f'DESCRIPTION:{self._ics_escape(event["description"])}',
                f'STATUS:{self._ics_escape(str(event.get("status", "upcoming")).upper())}',
                'END:VEVENT',
            ])
        lines.append('END:VCALENDAR')
        return '\r\n'.join(lines) + '\r\n'

    def _build_patient_passport(self, user_alias, source_paragraph=None, extracted_task=None,
                                 timeline_items=None, barrier_type=None, severity='low',
                                 continuity_priority='low', clinician_summary=None):
        timeline_items = timeline_items or []
        lines = [
            '# PATIENT PASSPORT',
            '',
            f'- Patient alias: {user_alias}',
            f'- Severity: {severity}',
            f'- Continuity priority: {continuity_priority}',
        ]
        if barrier_type:
            lines.append(f'- Barrier classification: {barrier_type}')
        if extracted_task:
            lines.append(f'- Active recovery task: {extracted_task}')
        if clinician_summary:
            lines.append(f'- Clinician continuity summary: {clinician_summary}')
        lines.extend(['', '## Active Recovery Items'])
        if timeline_items:
            for item in timeline_items:
                lines.append(
                    f'- {item.get("label")} | status={item.get("status")} | '
                    f'severity={item.get("severity")} | priority={item.get("priority")}'
                )
        else:
            lines.append('- None')
        lines.extend(['', '## Source Traceability'])
        if source_paragraph:
            lines.append(f'- Source paragraph: {source_paragraph}')
        else:
            lines.append('- Source paragraph: none provided')
        lines.extend([
            '',
            '## Interoperability Notes',
            '- Barrier classification maps to FHIR Condition / Observation style SDOH tracking.',
            '- Active recovery items map to FHIR CarePlan and ServiceRequest concepts.',
            '- The markdown export is local-first and can be serialized into enterprise resources later.',
        ])
        return '\n'.join(lines) + '\n'

    def _build_export_bundle(self, user_alias, source_paragraph, extracted_task, timeline_items,
                              barrier_type, severity, continuity_priority, timeline=None,
                              verification_required=False, clinician_summary=None):
        if verification_required or not timeline_items:
            return {
                'export_ready': False,
                'calendar_events': [],
                'calendar_filename': None,
                'ics_content': None,
                'passport_filename': None,
                'passport_markdown': None,
                'schema_notes': None,
            }

        calendar_events = self._calendar_events_from_timeline(
            user_alias=user_alias,
            timeline_items=timeline_items,
            source_paragraph=source_paragraph,
            extracted_task=extracted_task,
            timeline=timeline,
            severity=severity,
        )
        passport_markdown = self._build_patient_passport(
            user_alias=user_alias,
            source_paragraph=source_paragraph,
            extracted_task=extracted_task,
            timeline_items=timeline_items,
            barrier_type=barrier_type,
            severity=severity,
            continuity_priority=continuity_priority,
            clinician_summary=clinician_summary,
        )
        ics_content = self._build_ics_content(calendar_events)
        schema_notes = '\n'.join([
            'Export schema notes:',
            '- timeline_items -> FHIR CarePlan/ServiceRequest style action tracking.',
            '- barrier_classification -> FHIR Observation / Condition style SDOH barrier tracking.',
            '- source_paragraph -> provenance traceability for the originating report or note.',
            '- PATIENT_PASSPORT.md stays local-first and can later be serialized into enterprise resources.',
        ]) + '\n'
        return {
            'export_ready': True,
            'calendar_events': calendar_events,
            'calendar_filename': 'sdoh-followups.ics',
            'ics_content': ics_content,
            'passport_filename': 'PATIENT_PASSPORT.md',
            'passport_markdown': passport_markdown,
            'schema_notes': schema_notes,
        }
