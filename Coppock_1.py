import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. 系統環境配置
# ==============================================================================

st.set_page_config(page_title="Coppock 估波指標系統 (月線版)", layout="wide")

if "is_dark" not in st.session_state:
    st.session_state.is_dark = False

# ==============================================================================
# 2. 視覺設計 Tokens（依 Design Handoff「Classical」設計系統規格）
# ==============================================================================

LIGHT_TOKENS = {
    "bg": "#f3f2f2",
    "surface_alt": "#f8f7f6",
    "text": "#201f1d",
    "text_muted": "rgba(32,31,29,0.55)",
    "divider": "rgba(32,31,29,0.16)",
    "accent": "#b68235",
    "grid_line": "rgba(32,31,29,0.08)",
    "shadow": "0 3px 10px rgba(45,43,43,0.14)",
    "line": "#b68235",
    "zero_line": "rgba(32,31,29,0.45)",
}
DARK_TOKENS = {
    "bg": "#17140f",
    "surface_alt": "#1c1912",
    "text": "#f3ede2",
    "text_muted": "rgba(243,237,226,0.6)",
    "divider": "rgba(243,237,226,0.16)",
    "accent": "#c99a4e",
    "grid_line": "rgba(243,237,226,0.12)",
    "shadow": "0 12px 32px rgba(0,0,0,0.5)",
    "line": "#c99a4e",
    "zero_line": "rgba(243,237,226,0.45)",
}

is_dark = st.session_state.is_dark
tok = DARK_TOKENS if is_dark else LIGHT_TOKENS
chart_template = "plotly_dark" if is_dark else "plotly_white"

# ==============================================================================
# 3. 全域樣式（字型／配色／按鈕／輸入框／側邊欄版面）
# ==============================================================================

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Lora:wght@400;600&display=swap');

    html, body, [class*="css"] {{ font-family: 'Lora', serif; }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 600 !important;
    }}

    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {tok['bg']} !important;
        color: {tok['text']} !important;
    }}
    [data-testid="stHeader"] {{ background-color: transparent !important; }}

    /* 側邊欄版面 */
    [data-testid="stSidebar"] {{
        background-color: {tok['bg']} !important;
        border-right: 1px solid {tok['divider']};
        min-width: 300px !important;
        max-width: 300px !important;
    }}
    [data-testid="stSidebarUserContent"] {{ padding: 40px 28px !important; }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 18px; }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        font-size: 12px !important;
        color: {tok['text_muted']} !important;
        font-family: 'Lora', serif !important;
    }}

    /* 輸入框：邊框只畫在最外層容器，內層元素一律去邊框/去底色，避免雙層邊框與底色不一致 */
    [data-testid="stSidebar"] div[data-baseweb="input"] {{
        border: 1px solid {tok['divider']} !important;
        border-radius: 4px !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }}
    [data-testid="stSidebar"] div[data-baseweb="input"] * {{
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
    }}
    [data-testid="stSidebar"] div[data-baseweb="input"] input {{
        color: {tok['text']} !important;
    }}

    /* 瀏覽器自動填入(autofill)會強制套用自己的底色，一般CSS蓋不掉，需用此專門技巧解除 */
    [data-testid="stSidebar"] input:-webkit-autofill,
    [data-testid="stSidebar"] input:-webkit-autofill:hover,
    [data-testid="stSidebar"] input:-webkit-autofill:focus,
    [data-testid="stSidebar"] input:-webkit-autofill:active {{
        -webkit-box-shadow: 0 0 0 1000px transparent inset !important;
        -webkit-text-fill-color: {tok['text']} !important;
        caret-color: {tok['text']};
        transition: background-color 9999s ease-in-out 0s;
    }}

    /* 按鈕：設計系統一律採 outline 樣式，不使用實心填色 */
    div.stButton > button {{
        width: 100%;
        background-color: transparent !important;
        border-radius: 4px !important;
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        box-shadow: none !important;
    }}
    div.stButton > button[kind="secondary"] {{
        color: {tok['text']} !important;
        border: 1px solid {tok['divider']} !important;
    }}
    div.stButton > button[kind="secondary"]:hover {{
        border-color: {tok['accent']} !important;
        color: {tok['accent']} !important;
    }}
    div.stButton > button[kind="primary"] {{
        color: {tok['accent']} !important;
        border: 1px solid {tok['accent']} !important;
    }}
    div.stButton > button[kind="primary"]:hover {{
        background-color: color-mix(in srgb, {tok['accent']} 12%, transparent) !important;
    }}

    /* 圖表卡片容器（st.container(border=True)） */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {tok['divider']} !important;
        border-radius: 7px !important;
        background-color: {tok['surface_alt']} !important;
        box-shadow: {tok['shadow']};
    }}
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. 側邊欄：查詢設定
# ==============================================================================

st.sidebar.markdown(
    f"<div style='font-size:12px;letter-spacing:.08em;text-transform:uppercase;"
    f"color:{tok['text_muted']};margin-bottom:-6px;'>查詢設定</div>",
    unsafe_allow_html=True,
)

# 股票與結束日期輸入(起始日期由結束日期自動往前推20年計算，不開放使用者輸入)
stock_id = st.sidebar.text_input("股票代號(如2330或AAPL)", "2330")
end_date = st.sidebar.date_input("結束日期(YYYY/MM/DD)", datetime.now())

st.sidebar.markdown(
    f"<hr style='border:none;border-top:1px solid {tok['divider']};margin:4px 0;'>",
    unsafe_allow_html=True,
)

# 視覺主題切換：以按鈕切換整頁亮/深色（對應網頁背景）
theme_label = "切換為深色" if not is_dark else "切換為亮色"
theme_icon = ":material/dark_mode:" if not is_dark else ":material/light_mode:"
theme_clicked = st.sidebar.button(theme_label, icon=theme_icon, type="secondary", use_container_width=True)

# 開始計算觸發按鈕
analyze_btn = st.sidebar.button("開始計算", type="primary", use_container_width=True)

if theme_clicked:
    st.session_state.is_dark = not st.session_state.is_dark
    st.rerun()

# ==============================================================================
# 5. 主程式執行邏輯
# ==============================================================================

st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;">
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="{tok['accent']}" stroke-width="1.6">
        <path d="M3 12h3l3 7 4-14 3 7h5"/>
      </svg>
      <h1 style="margin:0;font-size:36px;">Coppock 估波指標系統 (月線版)</h1>
    </div>
    """, unsafe_allow_html=True)

if not analyze_btn:
    st.markdown(
        f"<div style='color:{tok['text_muted']};font-size:15px;margin-top:12px;'>"
        f"請點開左上角選單 [ >> ] 在左側面板設定參數後，按「開始計算」即可產出圖表</div>",
        unsafe_allow_html=True,
    )
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
        st.markdown(
            f"<div style='margin-top:4px;font-family:\"Cormorant Garamond\",serif;"
            f"font-size:19px;color:{tok['text_muted']};'>{search_id}</div>",
            unsafe_allow_html=True,
        )

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
        # 6. 視覺化繪圖 (Plotly 互動式圖表)
        # ==============================================================================
        fig = go.Figure()

        # 使用 Date_Str (字串日期) 當 X 軸，避開非交易月空隙
        fig.add_trace(go.Scatter(
            x=df['Date_Str'], y=df['Coppock'], name='Coppock',
            mode='lines', line=dict(color=tok['line'], width=2)
        ))

        # 零軸參考線：Coppock 慣例以零軸判斷多空轉折
        # 以灰色虛線加粗呈現，與 Y 軸其他水平格線做出區隔
        fig.add_hline(y=0, line_dash="dash", line_color=tok['zero_line'], line_width=2.5)

        fig.update_layout(
            title=dict(text="Coppock", font=dict(family="Cormorant Garamond, serif", color=tok['text'])),
            height=700,
            template=chart_template,
            hovermode='x unified',
            font=dict(color=tok['text'], family='Lora, serif'),
            # 關鍵：將 xaxis 類型設為 category，配合 Date_Str 使用以忽略非交易月
            xaxis=dict(
                title="月",
                type='category',
                color=tok['text'],
                tickfont=dict(color=tok['text']),
                gridcolor=tok['grid_line'],
                nticks=8  # 限制顯示的座標標籤數量，避免字體重疊
            ),
            yaxis=dict(
                title="%",
                color=tok['text'],
                tickfont=dict(color=tok['text']),
                gridcolor=tok['grid_line'],
                zeroline=False  # 停用預設黑色實線加粗的零軸，改由上方自訂灰色虛線呈現
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(color=tok['text_muted'], family='Lora, serif')
            ),
            paper_bgcolor=tok['surface_alt'],
            plot_bgcolor=tok['surface_alt']
        )

        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)

        # ==============================================================================
        # 7. 數據摘要指標
        # ==============================================================================
        st.markdown("<h4 style='margin:28px 0 16px;'>數據摘要</h4>", unsafe_allow_html=True)
        valid_df = df.dropna(subset=['Coppock'])

        if not valid_df.empty:
            last_close = valid_df['Close_1D'].iloc[-1]
            last_coppock = valid_df['Coppock'].iloc[-1]
            is_bullish = last_coppock > 0
            zone_text = "多頭區 (>0)" if is_bullish else "空頭區 (<0)"

            def _stat_card(label, value):
                return f"""
                <div style="border:1px solid {tok['divider']};border-radius:4px;padding:20px 22px;">
                  <div style="font-size:12px;color:{tok['text_muted']};margin-bottom:8px;">{label}</div>
                  <div style="font-family:'Cormorant Garamond',serif;font-size:28px;font-variant-numeric:tabular-nums;">{value}</div>
                </div>
                """

            col1, col2, col3 = st.columns(3)
            col1.markdown(_stat_card("最新收盤價", f"{last_close:.2f}"), unsafe_allow_html=True)
            col2.markdown(_stat_card("最新 Coppock 數值", f"{last_coppock:.2f}"), unsafe_allow_html=True)
            col3.markdown(_stat_card("目前狀態", zone_text), unsafe_allow_html=True)

            if is_bullish:
                icon_path = '<path d="M3 17l5-6 4 3 6-9"/><path d="M14 5h5v5"/>'
            else:
                icon_path = '<path d="M3 7l5 6 4-3 6 9"/><path d="M14 19h5v-5"/>'

            st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;margin-top:20px;
                            border:1px solid color-mix(in srgb, {tok['accent']} 40%, transparent);
                            background:color-mix(in srgb, {tok['accent']} 10%, transparent);
                            border-radius:4px;padding:16px 20px;">
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="{tok['accent']}"
                       stroke-width="1.8" style="flex-shrink:0">
                    {icon_path}
                  </svg>
                  <span style="font-size:14px;">Coppock 估波指標目前處於{zone_text}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("資料長度不足以計算 Coppock 指標（需至少24個月以上資料）。")

    else:
        st.error(f"找不到股票資料（已嘗試：{', '.join(candidates)}），請檢查代號或日期。")
