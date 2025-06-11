# utils/save_docs.py

import streamlit as st
import os
from utils.prepare_vectordb import get_vectorstore

def save_docs_to_vectordb(uploaded_docs, upload_docs):
    """
    Save uploaded documents (PDF, TXT, DOC, DOCX) to 'docs/' and update the vectorstore.

    Parameters:
    - uploaded_docs (list): List of uploaded documents from Streamlit uploader
    - upload_docs (list): Names of already-uploaded documents in session state
    """
    # Identify newly uploaded files
    new_files = [doc for doc in uploaded_docs if doc.name not in upload_docs]
    new_file_names = [doc.name for doc in new_files]

    if new_files and st.button("Process"):
        os.makedirs("docs", exist_ok=True)

        # Save to 'docs' directory
        for doc in new_files:
            file_path = os.path.join("docs", doc.name)
            with open(file_path, "wb") as f:
                f.write(doc.getvalue())

        # Update session state
        st.session_state.uploaded_pdfs = upload_docs + new_file_names

        # Process all current files (not just new ones)
        with st.spinner("Processing..."):
            get_vectorstore(st.session_state.uploaded_pdfs)
            st.success(f"Uploaded and processed: {', '.join(new_file_names)}")

        return new_file_names

    return []
