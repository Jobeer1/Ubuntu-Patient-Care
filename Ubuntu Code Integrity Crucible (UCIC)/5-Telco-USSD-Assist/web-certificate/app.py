from pathlib import Path

from flask import Flask, render_template, send_file, abort

BASE_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
CERTIFICATE_FILE = BASE_DIR.parent / "Telco_USSD_Technical_Certificate.jpg"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)


@app.route("/")
def certificate_page():
    """Render the interactive certificate page."""
    return render_template("index.html")


@app.route("/download-certificate")
def download_certificate():
    """Send the latest signed JPEG certificate for download."""
    if not CERTIFICATE_FILE.exists():
        abort(404, description="Certificate image not found. Generate it first via generate_certificate_v3.py.")

    return send_file(
        CERTIFICATE_FILE,
        mimetype="image/jpeg",
        as_attachment=True,
        download_name=CERTIFICATE_FILE.name,
    )


if __name__ == "__main__":
    app.run(debug=True)
