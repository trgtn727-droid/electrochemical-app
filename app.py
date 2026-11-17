import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# --- Page Configuration ---
st.set_page_config(page_title="Electrochemical Data Analysis Tool", layout="wide")

st.title("Electrochemical Data Analysis Tool")
st.markdown(
    "Upload your galvanostatic charge-discharge (GCD) Excel files to analyze"
    " electrochemical performance and calculate specific capacitance."
)

# --- Sidebar Inputs ---
st.sidebar.header("Analysis Parameters")
mass_mg = st.sidebar.number_input(
    "Active Mass (mg)", min_value=0.1, value=10.0, step=0.5
)
m = mass_mg / 1000.0  # convert mg to grams

# --- File Uploader (Accepts any uploaded files) ---
uploaded_files = st.file_uploader(
    "Upload Electrochemical Excel Files (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=True,
)

if uploaded_files:
  results = []
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

  colors = plt.cm.tab10(np.linspace(0, 1, len(uploaded_files)))

  for idx, uploaded_file in enumerate(uploaded_files):
    df = pd.read_excel(uploaded_file).iloc[:, 0:3].dropna()
    t = df.iloc[:, 0].values
    I = df.iloc[:, 1].values
    E = df.iloc[:, 2].values

    filename = uploaded_file.name
    color = colors[idx]

    # 1. Plot Full GCD Curve
    ax1.plot(t, E, label=filename, color=color, linewidth=1.8)

    # 2. Extract Discharge Segment
    dis_start = np.where(I < 0)[0][0]
    t_dis = t[dis_start - 1 :] - t[dis_start - 1]
    E_dis = E[dis_start - 1 :]
    ax2.plot(t_dis, E_dis, label=filename, color=color, linewidth=1.8)

    # 3. Calculations
    dt_step = t[-1] - t[dis_start - 1]
    I_dis_vals = np.abs(I[dis_start:]) / 1000.0  # Amperes
    I_avg = np.mean(I_dis_vals)

    dV_actual = E[dis_start - 1] - E[-1]
    dV_ir = E_dis[0] - E[-1]

    Cs_std = (I_avg * dt_step) / (m * dV_actual)
    Cs_ir = (I_avg * (t_dis[-1] - t_dis[0])) / (m * dV_ir)
    Qs_mAh = (I_avg * dt_step) / (m * 3.6)

    results.append({
        "File": filename,
        "Current (mA)": round(I_avg * 1000, 2),
        "Current Density (A/g)": round(I_avg / m, 2),
        "Discharge Time (s)": round(dt_step, 1),
        "Potential Window (V)": round(dV_actual, 3),
        "Standard Cs (F/g)": round(Cs_std, 2),
        "IR-Corrected Cs (F/g)": round(Cs_ir, 2),
        "Specific Capacity (mAh/g)": round(Qs_mAh, 2),
    })

  # Format Subplots
  ax1.set_title(
      "Galvanostatic Charge–Discharge (GCD) Curves",
      fontsize=12,
      fontweight="bold",
  )
  ax1.set_xlabel("Time (s)", fontsize=10, fontweight="bold")
  ax1.set_ylabel("Potential, E (V)", fontsize=10, fontweight="bold")
  ax1.grid(True, linestyle="--", alpha=0.35)
  ax1.legend(fontsize=9)

  ax2.set_title("Galvanostatic Discharge Profiles", fontsize=12, fontweight="bold")
  ax2.set_xlabel("Discharge Time (s)", fontsize=10, fontweight="bold")
  ax2.set_ylabel("Potential, E (V)", fontsize=10, fontweight="bold")
  ax2.grid(True, linestyle="--", alpha=0.35)
  ax2.legend(fontsize=9)

  plt.tight_layout()

  st.subheader("Electrochemical Performance Curves")
  st.pyplot(fig)

  st.subheader("Calculated Performance Metrics")
  res_df = pd.DataFrame(results)
  st.dataframe(res_df, use_container_width=True)
else:
  st.info(
      "Please upload one or more Excel files using the file uploader above to"
      " begin analysis."
  )
