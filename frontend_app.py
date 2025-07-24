import streamlit as st
import requests

st.set_page_config(page_title="Court Order Processor", layout="centered")
st.title("🏛️ Court Order Document Processor")
# background theme
st.markdown(
    """
    <style>
    /* Base dark background and fonts */
    html, body, [class*="stApp"] {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: 'Segoe UI', sans-serif;
    }

    /* Headings */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #f0f6fc;
    }

    /* Text Blocks */
    .stMarkdown, .stText, .stSubheader {
        background-color: #161b22;
        color: #c9d1d9;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(255, 255, 255, 0.05);
        margin-bottom: 1rem;
    }

    /* Primary Button */
    button[kind="primary"] {
        background-color: transparent !important;
        color: #f85149 !important;
        border: 2px solid #f85149 !important;
        border-radius: 8px;
        font-weight: bold;
        padding: 0.6em 1.2em;
        transition: all 0.3s ease;
    }

    button[kind="primary"]:hover {
        background-color: #8b0000 !important;
        color: white !important;
        transform: scale(1.03);
    }

    /* File uploader box */
    .stFileUploader > div:first-child {
        background-color: #161b22;
        border: 2px dashed #30363d;
        border-radius: 10px;
        padding: 1.2rem;
        color: #8b949e;
    }

    /* Input fields */
    input, textarea {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
    }

    /* Sidebar (if used) */
    .css-1d391kg, .css-1lcbmhc {
        background-color: #0d1117 !important;
    }

    /* Warning alert customization */
    .stAlert[data-testid="stAlert-warning"] {
        background-color: #b08900;
        color: white;
        border: 1px solid #f2cc60;
    }

    /* Section separator for 'Processing Outcome' */
    h2:has-text("Processing Outcome") {
        border-top: 1px solid #30363d;
        padding-top: 1rem;
        margin-top: 2rem;
    }

    /* Smooth font rendering */
    html {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    </style>
    """,
    unsafe_allow_html=True
)




API_URL = "http://localhost:8000/process_doc"

uploaded_file = st.file_uploader(" Upload a court order PDF for process", type=["pdf"])

if uploaded_file:
    st.success("PDF uploaded successfully!")

    if st.button("Process Court Order"):
        try:
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            response = requests.post(API_URL, files=files)

            if response.status_code == 200:
                data = response.json()
                # # print(data)
                # st.subheader(" Extracted Fields")
                # # st.markdown(f"**National ID:** `{data.get('national_id', 'N/A')}`")
                # st.markdown(f"**LLM Action Message:**\n\n```\n{data.get('llm_response', 'N/A')}\n```")
                # # with st.expander(" Raw LLM Response"):
                # #     st.text(data.get("llm_response", ""))

                st.subheader("Processing Outcome")
                status = data.get("status", "")

                if status == "success":
                    st.success(f"Action completed successfully!")
                    st.markdown(f"**Customer ID:** `{data.get('customer_id', 'N/A')}`")
                    st.markdown(f"**Result:** {data.get('result')}")
                elif status == "discarded":
                    st.warning("Court order discarded: Person is not a bank customer.")
                    st.markdown(f"**Reason:** {data.get('error')}")
                elif status == "discardaction":
                    st.warning("This specific type of action is not found")
                    st.markdown(f"**Reason:** {data.get('error')}")
                elif status == "executed":
                     st.warning(f"**Action:** `{data.get('action', 'N/A')}`")
                     st.markdown(f"**Result:** {data.get('result', 'No result available')}")

                elif status == "failed":
                    st.error("Action not supported.")
                    st.markdown(f"**Reason:** {data.get('error')}")
                else:
                    st.error("Unexpected status from backend.")
                    st.json(data)

            else:
                st.error(f"Backend Error: {response.status_code}")
                st.text(response.text)

        except Exception as e:
            st.exception(f"Exception occurred: {e}")
