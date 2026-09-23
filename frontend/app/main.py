import os
import requests
import streamlit as st


st.set_page_config(
    page_title="CloudVault",
    page_icon="☁️",
    layout="wide",
)


API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000",
)

def api_request(
    method: str,
    endpoint: str,
    token: str | None = None,
    **kwargs,
):
    headers = kwargs.pop("headers", {})

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return requests.request(
        method,
        f"{API_URL}{endpoint}",
        headers=headers,
        timeout=60,
        **kwargs,
    )


if "token" not in st.session_state:
    st.session_state.token = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None


st.title("☁️ CloudVault")
st.caption("Secure PDF storage and AI document chat")


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

if not st.session_state.token:

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Login")

        email = st.text_input(
            "Email",
            key="login_email",
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )

        if st.button("Login", type="primary"):
            if not email or not password:
                st.warning("Enter your email and password.")
            else:
                try:
                    response = api_request(
                        "POST",
                        "/auth/login-json",
                        json={
                            "email": email,
                            "password": password,
                        },
                    )

                    if response.ok:
                        data = response.json()

                        st.session_state.token = data["access_token"]
                        st.session_state.user_email = email

                        st.success("Login successful.")
                        st.rerun()

                    else:
                        try:
                            detail = response.json().get(
                                "detail",
                                "Login failed",
                            )
                        except Exception:
                            detail = "Login failed"

                        st.error(detail)

                except requests.RequestException as exc:
                    st.error(f"Backend connection failed: {exc}")

    with register_tab:
        st.subheader("Create account")

        register_email = st.text_input(
            "Email",
            key="register_email",
        )

        register_password = st.text_input(
            "Password",
            type="password",
            key="register_password",
        )

        if st.button("Register"):
            if not register_email or not register_password:
                st.warning("Enter an email and password.")
            else:
                try:
                    response = api_request(
                        "POST",
                        "/auth/register",
                        json={
                            "email": register_email,
                            "password": register_password,
                        },
                    )

                    if response.ok:
                        st.success(
                            "Registration successful. You can now log in."
                        )
                    else:
                        try:
                            detail = response.json().get(
                                "detail",
                                "Registration failed",
                            )
                        except Exception:
                            detail = "Registration failed"

                        st.error(detail)

                except requests.RequestException as exc:
                    st.error(f"Backend connection failed: {exc}")

    st.stop()


# ---------------------------------------------------------
# Logged-in application
# ---------------------------------------------------------

st.sidebar.write(
    f"Logged in as: **{st.session_state.user_email}**"
)

if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.session_state.user_email = None
    st.rerun()


# ---------------------------------------------------------
# Upload
# ---------------------------------------------------------

st.header("My Files")

uploaded_file = st.file_uploader(
    "Upload a PDF",
    type=["pdf"],
)

if uploaded_file is not None:

    if st.button("Upload PDF"):
        try:
            response = api_request(
                "POST",
                "/files/upload",
                token=st.session_state.token,
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf",
                    )
                },
            )

            if response.ok:
                st.success("PDF uploaded successfully.")
                st.rerun()

            else:
                try:
                    detail = response.json().get(
                        "detail",
                        "Upload failed",
                    )
                except Exception:
                    detail = "Upload failed"

                st.error(detail)

        except requests.RequestException as exc:
            st.error(f"Backend connection failed: {exc}")


# ---------------------------------------------------------
# File list
# ---------------------------------------------------------

try:
    response = api_request(
        "GET",
        "/files/",
        token=st.session_state.token,
    )

    if response.status_code == 401:
        st.session_state.token = None
        st.session_state.user_email = None
        st.rerun()

    if response.ok:
        files = response.json()

        if not files:
            st.info("No PDF files found.")

        for file in files:

            st.divider()

            col1, col2, col3 = st.columns([5, 1, 1])

            with col1:
                st.write(f"**{file['filename']}**")
                st.caption(
                    f"Size: {file['file_size']} bytes"
                )

            with col2:
                if st.button(
                    "Download",
                    key=f"download_{file['id']}",
                ):
                    try:
                        download_response = api_request(
                            "GET",
                            f"/files/{file['id']}/download",
                            token=st.session_state.token,
                        )

                        if download_response.ok:
                            download_data = download_response.json()

                            file_response = requests.get(
                                download_data["download_url"],
                                timeout=60,
                            )

                            if file_response.ok:
                                st.download_button(
                                    label="Save PDF",
                                    data=file_response.content,
                                    file_name=file["filename"],
                                    mime="application/pdf",
                                    key=f"save_{file['id']}",
                                )
                            else:
                                st.error("Could not download PDF.")

                        else:
                            st.error("Could not create download link.")

                    except requests.RequestException as exc:
                        st.error(f"Download failed: {exc}")

            with col3:
                if st.button(
                    "Delete",
                    key=f"delete_{file['id']}",
                ):
                    try:
                        delete_response = api_request(
                            "DELETE",
                            f"/files/{file['id']}",
                            token=st.session_state.token,
                        )

                        if delete_response.ok:
                            st.success("File deleted.")
                            st.rerun()
                        else:
                            st.error("Delete failed.")

                    except requests.RequestException as exc:
                        st.error(f"Delete failed: {exc}")


        # -------------------------------------------------
        # AI Chat
        # -------------------------------------------------

        st.divider()
        st.header("💬 Chat with a PDF")

        if files:
            file_options = {
                file["filename"]: file["id"]
                for file in files
            }

            selected_filename = st.selectbox(
                "Select a PDF",
                list(file_options.keys()),
            )

            selected_file_id = file_options[selected_filename]

            question = st.text_input(
                "Ask a question about this PDF",
                placeholder="Example: What is this document about?",
            )

            if st.button("Ask AI", type="primary"):
                if not question.strip():
                    st.warning("Enter a question.")
                else:
                    with st.spinner(
                        "Searching document and generating answer..."
                    ):
                        try:
                            chat_response = api_request(
                                "GET",
                                f"/files/{selected_file_id}/chat",
                                token=st.session_state.token,
                                params={
                                    "q": question,
                                },
                            )

                            if chat_response.ok:
                                result = chat_response.json()

                                st.subheader("Answer")
                                st.write(result["answer"])

                                sources = result.get("sources", [])

                                if sources:
                                    st.subheader("Sources")

                                    for source in sources:
                                        distance = source.get("distance")

                                        if distance is not None:
                                            st.write(
                                                f"- Page "
                                                f"{source['page_number']} "
                                                f"(chunk "
                                                f"{source['chunk_index']}, "
                                                f"distance "
                                                f"{distance})"
                                            )
                                        else:
                                            st.write(
                                                f"- Page "
                                                f"{source['page_number']} "
                                                f"(chunk "
                                                f"{source['chunk_index']})"
                                            )

                            else:
                                try:
                                    detail = chat_response.json().get(
                                        "detail",
                                        "AI request failed",
                                    )
                                except Exception:
                                    detail = "AI request failed"

                                st.error(detail)

                        except requests.RequestException as exc:
                            st.error(
                                f"AI request failed: {exc}"
                            )

except requests.RequestException as exc:
    st.error(f"Backend connection failed: {exc}")
