import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import os

# ============================================
# CONFIGURATION
# ============================================
FIG_DIR = "figures"
os.makedirs(FIG_DIR, exist_ok=True)

st.set_page_config(page_title="GCP Login Activity Report", layout="wide")
st.title("🌐 GCP Login Activity Report Generator")
st.info("This report shows visualizations for the entire uploaded dataset. All figures are optimized for publication.")

# ============================================
# LOAD & PREPARE DATA
# ============================================
@st.cache_data
def load_data(file_path):
    """Loads, renames, cleans, and preprocesses the CSV data."""
    df = pd.read_csv(file_path)\
         .rename(columns={"actor_email_anonymized":"user_name",
         				"event_time_anonymized":"event_time",
                        "ip_city_anonymized":"city",
                        "ip_country_anonymized":"country",
                        "ip_address_anonymized":"ip_address"})
    
    # --- CRITICAL FIX: DO NOT force NaN to False. Keep the three states. ---
    # Convert to pandas' nullable boolean type which supports True, False, and NA.
    if 'is_suspicious' in df.columns:
        df['is_suspicious'] = df['is_suspicious'].astype('boolean')

    # Robustly handle potential empty values in other key categorical columns
    for col in ['event_name', 'login_type', 'is_second_factor']:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].fillna('Unknown')
            elif col == 'is_second_factor':
                 # This column can also have NaNs, treat them as a separate category
                 df[col] = df[col].astype('object').fillna('Unknown')

    df['event_time'] = pd.to_datetime(df['event_time'], format="mixed", utc=False)
    # df.dropna(subset=['event_time'], inplace=True)

    df['hour'] = df['event_time'].dt.hour
    df['day'] = df['event_time'].dt.date
    df['weekday'] = df['event_time'].dt.day_name()
    return df

uploaded_file = st.file_uploader("Upload your GCP login activity dataset (CSV)", type=["csv"])
if uploaded_file is None:
    st.warning("Please upload your dataset CSV file to generate the report.")
    st.stop()

df_full = load_data(uploaded_file)

# ============================================
# HELPER FUNCTIONS FOR PUBLICATION-QUALITY FIGURES
# ============================================
def save_and_download(fig, filename, caption, width=1200, height=700):
    """Saves a Plotly figure with custom dimensions and provides a download button."""
    try:
        fig.write_image(os.path.join(FIG_DIR, f"{filename}.png"), scale=3, width=width, height=height)
        fig.write_image(os.path.join(FIG_DIR, f"{filename}.pdf"), scale=3, width=width, height=height)
        img_bytes = fig.to_image(format="png", scale=3, width=width, height=height)
        st.download_button(label=f"📥 Download {caption} (PNG)", data=img_bytes, file_name=f"{filename}.png", mime="image/png")
    except Exception as e:
        st.error(f"Failed to save '{filename}'. Error: {e}. Please ensure you have 'kaleido' installed (`pip install kaleido`).")

def style_figure(fig, legend_title=None, margin=dict(t=100, b=80, l=80, r=40)):
    """Applies a consistent, publication-quality style to a Plotly figure."""
    fig.update_layout(title_x=0.5, font=dict(size=15, family="Arial"), title_font=dict(size=24, family="Arial Black"), margin=margin, legend_title_text=legend_title)
    return fig

# ============================================
# REPORT PARAMETERS
# ============================================
st.sidebar.header("⚙️ Report Parameters")
top_n_users_slider = st.sidebar.slider("Select N for Top Users Heatmap", min_value=5, max_value=50, value=20, step=5)
top_n_actions_slider = st.sidebar.slider("Select N for Top Sensitive Actions", min_value=3, max_value=20, value=10, step=1)
top_n_anomalies_slider = st.sidebar.slider("Number of Anomalies to Detail", min_value=3, max_value=15, value=5, step=1)

# ============================================
# REPORT GENERATION
# ============================================
st.header("📈 Overall Dataset Metrics")
total_logins = len(df_full)
unique_users = df_full['user_name'].nunique()
# --- CORRECTED METRIC CALCULATIONS to handle three states ---
suspicious_logins = (df_full['is_suspicious'] == True).sum()
normal_logins = (df_full['is_suspicious'] == False).sum()
indeterminate_logins = df_full['is_suspicious'].isna().sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Logins", f"{total_logins:,}")
col2.metric("Unique Users", f"{unique_users:,}")
col3.metric("Suspicious Logins", f"{suspicious_logins:,}")
col4.metric("Normal Logins", f"{normal_logins:,}")
col5.metric("Indeterminate Logins", f"{indeterminate_logins:,}")
st.divider()

# ============================================
# SECURITY & BEHAVIOR ANALYSIS
# ============================================
st.header("🕒 Login Activity Over Time")
daily_logins = df_full.groupby('day').size().reset_index(name='count')
# REVERTED to original, simpler line plot as requested
fig_time = px.line(daily_logins, x='day', y='count', title='Daily Login Volume', labels={'day': 'Date', 'count': 'Number of Logins'})
fig_time = style_figure(fig_time)
st.plotly_chart(fig_time, use_container_width=True)
save_and_download(fig_time, "login_volume_time", "Daily Login Volume")

# --- Pie Charts for other behaviors ---
row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    if 'event_name' in df_full.columns:
        event_counts = df_full['event_name'].value_counts().reset_index()
        fig_event_pie = px.pie(event_counts, names='event_name', values='count', title="Distribution of Event Names", hole=0.4, color_discrete_sequence=px.colors.carto.Bold)
        fig_event_pie = style_figure(fig_event_pie, legend_title="Event Name")
        st.plotly_chart(fig_event_pie, use_container_width=True)
        save_and_download(fig_event_pie, "event_name_dist", "Event Name Distribution")
with row1_col2:
    if 'login_type' in df_full.columns:
        login_type_counts = df_full['login_type'].value_counts().reset_index()
        fig_login_type = px.pie(login_type_counts, names='login_type', values='count', title="Distribution of Login Types", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_login_type = style_figure(fig_login_type, legend_title="Login Type")
        st.plotly_chart(fig_login_type, use_container_width=True)
        save_and_download(fig_login_type, "login_type_dist", "Login Type Distribution")

row2_col1, row2_col2 = st.columns(2)
# --- Sensitive Actions Chart ---
with row2_col1:
	if 'sensitive_action_name' in df_full.columns and not df_full['sensitive_action_name'].isnull().all():
	    st.header(f"Sensitive Actions Analysis")
	    sensitive_counts = df_full['sensitive_action_name'].value_counts().nlargest(top_n_actions_slider).reset_index()
	    sensitive_counts.columns = ['Action', 'Count']
	    fig_sensitive = px.bar(sensitive_counts.sort_values('Count'), y='Action', x='Count', orientation='h', title=f"Top {top_n_actions_slider} Most Frequent Sensitive Actions", color="Count", color_continuous_scale='OrRd')
	    fig_sensitive = style_figure(fig_sensitive, margin=dict(t=100, b=80, l=400, r=40))
	    st.plotly_chart(fig_sensitive, use_container_width=True)
	    save_and_download(fig_sensitive, "sensitive_actions", "Sensitive Actions", width=1400)
with row2_col2:
    if 'is_second_factor' in df_full.columns:
        df_full['2fa_status'] = df_full['is_second_factor'].map({True: '2FA Enabled', False: 'No 2FA', 'Unknown': 'Unknown'})
        factor_counts = df_full['2fa_status'].value_counts().reset_index()
        fig_2fa_pie = px.pie(factor_counts, names='2fa_status', values='count', title="2-Factor Authentication Usage", hole=0.4, color_discrete_sequence=['#117864', '#E74C3C', '#95A5A6'])
        fig_2fa_pie = style_figure(fig_2fa_pie, legend_title="2FA Status")
        st.plotly_chart(fig_2fa_pie, use_container_width=True)
        save_and_download(fig_2fa_pie, "2fa_dist", "2FA Distribution")


# ============================================
# GEOGRAPHIC AND TEMPORAL PATTERNS
# ============================================
st.header("🌍 Geographic and Temporal Patterns")
c1, c2 = st.columns(2)
with c1:
    pivot_weekday_hour = df_full.pivot_table(index='weekday', columns='hour', values='user_name', aggfunc='count', fill_value=0)
    weekdays_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot_weekday_hour = pivot_weekday_hour.reindex(weekdays_order)
    colorscale = [[0, "#EAECEE"], [0.01, "#D4E6F1"], [0.5, "#85C1E9"], [1.0, "#2471A3"]]
    fig_heat = px.imshow(pivot_weekday_hour, color_continuous_scale=colorscale, labels=dict(x="Hour of Day", y="Weekday", color="Logins"), title="Logins by Hour and Weekday")
    fig_heat = style_figure(fig_heat, legend_title="Logins")
    st.plotly_chart(fig_heat, use_container_width=True)
    save_and_download(fig_heat, "login_heatmap_weekday_hour", "Weekday-Hour Heatmap")
with c2:
    top_n_users = df_full['user_name'].value_counts().nlargest(top_n_users_slider).index
    df_top_users = df_full[df_full['user_name'].isin(top_n_users)]
    pivot_user_hour = df_top_users.pivot_table(index='user_name', columns='hour', values='event_name', aggfunc='count', fill_value=0)
    fig_user_heat = px.imshow(pivot_user_hour, color_continuous_scale=colorscale, labels=dict(x="Hour of Day", y="User", color="Logins"), title=f"Hourly Logins for Top {top_n_users_slider} Active Users")
    fig_user_heat = style_figure(fig_user_heat, legend_title="Logins", margin=dict(t=100, b=80, l=220, r=40))
    st.plotly_chart(fig_user_heat, use_container_width=True)
    dynamic_height = 600 + top_n_users_slider * 20
    save_and_download(fig_user_heat, "login_heatmap_user_hour", "User-Hour Heatmap", height=dynamic_height)


# ============================================
# SUSPICIOUS ACTIVITY ANALYSIS
# ============================================
st.header("⚠️ Suspicious Activity Analysis")
if 'is_suspicious' in df_full.columns:
    df_full['status'] = df_full['is_suspicious'].map({True: 'Suspicious', False: 'Normal'}).fillna('Indeterminate')
    daily_status_counts = df_full.groupby(['day', 'status']).size().unstack(fill_value=0).reset_index()
    all_days_idx = pd.date_range(start=daily_status_counts['day'].min(), end=daily_status_counts['day'].max(), freq='D')
    trend_data = daily_status_counts.set_index('day').reindex(all_days_idx, fill_value=0).reset_index().rename(columns={'index': 'day'})
    
    # --- FIGURE 1: Side-by-Side Bar Chart on Log Scale ---
    st.subheader("Absolute Login Counts (Log Scale)")
    df_melted = trend_data.melt(id_vars=['day'], value_vars=['Normal', 'Suspicious'], var_name='status', value_name='count')
    fig_susp_bar = px.bar(df_melted, x='day', y='count', color='status', barmode='group', log_y=True, title="Daily Normal vs. Suspicious Login Counts", labels={'day': 'Date', 'count': 'Number of Logins (Log Scale)'}, color_discrete_map={'Normal': 'dodgerblue', 'Suspicious': 'crimson'})
    fig_susp_bar.update_xaxes(type='date')
    fig_susp_bar = style_figure(fig_susp_bar, legend_title="Login Status")
    save_and_download(fig_susp_bar, "suspicious_counts_log_trend", "Suspicious Counts Trend (Log)")
    st.plotly_chart(fig_susp_bar, use_container_width=True)
    

    # --- FIGURE 1: 100% Proportional Area Chart (Corrected Order & Color) ---
    st.subheader("Daily Login Status Proportions")
    # Correct order for stacking: bottom to top
    y_order = ['Normal', 'Indeterminate', 'Suspicious'] 
    fig_susp_prop = px.area(trend_data, x='day', y=[col for col in y_order if col in trend_data.columns],
                            title="Daily Proportional Breakdown of Login Status",
                            labels={"value": "Percentage of Logins", "day": "Date"},
                            color_discrete_map={'Normal': 'dodgerblue', 'Suspicious': 'crimson', 'Indeterminate': '#A9A9A9'}, # Darker grey
                            groupnorm='percent')
    fig_susp_prop.update_yaxes(ticksuffix="%")
    fig_susp_prop.update_xaxes(type='date')
    fig_susp_prop = style_figure(fig_susp_prop, legend_title="Status")
    save_and_download(fig_susp_prop, "suspicious_proportion_trend", "Suspicious Proportion Trend")
    st.plotly_chart(fig_susp_prop, use_container_width=True)
    


# ============================================
# ANOMALY DETECTION & DRILL-DOWN
# ============================================
st.header("🔍 Login Frequency Anomaly Detection")
def get_mode(series):
    return series.mode()[0] if not series.mode().empty else 'N/A'

user_daily = df_full.groupby(['user_name', 'day']).agg(count=('event_name', 'size'), dominant_event=('event_name', get_mode)).reset_index()

if not user_daily.empty and 'count' in user_daily and user_daily['count'].std() > 0:
    avg, std = user_daily['count'].mean(), user_daily['count'].std()
    user_daily['zscore'] = (user_daily['count'] - avg) / std
    user_daily['type'] = user_daily['zscore'].apply(lambda z: 'Anomaly (Z-Score > 3)' if z > 3 else 'Normal')
    
    fig_anom = px.scatter(user_daily, x='day', y='count', color='type', title="User Daily Login Frequencies", labels={'day': 'Date', 'count': 'Logins per Day'}, color_discrete_map={'Normal': 'lightgray', 'Anomaly (Z-Score > 3)': 'red'}, hover_data=['user_name', 'count', 'zscore', 'dominant_event'])
    fig_anom.update_traces(marker=dict(size=9))
    fig_anom = style_figure(fig_anom, legend_title="Login Type")
    st.plotly_chart(fig_anom, use_container_width=True)
    save_and_download(fig_anom, "login_anomalies", "Login Frequency Anomalies")
    
    anomalies = user_daily[user_daily['type'] == 'Anomaly (Z-Score > 3)'].sort_values('zscore', ascending=False)
    if not anomalies.empty:
        st.subheader(f"Drill-Down of Top {top_n_anomalies_slider} Anomalies")
        st.write("Examine event types and context for the most severe login frequency anomalies.")
        for i, anomaly in anomalies.head(top_n_anomalies_slider).iterrows():
            with st.expander(f"**Anomaly #{i+1}:** {anomaly['user_name']} on {anomaly['day'].strftime('%Y-%m-%d')} ({anomaly['count']} logins, Z-Score: {anomaly['zscore']:.2f})"):
                drill_col1, drill_col2 = st.columns([2,1])
                anomaly_events = df_full[(df_full['user_name'] == anomaly['user_name']) & (df_full['day'] == anomaly['day'])]
                with drill_col1:
                    event_counts = anomaly_events['event_name'].value_counts().reset_index()
                    fig_drilldown = px.bar(event_counts, x='count', y='event_name', orientation='h', title=f"Event Breakdown", labels={'count': 'Count', 'event_name': 'Event Name'})
                    fig_drilldown = style_figure(fig_drilldown, margin=dict(t=50, b=50, l=200, r=40))
                    st.plotly_chart(fig_drilldown, use_container_width=True)
                with drill_col2:
                    st.metric("Suspicious Logins in Anomaly", int((anomaly_events['is_suspicious'] == True).sum()))
                    st.metric("Unique IP Addresses", anomaly_events['ip_address'].nunique())
                    st.metric("Unique Cities", anomaly_events['city'].nunique())
                    st.write("**Locations on this Day:**")
                    st.dataframe(anomaly_events.groupby(['country', 'city']).size().rename('count').sort_values(ascending=False).reset_index())

st.success("Report generated successfully. All figures saved to the 'figures/' directory.")