import streamlit as st


def footer_home():
    st.markdown("""
        <div style="margin-top:2rem; display:flex; gap:6px; justify-content:center; align-items:center">
            <p style="font-weight:bold; color:white;">Created with ❤️ by <a href="https://github.com/bhoomiguptaa1" target="_blank" style="color:white; text-decoration:underline;">Bhoomi Gupta</a></p>  
        </div>
    """, unsafe_allow_html=True)


def footer_dashboard():
    st.markdown("""
        <div style="margin-top:2rem; display:flex; gap:6px; justify-content:center; align-items:center">
            <p style="font-weight:bold; color:black;">Created with ❤️ by <a href="https://github.com/bhoomiguptaa1" target="_blank" style="color:#5865F2; text-decoration:underline;">Bhoomi Gupta</a></p>  
        </div>
    """, unsafe_allow_html=True)
