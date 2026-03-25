
import streamlit as st
import requests

st.set_page_config(page_title="Bridge Inspection AI Tool", layout="centered")

st.title("Bridge Inspection AI Tool")
st.write(
    "Upload a CSV file containing a REMARKS column. "
    "The tool will analyze each remark and determine whether bridge replacement is needed."
)

uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file is not None:
    st.success("File uploaded successfully.")

    if st.button("Analyze File"):
        with st.spinner("Analyzing file... please wait"):
            try:
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")
                }

                response = requests.post(
                    ""https://bridge-ai-tool.onrender.com/analyze/"",
                    files=files
                )

                if response.status_code == 200:
                    st.success("Analysis complete.")

                    st.download_button(
                        label="Download Results CSV",
                        data=response.content,
                        file_name="bridge_replacement_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.error(f"Backend error: {response.text}")

            except Exception as e:
                st.error(f"Error: {str(e)}")
