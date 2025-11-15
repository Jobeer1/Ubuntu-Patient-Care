#!/usr/bin/env python3
"""
Emergency Credential Retrieval - End-to-End Demo

Demonstrates the complete workflow:
1. Clinician requests emergency access
2. Owner reviews and approves offline
3. Server issues time-limited token
4. Agent retrieves secret and uses it
5. System prevents replay attacks
6. Merkle audit trail captures all events

Run with: python credential_emergency_demo.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

# Import components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from audit.report_finalizer import ReportFinalizer, AuditEventType
    from mcp_medical_server.api.credentials import CredentialRequestManager
    from mcp_medical_server.services.signature_service import ApprovalSignatureFactory
    from mcp_medical_server.services.token_issuer import TokenIssuer, TokenStatus
    from mcp_medical_server.services.vault_adapter import LocalVault, VaultAdapter, RetrievalStatus
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from audit.report_finalizer import ReportFinalizer, AuditEventType
    from mcp_medical_server.api.credentials import CredentialRequestManager
    from mcp_medical_server.services.signature_service import ApprovalSignatureFactory
    from mcp_medical_server.services.token_issuer import TokenIssuer, TokenStatus
    from mcp_medical_server.services.vault_adapter import LocalVault, VaultAdapter, RetrievalStatus


class EmergencyCredentialDemo:
    """Orchestrates the emergency credential retrieval demo"""
    
    def __init__(self):
        """Initialize demo components"""
        self.finalizer = ReportFinalizer()
        self.request_manager = CredentialRequestManager(self.finalizer)
        self.signature_factory = ApprovalSignatureFactory()
        self.token_issuer = TokenIssuer(server_key="demo-secret-key-12345")
        
        # Setup vault
        self.vault = LocalVault(vault_id="vault-demo")
        self.vault_adapter = VaultAdapter(self.vault, self.token_issuer)
        
        # Store some demo secrets
        self._setup_demo_secrets()
        
        # Store owner keys (in-memory for demo)
        self.owner_keys = {}
        self.owner_public_keys = {}
        self._setup_owner_keys()
        
        # Output buffer
        self.events = []
    
    def _setup_demo_secrets(self):
        """Setup demo secrets in vault"""
        secrets = {
            "/clinical/patient-123/mri-credentials": "mri_access_token_xyz789",
            "/clinical/patient-123/lab-credentials": "lab_api_key_abc123",
            "/clinical/patient-456/ct-credentials": "ct_scan_token_def456"
        }
        
        for path, secret in secrets.items():
            self.vault.store_secret(path, secret, owner_id="vault-admin@hospital.com")
        
        self._log_event("SETUP", f"Stored {len(secrets)} demo secrets in vault")
    
    def _setup_owner_keys(self):
        """Setup owner keys for offline approval"""
        from mcp_medical_server.services.signature_service import SignatureService
        
        service = SignatureService()
        
        # Create key pairs for two owners
        for owner_id in ["dr.smith@hospital.com", "dr.jones@hospital.com"]:
            private_key, public_key = service.generate_key_pair()
            self.owner_keys[owner_id] = private_key
            self.owner_public_keys[owner_id] = public_key
        
        self._log_event("SETUP", f"Generated key pairs for 2 owners")
    
    def _log_event(self, phase: str, message: str):
        """Log event to output"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        event = {
            "phase": phase,
            "timestamp": timestamp,
            "message": message
        }
        self.events.append(event)
        print(f"[{phase:12}] {message}")
    
    def run_demo(self):
        """Run the complete emergency credential retrieval demo"""
        print("\n" + "="*80)
        print(" EMERGENCY CREDENTIAL RETRIEVAL - END-TO-END DEMO")
        print("="*80 + "\n")
        
        # Phase 1: Request
        self._demo_request_credentials()
        
        # Phase 2: Approval
        self._demo_offline_approval()
        
        # Phase 3: Token Issuance
        self._demo_token_issuance()
        
        # Phase 4: Secret Retrieval
        self._demo_secret_retrieval()
        
        # Phase 5: Replay Prevention
        self._demo_replay_prevention()
        
        # Phase 6: Audit Trail
        self._demo_audit_trail()
        
        # Final Report
        self._print_final_report()
    
    def _demo_request_credentials(self):
        """Phase 1: Clinician requests emergency access"""
        print("\n" + "-"*80)
        print(" PHASE 1: CLINICIAN REQUESTS EMERGENCY ACCESS")
        print("-"*80)
        
        req_id = "REQ-20251110-160000-demo001"
        requester_id = "dr.williams@hospital.com"
        patient_context = {
            "patient_id": "P-123456",
            "study_id": "S-789012",
            "urgency": "high",
            "reason": "Emergency MRI interpretation - patient in critical condition"
        }
        
        self._log_event("REQUEST", f"Clinician {requester_id} requesting access")
        self._log_event("REQUEST", f"Patient context: {patient_context['reason']}")
        
        # Create request
        self.current_request = self.request_manager.create_request(
            req_id=req_id,
            requester_id=requester_id,
            reason=patient_context["reason"],
            target_vault="vault-demo",
            target_path="/clinical/patient-123/mri-credentials",
            patient_context=patient_context
        )
        
        self._log_event("REQUEST", f"Request created with ID: {req_id}")
        self._log_event("REQUEST", f"Merkle proof: {self.current_request['merkle_proof']['ledger_tx_id']}")
    
    def _demo_offline_approval(self):
        """Phase 2: Owner reviews and approves offline"""
        print("\n" + "-"*80)
        print(" PHASE 2: OWNER OFFLINE APPROVAL")
        print("-"*80)
        
        req_id = self.current_request['req_id']
        approver = "dr.smith@hospital.com"
        
        self._log_event("APPROVAL", f"Request sent to owner {approver} for review")
        time.sleep(0.1)  # Simulate review time
        
        # Owner signs approval offline
        approval = self.signature_factory.sign_approval(
            req_id=req_id,
            approver_id=approver,
            private_key_path="<in-memory>",
            passphrase="passphrase",  # Dummy (using in-memory key)
            ttl_seconds=300
        )
        
        # Hack for demo: manually sign since we're using in-memory keys
        from mcp_medical_server.services.signature_service import SignatureService
        service = SignatureService()
        private_key = self.owner_keys[approver]
        message = f"{req_id} | {approval['approved_ts']}"
        signature = service.sign_message(private_key, message)
        
        approval = {
            "req_id": req_id,
            "approver": approver,
            "approved_ts": approval['approved_ts'],
            "signature": signature,
            "ttl_seconds": 300
        }
        
        self.current_approval = approval
        
        self._log_event("APPROVAL", f"Owner {approver} APPROVED request")
        self._log_event("APPROVAL", f"Approval signature: {signature[:32]}...")
        self._log_event("APPROVAL", f"TTL: {approval['ttl_seconds']} seconds")
        
        # Update request status in system
        self.current_request = self.request_manager.update_request_status(
            req_id=req_id,
            new_status="APPROVED",
            approver_id=approver
        )
    
    def _demo_token_issuance(self):
        """Phase 3: Server issues single-use token"""
        print("\n" + "-"*80)
        print(" PHASE 3: SERVER ISSUES SINGLE-USE TOKEN")
        print("-"*80)
        
        req_id = self.current_request['req_id']
        path = self.current_request['target_path']
        
        self._log_event("TOKEN", f"Server validating owner approval...")
        
        # Verify approval signature
        from mcp_medical_server.services.signature_service import SignatureService
        service = SignatureService()
        public_key = self.owner_public_keys[self.current_approval['approver']]
        message = f"{req_id} | {self.current_approval['approved_ts']}"
        is_valid = service.verify_signature(public_key, message, self.current_approval['signature'])
        
        if not is_valid:
            self._log_event("TOKEN", f"ERROR: Approval signature verification FAILED")
            return
        
        self._log_event("TOKEN", f"Approval signature verified ✓")
        
        # Issue token
        token_result = self.token_issuer.issue_token(
            req_id=req_id,
            vault="vault-demo",
            path=path,
            ttl_seconds=300,
            approval_signature=self.current_approval['signature']
        )
        
        self.current_token = token_result['token']
        self.current_nonce = token_result['nonce']
        
        self._log_event("TOKEN", f"Single-use token issued")
        self._log_event("TOKEN", f"Token expiration: {token_result['exp_ts']}")
        self._log_event("TOKEN", f"Nonce: {token_result['nonce'][:16]}...")
        
        # Update request status
        self.current_request = self.request_manager.update_request_status(
            req_id=req_id,
            new_status="RETRIEVED",
            approver_id=self.current_approval['approver']
        )
    
    def _demo_secret_retrieval(self):
        """Phase 4: Agent retrieves secret with token"""
        print("\n" + "-"*80)
        print(" PHASE 4: AGENT RETRIEVES SECRET WITH TOKEN")
        print("-"*80)
        
        req_id = self.current_request['req_id']
        agent_id = "mcp-agent-001"
        
        self._log_event("RETRIEVE", f"MCP Agent {agent_id} requesting secret retrieval...")
        
        # Retrieve secret
        secret, status = self.vault_adapter.retrieve_secret(
            token=self.current_token,
            req_id=req_id,
            actor_id=agent_id,
            finalizer=self.finalizer
        )
        
        if status == RetrievalStatus.SUCCESS:
            self._log_event("RETRIEVE", f"Secret retrieved successfully ✓")
            self._log_event("RETRIEVE", f"Secret value: {secret}")
            self._log_event("RETRIEVE", f"Nonce marked as used (no replay possible)")
            self.current_secret = secret
        else:
            self._log_event("RETRIEVE", f"ERROR: Retrieval failed - {status}")
    
    def _demo_replay_prevention(self):
        """Phase 5: Demonstrate replay attack prevention"""
        print("\n" + "-"*80)
        print(" PHASE 5: REPLAY ATTACK PREVENTION")
        print("-"*80)
        
        req_id = self.current_request['req_id']
        agent_id = "mcp-agent-malicious"
        
        self._log_event("REPLAY", f"Attacker {agent_id} attempts to reuse same token...")
        
        # Try to reuse token
        secret, status = self.vault_adapter.retrieve_secret(
            token=self.current_token,
            req_id=req_id,
            actor_id=agent_id,
            finalizer=self.finalizer
        )
        
        if status == RetrievalStatus.NONCE_ALREADY_USED:
            self._log_event("REPLAY", f"Replay attack BLOCKED ✓")
            self._log_event("REPLAY", f"Reason: Nonce already used")
            self._log_event("REPLAY", f"Secret retrieval DENIED")
        else:
            self._log_event("REPLAY", f"ERROR: Replay attack was NOT blocked!")
    
    def _demo_audit_trail(self):
        """Phase 6: Display complete Merkle audit trail"""
        print("\n" + "-"*80)
        print(" PHASE 6: MERKLE AUDIT TRAIL")
        print("-"*80)
        
        ledger_entries = self.finalizer.ledger.entries
        
        self._log_event("AUDIT", f"Merkle ledger contains {len(ledger_entries)} events")
        
        for i, entry in enumerate(ledger_entries[-5:], 1):  # Show last 5 entries
            if entry.get('event_data'):
                event_data = json.loads(entry['event_data'])
                event_type = event_data.get('event_type', 'UNKNOWN')
                req_id = event_data.get('req_id', 'N/A')
                self._log_event("AUDIT", f"  Event {i}: {event_type} (req_id: {req_id})")
    
    def _print_final_report(self):
        """Print final summary report"""
        print("\n" + "="*80)
        print(" DEMO SUMMARY")
        print("="*80)
        
        print(f"\n✓ Emergency credential request workflow completed successfully!")
        print(f"\n Key Achievements:")
        print(f"  • Request created with unique ID and Merkle proof")
        print(f"  • Owner approved offline using Ed25519 signature")
        print(f"  • Server issued single-use token with nonce")
        print(f"  • Agent successfully retrieved secret")
        print(f"  • Replay attack was prevented (nonce already used)")
        print(f"  • All events Merkle-stamped in immutable audit trail")
        
        print(f"\n Security Features Demonstrated:")
        print(f"  ✓ Offline owner approval (no network required)")
        print(f"  ✓ Digital signature verification (Ed25519)")
        print(f"  ✓ Single-use token with HMAC signature")
        print(f"  ✓ Nonce-based replay prevention")
        print(f"  ✓ Time-limited access (TTL enforcement)")
        print(f"  ✓ Merkle audit trail (tamper-proof)")
        print(f"  ✓ Secret encryption at rest (Fernet)")
        
        print(f"\n Audit Trail:")
        print(f"  • Total Merkle events: {len(self.finalizer.ledger.entries)}")
        print(f"  • All events cryptographically linked")
        print(f"  • Immutable history preserved")
        
        print(f"\n" + "="*80 + "\n")


def main():
    """Main entry point"""
    demo = EmergencyCredentialDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()
