import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Set page config
st.set_page_config(page_title="Logistics Festive Surge Analysis", layout="wide", page_icon="📦")

# ==========================================
# 1. DATA LOADING & PREPROCESSING
# ==========================================
@st.cache_data
def load_data():
    try:
        # Added utf-8-sig to automatically strip hidden BOM characters from copy-pasted text
        orders = pd.read_csv("orders.csv", encoding="utf-8-sig")
        nps = pd.read_csv("nps.csv", encoding="utf-8-sig")
        hubs = pd.read_csv("hubs.csv", encoding="utf-8-sig")
        couriers = pd.read_csv("couriers.csv", encoding="utf-8-sig")
        customers = pd.read_csv("customers.csv", encoding="utf-8-sig")
        tickets = pd.read_csv("tickets.csv", encoding="utf-8-sig")
        
        # Convert dates safely
        orders['order_date'] = pd.to_datetime(orders['order_date'], errors='coerce')
        orders['promised_date'] = pd.to_datetime(orders['promised_date'], errors='coerce')
        orders['delivery_date'] = pd.to_datetime(orders['delivery_date'], errors='coerce')
        nps['response_date'] = pd.to_datetime(nps['response_date'], errors='coerce')
        
        # Derived Metrics creation
        orders['Delivery Delay'] = (orders['delivery_date'] - orders['promised_date']).dt.days
        orders['SLA Breach Flag'] = np.where(orders['Delivery Delay'] > 0, 'Yes', 'No')
        orders['Month'] = orders['order_date'].dt.month_name()
        
        # Merge datasets for comprehensive analysis
        df_merged = orders.merge(customers, on='customer_id', how='left', suffixes=('', '_cust'))
        df_merged = df_merged.merge(nps, on=['order_id', 'customer_id'], how='left')
        df_merged = df_merged.merge(tickets, on='order_id', how='left')
        
        # Calculate NPS Categories
        def get_nps_category(score):
            if pd.isna(score): return np.nan
            elif score >= 9: return 'Promoter'
            elif score >= 7: return 'Passive'
            else: return 'Detractor'
            
        df_merged['NPS_Category'] = df_merged['score'].apply(get_nps_category)
        
        return orders, nps, hubs, couriers, customers, tickets, df_merged
    except FileNotFoundError as e:
        st.error(f"❌ File Not Found: {e.filename}. Please make sure all 6 CSV files are saved in the same folder as this script.")
        return None, None, None, None, None, None, None
    except Exception as e:
        st.error(f"❌ Error parsing data: {e}")
        return None, None, None, None, None, None, None

# Load data
orders, nps, hubs, couriers, customers, tickets, df_merged = load_data()

# Safety Stop: Prevent script from continuing if data didn't load properly
if orders is None or orders.empty:
    st.warning("⚠️ Waiting for correct data files. Please check the errors above.")
    st.stop()

# ==========================================
# Global KPI Calculations
# ==========================================
total_orders = len(orders)
sla_breach_pct = 0
if total_orders > 0:
    sla_breach_pct = round((orders[orders['SLA Breach Flag'] == 'Yes'].shape[0] / total_orders) * 100, 1)

promoters = df_merged[df_merged['NPS_Category'] == 'Promoter'].shape[0]
detractors = df_merged[df_merged['NPS_Category'] == 'Detractor'].shape[0]
total_responses = df_merged['NPS_Category'].dropna().shape[0]
nps_score = round(((promoters / total_responses) - (detractors / total_responses)) * 100, 1) if total_responses > 0 else 0

repeat_customers = customers[customers['segment'] == 'Repeat'].shape[0]
total_customers = customers.shape[0]
repeat_rate = round((repeat_customers / total_customers) * 100, 1) if total_customers > 0 else 0

# ==========================================
# 2. STORY NARRATIVE & UI LAYOUT
# ==========================================
st.title("📦 Case Study: Delivery Experience Decline During Festive Surge")
st.markdown("*An interactive, story-driven diagnosis of operations, customer experience, and actionable fixes.*")

# Top Level KPIs
st.markdown("### 📊 The Festive Surge: At a Glance")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Festive Orders", f"{total_orders:,.0f}", "+ Significant Surge")
col2.metric("Overall NPS Score", f"{nps_score}", "- Critical Danger Zone", delta_color="inverse")
col3.metric("SLA Breach Rate", f"{sla_breach_pct}%", "High Delay Volume", delta_color="inverse")
col4.metric("Repeat Customer Rate", f"{repeat_rate}%", "Dropping LTV")

st.divider()

# Create tabs for the narrative flow
tab1, tab2, tab3, tab4 = st.tabs([
    "📖 Chapter 1: The Collapse of Trust (NPS)", 
    "🏭 Chapter 2: The Operations Breakdown", 
    "🕵️ Chapter 3: The Fake Delivery Epidemic", 
    "💡 Chapter 4: Cost-Neutral Solutions"
])

# --- TAB 1: NPS & CUSTOMER EXPERIENCE ---
with tab1:
    st.markdown("### The Collapse of Customer Trust")
    st.markdown("""
    While the company successfully captured high festive volumes, our operational network buckled under pressure. 
    The immediate casualty was our **Customer NPS**, plunging deep into the negative. 
    Our highest-value customers felt the brunt of these delays.
    """)
    
    colA, colB = st.columns(2)
    with colA:
        # NPS Month on Month
        nps['Month'] = nps['response_date'].dt.to_period('M').astype(str)
        nps_trend = nps.groupby('Month').agg({'score':'mean'}).reset_index()
        fig_nps = px.line(nps_trend, x='Month', y='score', title="NPS Score Trend (MoM)", markers=True, color_discrete_sequence=['#ef553b'])
        fig_nps.update_yaxes(title="Avg NPS Score")
        st.plotly_chart(fig_nps, use_container_width=True)
    
    with colB:
        # Retention / Segment NPS
        segment_nps = df_merged.groupby('segment').apply(
            lambda x: ((x[x['NPS_Category'] == 'Promoter'].shape[0] - x[x['NPS_Category'] == 'Detractor'].shape[0]) / len(x.dropna(subset=['score']))) * 100 if len(x.dropna(subset=['score'])) > 0 else 0
        ).reset_index(name='NPS')
        
        fig_seg = px.bar(segment_nps, x='segment', y='NPS', title="NPS by Customer Segment", color='NPS', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_seg, use_container_width=True)

    st.markdown("**Pivot Table: Customer Segments vs NPS Metrics**")
    pivot_nps = pd.pivot_table(df_merged, values='score', index='segment', columns='NPS_Category', aggfunc='count', fill_value=0)
    st.dataframe(pivot_nps, use_container_width=True)

# --- TAB 2: OPERATIONS BREAKDOWN ---
with tab2:
    st.markdown("### Where Did Operations Break?")
    st.markdown("""
    The data points to a massive geographic and partner-specific failure. **Tier-2 Cities (Nagpur & Indore)** suffered catastrophic delay rates. Furthermore, our reliance on **QuickShip** proved disastrous compared to **FastEx**.
    """)
    
    colC, colD = st.columns(2)
    with colC:
        # Hub Performance Chart
        hubs['SLA_Breach_Rate_Implied'] = ((hubs['total_orders'] - hubs['on_time_delivery']) / hubs['total_orders']) * 100
        fig_hub = px.bar(hubs, x='city', y='SLA_Breach_Rate_Implied', title="% Orders Delayed by Hub (City)", color='city', text_auto='.1f')
        fig_hub.update_layout(yaxis_title="Delay Rate %")
        st.plotly_chart(fig_hub, use_container_width=True)
        
    with colD:
        # Courier Performance
        fig_courier = go.Figure(data=[
            go.Bar(name='SLA Breach %', x=couriers['courier_partner'], y=couriers['sla_breach_rate']*100),
            go.Bar(name='Complaint %', x=couriers['courier_partner'], y=couriers['complaint_rate']*100)
        ])
        fig_courier.update_layout(barmode='group', title="Courier Partner Performance Comparison")
        st.plotly_chart(fig_courier, use_container_width=True)

    st.markdown("**Pivot Table: Courier vs Hub Order Status**")
    pivot_ops = pd.pivot_table(orders, index=['city', 'courier_partner'], columns='order_status', values='order_id', aggfunc='count', fill_value=0)
    pivot_ops['RTO_Rate (%)'] = round((pivot_ops.get('RTO', 0) / pivot_ops.sum(axis=1)) * 100, 1)
    st.dataframe(pivot_ops, use_container_width=True)


# --- TAB 3: THE DEEP DIVE ---
with tab3:
    st.markdown("### The Toxic Loop: Fake Deliveries & RTOs")
    st.markdown("""
    **The Discovery:** Why did complaints spike so aggressively? Because delivery executives, overwhelmed by volume and trying to avoid SLA penalties, engaged in **Fake Delivery Attempts**. 
    Customers stayed home, received a "Customer Unavailable" text, and furiously raised support tickets. Ultimately, after 3 fake attempts, packages returned to origin (RTO).
    """)
    
    colE, colF = st.columns(2)
    with colE:
        # Complaint Breakdown
        issue_counts = tickets['issue_type'].value_counts().reset_index()
        issue_counts.columns = ['issue_type', 'count']
        fig_issues = px.pie(issue_counts, names='issue_type', values='count', hole=0.4, title="Complaint Distribution Breakdown")
        st.plotly_chart(fig_issues, use_container_width=True)
        
    with colF:
        # Failed Attempts vs RTO 
        fig_rto = px.scatter(hubs, x='failed_attempts', y='rto_count', size='total_orders', color='city', 
                             title="Correlation: Failed Attempts vs RTO Orders", trendline="ols")
        st.plotly_chart(fig_rto, use_container_width=True)
        
    st.markdown("**Funnel Analysis: Orders → Delivery Delay → Complaint → RTO**")
    
    total_delayed = orders[orders['SLA Breach Flag'] == 'Yes'].shape[0]
    delayed_with_complaints = df_merged[(df_merged['SLA Breach Flag'] == 'Yes') & (~df_merged['ticket_id'].isna())].shape[0]
    complaints_to_detractors = df_merged[(~df_merged['ticket_id'].isna()) & (df_merged['NPS_Category'] == 'Detractor')].shape[0]
    total_complaints = tickets.shape[0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("% of Delayed Orders Resulting in Complaints", f"{round((delayed_with_complaints/total_delayed)*100 if total_delayed else 0, 1)}%")
    c2.metric("% of Complaints Turn into Detractors", f"{round((complaints_to_detractors/total_complaints)*100 if total_complaints else 0, 1)}%")
    c3.metric("Impact on Repeat Usage", "Severe Churn")

# --- TAB 4: RECOMMENDATIONS ---
with tab4:
    st.markdown("### 🚀 Strategic Action Plan (Cost-Neutral Fixes)")
    
    st.success("**Primary Goal:** Improve NPS and reduce complaints without significantly increasing costs.")
    
    st.markdown("#### 1. Top 3 Root Causes")
    st.markdown("""
    1. **Over-reliance on QuickShip:** Allocating too much volume to an under-equipped partner caused massive cascading failures.
    2. **Tier-2 Hub Bottleneck:** Nagpur and Indore completely lacked the sortation bandwidth to handle peak scaling.
    3. **Last-Mile Deception:** Lack of validation allowed drivers to log "Fake Attempts" to bypass SLA clocks, infuriating customers and inflating RTO logistics costs.
    """)
    
    st.markdown("#### 2. Quick Wins (Next 30 Days)")
    st.info("""
    * **Implement OTP/Geofencing for 'Failed Attempts':** Force delivery agents to be within 50 meters of the delivery address or require a customer OTP to mark a package as "Customer Unavailable." This instantly kills the fake attempt loophole.
    * **Dynamic Volume Reallocation:** Shift priority volume (High Value & Repeat customers) dynamically to **FastEx**. FastEx has a 12% breach rate compared to QuickShip's 32%.
    * **Proactive Communcation:** Automatically text customers the moment a delay is detected in the OMS, apologizing and providing a new timeline *before* they call support to create a ticket.
    """)
    
    st.markdown("#### 3. Long-Term Strategic Improvements")
    st.warning("""
    * **Revamp Courier SLA Contracts:** Stop penalizing only for late delivery (which encourages lying). Instead, introduce severe financial penalties for high Complaint Rates and Unverified RTOs.
    * **Tier-2 Gig Workers:** Establish a plug-and-play gig workforce pool in Nagpur/Indore 30 days ahead of the next festive season to alleviate hub overflow.
    """)
    
    st.markdown("#### 4. New KPIs to Track")
    st.markdown("""
    * **True Delivery Rate (TDR):** Percentage of orders delivered successfully on the *first* attempt.
    * **Fake Attempt Complaint Ratio:** (Fake Attempt Tickets / Total Failed Scans).
    * **Cost of RTO vs Courier Savings:** Tracking how the "cheaper" rate of QuickShip actually costs the company more due to return shipping and lost customer LTV.
    """)

st.caption("End of Report | Prepared by Analytics Team")
