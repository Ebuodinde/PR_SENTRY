# 🚀 PR-Sentry Gelecek Yol Haritası (TODO)

Bu liste, projenin daha sağlam, geniş kapsamlı ve kullanıcı dostu olması için yapılabilecek iyileştirmeleri içerir.

## 🛠️ Teknik İyileştirmeler (Stabilite & Performans)
- [ ] **Exponential Backoff:** `reviewer.py` içindeki retry mekanizmasını sabit bekleme yerine exponential backoff (üstel geri çekilme) ile değiştir.
- [ ] **Pytest Suite:** Tüm modüller için unit test'ler ve `pytest` tabanlı bir test suite'i ekle.
- [ ] **Dockerization:** GitHub Action dışında yerel olarak da kolayca çalıştırılabilmesi için `Dockerfile` ekle.
- [ ] **Async GitHub Calls:** `urllib` yerine `httpx` veya `aiohttp` kullanarak GitHub API çağrılarını asenkron hale getir.

## 🔐 Güvenlik Genişletmesi
- [ ] **Entropy-based Secret Detection:** Sadece regex değil, yüksek entropili string'leri de tespit eden bir mantık ekle.
- [ ] **Cloud Provider Integration:** AWS, Azure ve GCP için daha spesifik (format doğrulamalı) tarama kuralları ekle.

## ✨ Yeni Özellikler
- [ ] **Multi-language Support:** Raporlama dilini (TR/EN) seçilebilir hale getir.
- [ ] **Custom Prompts:** Kullanıcıların kendi "Zero-Nitpick" kurallarını `.github/sentry-config.yml` üzerinden tanımlayabilmesini sağla.
- [ ] **Summary of Changes:** PR'ın genel bir özetini çıkaran (Security Report'tan bağımsız) küçük bir bölüm ekle.
- [ ] **Dashboard/UI:** Birden fazla repo için sonuçları görebileceğiniz basit bir web arayüzü (Stitch ile prototip yapılabilir).

## 📝 Dökümantasyon
- [ ] **Contributing Guide:** Diğer geliştiricilerin projeye nasıl katkı sağlayabileceğine dair döküman hazırla.
- [ ] **Examples:** Farklı dillerdeki (JS, Go, Rust vb.) pratik kullanım örneklerini içeren bir klasör oluştur.
