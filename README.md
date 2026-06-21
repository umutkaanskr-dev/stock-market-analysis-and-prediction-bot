# BIST Analiz Botu

Borsa İstanbul (BIST) hisseleri için localhost'ta çalışan, teknik analiz yapan
ve **borsa hakkında hiçbir bilgisi olmayan biri için bile anlaşılır** yorumlar
üreten bir Streamlit uygulaması.

## Özellikler
- Popüler BIST hisselerinden hızlı seçim (THYAO, GARAN, ASELS, BIMAS, vb.) veya
  kendi hisse kodunu yazma
- RSI, MACD, Hareketli Ortalamalar (SMA 20/50), Bollinger Bantları
- Mum grafiği (candlestick) ile interaktif görselleştirme
- Kural tabanlı, **sade Türkçe** ile "Pozitif / Negatif / Nötr" genel değerlendirme
  ve nedenlerinin maddeler halinde açıklanması
- Borsa terimleri için mini sözlük (RSI, MACD, hareketli ortalama vb. nedir?)

## Kurulum

```bash
# 1) (Önerilir) sanal ortam oluşturun
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2) Gerekli paketleri kurun
pip install -r requirements.txt
```

## Çalıştırma

```bash
streamlit run app.py
```

Komut çalıştıktan sonra tarayıcınızda otomatik olarak
`http://localhost:8501` açılacaktır. Açılmazsa bu adresi tarayıcınıza
elle yazabilirsiniz.

## Notlar
- Veriler `yfinance` kütüphanesi üzerinden, halka açık ve genelde ~15-20 dakika
  gecikmeli olabilen verilerle sağlanır.
- BIST hisse kodları yfinance'de `.IS` uzantısı ile aranır (örn. `THYAO.IS`).
  Uygulama bunu sizin için otomatik ekler; sadece "THYAO" yazmanız yeterli.
- Bu uygulama **yatırım danışmanlığı değildir**. Sunulan yorumlar, geçmiş
  fiyat verilerinden hesaplanan matematiksel göstergelere dayanan, eğitim
  amaçlı genellemelerdir. Yatırım kararlarınızı kendi araştırmanıza ve/veya
  lisanslı bir finansal danışmana dayandırmanız önerilir.

## Sorun Giderme
- **"Veri bulunamadı" hatası**: Hisse kodunu kontrol edin, internet
  bağlantınızı kontrol edin, ya da bir süre sonra tekrar deneyin (Yahoo
  Finance API zaman zaman geçici kısıtlama uygulayabilir).
- **Grafikler boş görünüyor**: Daha uzun bir zaman aralığı seçmeyi deneyin
  (örn. "Son 6 Ay" yerine "Son 1 Yıl").
