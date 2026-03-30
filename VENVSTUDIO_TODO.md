# VENVSTUDIO_TODO.md

---

## 🔴 EN ÖNCELİKLİ (Sonraki Sprint)

### 🎓 F52 — EĞİTİMSEL UYGULAMALAR MENÜSÜ
- [ ] Yeni "Learn" / "Education" sekmesi
- [ ] Kod Blokları: ML, DL, Transformers, HuggingFace, Colab, NLP, CV, TS, Finance
- [ ] Basitleştirilmiş kavramlar: venv, pip, PyPI, requirements.txt
- [ ] Launch App kullanım rehberi: ne işe yarar, başlangıç kodu, dokümantasyon linkleri
- [ ] Kod bloklarını kopyalama / env'e script olarak çalıştırma

### ⚙️ F53 — SETTINGS DETAYLANDIRMA
- [ ] 11 dilin tamamı aktif (şu an sadece EN/TR)
- [ ] Her ayarın yanında ℹ️ açıklama icon'u
- [ ] TUI/CLI araçları çok detaylı — kurulum sonrası rehber, tema önizleme
- [ ] Settings kategorileri netleştirme (6900+ satır karmaşık)
- [ ] Her bölüm için "Sıfırla" butonu

### 🖥️ F54 — DETAYLI CLI KOMUT SETİ
- [ ] `venvstudio create/delete/list/activate/clone/rename/export`
- [ ] `venvstudio install/uninstall/preset/update`
- [ ] `venvstudio launch <n> <app>`
- [ ] TUI modu: `venvstudio tui` (Rich/Textual)
- [ ] Bash/Fish/Zsh completion

---

## 🔴 KRİTİK BUGLAR

- **B42** — Python yükleyici güvenlik kontrolleri (en sona alındı)
- **B47** — ⚠️ DEVAM EDİYOR: Light mod'da siyah tablolar/log/kartlar
  - Settings tabloları (Custom Categories, Preset Manager, Custom Catalog)
  - CLI/TUI log alanı ve araç kartları
  - `_refresh_styles()` tema değişince çalışmıyor — sonraki chat'te çözülecek
- **B48** — @safe_slot/SafeWorkerMixin yaygınlaştırılmadı
- **B49** — Windows EXE: Python kurulu değilse kullanıcıya sor
- **B51** — Windows Only Name Rename sonrası pip bozuluyor
  - Çözüm: rename sonrası `venv --upgrade` çalıştır
- **B52** — Windows Delete WinError 32 (terminal açıkken)
  - Çözüm: retry mekanizması veya "terminali kapatın" uyarısı
- **B53** — Sistem bağımlılıkları dokümantasyonu
  - Debian/Ubuntu: `sudo apt install libxcb-cursor0 python3-pip python3-venv`
  - Arch: `sudo pacman -S python-pip`
  - AppImage ilk açılışta otomatik kontrol

---

## 🟡 PLANLI

### 🔄 F51 — ✅ TAMAMLANDI
- Rename (Only Name) + Rename (Full) — buton + sağ tık

### 🎨 F55 — Detaylı Tema Settings
- [ ] Renk paleti özelleştirme, font seçimi
- [ ] Kompakt/Normal/Geniş layout
- [ ] Tema import/export (.json)
- [ ] Canlı önizleme

### 📦 F56 — Ek Package Manager
- [ ] pixi, conda, micromamba/miniforge
- [ ] Her backend için ayrı settings

### 🛠️ F57 — ffmpeg + Graphviz Entegrasyonu
### 📊 F58 — R / RStudio Launch
### 💻 F59 — IDE Entegrasyonları (PyCharm, Cursor, Zed, Neovim)
### 🖥️ F60 — TUI Kompakt Mod (dropdown ile)

### 📚 F61 — Catalog Genişletme
- [ ] Time Series Transformers, Financial, Graph, Audio, Geo, Quantum, Bio, Robotics

### 🌐 F62 — SSH / Uzaktan Yönetim
### 🐳 F63 — Export / Docker / Podman

### ⚡ F64 — uv Backend Tam Entegrasyonu
### 🔍 F65 — Conflict Detection (pip --dry-run --report)
### 🔒 F66 — Reproducibility & Lock Files
### 🐍 F67 — Micromamba / Miniforge Backend
### 🐉 F68 — Pixi Backend
### 📊 F69 — Bağımlılık Ağacı Görselleştirme
### 🚀 F70 — Task Runner (pixi run benzeri)

### 🗄️ Cache Performance Refactoring
- [ ] In-memory cache dict, tek VenvManager/ConfigManager instance
- [ ] Env geçişlerinde cache'den servis

---

## ✅ TAMAMLANANLAR

| Bug/Feat | Versiyon | Açıklama |
|----------|----------|----------|
| B50 | v1.4.12 | email modülü PyInstaller exclude'dan çıkarıldı |
| B41 | v1.3.68–1.4.0 | AppImage/EXE subprocess re-launch loop |
| B43 | — | ✅ Arch + Python 3.14 Orange3 crash — çözüldü |
| B44 | — | ✅ Arch'ta IPython — çözüldü |
| B54 | v1.4.22–23 | UI fixes: Package Info butonlar, Open Terminal, Python path |
| F51 | v1.4.24 | Rename (Only Name) + Rename (Full) |
| — | v1.4.23 | env_dialog: dropdown'da versiyon, altında path |
| — | v1.4.21 | Preset'te kurulu paketler filtrelenir |
| — | v1.4.20 | Manual install parsing iyileştirme |
| — | v1.4.19 | Windows Terminal default open terminal |
| — | v1.4.17 | LD_LIBRARY_PATH pip'ten kaldırıldı |
| — | v1.4.16 | ensurepip sistem env |
| — | v1.4.15 | --cert ile sistem SSL |
| — | v1.4.12 | email fix |
| Temalar | v1.4.24 | 13 tema (8 dark + 5 light) |
