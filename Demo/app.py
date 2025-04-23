import streamlit as st
import pandas as pd
import openai
import json, os, time

openai.api_key = 

# set page
st.set_page_config(page_title="ChatPipe Lite", layout="wide")
st.title("📊 ChatPipe Lite: Data Cleaning with ChatGPT")


if "show_process" not in st.session_state:
    st.session_state["show_process"] = False
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "last_variables" not in st.session_state:
    st.session_state["last_variables"] = {}

# upload data 
uploaded_file = st.file_uploader("Upload your CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("### 🔍 Preview of your dataset:", df.head())

    # warning for missing value
    st.subheader("📊 Dataset Insights:")
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0]
    if not missing_cols.empty:
        st.warning("⚠️ Some columns contain missing values:")
        for col, count in missing_cols.items():
            st.write(f"• `{col}` has {count} missing values ({count / len(df):.1%})")
    else:
        st.success("✅ No missing values detected.")

    # use natural language 
    user_instruction = st.text_area("🧠 What do you want to do with this dataset?")

    if st.button("🚀 Generate transformation code"):
        st.session_state["show_process"] = not st.session_state["show_process"]

    if st.session_state["show_process"]:
        mentioned_cols = [col for col in df.columns if col in user_instruction]
        missing_related = [col for col in mentioned_cols if df[col].isnull().sum() > 0]

        if missing_related:
            st.warning(f"⚠️ Your instruction involves columns with missing values: {missing_related}")
            action = st.radio("How would you like to handle missing values?",
                              ["Drop rows", "Keep all", "Cancel"])

            if action == "Cancel":
                st.stop()
            elif action == "Drop rows":
                df = df.dropna(subset=missing_related)
                st.info(f"Dropped rows with missing values in {missing_related}")
            else:
                st.info("Proceeding without dropping missing values.")

        with st.spinner("Calling GPT... please wait"):
            profile = f"The dataset contains the following columns: {list(df.columns)}"
            prompt = f"""{profile}
User instruction: {user_instruction}

Generate only Python pandas code to apply the above transformation to a DataFrame named 'df'.
Make sure to handle missing values (e.g., with dropna or fillna) before performing type conversions or aggregations.
Do NOT include explanations or markdown. Output ONLY executable code."""

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                code = response.choices[0].message.content

                st.subheader("💡 Generated Code:")
                st.code(code, language="python")

                try:
                    exec_locals = {'df': df.copy()}
                    exec(code, {}, exec_locals)
                    new_df = exec_locals['df']

                    
                    st.session_state["last_result"] = new_df
                    st.session_state["last_variables"] = {k: v for k, v in exec_locals.items() if k != "df"}

                    # save history
                    os.makedirs("history", exist_ok=True)
                    ts = time.strftime("%Y%m%d-%H%M%S")
                    with open(f"history/transform_{ts}.json", "w") as f:
                        json.dump({"prompt": prompt, "code": code}, f, indent=2)

                except Exception as exec_err:
                    st.error(f"⚠️ Error during code execution:\n{exec_err}")

            except Exception as e:
                st.error(f"❌ Failed to get response from OpenAI API:\n{e}")

    if st.session_state["last_result"] is not None:
        st.success("✅ Transformation applied successfully!")
        st.write("### 📄 Transformed Data Preview:")
        st.dataframe(st.session_state["last_result"].head())
        csv = st.session_state["last_result"].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="transformed_data.csv",
            mime="text/csv",
        )

        for var_name, value in st.session_state["last_variables"].items():
            st.subheader(f"📤 Output: `{var_name}`")
            st.write(value)
