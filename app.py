import io
import zipfile
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.signal import find_peaks

st.set_page_config(
    page_title="Electrochemical CV Kinetics & Capacitance Analyzer",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Electrochemical Cyclic Voltammetry (CV) Modeling & Kinetics App")
st.markdown(
    "Upload multi-scan-rate CV data files (`.csv`, `.txt`, `.xls`, `.xlsx`) to automatically evaluate "
    "**Specific Capacitance ($C_s$)**, **Redox Peaks ($E_{pa}, E_{pc}$)**, **Storage Mechanism ($b$-value)**, "
    "and **Dunn's Current Separation ($k_1 v$ vs. $k_2 v^{0.5}$)**."
)

# Sidebar Inputs
st.sidebar.header("1. Experimental Parameters")
electrode_mass_mg = st.sidebar.number_input(
    "Active Electrode Mass (mg)", min_value=0.001, value=1.000, step=0.100, format="%.3f"
)
electrode_mass_g = electrode_mass_mg / 1000.0

target_scan_rate_mv = st.sidebar.number_input(
    "Target Scan Rate for Dunn's Split (mV/s)", min_value=0.1, value=20.0, step=1.0
)
target_scan_rate_vs = target_scan_rate_mv / 1000.0

skip_rows = st.sidebar.number_input(
    "Header Rows to Skip (if potentiostat metadata exists)", min_value=0, value=0, step=1
)

st.sidebar.header("2. Upload CV Files")
uploaded_files = st.sidebar.file_uploader(
    "Select CV files (CSV, TXT, XLS, XLSX)",
    type=["csv", "txt", "xls", "xlsx"],
    accept_multiple_files=True
)

def parse_uploaded_file(uploaded_file, skiprows=0):
    """Reads CSV, TXT, XLS, or XLSX and extracts Potential (V) and Current (A)."""
    name = uploaded_file.name.lower()
    if name.endswith((".xls", ".xlsx")):
        df = pd.read_excel(uploaded_file, skiprows=skiprows)
    else:
        df = pd.read_csv(uploaded_file, sep=None, engine="python", skiprows=skiprows)
    
    df = df.dropna(axis=1, how="all")
    numeric_cols = []
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() > len(df) * 0.5:
            df[col] = converted
            numeric_cols.append(col)
            
    df = df[numeric_cols].dropna()
    if df.shape[1] < 2:
        raise ValueError(f"File '{uploaded_file.name}' must have at least two numeric columns (Potential, Current).")
        
    v_raw = df.iloc[:, 0].values.astype(float)
    i_raw = df.iloc[:, 1].values.astype(float)
    return v_raw, i_raw

if uploaded_files:
    st.subheader("3. Assign Scan Rates (mV/s) to Uploaded Files")
    cols = st.columns(min(len(uploaded_files), 4))
    file_scan_rates_mv = []
    
    for idx, f in enumerate(uploaded_files):
        with cols[idx % 4]:
            digits = "".join([c if c.isdigit() or c == "." else " " for c in f.name]).split()
            default_sr = float(digits[0]) if digits and 0.1 <= float(digits[0]) <= 5000 else (idx + 1) * 10.0
            sr = st.number_input(
                f"{f.name} (mV/s)",
                min_value=0.01,
                value=default_sr,
                step=1.0,
                key=f"sr_{idx}"
            )
            file_scan_rates_mv.append(sr)

    if st.button("🚀 Run Complete CV Modeling & Generate Report", type="primary"):
        try:
            paired = sorted(zip(file_scan_rates_mv, uploaded_files), key=lambda x: x[0])
            scan_rates_mv = np.array([p[0] for p in paired])
            scan_rates_vs = scan_rates_mv / 1000.0
            sorted_files = [p[1] for p in paired]

            raw_data = []
            for f in sorted_files:
                f.seek(0)
                v_raw, i_raw = parse_uploaded_file(f, skiprows=skip_rows)
                raw_data.append((v_raw, i_raw))

            v_min = max(d[0].min() for d in raw_data)
            v_max = min(d[0].max() for d in raw_data)
            if v_min >= v_max:
                v_min = raw_data[0][0].min()
                v_max = raw_data[0][0].max()
            voltages = np.linspace(v_min, v_max, 300)
            delta_V = v_max - v_min

            n_scans = len(scan_rates_vs)
            current_matrix = np.zeros((len(voltages), n_scans))
            peak_records = []

            for j, (v_raw, i_raw) in enumerate(raw_data):
                v_rate = scan_rates_vs[j]
                dv = np.diff(v_raw)
                anodic_mask = np.append(dv > 0, dv[-1] > 0)
                cathodic_mask = ~anodic_mask

                v_anodic, i_anodic = v_raw[anodic_mask], i_raw[anodic_mask]
                v_cathodic, i_cathodic = v_raw[cathodic_mask], i_raw[cathodic_mask]

                epa, ipa = np.nan, np.nan
                if len(i_anodic) > 5:
                    prom = (np.max(i_anodic) - np.min(i_anodic)) * 0.05
                    peaks_a, _ = find_peaks(i_anodic, prominence=prom)
                    if len(peaks_a) > 0:
                        max_p = peaks_a[np.argmax(i_anodic[peaks_a])]
                        epa, ipa = v_anodic[max_p], i_anodic[max_p]

                epc, ipc = np.nan, np.nan
                if len(i_cathodic) > 5:
                    prom_c = (np.max(i_cathodic) - np.min(i_cathodic)) * 0.05
                    peaks_c, _ = find_peaks(-i_cathodic, prominence=prom_c)
                    if len(peaks_c) > 0:
                        min_p = peaks_c[np.argmin(i_cathodic[peaks_c])]
                        epc, ipc = v_cathodic[min_p], i_cathodic[min_p]

                delta_ep = (epa - epc) * 1000.0 if (not np.isnan(epa) and not np.isnan(epc)) else np.nan
                peak_ratio = abs(ipa / ipc) if (not np.isnan(ipa) and not np.isnan(ipc) and ipc != 0) else np.nan

                loop_area = np.abs(np.trapz(i_raw, v_raw))
                cs_val = loop_area / (2.0 * electrode_mass_g * delta_V * v_rate)

                peak_records.append({
                    "Scan_Rate_mV_s": scan_rates_mv[j],
                    "Scan_Rate_V_s": v_rate,
                    "Specific_Capacitance_F_g": cs_val,
                    "Epa_V": epa,
                    "Ipa_A": ipa,
                    "Epc_V": epc,
                    "Ipc_A": ipc,
                    "Delta_Ep_mV": delta_ep,
                    "Ipa_Ipc_Ratio": peak_ratio
                })

                if len(v_anodic) > 5:
                    sort_idx = np.argsort(v_anodic)
                    current_matrix[:, j] = np.interp(voltages, v_anodic[sort_idx], i_anodic[sort_idx])
                else:
                    sort_idx = np.argsort(v_raw)
                    current_matrix[:, j] = np.interp(voltages, v_raw[sort_idx], i_raw[sort_idx])

            summary_df = pd.DataFrame(peak_records)
            cs_values = summary_df["Specific_Capacitance_F_g"].values

            b_values = np.zeros(len(voltages))
            r2_values = np.zeros(len(voltages))
            log_v = np.log(scan_rates_vs)
            for i in range(len(voltages)):
                log_i = np.log(np.abs(current_matrix[i, :]) + 1e-12)
                slope, _, r_val, _, _ = linregress(log_v, log_i)
                b_values[i] = slope
                r2_values[i] = r_val ** 2

            k1 = np.zeros(len(voltages))
            k2 = np.zeros(len(voltages))
            sqrt_v = np.sqrt(scan_rates_vs)
            for i in range(len(voltages)):
                y = current_matrix[i, :] / sqrt_v
                slope, intercept, _, _, _ = linregress(sqrt_v, y)
                k1[i] = slope
                k2[i] = intercept

            cap_current = k1 * target_scan_rate_vs
            diff_current = k2 * np.sqrt(target_scan_rate_vs)
            total_current = cap_current + diff_current
            cap_pct = (np.abs(cap_current) / (np.abs(total_current) + 1e-12)) * 100.0
            cap_pct = np.clip(cap_pct, 0.0, 100.0)

            kinetics_df = pd.DataFrame({
                "Potential_V": voltages,
                "b_value": b_values,
                "b_value_R2": r2_values,
                "k1_Capacitive_Coeff": k1,
                "k2_Diffusion_Coeff": k2,
                "Capacitive_Current_A": cap_current,
                "Diffusion_Current_A": diff_current,
                "Total_Current_A": total_current,
                "Capacitive_Contribution_%": cap_pct
            })

            mean_b = float(np.mean(b_values))
            mean_cap_pct = float(np.mean(cap_pct))
            retention = (cs_values[-1] / cs_values[0]) * 100.0 if cs_values[0] > 0 else 0.0

            if mean_b >= 0.85:
                mech_label = "EDLC / Surface-Controlled Capacitive"
            elif mean_b <= 0.60:
                mech_label = "Battery-Type Diffusion-Controlled"
            else:
                mech_label = "Hybrid Pseudocapacitive & Diffusion"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Dominant Mechanism", mech_label)
            m2.metric("Mean b-Value", f"{mean_b:.3f}")
            m3.metric(f"Capacitive Share @ {target_scan_rate_mv:.0f} mV/s", f"{mean_cap_pct:.1f}%")
            m4.metric("Max Cs / Rate Retention", f"{cs_values[0]:.1f} F/g ({retention:.1f}%)")

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            for j, (v_raw, i_raw) in enumerate(raw_data):
                axes[0, 0].plot(v_raw, i_raw * 1000, label=f"{scan_rates_mv[j]:.0f} mV/s")
                if not np.isnan(peak_records[j]["Epa_V"]):
                    axes[0, 0].plot(peak_records[j]["Epa_V"], peak_records[j]["Ipa_A"] * 1000, "r^", ms=6)
                if not np.isnan(peak_records[j]["Epc_V"]):
                    axes[0, 0].plot(peak_records[j]["Epc_V"], peak_records[j]["Ipc_A"] * 1000, "bv", ms=6)
            axes[0, 0].set_title("(a) Multi-Scan-Rate CV & Peak Detection", fontweight="bold")
            axes[0, 0].set_xlabel("Potential (V)")
            axes[0, 0].set_ylabel("Current (mA)")
            axes[0, 0].legend(fontsize=8)
            axes[0, 0].grid(True, alpha=0.3)

            axes[0, 1].plot(scan_rates_mv, cs_values, "ko-", lw=2, mfc="crimson", ms=7)
            axes[0, 1].set_title("(b) Rate Capability: Specific Capacitance vs. Scan Rate", fontweight="bold")
            axes[0, 1].set_xlabel("Scan Rate (mV/s)")
            axes[0, 1].set_ylabel("Specific Capacitance Cs (F/g)")
            axes[0, 1].grid(True, alpha=0.3)

            axes[1, 0].plot(voltages, b_values, "b-", lw=2)
            axes[1, 0].axhline(0.5, color="gray", ls="--", label="Diffusion Limit (b = 0.5)")
            axes[1, 0].axhline(1.0, color="red", ls="--", label="Capacitive Limit (b = 1.0)")
            axes[1, 0].set_title("(c) Potential-Resolved b-Values", fontweight="bold")
            axes[1, 0].set_xlabel("Potential (V)")
            axes[1, 0].set_ylabel("b-Value")
            axes[1, 0].set_ylim(0.2, 1.3)
            axes[1, 0].legend(fontsize=8)
            axes[1, 0].grid(True, alpha=0.3)

            axes[1, 1].plot(voltages, total_current * 1000, "k-", lw=2, label="Total Current")
            axes[1, 1].fill_between(
                voltages, 0, cap_current * 1000, color="salmon", alpha=0.5,
                label=f"Capacitive ({mean_cap_pct:.1f}%)"
            )
            axes[1, 1].plot(voltages, diff_current * 1000, "g--", lw=1.5, label="Diffusion Current")
            axes[1, 1].set_title(f"(d) Dunn's Separation @ {target_scan_rate_mv:.0f} mV/s", fontweight="bold")
            axes[1, 1].set_xlabel("Potential (V)")
            axes[1, 1].set_ylabel("Current (mA)")
            axes[1, 1].legend(fontsize=8)
            axes[1, 1].grid(True, alpha=0.3)

            plt.tight_layout()
            st.pyplot(fig)

            st.subheader("4. Extracted Peaks & Specific Capacitance Summary")
            st.dataframe(summary_df, use_container_width=True)

            st.subheader("5. Scientific Interpretation & Kinetic Analysis")
            interpretation_md = f"""
- **Mechanism Diagnosis:** Mean b-value is **{mean_b:.3f}** (**{mech_label}**), with **{mean_cap_pct:.1f}%** surface-controlled capacitive contribution and **{100.0 - mean_cap_pct:.1f}%** diffusion-controlled contribution at **{target_scan_rate_mv:.0f} mV/s**.
- **Double-Layer & Rate Behavior:** Operating potential window Delta V = {delta_V:.2f} V. Specific capacitance shifts from **{cs_values[0]:.2f} F/g** ({scan_rates_mv[0]:.0f} mV/s) to **{cs_values[-1]:.2f} F/g** ({scan_rates_mv[-1]:.0f} mV/s), retaining **{retention:.1f}%** of initial capacitance. For EDLCs, interfacial capacitance follows series Helmholtz and diffuse layers (1/C_dl = 1/C_H + 1/C_diff).
"""
            st.markdown(interpretation_md)

            zip_buffer = io.BytesIO()
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="png", dpi=300)
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                zf.writestr("1_Peak_and_Capacitance_Summary.csv", summary_df.to_csv(index=False))
                zf.writestr("2_Potential_Resolved_Kinetics.csv", kinetics_df.to_csv(index=False))
                zf.writestr("3_CV_Comprehensive_Analysis.png", img_buffer.getvalue())
                zf.writestr("4_Interpretation_Report.md", interpretation_md)

            st.download_button(
                label="📥 Download Complete Results Bundle (CSV + 300 DPI Figure + Report)",
                data=zip_buffer.getvalue(),
                file_name="CV_Analysis_Results_Bundle.zip",
                mime="application/zip"
            )

        except Exception as e:
            st.error(f"Error processing files: {e}")
else:
    st.info("👈 Upload your multi-scan-rate CV files (`.csv`, `.txt`, `.xls`, or `.xlsx`) from the sidebar to begin.")
