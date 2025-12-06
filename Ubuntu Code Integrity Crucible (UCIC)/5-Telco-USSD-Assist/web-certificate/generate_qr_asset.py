"""Utility to generate the QR code asset used by the web certificate."""
from pathlib import Path

import qrcode

AUDIT_URL = (
    "https://github.com/Jobeer1/Ubuntu-Patient-Care/tree/main/"
    "Ubuntu%20Code%20Integrity%20Crucible%20%28UCIC%29/5-Telco-USSD-Assist"
)
OUTPUT_PATH = Path(__file__).parent / "static" / "qr-code.png"


def main() -> None:
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(AUDIT_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#001f3f", back_color="white")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT_PATH)
    print(f"QR code saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
