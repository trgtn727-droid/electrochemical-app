import streamlit as st
import pandas as pd
import numpy as np

st.title("Electrochemical Data Analysis Tool")

# Create separate tabs for each technique
tab_cv, tab_gcd, tab_eis = st.tabs(["Cyclic Voltammetry (CV)", "Galvanostatic Charge-Discharge (GCD)", "EIS Analysis"])

# --- CV TAB (Multi-File Upload Enabled) ---
with tab_cv:
    st.header("Cyclic Voltammetry (CV) - Multi-File Upload")
    
    # accept_multiple_files=True allows selecting multiple files at once
    cv_files = st.file_uploader(
        "Select and upload multiple CV files (Excel or CSV)", 
        type=["xlsx", "csv"], 
        accept_multiple_files=True, 
        key="cv_uploader"
    )
    
    if cv_files:
        st.success(f"Successfully loaded {len(cv_files)} CV file(s)!")
        
        # Shared parameters for mass and potential window
        col1, col2 = st.columns(2)
        with col1:
            mass_mg = st.number_input("Active Mass (mg) for all files", value=2.0, key="cv_mass")
            mass_g = mass_mg / 1000.0
        with col2:
            delta_v = st.number_input("Potential Window ΔV (V)", value=0.8, key="cv_deltav")
            
        st.divider()
        
        # Loop through each uploaded file
        for cv_file in cv_files:
            try:
                df_cv = pd.read_csv(cv_file) if cv_file.name.endswith('.csv') else pd.read_excel(cv_file)
                
                st.subheader(f"File: {cv_file.name}")
                
                # Map columns for CV (E/V and I/A)
                pot_col = next((c for c in df_cv.columns if any(k in str(c).lower() for k in ['pot', 'volt', 'e/v', 'potential'])), df_cv.columns[0])
                curr_col = next((c for c in df_cv.columns if any(k in str(c).lower() for k in ['curr', 'amp', '<i>', 'i/a'])), df_cv.columns[1])
                
                # Display individual plot
                st.line_chart(df_cv[[pot_col, curr_col]])
                
                # Scan rate specific to this file
                scan_rate_mv = st.number_input(f"Scan Rate (mV/s) for {cv_file.name}", value=10.0, key=f"rate_{cv_file.name}")
                scan_rate_v_s = scan_rate_mv / 1000.0
                
                # Calculate capacitance button per file
                if st.button(f"Calculate Specific Capacitance for {cv_file.name}", key=f"btn_{cv_file.name}"):
                    current_amp = df_cv[curr_col] / 1000.0
                    potential = df_cv[pot_col]
                    integral_area = np.trapz(current_amp, potential)
                    cap_f_g = np.abs(integral_area) / (2 * mass_g * scan_rate_v_s * delta_v)
                    st.metric(label=f"Specific Capacitance ({cv_file.name})", value=f"{cap_f_g:.2f} F/g")
                
                st.divider()
                
            except Exception as e:
                st.error(f"Error processing {cv_file.name}: {e}")

# --- GCD TAB ---
with tab_gcd:
    st.header("Galvanostatic Charge-Discharge (GCD)")
    gcd_file = st.file_uploader("Upload GCD file (Excel or CSV)", type=["xlsx", "csv"], key="gcd_uploader")
    if gcd_file is not None:
        try:
            df_gcd = pd.read_csv(gcd_file) if gcd_file.name.endswith('.csv') else pd.read_excel(gcd_file)
            st.success("GCD file loaded successfully!")
            
            time_col = next((c for c in df_gcd.columns if any(k in str(c).lower() for k in ['time', 't/s', 'time /s'])), df_gcd.columns[0])
            curr_col = next((c for c in df_gcd.columns if any(k in str(c).lower() for k in ['curr', 'i/ma', 'i /ma', 'amp'])), df_gcd.columns[1])
            pot_col = next((c for c in df_gcd.columns if any(k in str(c).lower() for k in ['pot', 'volt', 'e/v', 'e /v', 'potential'])), df_gcd.columns[2])
            
            st.line_chart(df_gcd[[time_col, pot_col]])
        except Exception as e:
            st.error(f"Error parsing GCD file: {e}")

# --- EIS TAB ---
with tab_eis:
    st.header("Electrochemical Impedance Spectroscopy (EIS)")
    eis_file = st.file_uploader("Upload EIS file (Excel or CSV)", type=["xlsx", "csv"], key="eis_uploader")
    if eis_file is not None:
        try:
            df_eis = pd.read_csv(eis_file) if eis_file.name.endswith('.csv') else pd.read_excel(eis_file)
            st.success("EIS file loaded successfully!")
            st.line_chart(df_eis)
        except Exception as e:
            st.error(f"Error parsing EIS file: {e}")
