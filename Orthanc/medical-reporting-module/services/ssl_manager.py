"""
SSL Certificate Manager for Medical Reporting Module
Handles SSL certificate generation, validation, and HTTPS configuration
"""

import os
import logging
import subprocess
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import tempfile
import shutil
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import ipaddress

logger = logging.getLogger(__name__)

class SSLManager:
    """Manages SSL certificates for HTTPS support"""
    
    def __init__(self, cert_directory: str = None):
        """Initialize SSL manager"""
        if cert_directory is None:
            # Default to ssl_certificates directory in the application root
            app_root = Path(__file__).parent.parent
            cert_directory = app_root / "ssl_certificates"
        
        self.cert_directory = Path(cert_directory)
        self.cert_directory.mkdir(parents=True, exist_ok=True)
        
        # Certificate file paths
        self.cert_file = self.cert_directory / "server.crt"
        self.key_file = self.cert_directory / "server.key"
        self.csr_file = self.cert_directory / "server.csr"
        
        # Development mode detection
        self.development_mode = os.getenv("FLASK_ENV") == "development"
        
        logger.info(f"SSL Manager initialized. Certificates directory: {self.cert_directory}")
        logger.info(f"Development mode: {self.development_mode}")
    
    def check_ssl_setup(self) -> Dict[str, any]:
        """Check current SSL setup status"""
        try:
            status = {
                "certificates_exist": False,
                "certificates_valid": False,
                "cert_file_path": str(self.cert_file),
                "key_file_path": str(self.key_file),
                "development_mode": self.development_mode,
                "openssl_available": self._check_openssl_available(),
                "cert_info": None,
                "recommendations": []
            }
            
            # Check if certificate files exist
            if self.cert_file.exists() and self.key_file.exists():
                status["certificates_exist"] = True
                
                # Validate certificates
                cert_info = self._get_certificate_info()
                if cert_info:
                    status["certificates_valid"] = True
                    status["cert_info"] = cert_info
                    
                    # Check expiration
                    if cert_info.get("days_until_expiry", 0) < 30:
                        status["recommendations"].append("Certificate expires soon, consider renewal")
                else:
                    status["recommendations"].append("Certificate files exist but are invalid")
            else:
                status["recommendations"].append("No SSL certificates found")
            
            # Add setup recommendations
            if not status["certificates_exist"]:
                if self.development_mode:
                    status["recommendations"].append("Generate self-signed certificate for development")
                else:
                    status["recommendations"].append("Set up production SSL certificate")
            
            if not status["openssl_available"]:
                status["recommendations"].append("Install OpenSSL for certificate management")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check SSL setup: {e}")
            return {"error": str(e)}
    
    def _check_openssl_available(self) -> bool:
        """Check if OpenSSL is available"""
        try:
            result = subprocess.run(["openssl", "version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _get_certificate_info(self) -> Optional[Dict]:
        """Get information about existing certificate using Python cryptography library"""
        try:
            if not self.cert_file.exists():
                return None
            
            # Read certificate file
            with open(self.cert_file, "rb") as f:
                cert_data = f.read()
            
            # Parse certificate
            cert = x509.load_pem_x509_certificate(cert_data)
            
            # Extract information
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            
            # Calculate days until expiry - handle timezone awareness properly
            now = datetime.utcnow()
            
            # Get certificate validity dates
            not_valid_after = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after
            not_valid_before = cert.not_valid_before_utc if hasattr(cert, 'not_valid_before_utc') else cert.not_valid_before
            
            # Ensure both datetimes are timezone-naive for comparison
            if hasattr(not_valid_after, 'replace') and not_valid_after.tzinfo is not None:
                not_valid_after = not_valid_after.replace(tzinfo=None)
            if hasattr(not_valid_before, 'replace') and not_valid_before.tzinfo is not None:
                not_valid_before = not_valid_before.replace(tzinfo=None)
            
            try:
                days_until_expiry = (not_valid_after - now).days
            except Exception as e:
                logger.warning(f"Could not calculate days until expiry: {e}")
                days_until_expiry = 0
            
            # Safely format datetime strings
            try:
                not_before_str = not_valid_before.isoformat() if hasattr(not_valid_before, 'isoformat') else str(not_valid_before)
                not_after_str = not_valid_after.isoformat() if hasattr(not_valid_after, 'isoformat') else str(not_valid_after)
            except Exception:
                not_before_str = "unknown"
                not_after_str = "unknown"
            
            info = {
                "subject": subject,
                "issuer": issuer,
                "serial_number": str(cert.serial_number),
                "not_before": not_before_str,
                "not_after": not_after_str,
                "signature_algorithm": cert.signature_algorithm_oid._name,
                "is_self_signed": subject == issuer,
                "days_until_expiry": days_until_expiry
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get certificate info: {e}")
            return None
    
    def _extract_cert_field(self, cert_text: str, field_name: str) -> Optional[str]:
        """Extract a field from certificate text"""
        try:
            lines = cert_text.split('\n')
            for line in lines:
                if field_name in line:
                    return line.split(field_name, 1)[1].strip()
            return None
        except:
            return None
    
    def generate_self_signed_certificate(self, 
                                       common_name: str = None,
                                       organization: str = "Medical Reporting Module",
                                       country: str = "ZA",
                                       validity_days: int = 365) -> bool:
        """Generate a self-signed SSL certificate using Python cryptography library"""
        try:
            # Determine common name
            if common_name is None:
                try:
                    common_name = socket.getfqdn()
                    if common_name == "localhost" or common_name == socket.gethostname():
                        common_name = "localhost"
                except:
                    common_name = "localhost"
            
            logger.info(f"Generating self-signed certificate for {common_name}")
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate subject and issuer (same for self-signed)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
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
                datetime.utcnow() + timedelta(days=validity_days)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv6Address("::1")),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Write private key
            with open(self.key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Write certificate
            with open(self.cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Set appropriate permissions
            os.chmod(self.key_file, 0o600)  # Private key should be readable only by owner
            os.chmod(self.cert_file, 0o644)  # Certificate can be readable by others
            
            logger.info(f"Self-signed certificate generated successfully")
            logger.info(f"Certificate: {self.cert_file}")
            logger.info(f"Private key: {self.key_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            return False
    
    def setup_development_ssl(self) -> bool:
        """Set up SSL for development environment"""
        try:
            logger.info("Setting up SSL for development environment")
            
            # Check if certificates already exist and are valid
            status = self.check_ssl_setup()
            
            if status.get("certificates_valid"):
                logger.info("Valid SSL certificates already exist")
                return True
            
            # Generate self-signed certificate
            success = self.generate_self_signed_certificate(
                common_name="localhost",
                organization="Medical Reporting Module - Development",
                validity_days=365
            )
            
            if success:
                logger.info("Development SSL setup completed successfully")
                self._print_setup_instructions()
                return True
            else:
                logger.error("Failed to set up development SSL")
                return False
            
        except Exception as e:
            logger.error(f"Failed to setup development SSL: {e}")
            return False
    
    def _print_setup_instructions(self):
        """Print SSL setup instructions"""
        logger.info("=" * 60)
        logger.info("SSL CERTIFICATE SETUP COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Certificate file: {self.cert_file}")
        logger.info(f"Private key file: {self.key_file}")
        logger.info("")
        logger.info("To use HTTPS with Flask:")
        logger.info("1. Start your Flask app with SSL context:")
        logger.info(f"   app.run(host='0.0.0.0', port=5001, ssl_context=('{self.cert_file}', '{self.key_file}'))")
        logger.info("")
        logger.info("2. Access your application at: https://localhost:5001")
        logger.info("")
        logger.info("Note: Browsers will show a security warning for self-signed certificates.")
        logger.info("This is normal for development. Click 'Advanced' and 'Proceed to localhost'.")
        logger.info("=" * 60)
    
    def get_ssl_context(self) -> Optional[Tuple[str, str]]:
        """Get SSL context tuple for Flask"""
        try:
            if self.cert_file.exists() and self.key_file.exists():
                return (str(self.cert_file), str(self.key_file))
            return None
        except Exception as e:
            logger.error(f"Failed to get SSL context: {e}")
            return None
    
    def validate_ssl_setup(self) -> bool:
        """Validate current SSL setup"""
        try:
            status = self.check_ssl_setup()
            return status.get("certificates_valid", False)
        except Exception as e:
            logger.error(f"Failed to validate SSL setup: {e}")
            return False
    
    def cleanup_certificates(self) -> bool:
        """Remove existing certificates"""
        try:
            files_removed = []
            
            for cert_file in [self.cert_file, self.key_file, self.csr_file]:
                if cert_file.exists():
                    cert_file.unlink()
                    files_removed.append(str(cert_file))
            
            if files_removed:
                logger.info(f"Removed certificate files: {files_removed}")
            else:
                logger.info("No certificate files to remove")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup certificates: {e}")
            return False
    
    def get_flask_ssl_config(self) -> Dict[str, any]:
        """Get Flask SSL configuration"""
        try:
            ssl_context = self.get_ssl_context()
            
            config = {
                "ssl_enabled": ssl_context is not None,
                "ssl_context": ssl_context,
                "development_mode": self.development_mode,
                "cert_directory": str(self.cert_directory)
            }
            
            if ssl_context:
                config["https_url"] = "https://localhost:5001"
                config["setup_instructions"] = [
                    "SSL certificates are configured",
                    "Application will run on HTTPS",
                    "Microphone access will be available",
                    "Browser may show security warning for self-signed certificates"
                ]
            else:
                config["http_url"] = "http://localhost:5001"
                config["setup_instructions"] = [
                    "No SSL certificates found",
                    "Application will run on HTTP",
                    "Microphone access may be blocked by browser",
                    "Run ssl_manager.setup_development_ssl() to enable HTTPS"
                ]
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get Flask SSL config: {e}")
            return {"ssl_enabled": False, "error": str(e)}

# Global SSL manager instance
ssl_manager = SSLManager()

def setup_ssl_for_development():
    """Convenience function to set up SSL for development"""
    return ssl_manager.setup_development_ssl()

def get_ssl_context_for_flask():
    """Convenience function to get SSL context for Flask"""
    return ssl_manager.get_ssl_context()