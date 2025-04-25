# MeetApp Backend

MeetApp, sosyal etkileşim ve toplantı yönetimi için geliştirilmiş bir web uygulamasının backend servisidir. FastAPI ve WebSocket teknolojilerini kullanarak gerçek zamanlı iletişim ve etkileşim sağlar.

## 🚀 Özellikler

- 🔐 JWT tabanlı kimlik doğrulama
- 💬 Gerçek zamanlı sohbet sistemi
- 👥 Kullanıcı yönetimi
- 📅 Aktivite ve toplantı yönetimi
- 🌐 WebSocket desteği
- 🛡️ CORS koruması
- 📝 Özelleştirilmiş hata yönetimi

## 🛠️ Teknolojiler

- FastAPI
- MongoDB
- WebSocket
- JWT Authentication
- Python 3.x
- Node.js (bazı bileşenler için)

## 📋 Gereksinimler

- Python 3.x
- Node.js
- MongoDB
- pip (Python paket yöneticisi)
- npm (Node.js paket yöneticisi)

## 🔧 Kurulum

1. Projeyi klonlayın:
```bash
git clone https://github.com/myusufkose/meetApp_backend_public.git
cd meetapp-backend
```

2. Python sanal ortamı oluşturun ve aktifleştirin:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Python bağımlılıklarını yükleyin:
```bash
pip install -r requirements.txt
```

4. Node.js bağımlılıklarını yükleyin:
```bash
npm install
```

5. `.env` dosyasını oluşturun ve gerekli değişkenleri ayarlayın:
```env
MONGODB_URL=your_mongodb_url
JWT_SECRET=your_jwt_secret
```

## 🚀 Çalıştırma

Geliştirme modunda çalıştırmak için:
```bash
uvicorn main:app --reload
```

Uygulama varsayılan olarak `http://localhost:8000` adresinde çalışacaktır.

## 📚 API Dokümantasyonu

Uygulama çalışırken API dokümantasyonuna şu adreslerden erişebilirsiniz:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Test

Testleri çalıştırmak için:
```bash
pytest
```

## 📁 Proje Yapısı

```
meetapp-backend/
├── auth/               # Kimlik doğrulama işlemleri
├── Database/          # Veritabanı işlemleri
├── models/            # Veri modelleri
├── routers/           # API rotaları
├── main.py           # Ana uygulama dosyası
├── websocket_manager.py # WebSocket yönetimi
├── chat.py           # Sohbet işlevselliği
├── utils.py          # Yardımcı fonksiyonlar
├── error_handler.py  # Hata yönetimi
├── exceptions.py     # Özel istisna sınıfları
├── requirements.txt  # Python bağımlılıkları
└── package.json      # Node.js bağımlılıkları
```

## 🤝 Katkıda Bulunma

1. Bu projeyi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

