# VENVSTUDIO_TODO.md

## 🔴 EN ÖNCELİKLİ (Sonraki Sprint)

### 🎓 F52 — EĞİTİMSEL UYGULAMALAR MENÜSÜ
- [ ] Yeni bir "Learn" veya "Education" sekmesi/menüsü
- [ ] **Kod Blokları Kütüphanesi:** En çok kullanılan kod parçaları kategorilere göre:
  - ML: sklearn, xgboost, lightgbm örnekleri
  - DL: Keras, PyTorch, TensorFlow temel modeller
  - Transformers: HuggingFace pipeline örnekleri
  - Google Colab entegrasyonu ipuçları
  - NLP, CV, Time Series, Finance örnekleri
- [ ] **Basitleştirilmiş Kavramlar:** venv, pip, PyPI, virtual environment, requirements.txt...
- [ ] **Launch App Kullanım Rehberi:** Her launcher app için:
  - Ne işe yarar, kime uygun
  - Başlangıç kodu / örnek notebook
  - Dokümantasyon linkleri
  - Video tutorial linkleri
- [ ] Kod bloklarını kopyalama / env'e otomatik script olarak çalıştırma

### ⚙️ F53 — SETTINGS DETAYLANDIRMA
- [ ] **11 dil desteğinin tamamı aktif edilecek** — şu an sadece EN/TR çalışıyor
- [ ] Her ayarın yanında ℹ️ açıklama icon'u — hover'da ne yaptığını anlat
- [ ] **TUI/CLI araçları çok detaylı yapılacak:**
  - Starship, Oh My Posh, Fish, Zsh, Bash config
  - Her araç için kurulum sonrası nasıl kullanılır rehberi
  - Tema önizleme
- [ ] Settings kategorileri netleştirilecek — şu an 6900+ satır karmaşık
- [ ] Her bölüm için "Sıfırla" butonu

### 🖥️ F54 — DETAYLI KOMUT SETİ (CLI/TUI)
- [ ] **Env yönetimi komutları:**
  - `venvstudio create <name> [--python 3.11]`
  - `venvstudio delete <name>`
  - `venvstudio list`
  - `venvstudio activate <name>`
  - `venvstudio clone <src> <dst>`
  - `venvstudio rename <old> <new>`
  - `venvstudio export <name> [--format requirements|docker|pyproject]`
- [ ] **Paket yönetimi komutları:**
  - `venvstudio install <name> <packages...>`
  - `venvstudio uninstall <name> <packages...>`
  - `venvstudio preset <name> <preset_name>`
  - `venvstudio update <name> [--all]`
- [ ] **Launch komutları:**
  - `venvstudio launch <name> <app>`
  - `venvstudio launch <name> jupyterlab`
- [ ] **TUI modu:** `venvstudio tui` — terminal tabanlı interaktif arayüz (Rich/Textual)
- [ ] Bash/Fish/Zsh completion desteği

---

## 🔴 KRİTİK BUGLAR

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

---

## 🟡 YENİ PLANLI MADDELER (v1.4.21 sonrası)

### 🐛 B54 — UI/UX Düzeltmeleri
- [ ] Environment dialog'da "System Default" Python'un versiyon ve yolu gösterilmiyor — dropdown altında seçili Python'un tam yolu gösterilmeli
- [ ] Catalog/Installed "Package Info" dialog butonları taşıyor — "Install xyz..." ve "Copy A..." kısaltılıyor, buton genişlikleri düzeltilmeli
- [ ] "Open Terminal" butonu metni sığmıyor (Packages ve Environments'ta) — font veya buton boyutu ayarlanmalı
- [ ] "Open Terminal" butonundaki "P" harfinin kuyruğu görünmüyor — font sorunu (Noto Color Emoji veya sistem fontu)

### 🎨 F55 — Detaylı Tema Settings
- [ ] Renk paleti özelleştirme (accent, background, text, border...)
- [ ] Font seçimi ve boyutu
- [ ] Kompakt / Normal / Geniş layout seçeneği
- [ ] Hazır temalar: Catppuccin, Dracula, Nord, Tokyo Night, Solarized...
- [ ] Tema önizleme canlı
- [ ] Tema import/export (.json)

### 📦 F56 — Ek Package Manager Desteği
- [ ] pixi — conda-compatible, fast
- [ ] conda — Anaconda/Miniconda
- [ ] micromamba / miniforge
- [ ] Her package manager için Settings'te ayrı konfigürasyon
- [ ] package_panel.py'de backend seçimi genişletilecek

### 🛠️ F57 — ffmpeg ve Graphviz Entegrasyonu
- [ ] CLI Tools Manager'a ffmpeg ekle (indirme + PATH'e ekleme)
- [ ] CLI Tools Manager'a Graphviz ekle
- [ ] Python binding'leri: `imageio-ffmpeg`, `graphviz` PyPI paketi
- [ ] Kurulum sonrası test: `ffmpeg -version`, `dot -V`

### 📊 F58 — Launch: R / RStudio Entegrasyonu
- [ ] R kurulum kontrolü (`r --version`)
- [ ] RStudio kurulum kontrolü
- [ ] Launch kısmına R Console ve RStudio eklenmesi
- [ ] rpy2 Python paketi ile R entegrasyonu
- [ ] CRAN paket yükleme desteği (opsiyonel)

### 💻 F59 — IDE Entegrasyonları Genişletme
- [ ] PyCharm (Community + Professional) — proje olarak aç
- [ ] Cursor IDE
- [ ] Zed
- [ ] Neovim / vim
- [ ] antigravity (easter egg 🐍)
- [ ] Her IDE için "Open in X" butonu env üzerinde

### 🖥️ F60 — TUI Kompakt Mod
- [ ] Settings'te TUI araçları bölümü dropdown ile değiştirilsin
- [ ] Sadece TUI kısmı kompakt — diğer settings normal kalacak
- [ ] Dropdown: Starship, Oh My Posh, Fig, Atuin, zoxide...

### 📚 F61 — Catalog Genişletme
- [ ] Time Series (Transformers): tsfm, lag-llama, moirai, chronos
- [ ] Financial Libraries: quantlib, backtrader, freqtrade, vectorbt
- [ ] Graph/Network: networkx, igraph, pyvis, torch-geometric
- [ ] Audio/Speech: librosa, pyaudio, speechbrain, whisper
- [ ] Geospatial: geopandas, folium, shapely, rasterio
- [ ] Quantum Computing: qiskit, pennylane, cirq
- [ ] Bioinformatics: biopython, scanpy, anndata
- [ ] Robotics: ROS2 bindings, pybullet, gymnasium
- [ ] Web Scraping: scrapy, playwright, mechanize
- [ ] PDF/Document: pdfplumber, pymupdf, docling

### 🌐 F62 — SSH / Uzaktan Yönetim
- [ ] SSH bağlantı yöneticisi (host, port, user, key)
- [ ] Uzak makineye bağlanıp VenvStudio işlemleri yapabilme
- [ ] Uzak env listesi, paket yönetimi, preset kurulumu
- [ ] Paramiko / asyncssh backend
- [ ] Bağlantı profilleri kaydetme
- [ ] Windows/Linux/macOS/BSD desteği

### 🐳 F63 — Export / Docker / Container Geliştirme
- [ ] Gemini önerisi doğrultusunda export formatları genişletme
- [ ] Podman desteği (Docker alternatifi)
- [ ] docker-compose.yml export
- [ ] Container image build (docker build)
- [ ] Dev container (.devcontainer/devcontainer.json) export
- [ ] Singularity/Apptainer desteği (HPC)
- [ ] Container'dan env import


---

## 🟡 PYTHON ENVIRONMENT HUB — Yeni Özellikler

### ⚡ F64 — uv Backend Tam Entegrasyonu
- [ ] uv kurulu değilse Settings'ten otomatik kur
- [ ] `uv pip install` / `uv pip uninstall` / `uv pip list` desteği (pip_manager.py'de)
- [ ] `uv venv` ile env oluşturma (venv_manager.py'de)
- [ ] `uv python install` ile Python sürümü indirme (python_downloader.py ile entegre)
- [ ] uv seçiliyken hız farkını kullanıcıya göster ("10x faster with uv")
- [ ] uv lock file desteği (`uv pip compile`)

### 🔍 F65 — Conflict Detection (Çakışma Analizi)
- [ ] Paket yüklemeden önce `pip install --dry-run --report report.json` ile ön kontrol
- [ ] Çakışma varsa "Bu paket X ile uyumsuz" uyarısı göster — yükleme öncesi
- [ ] `pip check` ile mevcut ortamdaki çakışmaları tara
- [ ] Env listesinde çakışan ortamları kırmızı ile işaretle (⚠️ ikonu)
- [ ] Çakışma detaylarını görselleştir (hangi paket hangi versiyonu istiyor)

### 🔒 F66 — Reproducibility & Lock Files
- [ ] `pip freeze --all` ile hash'li lock file üret (`venvstudio.lock`)
- [ ] `pip install --generate-hashes` ile güvenli kurulum
- [ ] pip-tools entegrasyonu: `pip-compile` ile alt bağımlılıkları dondur
- [ ] Export bölümüne "Lock File" seçeneği ekle
- [ ] Lock file'dan ortam kurma (import) desteği
- [ ] Lock file ile mevcut ortamı karşılaştır ("drift" tespiti)

### 🐍 F67 — Micromamba / Miniforge Backend
- [ ] Micromamba binary'sini otomatik indir (~15MB, kurulum gerektirmez)
- [ ] `micromamba create` ile env oluşturma
- [ ] `micromamba install` ile conda-forge paketleri
- [ ] conda ve pip kanallarını aynı ortamda yönet
- [ ] ffmpeg, graphviz, CUDA gibi sistem bağımlılıklarını micromamba ile kur
- [ ] Conda channel seçimi (conda-forge, defaults, bioconda...)
- [ ] `conda env export > environment.yml` desteği

### 🐉 F68 — Pixi Backend
- [ ] Pixi binary'sini otomatik indir
- [ ] `pixi.toml` dosyasını görsel tabloya dönüştür
- [ ] `pixi add` / `pixi remove` ile paket yönetimi
- [ ] `pixi run` ile task çalıştırma
- [ ] Pixi lock file (`pixi.lock`) desteği
- [ ] Çoklu dil desteği: Python + R + Rust aynı projede

### 📊 F69 — Bağımlılık Ağacı Görselleştirme
- [ ] `pip show` çıktısından bağımlılık ağacı oluştur
- [ ] Ağaç yapısında interaktif görselleştirme (tıklanabilir node'lar)
- [ ] "Bu paket kaldırılırsa ne etkilenir?" analizi
- [ ] Circular dependency tespiti
- [ ] pipdeptree entegrasyonu

### 🚀 F70 — Task Runner (pixi run benzeri)
- [ ] Ortam aktive etmeden komut çalıştırma ("Run in env")
- [ ] Sık kullanılan komutları kaydet (task shortcuts)
- [ ] `python script.py` → otomatik o env'in python'u ile çalıştır
- [ ] Jupyter notebook'u direkt o env'de başlat

