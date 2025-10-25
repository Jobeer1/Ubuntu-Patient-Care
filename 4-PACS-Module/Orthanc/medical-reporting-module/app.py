#!/usr/bin/env python3
"""Entrypoint for the Medical Reporting Module

Runs the Flask app created by core.app_factory using Flask-SocketIO.
"""
import os
import logging
import ssl
import ipaddress
from pathlib import Path

from core.app_factory import create_app, socketio
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_ssl_context():
    """Create SSL context for HTTPS"""
    cert_dir = Path(__file__).parent / 'certs'
    cert_file = cert_dir / 'cert.pem'
    key_file = cert_dir / 'key.pem'
    
    # Create certs directory if it doesn't exist
    cert_dir.mkdir(exist_ok=True)
    
    # Generate self-signed certificate if it doesn't exist
    if not cert_file.exists() or not key_file.exists():
        logger.info("Generating self-signed SSL certificate...")
        generate_self_signed_cert(cert_file, key_file)
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    return context


def generate_self_signed_cert(cert_file, key_file):
    """Generate a self-signed certificate for development"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Medical Reporting Module"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate and key to files
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info(f"SSL certificate generated: {cert_file}")
        
    except ImportError:
        logger.error("cryptography package not found. Installing...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'cryptography'])
        # Retry after installation
        generate_self_signed_cert(cert_file, key_file)


def main():
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(env)

    # Record start time for uptime reporting
    try:
        app.config['START_TIME'] = datetime.now(timezone.utc)
    except Exception:
        pass

    port = int(os.environ.get('PORT', 5443))  # Default to HTTPS port
    host = os.environ.get('HOST', '0.0.0.0')
    debug = app.config.get('DEBUG', env != 'production')
    
    no_ssl_env = os.environ.get('NO_SSL', '')
    no_ssl = no_ssl_env.lower() in ('1', 'true', 'yes', 'on')
    logger.info(f"NO_SSL environment variable: '{no_ssl_env}', interpreted as: {no_ssl}")
    
    if no_ssl:
        logger.info(f"Starting Medical Reporting Module on http://{host}:{port} (SSL disabled, env={env})")
        logger.info("Recommended: expose this port via a secure tunnel (eg. ngrok) for judges")
        socketio.run(app, host=host, port=port, debug=debug)
    else:
        # Create SSL context for HTTPS
        ssl_context = create_ssl_context()

        logger.info(f"Starting Medical Reporting Module on https://{host}:{port} (env={env})")
        logger.info("Note: You may see a security warning in your browser for the self-signed certificate")
        logger.info("This is normal for development. Click 'Advanced' and 'Proceed to localhost' to continue.")
        
        # Use socketio.run with SSL context
        socketio.run(app, host=host, port=port, debug=debug, ssl_context=ssl_context)


if __name__ == '__main__':
    main()
