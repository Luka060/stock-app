import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# --- 頁面設定 ---
st.set_page_config(page_title="Alpha Sniper Platinum+", layout="wide")
st.title("🚀 Alpha Sniper Platinum+ - 台美日全球操盤系統")
st.markdown("### 「看不見的風險最可怕，看得見的數據是武器。」")

# ==========================================
# 側邊欄：參數與說明書
# ==========================================
st.sidebar.header("⚙️ 戰情室參數")

# 1. 家人持股
st.sidebar.subheader("👨‍👩‍👧‍👦 家人持股")
default_family = "ZETA, NBIS"
family_input = st.sidebar.text_area("家人監控清單", default_family)
family_list = [x.strip().upper() for x in family_input.split(',')]

# 2. ETF 設定 (已移除 0P0000XS79.F)
st.sidebar.subheader("🛡️ ETF 戰略指揮部")
default_etf = "VOO, QQQ, 0050.TW, 2563.T, 2558.T"
etf_input = st.sidebar.text_area("ETF 清單", default_etf)
etf_list = [x.strip().upper() for x in etf_input.split(',')]

# 3. 觀察名單 (COIN -> JPM)
st.sidebar.subheader("⚡ 市場觀察名單")
default_watch = "NVDA, TSLA, AAPL, MSFT, PLTR, TSM, JPM"
watch_input = st.sidebar.text_area("觀察名單", default_watch)
watchlist = [x.strip().upper() for x in watch_input.split(',')]

st.sidebar.markdown("---")

# --- 說明書 ---
with st.sidebar.expander("📖 操盤手教戰手冊 (必讀)", expanded=True):
    st.markdown("### 1. RSI (相對強弱指標)")
    st.caption("判斷股價是否過熱或超賣")
    st.markdown("""
    | 數值 | 狀態 | 你的動作 |
    | :--- | :--- | :--- |
    | **> 85** | 🔥 **極度危險** | **清倉/快跑** |
    | **> 75** | ⚠️ **過熱警戒** | **分批獲利** |
    | **50-60**| 🟢 **趨勢健康** | **續抱** |
    | **< 30** | 💎 **黃金超賣** | **分批進場** |
    """)
    
    st.markdown("---")
    
    st.markdown("### 2. 機構籌碼 (heldPercent)")
    st.caption("華爾街大戶持股比例")
    st.markdown("""
    | 比例 | 意義 |
    | :--- | :--- |
    | **> 70%** | 🛡️ **大戶鎖碼** (穩) |
    | **40-70%**| 📈 **標準水位** (正常) |
    | **< 30%** | ⚠️ **散戶盤** (亂) |
    """)

    st.markdown("---")
    
    st.markdown("### 3. 關鍵代碼與價位")
    st.markdown("""
    - **0050.TW:** 元大台灣50 (台幣)
    - **2558.T:** eMAXIS 最佳替代品 (日圓)
    - **💰 黃金價 (200MA):** 長線價值區
    - **💎 恐慌坑 (BB Low):** 極端便宜區
    """)

# ==========================================
# 核心分析邏輯
# ==========================================
def analyze_asset(ticker, asset_type="stock"):
    if ticker == "FIG": return {"Error": "FIGMA 未上市"}
    
    try:
        stock = yf.Ticker(ticker)
        # 強制不調整，保留真實價格
        df = stock.history(period="2y", interval="1d", auto_adjust=False)
        
        if df.empty or len(df) < 5: 
            return {"Error": "資料來源無回應"}

        # 幣別判斷
        currency_symbol = "$"
        if ".T" in ticker or ".F" in ticker: currency_symbol = "¥"
        elif ".TW" in ticker or ".TWO" in ticker: currency_symbol = "NT$"
            
        # --- 基金判斷邏輯 ---
        recent_df = df.tail(10)
        is_fund_stat = (recent_df['High'] == recent_df['Low']).all()
        
        # 強制白名單 (ETF 必須顯示 K 棒)
        force_etf_list = ["0050", "2563", "2558", "VOO", "QQQ", "SPY", "IVV", "SOXL", "TQQQ"]
        is_known_etf = any(x in ticker for x in force_etf_list)
        
        if is_known_etf:
            is_fund = False
        else:
            is_fund = is_fund_stat

        # 名稱優化
        name = ticker
        if ticker == "0P0000XS79.F": name = "eMAXIS Slim S&P500"
        elif ticker == "2563.T": name = "iShares S&P500 (避險)"
        elif ticker == "2558.T": name = "MAXIS S&P500 (無避險)"
        elif ticker == "0050.TW": name = "元大台灣50 (0050)"
        
        pe, growth, inst, news = "N/A", "N/A", "N/A", "無消息"
        try:
            info = stock.info
            fetched_name = info.get('longName')
            if fetched_name and name == ticker: name = fetched_name

            if asset_type == "stock":
                pe = info.get('forwardPE', 'N/A')
                growth = info.get('revenueGrowth', 'N/A')
                inst_raw = info.get('heldPercentInstitutions', 0)
                inst = f"{round(inst_raw*100, 1)}%" if isinstance(inst_raw, (int, float)) else "N/A"
                if isinstance(pe, (int, float)): pe = round(pe, 1)
                if isinstance(growth, (int, float)): growth = f"{round(growth*100, 1)}%"
            
            if stock.news: news = stock.news[0]['title']
        except: pass

        # 技術指標
        df['SMA_20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator() if len(df)>20 else df['Close']
        df['SMA_50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator() if len(df)>50 else df['Close']
        
        golden_price = 0
        if len(df) > 200:
            df['SMA_200'] = SMAIndicator(close=df['Close'], window=200).sma_indicator()
            golden_price = df['SMA_200'].iloc[-1]
        else:
            df['SMA_200'] = df['SMA_50']
            
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi() if len(df)>14 else 50
        
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BB_Lower'] = bb.bollinger_lband()
        panic_price = df['BB_Lower'].iloc[-1]

        curr = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        sma20 = df['SMA_20'].iloc[-1]
        sma50 = df['SMA_50'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        
        # 買賣建議
        action = "觀望 / 續抱"
        action_color = "gray"
        confidence = 50
        
        # 買進
        if curr <= panic_price:
            action = "💎 恐慌底 (強力買進)"
            action_color = "green"
            confidence = 95
        elif golden_price > 0 and curr <= golden_price:
            action = "💰 黃金價 (價值買進)"
            action_color = "green"
            confidence = 90
        elif curr > sma50 > (golden_price if golden_price > 0 else 0):
            if rsi > 50 and rsi < 75:
                action = "🚀 多頭強勢 (持有)"
                action_color = "blue"
                confidence = 80
            
        # 賣出
        if rsi > 75: 
            action = "⚠️ 過熱 (獲利警戒)"
            action_color = "orange"
            confidence = 85
        if rsi > 85: 
            action = "🔥 極度危險 (清倉)"
            action_color = "red"
            confidence = 95
            
        trend_ma = df['SMA_20'] if asset_type == "stock" else df['SMA_50']
        trend_name = "月線" if asset_type == "stock" else "季線"
        if curr < trend_ma.iloc[-1] and prev > trend_ma.iloc[-2]:
             action = f"📉 跌破{trend_name} (警戒)"
             action_color = "orange"

        return {
            "Ticker": ticker, "Name": name, "Price": round(curr, 2),
            "Change%": round(((curr-prev)/prev)*100, 2),
            "Action": action, "Color": action_color, "Confidence": confidence,
            "Golden": round(golden_price, 2) if golden_price > 0 else "N/A",
            "Panic": round(panic_price, 2),
            "RSI": round(rsi, 2), "PE": pe, "Growth": growth, "Institutions": inst,
            "News": news, "Data": df, "Symbol": currency_symbol, "IsFund": is_fund
        }
    except Exception as e: 
        return {"Error": str(e)}

# --- 繪圖函式 ---
def draw_chart(item, height=300):
    df = item['Data'].tail(150)
    fig = go.Figure()
    
    if item['IsFund']:
        # 基金用折線
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], line=dict(color='white', width=2), name='Price'))
    else:
        # 股票/ETF 用 K 線 (紅漲綠跌)
        fig.add_trace(go.Candlestick(
            x=df.index, 
            open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
            name='Price',
            increasing_line_color='red',  
            decreasing_line_color='green' 
        ))
        
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name='20MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='blue', width=2), name='50MA'))
    
    if item['Golden'] != "N/A":
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='#00FF00', width=2), name='200MA'))
    
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='red', width=1, dash='dot'), name='恐慌坑'))
    
    fig.update_layout(height=height, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    return fig

# ==========================================
# 主程式介面
# ==========================================
if st.button('🚀 點我進行即時分析'):
    
    # 1. ETF
    st.markdown("## 🛡️ ETF 戰略指揮部 (台/美/日)")
    
    final_etf_list = etf_list
    
    for t in final_etf_list:
        if not t: continue
        item = analyze_asset(t, asset_type="etf")
        
        if not item or "Error" in item:
            error_msg = item['Error'] if item and "Error" in item else "資料無法讀取"
            st.warning(f"❌ **{t}**: {error_msg}")
            continue
            
        sym = item['Symbol']
        with st.expander(f"{item['Action']} | {item['Name']} | {sym}{item['Price']} ({item['Change%']}%)", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"### 指令: :{item['Color']}[{item['Action']}]")
                st.divider()
                
                golden_val = item['Golden']
                delta_gold = f"{round(item['Price'] - golden_val, 2)}" if golden_val != "N/A" else "N/A"
                st.metric("💰 黃金價 (200MA)", f"{sym}{golden_val}", delta=delta_gold, delta_color="inverse")
                
                st.metric("💎 恐慌坑 (底)", f"{sym}{item['Panic']}", delta=f"{round(item['Price'] - item['Panic'], 2)}", delta_color="inverse")
                st.divider()
                st.metric("RSI 強弱", item['RSI'])
                if item['IsFund']:
                    st.caption("⚠️ 此為基金 (折線圖)。")
            with c2:
                st.plotly_chart(draw_chart(item), use_container_width=True)

    st.divider()

    # 2. 家人持股
    st.markdown("## 👨‍👩‍👧‍👦 家人持股衛士")
    for t in family_list:
        if not t: continue
        item = analyze_asset(t, asset_type="stock")
        
        if not item or "Error" in item: 
            st.warning(f"⚠️ {t}: 無法讀取資料")
            continue
        
        is_expanded = item['Color'] in ['orange', 'red', 'green']
        sym = item['Symbol']
        
        with st.expander(f"{item['Action']} | {item['Ticker']} | {sym}{item['Price']} ({item['Change%']}%)", expanded=is_expanded):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"### 指令: :{item['Color']}[{item['Action']}]")
                st.divider()
                st.metric("📊 RSI 強弱指標", item['RSI'], delta="過熱" if item['RSI']>75 else "正常", delta_color="inverse")
                
                golden_val = item['Golden']
                delta_gold = f"{round(item['Price'] - golden_val, 2)}" if golden_val != "N/A" else "N/A"
                st.metric("💰 黃金價 (200MA)", f"{sym}{golden_val}", delta=delta_gold, delta_color="inverse")
                st.metric("💎 恐慌坑 (底)", f"{sym}{item['Panic']}", delta=f"{round(item['Price'] - item['Panic'], 2)}", delta_color="inverse")
                st.divider()
                st.write(f"**機構持股:** {item['Institutions']}")
                st.info(f"📰 {item['News']}")
            with c2:
                st.plotly_chart(draw_chart(item), use_container_width=True)

    # 3. 市場觀察
    st.markdown("## ⚡ 市場觀察名單")
    results = []
    prog = st.progress(0)
    for i, t in enumerate(watchlist):
        if not t: continue
        r = analyze_asset(t, asset_type="stock")
        if r and "Error" not in r: results.append(r)
        prog.progress((i+1)/len(watchlist))
    results.sort(key=lambda x: x['RSI'], reverse=True)
    
    for item in results:
        is_expanded = item['Color'] == 'green' or item['Confidence'] >= 80
        sym = item['Symbol']
        
        with st.expander(f"{item['Action']} | {item['Ticker']} | {sym}{item['Price']} ({item['Change%']}%)", expanded=is_expanded):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"### :{item['Color']}[{item['Action']}]")
                st.metric("RSI 強弱", item['RSI'])
                golden_val = item['Golden']
                delta_gold = f"{round(item['Price'] - golden_val, 2)}" if golden_val != "N/A" else "N/A"
                st.metric("黃金價", f"{sym}{golden_val}", delta=delta_gold, delta_color="inverse")
                st.metric("恐慌坑", f"{sym}{item['Panic']}", delta=f"{round(item['Price'] - item['Panic'], 2)}", delta_color="inverse")
                st.write(f"籌碼: {item['Institutions']}")
            with c2:
                st.plotly_chart(draw_chart(item), use_container_width=True)

else:
    st.info("👋 歡迎回到 Alpha Sniper 白金版，請點擊上方按鈕開始。")
