import streamlit as st
import pandas as pd
import os

from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool
from llama_index.experimental.query_engine import PandasQueryEngine


file_formats = {
    "csv": pd.read_csv,
    "xls": pd.read_excel,
    "xlsx": pd.read_excel,
    "xlsm": pd.read_excel,
    "xlsb": pd.read_excel,
}


def clear_submit():
    """
    Clear the Submit Button State
    Returns:

    """
    st.session_state["submit"] = False # False: rebuild an agent due to file changed


@st.cache_data(ttl="2h")
def load_data(uploaded_file):
    try:
        ext = os.path.splitext(uploaded_file.name)[1][1:].lower()
    except:
        ext = uploaded_file.split(".")[-1]
    if ext in file_formats:
        return file_formats[ext](uploaded_file)
    else:
        st.error(f"Unsupported file format: {ext}")
        return None


st.set_page_config(page_title="LlamaIndex: Chat with pandas DataFrame", page_icon="🦜")
st.title("🦜 LlamaIndex: Chat with pandas DataFrame")

uploaded_file = st.file_uploader(
    "Upload a Data file",
    type=list(file_formats.keys()),
    help="Various File formats are Support",
    on_change=clear_submit,
)

if not uploaded_file:
    st.warning(
        "This app uses eval() and exec() which is vulnerable to arbitrary code execution. Please use caution in deploying and sharing this app."
    )

if uploaded_file:
    df = load_data(uploaded_file)

openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
if "messages" not in st.session_state or st.sidebar.button("Clear conversation history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(placeholder="What is this data about?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()
    elif not uploaded_file:
        st.info("Please upload your data file to continue.")
        st.stop()

    # settings of the openai model
    if ("model_init" not in st.session_state) or (st.session_state["model_init"] is False):
        llm = OpenAI(model="gpt-4-turbo", api_key=openai_api_key, temperature=0)
        Settings.llm = llm
        st.session_state["model_init"] = True
    
    # build or rebuild an agent
    if ("chat_engine" not in st.session_state) or (st.session_state["submit"] is False):
        query_engine = PandasQueryEngine(df=df, verbose=True)
        pandas_tool = QueryEngineTool.from_defaults(
            query_engine,
            name="PandasQueryEngine",
            description="A engine to get data analysis result of the uploaded data by natural language query.",
        )
        st.session_state["chat_engine"] = ReActAgent.from_tools([pandas_tool], verbose=True)
        st.session_state["submit"] = True # True: agnet has been rebuilt

    pandas_df_agent = st.session_state["chat_engine"]

    with st.chat_message("assistant"):
        response = pandas_df_agent.stream_chat(prompt)
        response_str = ""
        response_container = st.empty()
        for token in response.response_gen:
            response_str += token
            response_container.write(response_str)
        # st.write(response.response)
        st.session_state.messages.append({"role": "assistant", "content": response.response})