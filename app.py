import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Page Configuration
st.set_page_config(
    page_title="Supercapacitor & LDH Electrochemical Analyzer",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Electrochemical Analysis Dashboard (CV, GCD, EIS)")
st.markdown("Upload your Excel or CSV files below to automatically inspect, analyze, and visualize your supercapacitor data.")

# --- Sidebar Controls ---
st.sidebar.header("🧪 Experimental Parameters")
default_mass_mg = st.sidebar.number_input("Active Mass (mg)", min_value=0.1, value=2.0, step=0.1)
default_current_mA = st.sidebar.number_input("Applied Current for GCD (mA)", min_value=0.1, value=5.0, step=0.5)

# --- File Uploader ---
uploaded_files = st.file_uploader(
    "Upload your Excel (.xlsx, .xls) or CSV files", 
    type=['xlsx', 'xls', 'csv'], 
    accept_multiple_files=True
)

def classify_data(filename, columns):
    """Classifies file/sheet type as CV, GCD, or EIS based on name or headers."""
    f_up = filename.upper()
    cols_low = [str(c).lower().strip() for c in columns]
    
    if 'CV' in f_up or 'SCAN' in f_up:
        return 'CV'
    if 'GCD' in f_up or 'CGD' in f_up or 'CHARGE' in f_up:
        return 'GCD'
    if 'EIS' in f_up or 'IMP' in f_up:
        return 'EIS'
        
    # Check headers
    if any('freq' in c for c in cols_low) or any("z'" in c or 'real' in c for c in cols_low):
        return 'EIS'
    if any('time' in c for c in cols_low) and any('pot' in c for c in cols_low):
        return 'GCD'
    if any('pot' in c for c in cols_low) and any('curr' in c for c in cols_low):
        return 'CV'
        
    return 'UNKNOWN'

if uploaded_files:
    gcd_summary_records = []
    
    tab1, tab2, tab3 = st.tabs(["📈 CV Analysis", "🔋 GCD Analysis", "Ω EIS Nyquist Analysis"])
    
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        
        # Read file
        try:
            if filename.endswith(('.xlsx', '.xls')):
                # Check sheets
                xl = pd.ExcelFile(uploaded_file)
                sheets = xl.sheet_names
            else:
                sheets = ['Sheet1']
                df_single = pd.read_csv(uploaded_file, sep=None, engine='python')
        except Exception as e:
            st.error(f"Error reading {filename}: {e}")
            continue
            
        for sheet in sheets:
            try:
                if filename.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file, sheet_name=sheet).dropna(how='all')
                else:
                    df = df_single
                    
                if df.empty or len(df.columns) < 2:
                    continue
                    
                test_type = classify_data(f"{filename}_{sheet}", df.columns)
                
                # --------------------------------------------------------------
                # 1. CV TAB
                # --------------------------------------------------------------
                if test_type == 'CV':
                    with tab1:
                        st.subheader(f"Cyclic Voltammetry: {filename} [{sheet}]")
                        pot_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['pot', 'volt', 'ewe'])), df.columns[0])
                        curr_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['curr', 'amp', '<i>'])), df.columns[1])
                        
                        x = pd.to_numeric(df[pot_col], errors='coerce').dropna()
                        y = pd.to_numeric(df[curr_col], errors='coerce').dropna()
                        
                        fig, ax = plt.subplots(figsize=(6, 4))
                        ax.plot(x, y, color='#1f77b4', lw=1.8)
                        ax.axhline(0, color='gray', linestyle='--', lw=0.8)
                        ax.axvline(0, color='gray', linestyle='--', lw=0.8)
                        ax.set_xlabel(pot_col, fontweight='bold')
                        ax.set_ylabel(curr_col, fontweight='bold')
                        ax.grid(True, linestyle=':', alpha=0.6)
                        st.pyplot(fig)

                # --------------------------------------------------------------
                # 2. GCD TAB
                # --------------------------------------------------------------
                elif test_type == 'GCD':
                    with tab2:
                        st.subheader(f"Galvanostatic Charge-Discharge: {filename} [{sheet}]")
                        time_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['time', 'sec', '(s)'])), df.columns[0])
                        pot_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['pot', 'volt', 'ewe'])), df.columns[1])
                        
                        clean_df = df[[time_col, pot_col]].apply(pd.to_numeric, errors='coerce').dropna()
                        time = clean_df[time_col].values
                        potential = clean_df[pot_col].values
                        
                        if len(time) > 5:
                            max_idx = np.argmax(potential)
                            charge_time = time[:max_idx + 1]
                            discharge_time = time[max_idx:]
                            discharge_pot = potential[max_idx:]
                            
                            # Calculations
                            v_max = potential[max_idx]
                            v_after_drop = discharge_pot[1] if len(discharge_pot) > 1 else v_max
                            ir_drop = abs(v_max - v_after_drop)
                            
                            t_charge = charge_time[-1] - charge_time[0] if len(charge_time) > 1 else 0
                            t_discharge = discharge_time[-1] - discharge_time[0] if len(discharge_time) > 1 else 0
                            v_min = np.min(discharge_pot)
                            delta_v = (v_max - ir_drop) - v_min
                            
                            I_amps = default_current_mA / 1000.0
                            m_grams = default_mass_mg / 1000.0
                            cs = (I_amps * t_discharge) / (m_grams * delta_v) if (delta_v > 0 and m_grams > 0) else 0.0
                            efficiency = (t_discharge / t_charge) * 100.0 if t_charge > 0 else 0.0
                            
                            gcd_summary_records.append({
                                'File': filename,
                                'Sheet': sheet,
                                'IR Drop (V)': round(ir_drop, 4),
                                'Discharge Time (s)': round(t_discharge, 2),
                                'Specific Capacitance (F/g)': round(cs, 2),
                                'Coulombic Efficiency (%)': round(efficiency, 2)
                            })
                            
                            fig, ax = plt.subplots(figsize=(6, 4))
                            ax.plot(time, potential, color='#2ca02c', lw=1.8)
                            ax.set_xlabel(time_col, fontweight='bold')
                            ax.set_ylabel(pot_col, fontweight='bold')
                            ax.grid(True, linestyle=':', alpha=0.6)
                            st.pyplot(fig)

                # --------------------------------------------------------------
                # 3. EIS TAB
                # --------------------------------------------------------------
                elif test_type == 'EIS':
                    with tab3:
                        st.subheader(f"EIS Nyquist Plot: {filename} [{sheet}]")
                        z_real_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['real', "z'", 're('])), df.columns[1])
                        z_imag_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['imag', "z''", 'im('])), df.columns[2])
                        
                        clean_df = df[[z_real_col, z_imag_col]].apply(pd.to_numeric, errors='coerce').dropna()
                        z_real = clean_df[z_real_col].values
                        z_imag = clean_df[z_imag_col].values
                        y_nyquist = -z_imag if np.mean(z_imag) < 0 else z_imag
                        
                        fig, ax = plt.subplots(figsize=(5, 5))
                        ax.plot(z_real, y_nyquist, marker='o', markersize=4, lw=1.5, color='#d62728')
                        ax.set_xlabel(r"$Z' \ (\Omega)$", fontweight='bold')
                        ax.set_ylabel(r"$-Z'' \ (\Omega)$", fontweight='bold')
                        ax.set_aspect('equal', adjustable='box')
                        ax.grid(True, linestyle=':', alpha=0.6)
                        st.pyplot(fig)
                        
            except Exception as e:
                continue

    # --- Summary Table Display ---
    if gcd_summary_records:
        st.markdown("---")
        st.header("📊 Compiled GCD Performance Summary Table")
        summary_df = pd.DataFrame(gcd_summary_records)
        st.dataframe(summary_df, use_container_width=True)
        
        # CSV Download Button
        csv_data = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download GCD Summary as CSV",
            data=csv_data,
            file_name="gcd_electrochemical_summary.csv",
            mime="text/csv"
        )
else:
    st.info("👆 Please upload your electrochemical data files above to get started.")