import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. 系統環境與側邊欄配置
# ==============================================================================

# 網頁配置
st.set_page_config(page_title="Coppock 估波指標系統 (月線版)", layout="wide")

# --- 側邊欄：參數設定 ---
st.sidebar.header("參數設定")

# 股票與結束日期輸入(起始日期由結束日期自動往前推20年計算，不開放使用者輸入)
stock_id = st.sidebar.text_input("股票代號(如2330或AAPL)", "2330")
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

# 圖表主題選擇：影響後續 CSS 渲染與 Plotly 模板
theme_choice = st.sidebar.radio("圖表主題(對應網頁背景)", ["亮色(白色背景)", "深色(深色背景)"])

# ==============================================================================
# 2. CSS 視覺樣式優化 (強制覆蓋各主題背景色)
# ==============================================================================

if theme_choice == "深色(深色背景)":
    chart_template = "plotly_dark"
    font_color = "white"
    bg_color = "#0E1117"
    st.markdown("""
        <style>
        /* 深色模式：設定側邊欄與背景為深黑色 (#0E1117)，文字為白色 */
        [data-testid="stSidebar"], .stApp, header { background-color: #0E1117 !important; color: white !important; }
        .stMarkdown, p, h1, h2, h3, span { color: white !important; }
        input { color: white !important; background-color: #262730 !important; }
        </style>
        """, unsafe_allow_html=True)
else:
    chart_template = "plotly_white"
    font_color = "black"
    bg_color = "#FFFFFF"
    st.markdown("""
        <style>
        /* 亮色模式：設定背景為純白，文字為純黑 */
        [data-testid="stSidebar"], .stApp, header { background-color: #FFFFFF !important; color: black !important; }
        .stMarkdown, p, h1, h2, h3, span { color: black !important; }

        /* 消除輸入框陰影，改用簡約淺灰色邊框 */
        div[data-baseweb="input"], div[data-baseweb="input"] > div, div[data-baseweb="input"] input {
            background-color: white !important;
            border-color: #dcdcdc !important;
            box-shadow: none !important;
        }

        /* 按鈕樣式：黑底白字，增加專業感 */
        div.stButton > button {
            background-color: #000000 !important;
            border: 1px solid #000000 !important;
            font-weight: bold !important;
        }
        div.stButton > button * {
            color: #FFFFFF !important;
        }
        div.stButton > button:hover {
            background-color: #333333 !important;
        }

        /* 側邊欄邊框調整 */
        [data-testid="stSidebar"] { border-right: 1px solid #f0f2f6; }
        input { color: black !important; background-color: white !important; }
        </style>
        """, unsafe_allow_html=True)

st.sidebar.markdown("---")

# 定義分析按鈕
analyze_btn = st.sidebar.button("開始分析")

st.title("📈 Coppock 估波指標系統 (月線版)")

# ==============================================================================
# 3. 數據抓取與計算邏輯
# ==============================================================================
if not analyze_btn:
    st.info("💡 請點開左上角選單 [ >> ] 在左側面板設定參數後，按「開始分析」即可產出圖表")
else:
    # 資料計算期間：結束日期往前算20年
    # 若實際資料長度不足20年(例如上市未滿20年)，yfinance 會自動從最早可得資料起算，不需額外處理
    start_date = (pd.Timestamp(end_date) - pd.DateOffset(years=20)).date()

    # 依序嘗試：原始代號 → .TW → .TWO
    candidates = [stock_id, f"{stock_id}.TW", f"{stock_id}.TWO"]
    search_id = None
    data = pd.DataFrame()
    for candidate in candidates:
        temp = yf.download(candidate, start=start_date, end=end_date, auto_adjust=True, interval="1mo")
        if not temp.empty:
            search_id = candidate
            data = temp
            break

    if search_id:
        # 顯示股票代碼(左上角)
        st.markdown(f"<h3 style='color: {font_color};'>{search_id}</h3>", unsafe_allow_html=True)

    if not data.empty:
        df = data.copy()

        # ★ 修正：必須先展平 MultiIndex 欄位，再 reset_index()
        #   yfinance 新版回傳的欄位結構為 MultiIndex，例如 ('Close', '2330.TW')
        #   若順序顛倒，reset_index() 後 'Date' 欄位無法正常存取
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()

        # 相容不同版本 yfinance：月線索引名稱可能為 'Date' 或 'Datetime'
        if 'Datetime' in df.columns:
            df = df.rename(columns={'Datetime': 'Date'})
        elif 'index' in df.columns:
            df = df.rename(columns={'index': 'Date'})

        # 格式化日期(用於 X 軸顯示)：移除 X 軸非交易月空隙的關鍵，先將日期轉為字串
        # 這樣會顯示成：Nov 2022
        df['Date_Str'] = df['Date'].dt.strftime('%b %Y')

        # 展平收盤價確保計算穩定
        df['Close_1D'] = df['Close'].values.flatten()

        # --- Coppock 估波指標計算 ---
        # Coppock.1 = WMA(10) of (ROC(14) + ROC(11))
        # ROC(n) = (Close - Close[n個月前]) / Close[n個月前] * 100
        # WMA(10)：以 1~10 為權重的加權移動平均，最近月權重最大(10)，10個月前權重最小(1)
        close = df['Close_1D']
        roc14 = (close - close.shift(14)) / close.shift(14) * 100
        roc11 = (close - close.shift(11)) / close.shift(11) * 100
        roc_sum = roc14 + roc11

        weights = np.arange(1, 11)
        df['Coppock'] = roc_sum.rolling(10).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

        # ==============================================================================
        # 4. 繪圖與互動優化
        # ==============================================================================
        fig = go.Figure()

        line_color = '#FF4136' if theme_choice == "亮色(白色背景)" else '#00CFFF'

        # 使用 Date_Str (字串日期) 當 X 軸，避開非交易月空隙
        fig.add_trace(go.Scatter(
            x=df['Date_Str'], y=df['Coppock'], name='Coppock',
            mode='lines', line=dict(color=line_color, width=2)
        ))

        # 零軸參考線：Coppock 慣例以零軸判斷多空轉折
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)

        fig.update_layout(
            title="Coppock",
            height=700,
            template=chart_template,
            hovermode='x unified',
            font=dict(color=font_color),
            # 關鍵：將 xaxis 類型設為 category，配合 Date_Str 使用以忽略非交易月
            xaxis=dict(
                title="月",
                type='category',
                color=font_color,
                tickfont=dict(color=font_color),
                nticks=8  # 限制顯示的座標標籤數量，避免字體重疊
            ),
            yaxis=dict(
                title="%",
                color=font_color,
                tickfont=dict(color=font_color)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(color=font_color)
            ),
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color
        )

        st.plotly_chart(fig, use_container_width=True)

        # ==============================================================================
        # 5. 數據摘要指標
        # ==============================================================================
        st.header("📊 最新狀態")
        valid_df = df.dropna(subset=['Coppock'])

        if not valid_df.empty:
            last_close = valid_df['Close_1D'].iloc[-1]
            last_coppock = valid_df['Coppock'].iloc[-1]
            is_bullish = last_coppock > 0
            zone_text = "多頭區 (>0)" if is_bullish else "空頭區 (<0)"
            zone_icon = "📈" if is_bullish else "📉"

            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("最新收盤價")
                st.markdown(f"### {last_close:.2f}")
            with col2:
                st.subheader("最新 Coppock 數值")
                st.markdown(f"### {last_coppock:.2f}")
            with col3:
                st.subheader("目前狀態")
                st.markdown(f"### {zone_icon} {zone_text}")
        else:
            st.warning("資料長度不足以計算 Coppock 指標（需至少24個月以上資料）。")

    else:
        st.error(f"找不到股票資料（已嘗試：{', '.join(candidates)}），請檢查代號或日期。")
