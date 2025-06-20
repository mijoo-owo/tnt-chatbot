import streamlit as st
import os

def save_docs_to_vectordb(uploaded_docs, existing_docs):
    """
    Save newly uploaded documents to 'docs/' and return the list of newly added filenames.

    Parameters:
    - uploaded_docs (list): Files uploaded through Streamlit uploader.
    - existing_docs (list): Filenames already in the 'docs/' folder (used to avoid duplicates).

    Returns:
    - List of newly saved filenames.
    """

    # Filter out already existing files by name
    new_files = [doc for doc in uploaded_docs if doc.name not in existing_docs]
    new_file_names = [doc.name for doc in new_files]

    if new_files and st.button("Process"):
        os.makedirs("docs", exist_ok=True)

        for doc in new_files:
            file_path = os.path.join("docs", doc.name)
            try:
                with open(file_path, "wb") as f:
                    f.write(doc.getvalue())
                st.success(f"✅ Saved: {doc.name}")
            except Exception as e:
                st.error(f"❌ Failed to save {doc.name}: {e}")

        return new_file_names

    return []
