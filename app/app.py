import os
import streamlit as st
import shutil

from utils.save_docs import save_docs_to_vectordb
from utils.save_urls import save_url_to_vectordb
from utils.session_state import initialize_session_state_variables
from utils.prepare_vectordb import get_vectorstore, has_new_files, has_new_custom_chunks, DEFAULT_PERSIST_DIR, force_refresh_with_custom_chunks
from utils.chatbot import chat

class ChatApp:
    """
    A Streamlit application for chatting with documents and websites.
    """

    def __init__(self):
        st.set_page_config(page_title="Pharma ChatBot 📚")
        st.title("Pharma ChatBot 📚")

        os.makedirs("docs", exist_ok=True)
        os.makedirs("chunks", exist_ok=True)
        os.makedirs("Vector_DB - Documents", exist_ok=True)
        
        # Initialize session state variables only if they are not already set
        if 'uploaded_pdfs' not in st.session_state:
            initialize_session_state_variables(st)

    def _reset_session_dirs_and_state(self):
        """Clean session state and temporary directories."""
        for folder in ["docs"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        os.makedirs("docs", exist_ok=True)
        # Keep other state variables that should not be reset
        st.success("Documents and selected session states have been reset.")

    def reset_all(self):
        """Delete docs folder and reset Streamlit session state."""
        import shutil
        import os

        if os.path.exists("docs"):
            shutil.rmtree("docs")
        os.makedirs("docs", exist_ok=True)

        if os.path.exists("chunks"):
            shutil.rmtree("chunks")
        os.makedirs("chunks", exist_ok=True)

        files_txt_path = "Vector_DB - Documents/files.txt"
        if os.path.exists(files_txt_path):
            os.remove(files_txt_path)

        # Clear custom chunks cache
        custom_chunks_cache_path = "Vector_DB - Documents/custom_chunks.txt"
        if os.path.exists(custom_chunks_cache_path):
            os.remove(custom_chunks_cache_path)

        st.session_state.uploaded_pdfs = []
        st.session_state.uploaded_urls = []
        st.session_state.previous_upload_docs_length = 0
        st.session_state.vectordb = None
        st.session_state.chat_history = []
        st.session_state.url_inputs = [""]
        st.success("All documents and session state have been reset.")
        st.rerun()

    def _handle_url_inputs(self):
        """Render and manage the dynamic URL input fields in the sidebar."""
        if st.button("Add another URL"):
            st.session_state.url_inputs.append("")
            st.rerun()

        new_url_inputs = []
        should_rerun = False
        
        for i, url in enumerate(st.session_state.url_inputs):
            col1, col2 = st.columns([10, 1])
            with col1:
                new_url = st.text_input(
                    f"URL #{i+1}", 
                    value=url, 
                    key=f"url_{i}"
                )
                new_url_inputs.append(new_url)
            with col2:
                if st.button("❌", key=f"remove_url_{i}"):
                    new_url_inputs.pop(i)
                    should_rerun = True
        
        st.session_state.url_inputs = new_url_inputs
        
        if should_rerun:
            st.rerun()

    def run(self):
        # -------------------------------
        # Sidebar: Upload & URL options
        # -------------------------------
        # with st.sidebar:
        #     st.subheader("Upload documents")
        #     uploaded_docs = st.file_uploader(
        #         "Upload (.pdf, .txt, .doc, .docx, .xls, .xlsx)",
        #         type=["pdf", "txt", "doc", "docx", "xls", "xlsx"],
        #         accept_multiple_files=True
        #     )

        #     if uploaded_docs:
        #         files_on_disk = os.listdir("docs")
        #         new_files = save_docs_to_vectordb(uploaded_docs, files_on_disk)
        #         if new_files:
        #             st.success(f"📁 Saved: {', '.join(new_files)}")

        #     st.subheader("Or enter website URLs")

        #     crawl_links = st.checkbox("Crawl all links on the same domain", value=False)
        #     page_limit = 50
        #     if crawl_links:
        #         page_limit = st.number_input(
        #             "Maximum pages to crawl", min_value=1, max_value=1000, value=50
        #         )

        #     self._handle_url_inputs()

        #     if st.button("🌐 Process URLs", use_container_width=True):
        #         files_on_disk = os.listdir("docs")
        #         for url in st.session_state.url_inputs:
        #             url = url.strip()
        #             if url:
        #                 save_url_to_vectordb(
        #                     url, 
        #                     files_on_disk, 
        #                     crawl_links=crawl_links, 
        #                     page_limit=page_limit
        #                 )
        #         st.success("✅ All valid URLs processed.")

        #     if st.button("Reset", use_container_width=True):
        #         self.reset_all()

        #     st.subheader("Custom Chunks")
        #     if st.button("🔄 Refresh with Custom Chunks", use_container_width=True):
        #         with st.spinner("Refreshing knowledge base with custom chunks..."):
        #             try:
        #                 st.session_state.vectordb = force_refresh_with_custom_chunks()
        #                 st.success("✅ Knowledge base refreshed with custom chunks.")
        #             except Exception as e:
        #                 st.error(f"Error refreshing vector store: {e}")

        # -------------------------------
        # Vectorstore and Chat
        # -------------------------------
        all_docs_in_folder = os.listdir("docs")
        
        # Check if we need to update the vector database
        # We update if: 1) vectordb is None, 2) there are new files, or 3) we want to ensure custom chunks are included
        should_update = (
            st.session_state.vectordb is None or 
            has_new_files(DEFAULT_PERSIST_DIR, all_docs_in_folder) or
            has_new_custom_chunks(DEFAULT_PERSIST_DIR)
        )
        
        if should_update:
            with st.spinner("Updating knowledge base..."):
                try:
                    st.session_state.vectordb = get_vectorstore(all_docs_in_folder)
                    st.success("✅ Knowledge base is up to date.")
                except Exception as e:
                    st.error(f"Error updating vector store: {e}")

        if st.session_state.vectordb is not None:
            st.session_state.chat_history = chat(
                st.session_state.chat_history,
                st.session_state.vectordb
            )
        else:
            st.info("Upload documents or enter URLs to begin.")


if __name__ == "__main__":
    ChatApp().run()
