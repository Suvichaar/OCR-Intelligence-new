import os
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


def run_ocr(pdf_bytes: bytes, filename: str, title: str | None) -> tuple[bytes, bytes, str, str, str]:
    """
    Save uploaded PDF to a temp file, run mistral_ocr-v6.py (hybrid approach),
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

        # Use v6 from app folder (hybrid approach: Pandoc + python-docx)
        # BASE_DIR is app/, so script is in same folder
        script_path = BASE_DIR / "mistral_ocr-v6.py"
        
        cmd = [
            "python",
            str(script_path),
            str(pdf_path),
            "--out",
            str(out_base),
        ]

        if title:
            cmd += ["--title", title]

        logs.append(f"$ {' '.join(cmd)}")

        # Get environment variables from Streamlit secrets
        env = get_env_from_secrets()

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),  # Run from app folder
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

        # mistral_ocr-v6 writes <out>.md and <out>.docx
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
    st.set_page_config(page_title="Mistral OCR – Hybrid DOCX", layout="centered")
    st.title("📄Suvichaar Docx Intelligence")
    st.write(
        "Don't upload more than 10 pages"
    )
    # Check if secrets are configured
    try:
        if "mistral" not in st.secrets or "api_key" not in st.secrets["mistral"]:
            st.error("⚠️ **Secrets not configured!**")
            st.info(
                "Please set up `.streamlit/secrets.toml` with your Mistral API credentials.\n\n"
                "Example:\n"
                "```toml\n"
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

    # Title input
    title = st.text_input("Optional title for the document (H1 in markdown/DOCX)", "")
    
    st.caption("Using hybrid approach: Pandoc (math) + python-docx (tables)")

    run_btn = st.button("Run OCR", type="primary", disabled=uploaded_file is None)

    if run_btn and uploaded_file is not None:
        try:
            with st.spinner("Running OCR with hybrid approach (Pandoc + python-docx)..."):
                md_bytes, docx_bytes, md_filename, docx_filename, logs = run_ocr(
                    pdf_bytes=uploaded_file.read(),
                    filename=uploaded_file.name,
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




