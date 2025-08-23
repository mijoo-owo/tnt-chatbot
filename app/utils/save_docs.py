import streamlit as st
import os
from .prepare_vectordb import get_user_dirs, ensure_user_dirs


def save_docs_to_vectordb_user(username: str, uploaded_docs, existing_docs):
    """
    Save newly uploaded documents to user-specific docs folder

    Parameters:
    - username (str): Current logged-in user
    - uploaded_docs (list): Files uploaded through Streamlit uploader
    - existing_docs (list): Filenames already in user's docs folder

    Returns:
    - List of newly saved filenames
    """

    # Get user-specific directories
    dirs = ensure_user_dirs(username)
    docs_dir = dirs['docs']

    # Filter out already existing files by name
    new_files = [doc for doc in uploaded_docs if doc.name not in existing_docs]
    new_file_names = [doc.name for doc in new_files]

    if new_files and st.button("Process"):
        for doc in new_files:
            file_path = os.path.join(docs_dir, doc.name)
            try:
                with open(file_path, "wb") as f:
                    f.write(doc.getvalue())
                st.success(f"✅ Saved for {username}: {doc.name}")
            except Exception as e:
                st.error(f"❌ Failed to save {doc.name}: {e}")
                continue

        return new_file_names

    return []


def get_user_documents(username: str):
    """Get list of documents for specific user"""
    dirs = get_user_dirs(username)
    docs_dir = dirs['docs']

    if os.path.exists(docs_dir):
        return os.listdir(docs_dir)
    return []


def delete_user_document(username: str, filename: str):
    """Delete specific document for user"""
    dirs = get_user_dirs(username)
    file_path = os.path.join(dirs['docs'], filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        st.success(f"🗑️ Deleted {filename} for user {username}")
        return True
    return False


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
                # st.success(f"✅ Saved: {doc.name}")  # Removed to avoid duplicate messages
            except Exception as e:
                continue

        return new_file_names

    return []
