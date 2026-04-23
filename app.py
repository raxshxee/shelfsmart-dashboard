import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="ShelfSmart", layout="wide")

# ---------------- THEME ----------------
st.markdown("""
<style>
.stApp {background:#07111f; color:white;}
h1,h2,h3 {color:#7EC8E3;}
section[data-testid="stSidebar"] {background:#0d1b2a;}
[data-testid="metric-container"] {
    background:#10243d;
    padding:14px;
    border-radius:10px;
}
div.stButton > button, div.stDownloadButton > button {
    background:#FFBF3F; color:black; border:none;
    border-radius:8px; font-weight:600;
}
</style>
""", unsafe_allow_html=True)

st.title("🛒 ShelfSmart")
st.caption("Retail planning dashboard for smarter stock and sales decisions")

# ---------------- DATA ----------------
@st.cache_data
def load_data():
    df = pd.read_excel("data/Online Retail.xlsx", engine="openpyxl")
    df = df.dropna(subset=["Description"])
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] > 0]

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    df["Date"] = df["InvoiceDate"].dt.date
    df["Hour"] = df["InvoiceDate"].dt.hour
    df["Weekday"] = df["InvoiceDate"].dt.day_name()

    return df

df = load_data()

# ---------------- FILTERS ----------------
st.sidebar.title("View Options")

countries = sorted(df["Country"].unique())
country = st.sidebar.selectbox("Market", ["All"] + countries)

if country != "All":
    df = df[df["Country"] == country]

search_term = st.sidebar.text_input("Search Product")

if search_term:
    df = df[df["Description"].str.contains(search_term, case=False, na=False)]

min_rev = st.sidebar.slider("Minimum Unit Price", 0, 100, 0)
df = df[df["UnitPrice"] >= min_rev]

# ---------------- METRICS ----------------
revenue = df["Revenue"].sum()
orders = df["InvoiceNo"].nunique()
buyers = df["CustomerID"].nunique()
basket = revenue / orders if orders else 0
units = df["Quantity"].sum()
units_per_order = units / orders if orders else 0
orders_per_customer = orders / buyers if buyers else 0

monthly = df.groupby("Month")["Revenue"].sum().reset_index()
growth = 0
if len(monthly) >= 2:
    growth = ((monthly.iloc[-1,1] - monthly.iloc[-2,1]) / monthly.iloc[-2,1]) * 100

st.subheader("Business Snapshot")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Revenue", f"${revenue:,.0f}")
c2.metric("Orders", f"{orders:,}")
c3.metric("Buyers", f"{buyers:,}")
c4.metric("Avg Basket", f"${basket:,.2f}")

c5,c6,c7,c8 = st.columns(4)
c5.metric("Units Sold", f"{units:,.0f}")
c6.metric("Units / Order", f"{units_per_order:,.1f}")
c7.metric("Orders / Buyer", f"{orders_per_customer:,.1f}")
c8.metric("Latest Growth %", f"{growth:,.1f}%")

# ---------------- CHARTS ----------------
st.subheader("Sales Over Time")
fig1 = px.line(monthly, x="Month", y="Revenue", markers=True)
fig1.update_traces(line_color="#7EC8E3")
st.plotly_chart(fig1, use_container_width=True)

# Top products
exclude = ["POSTAGE","MANUAL","BANK CHARGES","CARRIAGE"]
pdf = df[~df["Description"].str.upper().str.contains("|".join(exclude), na=False)]

top_products = (
    pdf.groupby("Description")["Revenue"]
    .sum().sort_values(ascending=False)
    .head(10).reset_index()
)

st.subheader("Best-Selling Products")
fig2 = px.bar(top_products, x="Revenue", y="Description", orientation="h")
fig2.update_traces(marker_color="#FFBF3F")
st.plotly_chart(fig2, use_container_width=True)

# Country share
country_share = df.groupby("Country")["Revenue"].sum().reset_index()

st.subheader("Market Contribution")
fig3 = px.pie(country_share, names="Country", values="Revenue")
st.plotly_chart(fig3, use_container_width=True)

# Weekday sales
weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
wd = df.groupby("Weekday")["Revenue"].sum().reset_index()
wd["Weekday"] = pd.Categorical(wd["Weekday"], weekday_order)
wd = wd.sort_values("Weekday")

st.subheader("Revenue by Weekday")
fig4 = px.bar(wd, x="Weekday", y="Revenue")
fig4.update_traces(marker_color="#7EC8E3")
st.plotly_chart(fig4, use_container_width=True)

# ---------------- BUYERS ----------------
top_buyers = (
    df.groupby("CustomerID")["Revenue"]
    .sum().sort_values(ascending=False)
    .head(10).reset_index()
)

st.subheader("Top Buyers")
st.dataframe(top_buyers)

# ---------------- RESTOCK ----------------
daily = df.groupby(["Description","Date"])["Quantity"].sum().reset_index()
avg = daily.groupby("Description")["Quantity"].mean().reset_index()
avg.columns = ["Description","Avg_Daily_Demand"]

price = df.groupby("Description")["UnitPrice"].mean().reset_index()
forecast = avg.merge(price, on="Description")
forecast["Next_7_Days"] = (forecast["Avg_Daily_Demand"]*7).round()
forecast["Suggested_Restock"] = (forecast["Avg_Daily_Demand"]*10).round()
forecast["Est_Budget"] = (forecast["Suggested_Restock"]*forecast["UnitPrice"]).round(2)

forecast = forecast.sort_values("Suggested_Restock", ascending=False)

st.subheader("Restock Planner")
st.dataframe(forecast.head(10))

# ---------------- INSIGHTS ----------------
best_month = monthly.loc[monthly["Revenue"].idxmax(),"Month"] if len(monthly)>0 else "N/A"

st.subheader("Key Takeaways")
st.success(f"""
• Strongest month: {best_month}

• Use top products for shelf priority.

• Use top buyers for retention campaigns.

• Use weekday trends for staffing & promotions.

• Use restock planner for procurement decisions.

• Deploying this online will complete cloud implementation.
""")
