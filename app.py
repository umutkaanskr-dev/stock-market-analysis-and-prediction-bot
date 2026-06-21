"""
BIST Analiz Botu
-----------------
Borsa İstanbul (BIST) hisseleri için teknik analiz yapan ve
borsa hakkında bilgisi olmayan kullanıcılara sade dille
tavsiye/yorum sunan localhost uygulaması.

NOT: Bu araç YATIRIM TAVSİYESİ değildir. Eğitim ve bilgilendirme
amaçlıdır. Yatırım kararlarınızı kendi araştırmanıza ve/veya
lisanslı bir finansal danışmana dayandırın.

Çalıştırmak için:
    pip install -r requirements.txt
    streamlit run app.py UMUT KAAN ŞEKER 
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# SAYFA AYARLARI
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="BIST Analiz Botu",
    page_icon="📈",
    layout="wide",
)

# ----------------------------------------------------------------------
# YARDIMCI: BIST'TE EN ÇOK İŞLEM GÖREN BAZI HİSSELER (kısayol listesi)
# ----------------------------------------------------------------------
POPULER_HISSELER = {
    "THYAO - Türk Hava Yolları": "THYAO.IS",
    "ASELS - Aselsan": "ASELS.IS",
    "GARAN - Garanti BBVA": "GARAN.IS",
    "AKBNK - Akbank": "AKBNK.IS",
    "BIMAS - BİM Mağazaları": "BIMAS.IS",
    "EREGL - Ereğli Demir Çelik": "EREGL.IS",
    "KCHOL - Koç Holding": "KCHOL.IS",
    "SAHOL - Sabancı Holding": "SAHOL.IS",
    "SISE - Şişecam": "SISE.IS",
    "TUPRS - Tüpraş": "TUPRS.IS",
    "PGSUS - Pegasus": "PGSUS.IS",
    "FROTO - Ford Otosan": "FROTO.IS",
    "ISCTR - İş Bankası (C)": "ISCTR.IS",
    "TCELL - Turkcell": "TCELL.IS",
    "BIST 100 Endeksi": "XU100.IS",
}


# ----------------------------------------------------------------------
# TEKNİK GÖSTERGE HESAPLAMALARI (harici kütüphaneye bağımlı olmadan)
# ----------------------------------------------------------------------
def hesapla_rsi(close: pd.Series, periyot: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / periyot, min_periods=periyot).mean()
    avg_loss = loss.ewm(alpha=1 / periyot, min_periods=periyot).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def hesapla_macd(close: pd.Series, hizli=12, yavas=26, sinyal=9):
    ema_hizli = close.ewm(span=hizli, adjust=False).mean()
    ema_yavas = close.ewm(span=yavas, adjust=False).mean()
    macd = ema_hizli - ema_yavas
    sinyal_hat = macd.ewm(span=sinyal, adjust=False).mean()
    histogram = macd - sinyal_hat
    return macd, sinyal_hat, histogram


def hesapla_bollinger(close: pd.Series, periyot=20, std_carpan=2):
    orta = close.rolling(periyot).mean()
    std = close.rolling(periyot).std()
    ust = orta + std_carpan * std
    alt = orta - std_carpan * std
    return ust, orta, alt


def hesapla_sma(close: pd.Series, periyot: int) -> pd.Series:
    return close.rolling(periyot).mean()


# ----------------------------------------------------------------------
# VERİ ÇEKME
# ----------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def veri_cek(ticker: str, periyot: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=periyot, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


# ----------------------------------------------------------------------
# BASİT DİLLE YORUM ÜRETME (kural tabanlı "uzman" mantığı)
# ----------------------------------------------------------------------
def yorum_uret(df: pd.DataFrame) -> dict:
    son = df.iloc[-1]
    onceki = df.iloc[-2]

    puan = 0
    nedenler = []

    # RSI yorumu
    rsi = son["RSI"]
    if pd.notna(rsi):
        if rsi < 30:
            puan += 1
            nedenler.append(
                f"RSI değeri {rsi:.1f} ile 30'un altında. Bu genelde hissenin "
                "'aşırı satılmış' olabileceğini, yani fiyatın gerekenden fazla "
                "düşmüş olabileceğini gösterir. Bazı yatırımcılar bunu olası bir "
                "tepki yükselişi sinyali olarak okur."
            )
        elif rsi > 70:
            puan -= 1
            nedenler.append(
                f"RSI değeri {rsi:.1f} ile 70'in üzerinde. Bu genelde hissenin "
                "'aşırı alınmış' olabileceğini, yani fiyatın hızlı yükseldiğini "
                "gösterir. Böyle durumlarda kısa vadeli bir düzeltme (geri çekilme) "
                "görülebilir."
            )
        else:
            nedenler.append(
                f"RSI değeri {rsi:.1f} ile nötr bölgede (30-70 arası). Belirgin bir "
                "aşırı alım/satım sinyali yok."
            )

    # MACD yorumu
    macd, macd_sinyal = son["MACD"], son["MACD_Sinyal"]
    macd_onceki, macd_sinyal_onceki = onceki["MACD"], onceki["MACD_Sinyal"]
    if pd.notna(macd) and pd.notna(macd_sinyal):
        if macd_onceki < macd_sinyal_onceki and macd > macd_sinyal:
            puan += 1
            nedenler.append(
                "MACD çizgisi sinyal çizgisini yukarı yönlü kesti. Bu, kısa vadede "
                "momentumun (ivmenin) yukarı döndüğüne işaret eden klasik bir "
                "'al' sinyali olarak yorumlanır."
            )
        elif macd_onceki > macd_sinyal_onceki and macd < macd_sinyal:
            puan -= 1
            nedenler.append(
                "MACD çizgisi sinyal çizgisini aşağı yönlü kesti. Bu, momentumun "
                "zayıfladığına işaret eden klasik bir 'sat' sinyali olarak "
                "yorumlanır."
            )
        elif macd > macd_sinyal:
            puan += 0.5
            nedenler.append(
                "MACD, sinyal çizgisinin üzerinde seyrediyor; bu kısa vadeli "
                "trendin halen yukarı yönlü olabileceğini gösterir."
            )
        else:
            puan -= 0.5
            nedenler.append(
                "MACD, sinyal çizgisinin altında seyrediyor; bu kısa vadeli "
                "trendin halen aşağı yönlü olabileceğini gösterir."
            )

    # Hareketli ortalama (trend) yorumu
    sma20, sma50 = son.get("SMA20"), son.get("SMA50")
    fiyat = son["Close"]
    if pd.notna(sma20) and pd.notna(sma50):
        if fiyat > sma20 > sma50:
            puan += 1
            nedenler.append(
                "Fiyat, hem 20 günlük hem 50 günlük ortalamanın üzerinde ve kısa "
                "ortalama uzun ortalamanın üstünde. Bu, genel görünümün yukarı "
                "yönlü (boğa) olduğuna işaret eder."
            )
        elif fiyat < sma20 < sma50:
            puan -= 1
            nedenler.append(
                "Fiyat, hem 20 günlük hem 50 günlük ortalamanın altında ve kısa "
                "ortalama uzun ortalamanın altında. Bu, genel görünümün aşağı "
                "yönlü (ayı) olduğuna işaret eder."
            )
        else:
            nedenler.append(
                "Fiyat ile hareketli ortalamalar arasında karışık bir görünüm var; "
                "net bir trend yönü şu an için belirgin değil."
            )

    # Bollinger
    bol_ust, bol_alt = son.get("BOL_UST"), son.get("BOL_ALT")
    if pd.notna(bol_ust) and pd.notna(bol_alt):
        if fiyat >= bol_ust:
            nedenler.append(
                "Fiyat, Bollinger Bantları'nın üst sınırına yakın/üzerinde. Bu "
                "kısa vadede fiyatın 'gerilmiş' olabileceğini gösterir."
            )
        elif fiyat <= bol_alt:
            nedenler.append(
                "Fiyat, Bollinger Bantları'nın alt sınırına yakın/altında. Bu "
                "kısa vadede fiyatın 'aşırı baskılanmış' olabileceğini gösterir."
            )

    # Genel skor -> sade tavsiye
    if puan >= 1.5:
        etiket = "Pozitif Görünüm"
        renk = "green"
        ozet = (
            "Teknik göstergelerin çoğu şu an yukarı yönlü bir görünüme işaret "
            "ediyor. Bu, kısa vadede fiyatın yükselme ihtimalinin göstergeler "
            "açısından biraz daha güçlü olduğu anlamına gelebilir."
        )
    elif puan <= -1.5:
        etiket = "Negatif Görünüm"
        renk = "red"
        ozet = (
            "Teknik göstergelerin çoğu şu an aşağı yönlü bir görünüme işaret "
            "ediyor. Bu, kısa vadede fiyatın baskı altında kalma ihtimalinin "
            "göstergeler açısından biraz daha güçlü olduğu anlamına gelebilir."
        )
    else:
        etiket = "Kararsız / Nötr Görünüm"
        renk = "orange"
        ozet = (
            "Göstergeler karışık sinyaller veriyor; net bir yön henüz "
            "oluşmamış görünüyor. Böyle durumlarda 'bekle-gör' yaklaşımı "
            "yaygın bir tercihtir."
        )

    return {
        "etiket": etiket,
        "renk": renk,
        "ozet": ozet,
        "nedenler": nedenler,
        "puan": puan,
    }


# ----------------------------------------------------------------------
# ARAYÜZ
# ----------------------------------------------------------------------
st.title("📈 BIST Analiz Botu")
st.caption(
    "Borsa İstanbul hisseleri için teknik analiz — borsa hakkında hiçbir "
    "ön bilgisi olmayan biri için sade dille açıklanır."
)

with st.sidebar:
    st.header("⚙️ Ayarlar")

    secim_modu = st.radio("Hisse nasıl seçilsin?", ["Popüler listeden seç", "Kendim yazayım"])

    if secim_modu == "Popüler listeden seç":
        secilen_etiket = st.selectbox("Hisse seçin", list(POPULER_HISSELER.keys()))
        ticker = POPULER_HISSELER[secilen_etiket]
    else:
        kod = st.text_input("BIST kodu girin (örn: THYAO)", value="THYAO").strip().upper()
        ticker = f"{kod}.IS" if kod else "THYAO.IS"

    periyot_secenekleri = {
        "Son 1 Ay": "1mo",
        "Son 3 Ay": "3mo",
        "Son 6 Ay": "6mo",
        "Son 1 Yıl": "1y",
        "Son 2 Yıl": "2y",
    }
    periyot_etiket = st.selectbox("Zaman aralığı", list(periyot_secenekleri.keys()), index=2)
    periyot = periyot_secenekleri[periyot_etiket]

    interval = "1d"

    st.markdown("---")
    st.markdown(
        "⚠️ **Uyarı:** Bu uygulama yatırım tavsiyesi vermez. Sadece teknik "
        "göstergeleri sade bir dille açıklar. Yatırım kararı vermeden önce "
        "kendi araştırmanızı yapın veya lisanslı bir danışmana sorun."
    )

st.markdown(f"### Seçilen Sembol: `{ticker}`")

with st.spinner("Veriler çekiliyor..."):
    try:
        df = veri_cek(ticker, periyot, interval)
    except Exception as e:
        st.error(f"Veri çekilemedi: {e}")
        st.stop()

if df is None or df.empty:
    st.error(
        "Bu sembol için veri bulunamadı. Kodu kontrol edin (BIST kodları "
        "yfinance'de '.IS' uzantısıyla biter, örn: THYAO.IS)."
    )
    st.stop()

# Göstergeleri hesapla
df["RSI"] = hesapla_rsi(df["Close"])
df["MACD"], df["MACD_Sinyal"], df["MACD_Hist"] = hesapla_macd(df["Close"])
df["SMA20"] = hesapla_sma(df["Close"], 20)
df["SMA50"] = hesapla_sma(df["Close"], 50)
df["BOL_UST"], df["BOL_ORTA"], df["BOL_ALT"] = hesapla_bollinger(df["Close"])

if len(df) < 30:
    st.warning(
        "Seçilen zaman aralığı için yeterli veri yok. Daha uzun bir zaman "
        "aralığı seçmeyi deneyin."
    )

# ----------------------------------------------------------------------
# ÜST ÖZET KARTLARI
# ----------------------------------------------------------------------
son_fiyat = df["Close"].iloc[-1]
onceki_fiyat = df["Close"].iloc[-2] if len(df) > 1 else son_fiyat
degisim = son_fiyat - onceki_fiyat
degisim_yuzde = (degisim / onceki_fiyat * 100) if onceki_fiyat else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Son Fiyat", f"{son_fiyat:,.2f} ₺", f"{degisim:+.2f} ({degisim_yuzde:+.2f}%)")
col2.metric("Günlük En Yüksek", f"{df['High'].iloc[-1]:,.2f} ₺")
col3.metric("Günlük En Düşük", f"{df['Low'].iloc[-1]:,.2f} ₺")
col4.metric("İşlem Hacmi", f"{df['Volume'].iloc[-1]:,.0f}")

st.markdown("---")

# ----------------------------------------------------------------------
# SADE DİLLE YORUM BÖLÜMÜ (borsayı bilmeyen biri için)
# ----------------------------------------------------------------------
yorum = yorum_uret(df)

st.subheader("🧭 Sade Dille Genel Değerlendirme")
st.markdown(
    f"<div style='padding:16px;border-radius:10px;background-color:rgba(128,128,128,0.08);"
    f"border-left:6px solid {yorum['renk']};'>"
    f"<h4 style='margin:0;color:{yorum['renk']};'>{yorum['etiket']}</h4>"
    f"<p style='margin-top:8px;'>{yorum['ozet']}</p>"
    f"</div>",
    unsafe_allow_html=True,
)

with st.expander("📋 Bu değerlendirme neye dayanıyor? (Detaylı nedenler)"):
    for n in yorum["nedenler"]:
        st.markdown(f"- {n}")

st.info(
    "💡 **Borsa bilmeyenler için not:** RSI, MACD, hareketli ortalama gibi "
    "terimler, geçmiş fiyat hareketlerinden hesaplanan matematiksel "
    "göstergelerdir. Geleceği garanti etmezler; sadece olasılık ve eğilim "
    "hakkında fikir verirler. Hiçbir gösterge %100 doğru değildir."
)

st.markdown("---")

# ----------------------------------------------------------------------
# GRAFİKLER
# ----------------------------------------------------------------------
st.subheader("📊 Fiyat Grafiği ve Göstergeler")

fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.55, 0.2, 0.25],
    vertical_spacing=0.04,
    subplot_titles=("Fiyat (Mum Grafiği) + Bollinger + Ortalamalar", "RSI", "MACD"),
)

fig.add_trace(
    go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Fiyat",
    ),
    row=1, col=1,
)
fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20", line=dict(width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line=dict(width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["BOL_UST"], name="Bollinger Üst", line=dict(width=1, dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["BOL_ALT"], name="Bollinger Alt", line=dict(width=1, dash="dot")), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="purple")), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="blue")), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Sinyal"], name="Sinyal", line=dict(color="orange")), row=3, col=1)
fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="Histogram", marker_color="gray"), row=3, col=1)

fig.update_layout(height=850, xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.02))

st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------
# SÖZLÜK / EĞİTİM BÖLÜMÜ
# ----------------------------------------------------------------------
st.markdown("---")
st.subheader("📚 Borsa Bilmeyenler İçin Mini Sözlük")

terimler = {
    "RSI (Göreceli Güç Endeksi)": "0-100 arasında değişen, hissenin 'aşırı alınmış' ya da "
        "'aşırı satılmış' olup olmadığını gösteren bir gösterge. 70 üzeri yüksek, 30 altı düşük "
        "kabul edilir.",
    "MACD": "İki farklı hareketli ortalamanın farkına dayanan, fiyat momentumunun (ivmesinin) "
        "yön değiştirip değiştirmediğini gösteren bir gösterge.",
    "Hareketli Ortalama (SMA)": "Son X günün ortalama fiyatı. Fiyatın genel eğilimini (trendini) "
        "daha yumuşak bir çizgiyle göstermeye yarar.",
    "Bollinger Bantları": "Fiyatın etrafına çizilen ve fiyatın istatistiksel olarak ne kadar "
        "'normal' veya 'aşırı' hareket ettiğini gösteren üst ve alt sınır çizgileri.",
    "Mum Grafiği (Candlestick)": "Her bir 'mum', belirli bir zaman diliminde açılış, kapanış, en "
        "yüksek ve en düşük fiyatı gösterir. Yeşil mum genelde yükselişi, kırmızı mum düşüşü "
        "temsil eder.",
    "İşlem Hacmi": "Belirli bir zaman diliminde kaç hisse alınıp satıldığını gösterir. Yüksek "
        "hacim, o fiyat hareketine daha fazla yatırımcının katıldığı anlamına gelir.",
}

for terim, aciklama in terimler.items():
    with st.expander(terim):
        st.write(aciklama)

st.markdown("---")
st.caption(
    "Bu uygulama yfinance üzerinden alınan halka açık piyasa verilerini kullanır. "
    "Veriler gecikmeli olabilir ve sadece bilgilendirme amaçlıdır. "
    "Yatırım tavsiyesi değildir (Bu bir 'Yatırım Danışmanlığı' faaliyeti kapsamında değildir)."
)
