# VENVSTUDIO_TODO.md

## 🔴 KRİTİK

- **B41** — ✅ ÇÖZÜLDÜ (v1.3.68–1.4.0): AppImage/EXE subprocess re-launch loop
- **B42** — Python yükleyici güvenlik kontrolleri
- **B43** — Arch + Python 3.14 Orange3 crash
- **B44** — Arch'ta IPython çalışmıyor
- **B47** — 182 satır hardcoded dark renk
- **B48** — @safe_slot/SafeWorkerMixin henüz yaygınlaştırılmadı
- **B49** — Windows EXE: ilk açılışta Python kurulu değilse kullanıcıya sor, python.org installer indir
- **B50** — ✅ ÇÖZÜLDÜ (v1.4.12): Linux AppImage env sonrası crash — email modülü exclude'dan çıkarıldı

---

## 🟡 PLANLI (öncelik sırasıyla)

### 1. 🔄 F51 — Rename (Full) + Rename (Only Name)
- [ ] **Rename (Full)**: clone + delete — yeni isimde env oluştur, tüm paketleri kur, eskiyi sil. Yavaş ama temiz.
- [ ] **Rename (Only Name)**: sadece klasör rename — anında biter, symlink'ler bozulabilir ama çoğu durumda çalışır.
- [ ] Her ikisi de butonlarda VE sağ tık context menüde olacak
- [ ] Mevcut "Rename" butonu → "Rename (Only Name)" olarak güncellenecek
- [ ] Yeni "Rename (Full)" butonu eklenecek

### 2. 🎓 F38 — EĞİTİCİ ÖZELLİKLER (devam)
- [ ] EDUCATIONAL_HINTS UI'da göster — "venv nedir?", "pip nedir?"
- [ ] Onboarding wizard — ilk açılışta adım adım rehber
- [ ] Şeffaflık modu — terminal komutlarını göster/gizle
- [ ] Settings'te ℹ️ info icon'ları

### 3. ⚡ Windows Startup Hızı
- [ ] SettingsPage lazy-load
- [ ] _scan_pythons() cache'le

### 4. 🗄️ Cache Performance Refactoring
- [ ] In-memory cache dict, tek VenvManager/ConfigManager instance
- [ ] Env geçişlerinde her şey cache'den gelsin

### 5. 🛡️ @safe_slot / SafeWorkerMixin Yaygınlaştırma

### 6. settings_page.py Duplicate Temizliği (6900+ satır)

### 7. B47 — Tema Refactoring (182 satır hardcoded renk)

---

## 🟢 İYİLEŞTİRME
- M5–M18 — README, CHANGELOG, Quick Launch UX vb.

---

## ✅ TAMAMLANANLAR

| Bug/Feat | Versiyon | Açıklama |
|----------|----------|----------|
| B50 | v1.4.12 | email modülü PyInstaller exclude'dan çıkarıldı |
| B41 | v1.3.68–1.4.0 | AppImage/EXE subprocess re-launch loop |
| F46 | v1.4.6 | Env tablosunda sağ tık context menu |
| — | v1.4.17 | LD_LIBRARY_PATH pip subprocess'ten kaldırıldı |
| — | v1.4.16 | ensurepip sistem env ile çalıştırılıyor |
| — | v1.4.15 | --cert ile sistem SSL sertifikası |
| — | v1.4.11 | get-pip.py fallback |
| — | v1.4.9 | SSL_CERT_FILE sistem sertifikasına yönlendirildi |
| — | v1.3.91 | Python versiyonları numerik sort |
| — | v1.3.90 | Windows EXE default Python env oluşturma |
| F38 | v1.3.62 | Preset descriptions, launcher tooltips, UI tooltips |

---

## 🔴 YENİ KRİTİK (v1.4.19 sonrası)

- **B51** — Windows'ta "Only Name Rename" sonrası venv bozuluyor
  - Sebep: Windows venv'deki `pip.exe`, `python.exe` launcher'ları absolute path içeriyor
  - `C:\venv\test\Scripts\python.exe` → rename sonrası `C:\venv\test-renamed` olunca eski path geçersiz
  - **Çözüm seçenekleri:**
    - [ ] Rename sonrası venv'i "fix" et: `python -m venv --upgrade C:\venv\test-renamed`
    - [ ] Veya Windows'ta Only Name Rename'de uyarı göster: "pip/python path'leri güncellenecek"
    - [ ] Rename sonrası otomatik `venv --upgrade` çalıştır

- **B52** — Windows'ta Delete sonrası "WinError 32" — dosya başka process tarafından kullanılıyor
  - Sebep: Open Terminal açıkken o env'in dosyalarını kullanan process var
  - **Çözüm seçenekleri:**
    - [ ] Silmeden önce kullanıcıya "terminali kapatın" uyarısı ver
    - [ ] `shutil.rmtree` yerine retry mekanizması ekle (birkaç kez dene)
    - [ ] Windows'ta `rmdir /s /q` komutu ile zorla sil

- **B53** — Sistem bağımlılıkları dokümantasyonu ve otomatik kontrol
  - **README'ye eklenecek sistem gereksinimleri:**
    - Linux (Debian/Ubuntu/Pardus): `sudo apt install libxcb-cursor0 python3-pip python3-venv`
    - Linux (Fedora): `sudo dnf install python3-pip`
    - Linux (Arch): `sudo pacman -S python-pip`
    - macOS: Homebrew ile Python kurulumu önerilmeli
    - Windows: Python 3.10+ (python.org'dan, "Add to PATH" seçili)
  - **AppImage/EXE ilk açılışta otomatik kontrol:**
    - [ ] Eksik bağımlılıkları tespit et (libxcb-cursor0, python3-pip, python3-venv)
    - [ ] Kullanıcıya hangi komutu çalıştırması gerektiğini göster
    - [ ] Mümkünse otomatik kur (pkexec/sudo ile)
    - [ ] main.py'deki _check_and_install_linux_deps() genişletilecek
  - **macOS için:**
    - [ ] Homebrew Python kontrolü
    - [ ] Xcode Command Line Tools kontrolü
