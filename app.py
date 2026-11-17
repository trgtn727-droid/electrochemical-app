import streamlit as st
import pandas as pd

st.title("Electrochemical Data Analysis Tool")

# Create separate tabs for each technique
tab_cv, tab_gcd, tab_eis = st.tabs(["Cyclic Voltammetry (CV)", "Galvanostatic Charge-Discharge (GCD)", "EIS Analysis"])

# --- CV TAB ---
with tab_cv:
    st.header("Cyclic Voltammetry")
    cv_file = st.file_uploader("Upload CV file (Excel or CSV)", type=["xlsx", "csv"], key="cv_uploader")
    if cv_file is not None:
        try:
            df_cv = pd.read_csv(cv_file) if cv_file.name.endswith('.csv') else pd.read_excel(cv_file)
            st.success("CV file loaded successfully!")
            
            # Map columns for CV (E/V and I/A)
            pot_col = next((c for c in df_cv.columns if any(k in str(c).lower() for k in ['pot', 'volt', 'e/v', 'potential'])), df_cv.columns[0])
            curr_col = next((c for c in df_cv.columns if any(k in str(c).lower() for k in ['curr', 'amp', '<i>', 'i/a'])), df_cv.columns[1])
            
            st.line_chart(df_cv[[pot_col, curr_col]])
        except Exception as e:
            st.error(f"Error parsing CV file: {e}")

# --- GCD TAB ---
with tab_gcd:
    st.header("Galvanostatic Charge-Discharge")
    gcd_file = st.file_uploader("Upload GCD file (Excel or CSV)", type=["xlsx", "csv"], key="gcd_uploader")
    if gcd_file is not None:
        try:
            df_gcd = pd.read_csv(gcd_file) if gcd_file.name.endswith('.csv') else pd.read_excel(gcd_file)
            st.success("GCD file loaded successfully!")
            
            # Map columns for GCD (Time /s, I /mA, E /V)
            time_col = next((c for c in df_gcd.columns if any(k in str(c).lower() for k in ['time', 't/s', 'time /s'])), df_gcd.columns[0])
            curr_col = next((c for c in df_gcd.columns if any(k in str(c).lower() for k in ['curr', 'i/ma', 'i /ma', 'amp'])), df_gcd.columns[1])
            pot_col = next((c for c in df_gcd.columns if any(k in str(c).lower() for k in ['pot', 'volt', 'e/v', 'e /v', 'potential'])), df_gcd.columns[2])
            
            # Plot Time vs Potential
            st.line_chart(df_gcd[[time_col, pot_col]])
        except Exception as e:
            st.error(f"Error parsing GCD file: {e}")

# --- EIS TAB ---
with tab_eis:
    st.header("Electrochemical Impedance Spectroscopy")
    eis_file = st.file_uploader("Upload EIS file (Excel or CSV)", type=["xlsx", "csv"], key="eis_uploader")
    if eis_file is not None:
        try:
            df_eis = pd.read_csv(eis_file) if eis_file.name.endswith('.csv') else pd.read_excel(eis_file)
            st.success("EIS file loaded successfully!")
            st.line_chart(df_eis)
        except Exception as e:
            st.error(f"Error parsing EIS file: {e}")
