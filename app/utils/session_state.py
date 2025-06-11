# utils/session_state.py

def initialize_session_state_variables(st):
    if "uploaded_pdfs" not in st.session_state:
        st.session_state.uploaded_pdfs = []
    if "uploaded_urls" not in st.session_state:
        st.session_state.uploaded_urls = []
    if "previous_upload_docs_length" not in st.session_state:
        st.session_state.previous_upload_docs_length = 0
    if "vectordb" not in st.session_state:
        st.session_state.vectordb = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
