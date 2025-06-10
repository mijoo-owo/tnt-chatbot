import os
import streamlit as st

from utils.save_docs import save_docs_to_vectordb
from utils.save_urls import save_url_to_vectordb
from utils.session_state import initialize_session_state_variables
from utils.prepare_vectordb import get_vectorstore, save_pdf_chunks
from utils.chatbot import chat

class ChatApp:
    """
    A Streamlit application for chatting with PDF documents.
    """

    def __init__(self):
        # Ensure the docs folder exists
        os.makedirs("docs", exist_ok=True)

        # Streamlit config & session state
        st.set_page_config(page_title="Chat with PDFs 📚")
        st.title("Chat with PDFs 📚")
        initialize_session_state_variables(st)

    def run(self):
        upload_docs = os.listdir("docs")

        # Sidebar: upload PDFs or URLs
        with st.sidebar:
            st.subheader("Your documents")
            if upload_docs:
                st.text(", ".join(upload_docs))
            else:
                st.info("No documents uploaded yet.")

            # PDF Upload
            st.subheader("Upload PDF documents")
            pdf_docs = st.file_uploader(
                "Select PDF(s) and click 'Process'", 
                type=["pdf"], 
                accept_multiple_files=True
            )
            if pdf_docs:
                new_files = save_docs_to_vectordb(pdf_docs, upload_docs)
                if new_files:
                    st.session_state.uploaded_pdfs += new_files
                    st.success(f"Saved files: {', '.join(new_files)}")

            # URL Processing
            st.subheader("Or enter a website URL")
            url = st.text_input("Website URL", placeholder="https://example.com/article")
            if url and st.button("Process URL"):
                fname, ftype = save_url_to_vectordb(url, upload_docs)
                if not fname:
                    st.info("This URL was already processed.")
                else:
                    if ftype == "pdf":
                        st.session_state.uploaded_pdfs.append(fname)
                        st.success(f"Downloaded PDF: {fname}")
                    else:
                        st.session_state.uploaded_urls.append(fname)
                        st.success(f"Saved HTML text: {fname}")

        # Rebuild vectorstore if new documents appear
        upload_docs = os.listdir("docs")
        if len(upload_docs) > st.session_state.previous_upload_docs_length:
            try:
                # 1) rebuild the vectorstore
                st.session_state.vectordb = get_vectorstore(
                    upload_docs, from_session_state=True
                )

                # 2) export all text chunks
                save_pdf_chunks(upload_docs)
                st.success("✅ Saved all text chunks to the `chunks/` folder.")

                # 3) update counter
                st.session_state.previous_upload_docs_length = len(upload_docs)

            except Exception as e:
                st.error(f"Error loading vector store or saving chunks: {e}")

        # Always show the chat interface
        st.session_state.chat_history = chat(
            st.session_state.chat_history,
            st.session_state.vectordb
        )

if __name__ == "__main__":
    ChatApp().run()
