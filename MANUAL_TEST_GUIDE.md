# 🧪 PR-Sentry Manuel Test Rehberi

Bu doküman, yeni özelliklerin manuel olarak test edilmesi için gerekli adımları içerir.

## ✅ Otomatik Testler (Yapıldı)

- ✅ 105 pytest testi başarıyla geçiyor
- ✅ Tüm modüller için unit testler mevcut

## 🔧 Manuel Test Gereken Özellikler

### 1. Exponential Backoff (Retry Mekanizması)

**Test senaryosu:** API rate limiting durumunda retry'ların çalışıp çalışmadığını kontrol et.

```bash
# Geçersiz API key ile test et - retry'ları görmek için
export ANTHROPIC_API_KEY="sk-ant-invalid-key-123"
export GITHUB_TOKEN="your_token"
export GITHUB_REPOSITORY="your_repo"
export PR_NUMBER="1"

python main.py
```

**Beklenen:** 
- 5 retry denemesi (1s, 2s, 4s, 8s, 16s)
- Her deneme arasında jitter (±25%) eklenmiş olmalı
- Console'da "Retrying..." mesajları görülmeli

---

### 2. Docker Çalıştırma

**Test senaryosu:** Docker container'ın düzgün build olup çalışıp çalışmadığını kontrol et.

```bash
# Build
docker build -t pr-sentry .

# .env dosyası oluştur
cat > .env << EOF
GITHUB_TOKEN=your_github_token
GITHUB_REPOSITORY=owner/repo
PR_NUMBER=123
ANTHROPIC_API_KEY=your_key
EOF

# Çalıştır
docker run --env-file .env pr-sentry
```

**Beklenen:**
- Container başarıyla build olmalı
- Non-root user olarak çalışmalı
- Health check geçmeli
- PR review tamamlanmalı

---

### 3. Entropy-Based Secret Detection

**Test senaryosu:** Yüksek entropili (rastgele) stringleri tespit edip etmediğini kontrol et.

Bir test PR'ı aç ve şu satırları ekle:

```python
# Bu satır yüksek entropili - tespit edilmeli
api_key = "x8Kj9mNpQr2sT4uVwX5yZ6aB7cD8eF9gH0iJ1kL2mN3oP4qR"

# Base64 encoded - tespit edilmeli  
secret = "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBzZWNyZXQh"
```

**Beklenen:**
- Security report'ta "High-entropy string detected" uyarısı görülmeli
- Her iki satır için de flag atılmalı

---

### 4. Multi-Language Support (TR/EN)

**Test senaryosu:** Türkçe ve İngilizce raporların düzgün çalışıp çalışmadığını kontrol et.

```bash
# İngilizce test
export SENTRY_LANG="en"
python main.py

# Türkçe test
export SENTRY_LANG="tr"
python main.py
```

**Beklenen:**
- `SENTRY_LANG=en` → "Security Report", "Review"
- `SENTRY_LANG=tr` → "Güvenlik Raporu", "İnceleme"
- PR comment'i seçilen dilde olmalı

---

### 5. Custom Prompts (sentry-config.yml)

**Test senaryosu:** Özel kuralların LLM prompt'una eklenip eklenmediğini kontrol et.

Repo'ya `.github/sentry-config.yml` ekle:

```yaml
custom_rules:
  - "Always check for race conditions in concurrent code"
  - "Flag any use of eval() or exec()"

ignore_paths:
  - "test/"
  - "*.md"

slop_threshold: 80
```

**Beklenen:**
- Custom rules LLM review'ında dikkate alınmalı
- `test/` klasöründeki değişiklikler ignore edilmeli
- Markdown dosyaları review'a dahil olmamalı
- Slop threshold 80'e yükseltilmiş olmalı

---

### 6. PR Summary Feature

**Test senaryosu:** PR özet bilgilerinin doğru çıkıp çıkmadığını kontrol et.

Bir test PR'ı oluştur:
- 5 dosya değiştir
- 100 satır ekle
- 50 satır sil

**Beklenen PR comment formatı:**
```
📊 **PR Summary**
- **Files changed:** 5
- **Additions:** +100 lines
- **Deletions:** -50 lines
- **File types:** Python (3), JavaScript (2)
```

---

### 7. Async HTTP Calls

**Test senaryosu:** Concurrent API call'ların çalışıp çalışmadığını kontrol et.

```bash
# Zaman ölç
time python main.py
```

**Beklenen:**
- PR data, diff ve commit messages aynı anda (concurrently) fetch edilmeli
- Topla süre ~30-40% daha hızlı olmalı (sequential'e göre)
- Console'da "🔍 PR-Sentry started" mesajından sonra hızlıca veriler gelmeli

---

### 8. Cloud Provider Credential Patterns

**Test senaryosu:** Farklı cloud provider credential'larını tespit edip etmediğini kontrol et.

Test PR'ına şunları ekle:

```python
# AWS
aws_key = "AKIAIOSFODNN7EXAMPLE"
aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Azure
azure_key = "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=abcd1234"

# GCP Service Account
gcp = '{"type": "service_account", "project_id": "my-project"}'

# GitHub PAT
github_token = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# OpenAI
openai_key = "sk-1234567890abcdef1234567890abcdef12345678901234567890"

# Anthropic
anthropic_key = "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxx"

# MongoDB
mongo_uri = "mongodb://admin:password123@localhost:27017/mydb"

# Stripe (Example pattern - build at runtime to avoid push protection)
stripe_prefix = "sk" + "_live_"
stripe_key = stripe_prefix + "51ABCDEFabcdef1234567890"
```

**Beklenen:**
- Her bir credential için security warning
- Toplam 9 farklı pattern tespit edilmeli
- Report'ta detaylı açıklamalar olmalı

---

## 🎯 Integration Test (End-to-End)

**En kapsamlı test:** Gerçek bir PR üzerinde tüm özelliklerin birlikte çalıştığını kontrol et.

1. Test reposu oluştur
2. GitHub Action workflow ekle
3. Test PR'ı aç:
   - Bir security issue ekle (hardcoded secret)
   - Bir logic bug ekle (null pointer risk)
   - AI-generated slop içerik ekle
4. PR-Sentry'nin comment'ini kontrol et

**Beklenen comment içeriği:**
- ✅ Slop score
- ✅ Security report (hardcoded secret bulmuş)
- ✅ LLM review (logic bug'ı açıklamış)
- ✅ PR summary
- ✅ Doğru dilde (SENTRY_LANG'e göre)

---

## 📝 Test Checklist

Manuel test yaparken bu checklist'i kullan:

- [ ] Exponential backoff retry'ları çalışıyor
- [ ] Docker container başarıyla build oluyor ve çalışıyor
- [ ] Entropy scanner yüksek entropili stringleri tespit ediyor
- [ ] Multi-language (TR/EN) düzgün çalışıyor
- [ ] Custom config (sentry-config.yml) uygulanıyor
- [ ] PR summary doğru bilgiler içeriyor
- [ ] Async HTTP calls concurrent çalışıyor
- [ ] 35+ cloud provider pattern'i çalışıyor
- [ ] GitHub Action workflow sorunsuz çalışıyor
- [ ] PR comment düzgün formatlanmış ve okunabilir

---

## 🐛 Bilinen Limitasyonlar

1. **Rate Limiting:** Anthropic API rate limit'e takılırsa exponential backoff devreye girer
2. **Large PRs:** 1000+ satır diff'lerde LLM timeout riski var
3. **Binary Files:** Binary dosyalar security scan'e dahil edilmiyor
4. **Language Detection:** Dosya uzantısına göre yapılıyor (içerik analizi yok)

---

## 📞 Sorun Yaşarsan

Testler sırasında sorun yaşarsan:

1. `pytest` ile unit testleri çalıştır
2. Log'ları kontrol et
3. Environment variable'ların doğru set edildiğinden emin ol
4. GitHub Action'da ise workflow logs'u incele
