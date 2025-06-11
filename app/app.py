# app.py

import os
import streamlit as st
import shutil

from utils.save_docs import save_docs_to_vectordb
from utils.save_urls import save_url_to_vectordb
from utils.session_state import initialize_session_state_variables
from utils.prepare_vectordb import get_vectorstore
from utils.chatbot import chat

class ChatApp:
    """
    A Streamlit application for chatting with PDF documents.
    """

    def __init__(self):
        # Streamlit config
        st.set_page_config(page_title="TNT ChatBot 📚")
        st.title("TNT ChatBot 📚")

        if "session_initialized" not in st.session_state:
            self._reset_session_dirs_and_state()
            st.session_state.session_initialized = True

        initialize_session_state_variables(st)

    def _reset_session_dirs_and_state(self):
        """Delete all docs, chunks, and vectorstore tracker when a new session starts."""
        # Delete folders
        for folder in ["docs", "chunks"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)

        # Delete the embedding tracker file
        files_txt_path = "Vector_DB - Documents/files.txt"
        if os.path.exists(files_txt_path):
            os.remove(files_txt_path)

        # Recreate clean docs folder
        os.makedirs("docs", exist_ok=True)

        # Reset Streamlit session state
        st.session_state.uploaded_pdfs = []
        st.session_state.uploaded_urls = []
        st.session_state.previous_upload_docs_length = 0
        st.session_state.vectordb = None
        st.session_state.chat_history = []

    def run(self):
        upload_docs = os.listdir("docs")

        # Sidebar: upload & URL
        with st.sidebar:
            st.subheader("Your documents")
            if upload_docs:
                st.text(", ".join(upload_docs))
            else:
                st.info("No documents uploaded yet.")

            # --- Upload documents ---
            st.subheader("Upload documents")
            uploaded_docs = st.file_uploader(
                "Upload (.pdf, .txt, .doc, .docx)",
                type=["pdf", "txt", "doc", "docx"],
                accept_multiple_files=True
            )
            if uploaded_docs:
                new_files = save_docs_to_vectordb(uploaded_docs, upload_docs)
                if new_files:
                    st.session_state.uploaded_pdfs += new_files
                    st.success(f"Saved files: {', '.join(new_files)}")

            # --- URL Inputs ---
            st.subheader("Or enter website URLs")

            if "url_inputs" not in st.session_state:
                st.session_state.url_inputs = [""]

            if st.button("Add another URL"):
                st.session_state.url_inputs.append("")

            updated_inputs = []
            url_container = st.container()

            for i, url in enumerate(st.session_state.url_inputs):
                cols = url_container.columns([5, 1])
                with cols[0]:
                    updated_url = cols[0].text_input(f"URL #{i+1}", value=url, key=f"url_input_{i}")
                with cols[1]:
                    if cols[1].button("❌", key=f"remove_url_{i}"):
                        st.session_state.url_inputs.pop(i)
                        st.rerun()
                updated_inputs.append(updated_url)

            st.session_state.url_inputs[:] = updated_inputs

            if st.button("🌐 Process URLs"):
                current_docs = os.listdir("docs")
                for url in st.session_state.url_inputs:
                    url = url.strip()
                    if url:
                        fname, ftype = save_url_to_vectordb(url, current_docs)
                        if fname:
                            if ftype == "pdf":
                                st.session_state.uploaded_pdfs.append(fname)
                            elif ftype == "html":
                                st.session_state.uploaded_urls.append(fname)
                st.success("✅ All valid URLs processed.")

        # --- Vectorstore update ---
        upload_docs = os.listdir("docs")
        combined_uploaded_files = st.session_state.uploaded_pdfs + st.session_state.uploaded_urls

        if len(combined_uploaded_files) > st.session_state.previous_upload_docs_length:
            try:
                st.session_state.vectordb = get_vectorstore(combined_uploaded_files)
                st.success("✅ Vectorstore updated with all uploaded documents.")
                st.session_state.previous_upload_docs_length = len(combined_uploaded_files)
            except Exception as e:
                st.error(f"Error loading vector store or saving chunks: {e}")

        # --- Chat Interface ---
        st.session_state.chat_history = chat(
            st.session_state.chat_history,
            st.session_state.vectordb
        )

if __name__ == "__main__":
    ChatApp().run()
