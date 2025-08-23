import os
import streamlit as st
import shutil

from utils.auth import UserAuth
from utils.save_docs import save_docs_to_vectordb_user, get_user_documents
from utils.save_urls import save_url_to_vectordb_user
from utils.session_state import initialize_session_state_variables
from utils.prepare_vectordb import (
    get_vectorstore_user,
    has_new_files_user,
    cleanup_user_data,
    get_user_dirs
)
from utils.chatbot import chat


class ChatApp:
    """
    A Streamlit application for chatting with documents and websites.
    """

    def __init__(self):
        st.set_page_config(page_title="PC1 ChatBot")
        # st.title("PC1 ChatBot")

        # Initialize authentication
        self.auth = UserAuth()

        # Check if user is logged in
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = None
        if 'username' not in st.session_state:
            st.session_state.username = None

    # def _reset_session_dirs_and_state(self):
    #     """Clean session state and temporary directories."""
    #     for folder in ["docs"]:
    #         if os.path.exists(folder):
    #             shutil.rmtree(folder)
    #     os.makedirs("docs", exist_ok=True)
    #     # Keep other state variables that should not be reset
    #     st.success("Documents and selected session states have been reset.")

    def render_login_page(self):
        """Render login page"""
        st.title("🔐 Login to PC1 ChatBot")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username, auth_status = self.auth.login()

            if auth_status:
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.success(f'Welcome *{username}*')
                st.rerun()

        # Optional: Registration section for admin
        if st.checkbox("Admin: Register new user"):
            self.auth.register_new_user()

    def render_main_app(self):
        """Render main application for authenticated users"""
        username = st.session_state.username

        # Header with user info and logout
        col1, col2 = st.columns([3, 1])
        with col1:
            st.title(f"PC1 ChatBot 📚")
            st.write(f"Welcome back, **{username}**!")

        with col2:
            self.auth.logout()

        # Ensure user directories exist
        user_dirs = get_user_dirs(username)
        for dir_path in user_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        # Initialize session state for user
        if f'uploaded_pdfs_{username}' not in st.session_state:
            self.initialize_user_session_state(username)

        # Sidebar: Upload & URL options
        with st.sidebar:
            st.subheader(f"📁 {username}'s Documents")

            # Show current document count
            user_docs = get_user_documents(username)
            st.info(f"📊 You have {len(user_docs)} documents")

            uploaded_docs = st.file_uploader(
                "Upload (.pdf, .txt, .doc, .docx, .xls, .xlsx)",
                type=["pdf", "txt", "doc", "docx", "xls", "xlsx"],
                accept_multiple_files=True
            )

            if uploaded_docs:
                new_files = save_docs_to_vectordb_user(username, uploaded_docs, user_docs)
                if new_files:
                    st.success(f"📁 Saved: {', '.join(new_files)}")

            st.subheader("🌐 Website URLs")
            crawl_links = st.checkbox("Crawl all links on the same domain", value=False)
            page_limit = 50
            if crawl_links:
                page_limit = st.number_input(
                    "Maximum pages to crawl", min_value=1, max_value=1000, value=50
                )

            self._handle_url_inputs_user(username)

            if st.button("🌐 Process URLs", use_container_width=True):
                for url in st.session_state.get(f'url_inputs_{username}', [""]):
                    url = url.strip()
                    if url:
                        save_url_to_vectordb_user(
                            username, url, user_docs,
                            crawl_links=crawl_links,
                            page_limit=page_limit
                        )
                st.success("✅ All valid URLs processed.")

            # User-specific reset
            if st.button("🗑️ Reset My Data", use_container_width=True):
                if st.button("⚠️ Confirm Reset", use_container_width=True):
                    self.reset_user_data(username)

        # Vector store and chat for user
        all_user_docs = get_user_documents(username)
        user_vectordb_key = f'vectordb_{username}'

        if (user_vectordb_key not in st.session_state or
                has_new_files_user(username, all_user_docs)):

            with st.spinner(f"Updating {username}'s knowledge base..."):
                try:
                    st.session_state[user_vectordb_key] = get_vectorstore_user(username, all_user_docs)
                    st.success("✅ Knowledge base updated.")
                except Exception as e:
                    st.error(f"Error updating vector store: {e}")

        # Chat interface
        if user_vectordb_key in st.session_state:
            chat_history_key = f'chat_history_{username}'
            if chat_history_key not in st.session_state:
                st.session_state[chat_history_key] = []

            st.session_state[chat_history_key] = chat(
                st.session_state[chat_history_key],
                st.session_state[user_vectordb_key]
            )
        else:
            st.info("Upload documents or enter URLs to begin chatting.")

    def initialize_user_session_state(self, username):
        """Initialize session state variables for specific user"""
        st.session_state[f'uploaded_pdfs_{username}'] = []
        st.session_state[f'uploaded_urls_{username}'] = []
        st.session_state[f'url_inputs_{username}'] = [""]
        st.session_state[f'chat_history_{username}'] = []

    def _handle_url_inputs_user(self, username):
        """Handle URL inputs for specific user"""
        url_inputs_key = f'url_inputs_{username}'

        if url_inputs_key not in st.session_state:
            st.session_state[url_inputs_key] = [""]

        if st.button("Add another URL"):
            st.session_state[url_inputs_key].append("")
            st.rerun()

        new_url_inputs = []
        should_rerun = False

        for i, url in enumerate(st.session_state[url_inputs_key]):
            col1, col2 = st.columns([10, 1])
            with col1:
                new_url = st.text_input(
                    f"URL #{i+1}",
                    value=url,
                    key=f"url_{username}_{i}"
                )
                new_url_inputs.append(new_url)
            with col2:
                if st.button("❌", key=f"remove_url_{username}_{i}"):
                    new_url_inputs.pop(i)
                    should_rerun = True

        st.session_state[url_inputs_key] = new_url_inputs

        if should_rerun:
            st.rerun()

    def reset_user_data(self, username):
        """Reset all data for specific user"""
        cleanup_user_data(username)

        # Clear user-specific session state
        keys_to_remove = [key for key in st.session_state.keys() if key.endswith(f'_{username}')]
        for key in keys_to_remove:
            del st.session_state[key]

        st.success(f"🗑️ All data reset for user: {username}")
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
        """Main application runner"""
        if st.session_state.authentication_status == True:
            self.render_main_app()
        else:
            self.render_login_page()


if __name__ == "__main__":
    ChatApp().run()
