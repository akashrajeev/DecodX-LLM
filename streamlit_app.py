import requests
import streamlit as st

st.set_page_config(page_title="DecodX QA", page_icon="🤖", layout="wide")

st.title("DecodX Document Q&A")
st.caption("Upload files or pass a URL, then ask one or more questions.")

with st.sidebar:
    st.header("Configuration")
    api_base = st.text_input("API Base URL", value="http://127.0.0.1:8000")
    ocr_method = st.selectbox("OCR Method", ["auto", "easyocr", "tesseract", "gemini"], index=0)
    st.markdown("Backend health:")
    if st.button("Check Health", use_container_width=True):
        try:
            health = requests.get(f"{api_base}/health", timeout=10)
            st.success(f"Healthy ({health.status_code})")
            st.json(health.json())
        except Exception as exc:
            st.error(f"Health check failed: {exc}")

mode = st.radio("Input Type", ["URL", "File Upload"], horizontal=True)

questions_input = st.text_area(
    "Questions (one per line)",
    placeholder="What is the waiting period?\nWhat are exclusions?",
    height=130,
)
questions = [q.strip() for q in questions_input.splitlines() if q.strip()]

if mode == "URL":
    document_url = st.text_input("Document URL", placeholder="https://example.com/policy.pdf")
    run_clicked = st.button("Ask Questions", type="primary")
    if run_clicked:
        if not document_url.strip():
            st.error("Please enter a document URL.")
        elif not questions:
            st.error("Please add at least one question.")
        else:
            payload = {"documents": document_url.strip(), "questions": questions, "ocr_method": ocr_method}
            try:
                with st.spinner("Processing..."):
                    resp = requests.post(f"{api_base}/hackrx/run", json=payload, timeout=180)
                if not resp.ok:
                    st.error(f"Request failed ({resp.status_code}): {resp.text}")
                else:
                    data = resp.json()
                    st.success("Done")
                    if data.get("processing_info"):
                        st.subheader("Processing Info")
                        st.json(data["processing_info"])
                    st.subheader("Answers")
                    for idx, answer in enumerate(data.get("answers", []), start=1):
                        question_label = questions[idx - 1] if idx - 1 < len(questions) else f"Question {idx}"
                        st.markdown(f"**Q{idx}: {question_label}**")
                        st.write(answer)
            except Exception as exc:
                st.error(f"Error: {exc}")
else:
    files = st.file_uploader(
        "Upload files",
        type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"],
        accept_multiple_files=True,
    )
    run_clicked = st.button("Ask Questions", type="primary")
    if run_clicked:
        if not files:
            st.error("Please upload at least one file.")
        elif not questions:
            st.error("Please add at least one question.")
        else:
            multipart_files = []
            for file in files:
                content_type = file.type or "application/octet-stream"
                multipart_files.append(("files", (file.name, file.getvalue(), content_type)))

            form_data = [("ocr_method", ocr_method)] + [("questions", q) for q in questions]

            try:
                with st.spinner("Processing uploads..."):
                    resp = requests.post(
                        f"{api_base}/hackrx/upload-images",
                        files=multipart_files,
                        data=form_data,
                        timeout=300,
                    )
                if not resp.ok:
                    st.error(f"Request failed ({resp.status_code}): {resp.text}")
                else:
                    data = resp.json()
                    st.success("Done")
                    if data.get("processing_info"):
                        st.subheader("Processing Info")
                        st.json(data["processing_info"])
                    st.subheader("Answers")
                    for idx, answer in enumerate(data.get("answers", []), start=1):
                        question_label = questions[idx - 1] if idx - 1 < len(questions) else f"Question {idx}"
                        st.markdown(f"**Q{idx}: {question_label}**")
                        st.write(answer)
            except Exception as exc:
                st.error(f"Error: {exc}")
