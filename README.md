# MultiAgent (Microsoft AutoGen ile Yerelde 4 Ajanlı Geliştirme Yol Haritası)

Bu depo, **Microsoft AutoGen** kullanarak yerelde (local) çalışan ve birbiriyle iletişim kuran **4 yapay zekâ ajanı** (Software Designer, Backend, Frontend, QA) ile yazılım geliştirme sürecini uçtan uca otomatikleştirmeyi hedefleyen bir proje planı içerir.

## 1) Proje Amacı

- Tek bir uygulamayı (ör. küçük bir ürün/servis) **tasarım → API → arayüz → test** adımlarında çok ajanlı bir akışla üretmek.
- Ajanların rol bazlı sorumluluklarla **birbirini denetlediği** (review) ve **çıktıları devrettiği** bir süreç kurmak.
- AutoGen ile **GroupChat + Manager** yaklaşımı kullanarak görevleri doğru ajana yönlendirmek.
- Yerelde çalıştırılabilir olmak: 
  - Bulut LLM (OpenAI/Azure OpenAI vb.) veya
  - Yerel LLM (ör. **Ollama**) ile.

## 2) Mimari Genel Bakış

Önerilen mimari, AutoGen’in çok ajanlı sohbet altyapısı üzerine kuruludur:

- **Agent’lar**: Her biri ayrı rol/kişilik/araç seti olan `AssistantAgent` türevleri.
- **GroupChat**: Ajanların mesajlaştığı ortak kanal.
- **GroupChatManager**: 
  - Görevleri parçalara ayırır,
  - Mesaj sırasını yönetir,
  - Hangi ajanın ne zaman konuşacağını belirler,
  - Gerekirse tur sayısı/bitirme koşulu uygular.

Akış örneği:

1. Kullanıcı hedefi verir.
2. Manager, görevi tasarım → backend → frontend → QA olarak böler.
3. Designer tasarım dokümanı + backlog çıkarır.
4. Backend API sözleşmesi ve servis iskeletini üretir.
5. Frontend UI akışı ve entegrasyonu üretir.
6. QA test senaryoları + otomasyon önerileri ve regression checklist üretir.
7. Manager çıktıları “Done” kriterlerine göre toparlar ve sonraki adımı başlatır.

## 3) Ajan Rolleri ve Sorumluluklar

### 3.1 Software Designer (Yazılım Tasarımcısı)
- Ürün hedeflerini netleştirir, gereksinim çıkarır (functional/non-functional).
- Kullanım senaryoları (user stories), kabul kriterleri (acceptance criteria) üretir.
- Yüksek seviye mimari: modüller, veri akışı, hata senaryoları.
- Backend–Frontend sözleşmesini başlatır: endpoint taslağı, DTO şemaları.

### 3.2 Backend Agent
- API tasarımı (OpenAPI/Swagger taslağı önerilir).
- Veri modeli ve kalıcılık yaklaşımı (örn. SQLite/PostgreSQL).
- Servis katmanı, iş kuralları, hata yönetimi.
- Docker/uvicorn/fastapi gibi çalışma modelleri (seçilen stack’e göre).
- “Frontend’in tüketebileceği şekilde” örnek request/response üretir.

### 3.3 Frontend Agent
- UI akışları, sayfa/komponent kırılımı.
- State yönetimi ve API entegrasyonu.
- UX odaklı iyileştirmeler: loading/error/empty state.
- Gerekirse basit tasarım sistemi / komponent kütüphanesi seçimi.

### 3.4 QA Agent
- Test matrisi: birim, entegrasyon, e2e, smoke, regression.
- Kritik kullanıcı yolculukları için test senaryoları.
- Otomasyon önerileri (pytest, playwright/cypress vb.).
- Hata raporu şablonu ve kalite kapıları (quality gates).

## 4) Ajanlar Nasıl İletişim Kurar? (GroupChat / Manager)

AutoGen’de tipik yaklaşım:

- Her ajan, belirli bir “system prompt” ile tanımlanır (rol, sınırlar, çıktı formatı).
- `GroupChat`, ajan listesini ve mesaj geçmişini tutar.
- `GroupChatManager`, mesajları orkestre eder:
  - “Designer konuşsun → Backend devam etsin → Frontend uygulasın → QA doğrulasın” gibi.
  - Gerekirse tekrar turları: QA bulgu çıkarır, Manager Backend/Frontend’e düzeltme döngüsü açar.

Öneri: Manager, her aşamada şu formatı zorunlu kılabilir:

- **Çıktı** (deliverable)
- **Varsayımlar**
- **Riskler**
- **Sonraki adım için input**

## 5) Kurulum Ön Koşulları

### 5.1 Python ve Sanal Ortam
- Python **3.10+** (tercihen 3.11)
- `venv` veya `conda`

### 5.2 LLM Seçenekleri

#### Seçenek A: Bulut LLM (OpenAI / Azure OpenAI)
- Ortam değişkenleri (örnek):
  - `OPENAI_API_KEY=...`
  - (Azure kullanıyorsanız) `AZURE_OPENAI_ENDPOINT=...`, `AZURE_OPENAI_API_KEY=...`, `AZURE_OPENAI_DEPLOYMENT=...`

#### Seçenek B: Yerel LLM (Ollama)
- Ollama kurulumu ve bir model indirme:
  - `ollama pull llama3.1` (örnek)
- AutoGen’i Ollama endpoint’i ile konuşturacak yapılandırma (kütüphane sürümüne göre değişebilir).

Not: AutoGen sürümleri ve sağlayıcı entegrasyonları değişebildiği için, repo içinde `config/llm.json` veya `.env` üzerinden yönetim önerilir.

## 6) Quickstart (Önerilen Komutlar)

Aşağıdaki komutlar bir iskelet akış içindir (dosya adları ve paketler projeye göre uyarlanır):

```bash
# 1) Repo
git clone https://github.com/MertOmgen/MultiAgent.git
cd MultiAgent

# 2) venv
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .\.venv\Scripts\Activate.ps1

# 3) bağımlılıklar
pip install -U pip
pip install -r requirements.txt

# 4) environment
cp .env.example .env
# .env içine API key veya Ollama ayarlarını girin

# 5) çalıştırma
python -m app.main
```

## 7) Önerilen Klasör Yapısı

```text
MultiAgent/
  README.md
  requirements.txt
  .env.example
  app/
    main.py                # groupchat + manager başlangıç noktası
    agents/
      designer.py          # Software Designer agent tanımları
      backend.py           # Backend agent
      frontend.py          # Frontend agent
      qa.py                # QA agent
      prompts/
        designer.md
        backend.md
        frontend.md
        qa.md
    orchestration/
      groupchat.py         # GroupChat/Manager kurulumu
      routing.py           # görev yönlendirme / turn policy
    tools/
      repo_tools.py        # dosya yazma/okuma, şema üretim, vb.
      http_tools.py        # API çağrıları gerekiyorsa
    config/
      llm_config.py        # LLM seçimi (OpenAI/Azure/Ollama)
  docs/
    architecture.md
    api_contract.md
    qa_plan.md
```

## 8) Sonraki Adımlar

1. **AutoGen sürümü + sağlayıcı** kararını netleştirin (OpenAI/Azure/Ollama).
2. Her ajan için **system prompt** dosyalarını (`app/agents/prompts/*.md`) oluşturun.
3. `GroupChatManager` için bir **turn policy** belirleyin:
   - Sıra tabanlı (Designer → Backend → Frontend → QA)
   - veya hedef odaklı (Manager, son çıktıya göre ajana paslar)
4. İlk PoC senaryosu seçin:
   - Örn. “Basit görev takip uygulaması” (CRUD + login opsiyonel).
5. QA kapılarını tanımlayın:
   - API contract doğrulama,
   - Frontend entegrasyon testi,
   - Minimum test kapsamı.
6. “Kod üretimi” yerine önce **doküman üretimi** ile başlayın (tasarım + API sözleşmesi + test planı), sonra iteratif olarak kod aşamasına geçin.

---

> Bu README bir yol haritasıdır. Uygulama detayları (stack seçimi, AutoGen entegrasyon kodu, model/endpoint ayarları) proje ilerledikçe repo içinde netleştirilecektir.
