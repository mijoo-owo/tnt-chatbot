import streamlit as st
import os
from utils.prepare_vectordb import get_vectorstore

def save_docs_to_vectordb(pdf_docs, upload_docs):
    """
    Save uploaded PDF documents to the 'docs' folder and create or update the vectorstore.

    Parameters:
    - pdf_docs (list): List of uploaded PDF documents (from Streamlit file uploader)
    - upload_docs (list): List of names of previously uploaded documents (from session state)
    """
    # Identify newly uploaded files
    new_files = [pdf for pdf in pdf_docs if pdf.name not in upload_docs]
    new_file_names = [pdf.name for pdf in new_files]

    # Display "Process" button only if new files are uploaded
    if new_files and st.button("Process"):
        os.makedirs("docs", exist_ok=True)

        # Save new files to 'docs' directory
        for pdf in new_files:
            pdf_path = os.path.join("docs", pdf.name)
            with open(pdf_path, "wb") as f:
                f.write(pdf.getvalue())

        # Update session state
        st.session_state.uploaded_pdfs = upload_docs + new_file_names

        # Process and update vectorstore
        with st.spinner("Processing..."):
            get_vectorstore(new_file_names)
            st.success(f"Uploaded and processed: {', '.join(new_file_names)}")
