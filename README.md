# Mistral OCR Streamlit App

This folder contains the Streamlit web application for Mistral OCR.

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Configure secrets:**
   - Create `.streamlit/secrets.toml` in the **project root** (not in app folder)
   - See [SECRETS_SETUP.md](./SECRETS_SETUP.md) for detailed instructions
   
   Quick example:
   ```toml
   [mistral]
   ocr_endpoint = "https://your-endpoint.services.ai.azure.com/providers/mistral/azure/ocr"
   api_key = "your_mistral_api_key_here"
   model = "mistral-document-ai-2505"
   ```

3. **Run the app:**
   ```bash
   streamlit run app/streamlit_app.py
   ```

## Files

- `streamlit_app.py` - Main Streamlit application
- `mistral_ocr-v6.py` - OCR processing script (hybrid approach: Pandoc + python-docx)
- `SECRETS_SETUP.md` - Detailed guide for setting up secrets

## Features

- PDF upload
- Hybrid DOCX generation (Pandoc for math + python-docx for tables)
- Markdown and DOCX download
- Markdown preview
- Processing logs
- Secure secrets management via Streamlit secrets.toml

## Secrets Configuration

**Important:** Secrets file location:
- ✅ Correct: `C:\mistral-ocr-api\.streamlit\secrets.toml`
- ❌ Wrong: `C:\mistral-ocr-api\app\.streamlit\secrets.toml`

For detailed setup instructions, see [SECRETS_SETUP.md](./SECRETS_SETUP.md)

