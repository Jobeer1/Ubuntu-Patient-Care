"""Generate secret keys for MCP Server"""
import secrets

def generate_secret_key(length=32):
    """Generate a random secret key"""
    return secrets.token_hex(length)

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           Secret Key Generator                            ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("Generated Secret Keys:\n")
    print(f"SECRET_KEY={generate_secret_key()}")
    print(f"JWT_SECRET_KEY={generate_secret_key()}")
    
    print("""
    
    Copy these keys to your .env file:
    1. Replace SECRET_KEY value
    2. Replace JWT_SECRET_KEY value
    
    ⚠️  Keep these keys secure and never commit them to version control!
    """)

if __name__ == "__main__":
    main()
