"""Convert HTML certificate to PDF with proper A4 sizing."""
from pathlib import Path
from subprocess import run, PIPE
import json

def html_to_pdf_via_edge(html_file: str, output_pdf: str) -> None:
    """
    Use headless Microsoft Edge to render HTML to PDF.
    Requires Edge browser to be installed.
    """
    html_path = Path(html_file).resolve()
    output_path = Path(output_pdf).resolve()
    
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Edge command to save as PDF
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    cmd = [
        edge_exe,
        f"--headless",
        f"--disable-gpu",
        f"--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={output_path}",
        f"--print-to-pdf-no-header",
        f"file:///{html_path.as_posix()}",
    ]
    
    print(f"Converting {html_path.name} to PDF...")
    result = run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError(f"Edge conversion failed: {result.stderr}")
    
    print(f"✅ PDF saved to: {output_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python html_to_pdf.py <input_html> [output_pdf]")
        print("Example: python html_to_pdf.py certificate.html certificate.pdf")
        sys.exit(1)
    
    html_input = sys.argv[1]
    pdf_output = sys.argv[2] if len(sys.argv) > 2 else Path(html_input).with_suffix(".pdf")
    
    html_to_pdf_via_edge(html_input, pdf_output)
