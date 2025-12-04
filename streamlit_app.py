import os
import sys
import tempfile
import subprocess
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent.resolve()

def get_env_from_secrets() -> dict:
    """Get environment variables from Streamlit secrets"""
    env = os.environ.copy()
    
    # Get secrets from Streamlit secrets.toml
    try:
        if "mistral" in st.secrets:
            mistral_secrets = st.secrets["mistral"]
            if "ocr_endpoint" in mistral_secrets:
                env["MISTRAL_OCR_ENDPOINT"] = mistral_secrets["ocr_endpoint"]
            if "api_key" in mistral_secrets:
                env["API_KEY"] = mistral_secrets["api_key"]
            if "model" in mistral_secrets:
                env["MISTRAL_MODEL"] = mistral_secrets["model"]
    except Exception as e:
        st.warning(f"Could not load secrets: {e}. Make sure .streamlit/secrets.toml is configured.")
    
    return env

def run_ocr(pdf_bytes: bytes, filename: str, backend: str, title: str | None) -> tuple[bytes, bytes, str, str, str]:
    """
    Save uploaded PDF to a temp file, run mistral_ocr-v5.py with selected backend,
    and return (md_bytes, docx_bytes, md_filename, docx_filename, logs).
    Returns file contents as bytes to avoid temp directory cleanup issues.
    """
    logs = []

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        pdf_path = td_path / filename
        pdf_path.write_bytes(pdf_bytes)

        # Out base (without extension)
        out_base = td_path / "out_streamlit"

        # Use v5 which supports --backend option
        # Check if mistral_ocr-v5.py exists, otherwise use v6 (hybrid)
        script_path = BASE_DIR / "mistral_ocr-v5.py"
        if not script_path.exists():
            # Fallback to v6 if v5 doesn't exist
            script_path = BASE_DIR / "mistral_ocr-v6.py"
            backend = None  # v6 doesn't support --backend
        
        # Use sys.executable to use the same Python interpreter as Streamlit
        cmd = [
            sys.executable,
            str(script_path),
            str(pdf_path),
            "--out",
            str(out_base),
        ]
        
        # Add --backend only if using v5 (which supports it)
        if backend:
            cmd += ["--backend", backend]

        if title:
            cmd += ["--title", title]

        logs.append(f"$ {' '.join(cmd)}")

        # Get environment variables from Streamlit secrets
        env = get_env_from_secrets()

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),  # Run from root directory
            env=env,  # Pass secrets as environment variables
        )

        logs.append("=== STDOUT ===")
        logs.append(p.stdout)
        logs.append("=== STDERR ===")
        logs.append(p.stderr)

        if p.returncode != 0:
            raise RuntimeError(
                f"OCR script failed with code {p.returncode}.\n\nSTDERR:\n{p.stderr[:4000]}"
            )

        # mistral_ocr-v5/v6 writes <out>.md and <out>.docx
        md_path = out_base.with_suffix(".md")
        docx_path = out_base.with_suffix(".docx")

        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {docx_path}")

        # Read files as bytes BEFORE temp directory is cleaned up
        md_bytes = md_path.read_bytes()
        docx_bytes = docx_path.read_bytes()
        
        # Generate filenames for download
        base_name = Path(filename).stem
        md_filename = f"{base_name}_ocr.md"
        docx_filename = f"{base_name}_ocr.docx"

        return md_bytes, docx_bytes, md_filename, docx_filename, "\n".join(logs)

def main():
    st.set_page_config(page_title="Suvichaar Docx Intelligence", layout="centered")

    st.title("📄 Suvichaar Docx Intelligence")
    st.write(
        "Don't upload pdfs more than 13 pages"
    )

    # Check if secrets are configured
    try:
        if "mistral" not in st.secrets or "api_key" not in st.secrets["mistral"]:
            st.error("⚠️ **Secrets not configured!**")
            st.info(
                "Please set up `.streamlit/secrets.toml` with your Mistral API credentials.\n\n"
                "Example:\n"
                "\n"
                "[mistral]\n"
                'ocr_endpoint = "https://your-endpoint.services.ai.azure.com/providers/mistral/azure/ocr"\n'
                'api_key = "your_api_key_here"\n'
                'model = "mistral-document-ai-2505"\n'
                "```"
            )
            st.stop()
    except Exception as e:
        st.error(f"⚠️ **Secrets not configured!** Error: {e}")
        st.info("Please set up `.streamlit/secrets.toml` with your Mistral API credentials.")
        st.stop()

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    # Backend selection
    st.write("### Choose Backend")
    backend_choice = st.radio(
        "Document type",
        options=[
            "PDFs with heavy tables",
            "PDFs with heavy mathematical formulas"
        ],
        index=0,
        help=(
            "**PDFs with heavy tables**: Better table formatting, alignment, and styling for documents with many tables.\n\n"
            "**PDFs with heavy mathematical formulas**: Better mathematical formula handling for documents with LaTeX-style math formulas."
        ),
    )
    
    # Map choice to backend
    if "Python-Docx" in backend_choice:
        backend = "python-docx"
        backend_display = "Python-Docx"
    else:
        backend = "pandoc"
        backend_display = "Pandoc"
    
    st.write("---")

    # Title input
    title = st.text_input("Optional title for the document", "")

    run_btn = st.button("Run OCR", type="primary", disabled=uploaded_file is None)

    if run_btn and uploaded_file is not None:
        try:
            with st.spinner(f"Running OCR using {backend_display} backend..."):
                md_bytes, docx_bytes, md_filename, docx_filename, logs = run_ocr(
                    pdf_bytes=uploaded_file.read(),
                    filename=uploaded_file.name,
                    backend=backend,
                    title=title or None,
                )

            st.success("✅ OCR completed successfully!")

            # Show basic info
            st.write("### Outputs")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Markdown**: `{md_filename}`")
            with col2:
                st.write(f"**DOCX**: `{docx_filename}`")

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download Markdown",
                    data=md_bytes,
                    file_name=md_filename,
                    mime="text/markdown",
                )

            with col2:
                st.download_button(
                    label="⬇️ Download DOCX",
                    data=docx_bytes,
                    file_name=docx_filename,
                    mime=(
                        "application/"
                        "vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ),
                )

            # Optional: show a preview of markdown (first N lines)
            preview = md_bytes.decode('utf-8', errors='ignore')
            st.write("### Markdown Preview (first 2000 characters)")
            st.code(preview[:2000] + ("..." if len(preview) > 2000 else ""), language="markdown")

            # Logs
            with st.expander("Show processing logs"):
                st.text(logs)

        except Exception as e:
            st.error(f"❌ Error during OCR: {e}")
            st.exception(e)

if __name__ == "__main__":
    main()




