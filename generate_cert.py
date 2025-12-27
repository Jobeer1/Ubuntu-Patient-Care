#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for HTTPS support
Required for microphone access in browsers
Pure Python implementation using cryptography library
"""

import os
import sys
from datetime import datetime, timedelta

def generate_certificate():
    """Generate self-signed certificate using cryptography library"""
    
    cert_file = 'cert.pem'
    key_file = 'key.pem'
    
    # Check if certificates already exist
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"✅ Certificates already exist ({cert_file}, {key_file})")
        return True
    
    print("🔐 Generating self-signed SSL certificate...")
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Build certificate subject and issuer
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Localhost"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SDOH"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.DNSName(u"127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Write certificate to file
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key to file
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        print(f"✅ Certificate generated: {cert_file}")
        print(f"✅ Private key generated: {key_file}")
        print(f"✅ Valid for 365 days")
        print("\n🔒 HTTPS is now enabled!")
        print("[*] Start the server with: python run.py")
        
        return True
        
    except ImportError:
        print("❌ ERROR: 'cryptography' library not found!")
        print("\nInstall it with:")
        print("  pip install cryptography")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
