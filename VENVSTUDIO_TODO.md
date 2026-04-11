# VENVSTUDIO_TODO.md

---

## 🔴 EN ÖNCELİKLİ (Sonraki Sprint)

### 🎓 F52 — EĞİTİMSEL UYGULAMALAR MENÜSÜ
- [ ] Yeni "Learn" / "Education" sekmesi
- [ ] Kod Blokları: ML, DL, Transformers, HuggingFace, Colab, NLP, CV, TS, Finance
- [ ] Basitleştirilmiş kavramlar: venv, pip, PyPI, requirements.txt
- [ ] Launch App kullanım rehberi: ne işe yarar, başlangıç kodu, dokümantasyon linkleri
- [ ] **F74 ile bağlantı:** Her uygulamanın üstünde eğitimsel linkler (YouTube, resmi site, docs)
- [ ] Kod bloklarını kopyalama / env'e script olarak çalıştırma

### ⚙️ F53 — SETTINGS DETAYLANDIRMA
- [x] 11 dilin tamamı aktif — FR/PT/ZH/KO tamamlandı (v1.4.27+)
- [x] Her ayarın yanında ℹ️ açıklama icon'u — tamamlandı (v1.4.27+)
- [x] Her bölüm için "Sıfırla" butonu — tamamlandı (v1.4.27+)
- [ ] TUI/CLI araçları çok detaylı — kurulum sonrası rehber, tema önizleme
- [ ] Settings kategorileri netleştirme (6900+ satır karmaşık) — duplike yapı refactor

### 🖥️ F54 — DETAYLI CLI KOMUT SETİ
- [ ] `venvstudio create/delete/list/activate/clone/rename/export`
- [ ] `venvstudio install/uninstall/preset/update`
- [ ] `venvstudio launch <n> <app>`
- [ ] TUI modu: `venvstudio tui` (Rich/Textual)
- [ ] Bash/Fish/Zsh completion

### 🔗 F74 — LAUNCH'TA EĞİTİMSEL LİNKLER
- [ ] Her uygulama kartının üstüne tutorial linkleri satırı ekle
- [ ] Linkler: YouTube kanalı, resmi website, resmi docs, GitHub
- [ ] Tıklanabilir ikon butonlar (▶ YouTube, 🌐 Site, 📖 Docs, 🐙 GitHub)
- [ ] Linkler `constants.py`'deki uygulama tanımlarına `"links": {}` key'i olarak eklenecek
- [ ] Her uygulamaya özel — boş olanlar gösterilmez
- **Örnek:** Jupyter: YouTube=sentdex, Site=jupyter.org, Docs=jupyter-notebook.readthedocs.io

---

---

## 🔴 v1.4.53 Sonrası Buglar

### ✅ B122–B129 — Cross-Platform Fix'ler (v1.4.55)
- B122: Windows poetry path `%LOCALAPPDATA%\pypoetry\Cache\virtualenvs\` düzeltildi
- B123: Poetry env duplicate sorunu giderildi (base_dir marker skip)
- B124: Poetry env path/size/packages gerçek venv'den okunuyor
- B125: uv Packages 0 sorunu — `uv pip list` kullanılıyor
- B126: conda Packages 0 sorunu — `conda-meta/*.json` sayılıyor
- B127: Poetry env delete çalışıyor — `env_path` + `env_type` ile
- B128: pipx tam path gösteriliyor (tilde kısaltma kaldırıldı)
- B129: `get_pipx_home()` tilde expand eklendi



### ✅ B115 — Windows/macOS Poetry Path Yanlış (v1.4.53)
- Windows: `%APPDATA%\pypoetry\virtualenvs\` taranmalı
- macOS: `~/Library/Caches/pypoetry/virtualenvs/` taranmalı
- `list_venvs_fast`'ta platform kontrolü eklenmeli
- `venv_manager.py` → poetry discovery bloğu platform'a göre path seçmeli

### ✅ B116 — Windows pipx Path Yanlış (v1.4.53 kısmi)
- Windows'ta `~\pipx` gösteriyor, `%LOCALAPPDATA%\pipx\` veya `%USERPROFILE%\pipx\` olmalı
- `get_pipx_home()` Windows'ta doğru path dönmüyor

### ✅ B117 — Settings > Remove All Data — WinError 32 (v1.4.53)
- `venvstudio.log` dosyası açık olduğu için silinemiyor
- Log dosyasını kapatıp sonra silmeli, ya da log handler'ı release etmeli
- `settings_advanced.py` → `_clear_all_data()` içinde log handler kapatılmalı

### ✅ B118 — Settings > Download Python Çalışmıyor (v1.4.53)
- `settings_python.py` satır 799: `PythonDownloadDialog` tanımsız
- `from src.gui.settings_python_download import PythonDownloadDialog` import eksik
- `settings_python.py` → `_download_python()` metoduna import ekle

### B119 — Poetry Settings'te Kurulum Sonrası Refresh Yok
- Poetry kurulduktan sonra env listesi otomatik refresh edilmiyor
- `env_dialog.py` veya `settings_toolchain.py` → kurulum callback'ine `_refresh_env_list()` ekle

### ✅ B120 — pipx Delete Aktif Olmamalı (v1.4.53)
- Environments tablosunda pipx satırı seçilince Delete butonu aktif oluyor
- pipx silinmemeli — Settings > Toolchain Manager > Uninstall kullanılmalı
- `main_window.py` → `_on_env_selected()` içinde pipx için Delete butonunu disable et
- Sağ tık menüsünde de Delete gizlenmeli, yerine "Use Toolchain Manager to uninstall" mesajı

### B121 — Yüksek DPI / Ölçek > 100% Form Elemanları Sağa Kayıyor
- Create Environment dialog ve diğer formlarda scroll bar yok
- `env_dialog.py` → form container'a `QScrollArea` ekle
- Settings sayfalarına da scroll ekle

## 🔴 YENİ BUGLAR & FEATURE'LAR (Bu Oturumdan)

### 🟡 F118 — Open Folder Butonu ve Sağ Tık Menüsü
- Environments tablosunda sağ tık menüsüne "Open Folder" ekle (Open Terminal'ın altına)
- Package panel üst bar'a "Open Folder" butonu ekle (Open Terminal butonunun yanına)
- Windows: `explorer <path>`, Linux: `xdg-open <path>`, macOS: `open <path>`
- pipx için: `pipx_home/venvs/` klasörünü aç
- poetry için: gerçek venv path'ini aç (`%LOCALAPPDATA%\pypoetry\Cache\virtualenvs\...`)


### ✅ B110 — AppImage Quick Launch Uygulamalar Çalışmıyor (v1.4.56)
- AppImage'da Quick Launch'taki uygulamalar (Jupyter, IPython vb.) çalışmıyor
- Linux AppImage ortamında `launch_in_terminal` veya subprocess env sorunu olabilir

### 🔴 B111 — Toolchain Manager Remove Çalışmıyor
- pipx kaldırılamıyor Toolchain Manager'dan
- Kaldırınca Environments altındaki pipx env kaybolacak mı? Test edilmedi
- Refresh yapıldığında pipx env yoksa otomatik yeniden oluşturulsun

### 🔴 B112 — Conda Installed Tab Yanlış Gösteriyor
- Micromamba env'lerde Installed kısmında kurulu olmayan paketler kurulu gösteriliyor
- Sağ tık → "Yükle" diyor ama zaten kurulu değil mi?

### 🔴 B113 — pip Dışı Env'lerde Python Versiyonu Yanlış
- uv env Python 3.14 ile yapıldı ama Python 3.12 gösteriyor
- Create Environments ekranında pip dışı env'ler için Python seçimi gereksiz
- uv/conda/pipx kendi Python'larını kullanıyor, seçim ignore ediliyor

### 🔴 B114 — pip Dışı Env'lerde Clone/Rename Hata
- uv, poetry, conda, pipx env'lerinde clone ve rename başarısız
- B82 ile aynı sorun — her env tipi için özel strateji gerekiyor

### 🟡 F111 — Sağ Tık Menüsü Genişletme (Environments)
- Copy Path, Runtime bilgisi kopyalama
- Run Command → her env tipine özel en sık kullanılan 10-15 komut
  - pipx: `pipx list`, `pipx install <pkg>`, `pipx upgrade <pkg>`, `pipx uninstall <pkg>`...
  - poetry: `poetry add <pkg>`, `poetry show`, `poetry update`, `poetry shell`...
  - conda: `conda list`, `conda install <pkg>`, `conda update`...
  - venv/uv: `pip list`, `pip show <pkg>`, `pip install <pkg>`...

### 🟡 F112 — Manual Install Geçmişi
- Her env için ayrı manual install geçmişi (300-500 satır veya 5-10 action)

### 🟡 F113 — İlk Çalıştırma Deneyimi
- Hiç env yokken Environments'a yönlendir veya Create Env sihirbazı başlatsın

### 🟡 F114 — Settings > Install VenvStudio
- AppImage/EXE'den çalışıyorsa `pip install venvstudio` komutu göster
- CLI/komut satırı için path ayarı veya kurulum rehberi

### 🟡 F115 — TUI/CLI Tools Bölümü Kompakt Hale Getirme
- Şu an çok yer kaplıyor
- Dropdown'dan seçince yandaki menü değişsin (Starship/OhMyPosh vb.)

### 🟡 F116 — Refresh'te pipx Env Otomatik Oluşturma
- Refresh yapıldığında pipx kuruluysa ama env yoksa otomatik marker oluştursun

### 🟡 F117 — Settings > pip Backend Kaldırılacak
- Settings altındaki pip Backend seçeneği gereksiz — kaldırılacak

## 🔴 KRİTİK BUGLAR

- **B42** — Python yükleyici güvenlik kontrolleri (en sona alındı)
- **B47** — ✅ TAMAMLANDI (v1.4.25): Light mod tema düzeltmeleri
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
- **B58** — Windows EXE'de Settings > Python Versions "Custom" gösteriyor
  - `pip install venvstudio` ile kurulumda System Default Python "Custom" görünüyor
  - Kaynak: `_source_label()` veya `_populate_python_table()` içinde EXE kontrolü eksik
  - Çözüm: `getattr(sys, "frozen", False)` kontrolü + pip kurulumunda Source="System" zorla
- **B59** — AppImage'da Orange3 çalışmıyor (pip kurulumunda çalışıyor)
  - Neden: AppImage'ın `LD_LIBRARY_PATH` / `APPDIR` kütüphaneleri PyQt5 kurulumunu bozuyor
  - `pip_manager.py`'de `LD_LIBRARY_PATH` temizleniyor ama kurulum sırasında PyQt5 `.so` linkleri yanlış konuma yapılıyor olabilir
  - Çözüm adayı: Orange3 kurulumu öncesi `PYTHONPATH`, `LD_LIBRARY_PATH`, `APPIMAGE` env'lerini sıfırla; kurulum sonrası venv içi kütüphane yollarını doğrula
  - Test: AppImage'dan Orange3 kur → `python -c "import Orange"` çalışıyor mu?
- **B60** — Windows'ta cache loglarında path separator yanlış
  - `[Cache] Written: C:/venv/ml -> ...` — ters slash olmalıydı (`C:\venv\ml`)
  - Kaynak: `venv_manager.py` → `_cache_key()`: `str(venv_path.resolve()).replace("\\", "/")` — JSON key için normalize ederken log'a da bu normalize edilmiş key yazılıyor
  - Çözüm: log satırında `str(venv_path)` (orijinal) kullan, `_cache_key()` return değerini değil
  - Etkilenen satır: `venv_manager.py:573` — `print(f"[Cache] Written: {self._cache_key(venv_path)} -> ...")`

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


### 🔧 Refactor — Büyük Dosyaları Bölme (Mixin Pattern)

#### ✅ settings_page.py — TAMAMLANDI (v1.4.49)
- [x] `settings_page.py` (8000+ satır) → 7 dosyaya bölündü
- [x] `settings_appearance.py` (924 satır) — Tema, font, CLI tools, terminals
- [x] `settings_python.py` (815 satır) — Python Versions, scan, download, PATH
- [x] `settings_toolchain.py` (991 satır) — Toolchain Manager
- [x] `settings_catalog.py` (632 satır) — Presets, categories, custom catalog
- [x] `settings_advanced.py` (444 satır) — Export/import, update, save, reset
- [x] `settings_python_download.py` (570 satır) — Download dialog & workers

#### 🔴 main_window.py — BEKLIYOR (2041 satır)
- [ ] `main_window.py` — MainWindow base + __init__ + _setup_ui + _setup_menubar
- [ ] `main_window_env.py` — Env ops: create, delete, clone, rename, context menu, export
- [ ] `main_window_ql.py` — Quick Launch: _ql_load_env_packages, _rebuild_ql_buttons, _sync_ql_selector

#### 🔴 package_panel.py — BEKLIYOR (~2900 satır)
- [ ] `package_panel.py` — PackagePanel base + __init__
- [ ] `package_launcher.py` — Launch tab: _launch_app, _launch_script, _launch_system_app, _update_launcher_status
- [ ] `package_list.py` — Packages tab: install, uninstall, search, info

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
| B47 | v1.4.25 | Light mod tema: tablolar, log, kartlar, _refresh_styles, hardcoded renkler |
| B55 | v1.4.25 | Quick Launch sidebar tema bozulması düzeltildi |
| B56 | v1.4.25 | System Default Python gösterimi, Source etiketleri, Download dialog |
| — | v1.4.25 | Verify pip & venv, Download Python sola, sticky Save/Reset |
| — | v1.4.26 | 3-level font sistemi (Headings/UI&Menus/Details), font hiyerarşisi, Reset Fonts |
| — | v1.4.26 | Buton setFixedHeight kaldırıldı, package_panel hardcoded renkler tema-aware |
| B57 | v1.4.27 | Package Info dialog setMinimumSize, hardcoded renkler, Open Terminal P harfi |
| F71 | v1.4.27 | Export alt menüleri: requirements-frozen.txt + JSON, sağ tık submenu |
| F72 | v1.4.27 | Environments boş alana sağ tık → New Environment + Refresh |
| F53 i18n | v1.4.27 | FR/PT/ZH/KO tamamlandı (126/126 key) |
| F53 ℹ️ | v1.4.27+ | Her section'a ℹ️ ikonu + Appearance/Language/General Sıfırla butonları |
| B58 | v1.4.27+ | Python Sources label düzeltildi: System/User Install/Custom doğru ayrımı |
| B60 | v1.4.27+ | Cache log path separator: Windows'ta artık ters slash ile gösteriliyor |
| B96 | v1.4.45 | Terminal flash: PowerShell subprocess'lere CREATE_NO_WINDOW eklendi |
| B97 | v1.4.45 | Drive letter normalization: Python path'lerinde C büyük harf |
| B98 | v1.4.45 | Frozen exe: VenvStudio.exe Toolchain combo'da görünmüyor |
| B99 | v1.4.45 | Duplicate helper classes kaldırıldı (466 satır) |
| B100 | v1.4.45 | Toolchain status labels: Built-in/Global/User/Python/Managed |
| B101 | v1.4.45 | pip/venv çift Upgrade butonu giderildi |
| B102 | v1.4.45 | python/python3 symlink duplikasyonu giderildi |
| B103 | v1.4.45 | Linux'ta Scripts in PATH yanlış hesaplanıyordu |
| B104 | v1.4.48 | Scripts in PATH yanlış pozitif — which python/python3 karşılaştırması |
| B105 | v1.4.48 | Quick Launch terminal açılmıyordu — launch_in_terminal() eklendi |
| Refactor | v1.4.49 | settings_page.py → 7 dosyaya bölündü (mixin pattern) |
| B108 | v1.4.52 | pipx/conda/poetry terminal — src/utils/platform_utils.py fix |
| B109 | v1.4.52 | pipx yanlış path — ~/.local/share/pipx/ kullanılıyor |
| F110 | v1.4.52 | Environments tablosuna Path kolonu eklendi |
| B106 | v1.4.50 | Check for Updates — urllib fallback + SSL fix |
| B107 | v1.4.51 | Windows subprocess CREATE_NO_WINDOW |
| — | v1.4.48 | Font satırı hizalama: setFixedHeight(32) tüm widget'lara eklendi |
| B103 | v1.4.45 | Linux scripts_dir yanlış hesaplama (usr/bin/bin) düzeltildi |
| UI | v1.4.45 | Package Manager & Defaults bölümü (Default Env Type + pip Backend) kaldırıldı |
| B59 | v1.4.27+ | AppImage Orange3: _APPIMAGE_VARS genişletildi, pip env temizliği güçlendirildi, post-install import doğrulaması eklendi |

---

## 🔴 YENİ BUGLAR

- **B79** — ✅ TAMAMLANDI (v1.4.36): System app status mesajları düzeltildi

- **B62** — 🔴 Uygulama rastgele çöküyor (kritik stabilite sorunu)
  - **Tetikleyiciler:** açılışta, tab/kısım geçişlerinde, environment değiştirirken, sağ tıkta, pencere tam dolmadan taşınırken
  - **Kök neden adayları:**
    - Thread-unsafe UI güncellemeleri: worker thread'den doğrudan widget erişimi (Qt'da sadece main thread widget'a dokunabilir)
    - Sinyal/slot yarış koşulu: `@safe_slot` / `SafeWorkerMixin` henüz yaygınlaştırılmadı (B48 ile bağlantılı)
    - Sağ tık context menu: `QMenu.exec()` sırasında alttaki widget yenilenirse segfault
    - Pencere taşıma: `paintEvent` / `resizeEvent` sırasında veri henüz hazır değilse NoneType hatası
    - Açılışta: `_load_current_settings` veya ilk env scan tamamlanmadan UI'a yazma
  - **Çözüm planı:**
    - [ ] Tüm worker callback'lerini `QMetaObject.invokeMethod(..., Qt.QueuedConnection)` veya `Signal` üzerinden main thread'e taşı
    - [ ] B48: `@safe_slot` / `SafeWorkerMixin` tüm dosyalara yaygınlaştır
    - [ ] Sağ tık menüsünü `QTimer.singleShot(0, ...)` ile defer et
    - [ ] Açılış sırasını guarantee et: env scan → UI populate → pencere göster
    - [ ] Detaylı log sistemi ekle (bkz. F75)
  - **Öncelik:** 🔴 Kritik — kullanıcı deneyimini en çok etkileyen sorun

- **B63** — Linux'ta textbox (QLineEdit / QTextEdit) alanları çok dar
  - Boylamsal (dikey) olarak çok kısa görünüyor
  - Neden: Linux'ta varsayılan QLineEdit minimum height Windows'tan düşük; font metrics farklı
  - Çözüm: `setMinimumHeight()` veya QSS ile `min-height` değeri tüm input'lara uygulanmalı
  - Etkilenen: tüm `QLineEdit`, `QTextEdit`, `QSpinBox`, `QComboBox` içeren paneller
  - Çözüm adayı: `styles.py`'deki global QSS'e Linux için `min-height: 28px` ekle

## 🟡 YENİ PLANLI

- **F75** — Detaylı Log Sistemi
  - Tüm önemli olayları (env yükleme, paket kurulumu, tab geçişi, sağ tık, crash) dosyaya yaz
  - Log dosyası: `~/.local/share/venvstudio/venvstudio.log` (Linux) / `%APPDATA%\VenvStudio\venvstudio.log` (Windows)
  - Log seviyeleri: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - Rotating log: max 5MB × 3 dosya (logging.handlers.RotatingFileHandler)
  - Settings > Diagnostics'te "📄 Open Log File" butonu
  - Crash anında stack trace otomatik log'a yazılsın (sys.excepthook override)
  - B62'yi teşhis etmek için zorunlu altyapı

- **B57** — ✅ TAMAMLANDI (v1.4.27): Package Info penceresi buton yazı taşması

- **B58** — ✅ TAMAMLANDI: Windows EXE/pip kurulumunda Python Sources yanlış etiketleniyor
  - Düzeltme: `settings_page.py` — PROGRAMFILES/WINDIR/usr/opt → "System", home/APPDATA → "User Install", geri kalan → "Custom". EXE modunda `sys.executable` eşleşmesi de "System" sayılıyor.

- **B59** — ✅ TAMAMLANDI: AppImage'da Orange3 çalışmıyor
  - `platform_utils.py` — `_APPIMAGE_VARS`'a `LD_LIBRARY_PATH`, `LD_PRELOAD`, `PYTHONPATH`, `PYTHONHOME`, GDK/GIO/XDG path'leri eklendi
  - `pip_manager.py` — `_run_pip` env temizliği güçlendirildi: `sp_kwargs.get("env") or ...` yerine explicit `"env" in sp_kwargs` kontrolü; Linux'ta her zaman zararlı değişkenler temizleniyor
  - `package_panel.py` — Orange3 kurulumu sonrası AppImage'da `import PyQt5; import Orange` doğrulaması yapılıyor; başarısız olursa kullanıcıya açıklayıcı uyarı + pip kurulumu önerisi gösteriliyor

- **B60** — ✅ TAMAMLANDI: Windows cache loglarında path separator sorunu
  - `venv_manager.py` — log satırında `_cache_key()` yerine `str(venv_path)` kullanıldı

## 📝 AÇIKLAMALAR

### requirements.txt vs requirements-frozen.txt — FARK VAR MI?
Mevcut kodda (`pip_manager.py::freeze()`) **her ikisi de `pip freeze` çıktısı** kullanıyor — fark yok.
Olması gereken fark:
- `requirements.txt` → `pip freeze` (sadece paket==versiyon, hash yok)
- `requirements-frozen.txt` → `pip download --require-hashes` veya `pip-compile --generate-hashes` çıktısı (SHA256 hash'li, tam reproducible)

**B61** — ✅ TAMAMLANDI: F71 Export'ta requirements-frozen.txt artık gerçek SHA-256 hash'li
- `main_window.py` — `pip download --no-deps` + `hashlib.sha256` ile her pakete hash ekleniyor
- Çıktı formatı: `numpy==1.26.4 \\\n    --hash=sha256:...` — `pip install --require-hashes` ile doğrudan kullanılabilir

## 🟡 YENİ PLANLI

- **F71** — ✅ TAMAMLANDI (v1.4.27): Env sağ tık Export alt menüleri

- **F72** — ✅ TAMAMLANDI (v1.4.27): Environments boş alana sağ tık menüsü

- **F73** — UI/UX Genel İyileştirme
  - Font büyütünce layout bozulmaları (buton taşmaları, kart genişlikleri)
  - Tüm sayfaların farklı font boyutlarında test edilmesi
  - Responsive layout — pencere boyutuna göre uyum
  - Buton yazılarının kesilmemesi (elide yerine wrap veya minimum genişlik)
  - Genel görsel tutarlılık kontrolü (spacing, padding, alignment)

- **F74** — Launch'ta Eğitimsel Linkler (bkz. EN ÖNCELİKLİ)

- **F80** — Tool Installer ile Admin Yetkileri (pip, uv, poetry, pipx, mamba, conda)
  - Env oluşturma sırasında gerekli tool (uv, poetry, pipx, mamba, conda vb.) yoksa otomatik algıla
  - Kullanıcıya "X bulunamadı, yüklensin mi?" dialog'u göster
  - Windows'ta admin yetki isteği (UAC elevation) ile `pip install uv` / `pipx install poetry` vb.
  - Linux'ta `sudo` ile veya `--user` flag ile kurulum seçeneği
  - Kurulum sonrası PATH refresh ve tool doğrulaması
  - Başarısız olursa kullanıcıya manual kurulum talimatı göster

- **F81** — Settings > Python Toolchain Manager
  - Settings altında yeni "🛠️ Toolchain" veya "📦 Package Managers" bölümü
  - Sistemdeki tüm Python kurulumları listelenir (mevcut Python Versions tablosu gibi)
  - Her Python altında kurulu/kurulmamış tool'lar gösterilir: pip, venv, uv, poetry, pipx, rye, mamba, conda
  - Her tool yanında durum ikonu: ✅ Installed (versiyon) / ❌ Not installed
  - "Install" butonu → seçili Python'a o tool'u kurar (admin yetkisi ile)
  - "Uninstall" / "Update" seçenekleri
  - Toplu kurulum: birden fazla tool seçip tek seferde kur
  - Tool versiyonları ve yolları gösterilir
  - F80 ile bağlantılı — env oluşturma sırasındaki auto-install buradan da tetiklenebilir

- **F82** — Create Env'de Package Manager Yükleme Butonu
  - Create Env dialog'unda seçilen package manager (uv, poetry, conda, rye, pipx) yanında "⬇️ Install" butonu
  - Tıklanınca seçilen tool'u sisteme kurar (admin yetkili)
  - Python seçiliyse: yeni bir Python sürüm yükleme ekranı açılsın (download + install)
  - Yüklenen Python versiyonu otomatik olarak Create Env ekranındaki dropdown'a eklensin ve seçilsin
  - F80/F81 ile bağlantılı

- **F83** — Force Delete (Silinemeyen Env'ler İçin)
  - Normal delete başarısız olursa (WinError 32, dosya kilitli vb.) "Force Delete" seçeneği sun
  - Force yöntemler: retry with delay, rename-then-delete, `shutil.rmtree(onerror=...)`, process kill
  - Linux'ta `rm -rf` fallback
  - B52 ile bağlantılı

- **F84** — Rename Tooltip Açıklamaları
  - "Rename (Full)" butonuna hover → "Renames the folder on disk and updates all internal references"
  - "Rename (Only Name)" butonuna hover → "Changes only the display name — folder stays the same"
  - Sağ tık menüsündeki rename seçeneklerine de aynı tooltip'ler

- **F85** — Weka Launcher Entegrasyonu
  - Launch tab'a Weka (Waikato Environment for Knowledge Analysis) ekle
  - System app olarak: Java tabanlı, `weka.jar` path tespiti
  - `java -jar weka.jar` komutu ile çalıştırma
  - env_types: ["system_tools"]

- **F86** — Package Manager Env Yolu Sorunu (AppData vs Custom Path)
  - Şu an micromamba/uv gibi tool'lar env'leri AppData altına kuruyor (`C:\Users\...\AppData\Roaming\VenvStudio\micromamba\...`)
  - Bunun yerine kullanıcının seçtiği base_dir'e (`C:\venv\` gibi) doğrudan kursun
  - Mevcut Python (system) kullanarak env oluşturabilsin → tool'un kendi Python'ını indirmek zorunda kalmasın
  - `--prefix` parametresi kullanıcı path'ine yönlendirilmeli
  - conda, mamba, rye, uv ve diğer tüm PM'ler için geçerli

- **F87** — Sidebar Sıralama: Environments Üstte
  - Sol sidebar'da Environments bölümü Packages'ın üzerine taşınsın
  - Açılışta yine Packages → Launch tab aktif olsun (primary/default env için)
  - Kullanıcı ilk bakışta env listesini görsün ama çalışma alanı Launch olarak açılsın

- **F88** — Poetry/Rye Create'te Seçilen Python Kullanımı
  - Poetry create flow'unda seçilen `_python`'ı `poetry env use <python_path>` ile geçir
  - Rye create flow'unda `rye pin <python_version>` veya `--python` flag kullan
  - Şu an Python combo görünüyor ama seçilen Python sadece marker'a yazılıyor, create'te kullanılmıyor

- **F89** — VenvStudio Çoklu Platform Dağıtımı
  - Şu an sadece `pip install venvstudio` (PyPI) ile kurulabiliyor
  - Hedef: tüm popüler paket yöneticilerinden kurulabilir olması
  - **conda / mamba:** conda-forge'a paket gönder
    - `meta.yaml` (veya `recipe.yaml`) hazırla → conda-forge/staged-recipes repo'suna PR aç
    - Gerekli: `meta.yaml`, `build.sh` (Linux/macOS), `bld.bat` (Windows)
    - conda-forge review süreci ~1-2 hafta
    - Sonuç: `conda install -c conda-forge venvstudio`
  - **pipx:** Zaten çalışıyor → `pipx install venvstudio` (PyPI'den çeker, CLI entry point gerekli)
    - `pyproject.toml`'da `[project.scripts]` veya `[tool.poetry.scripts]` ile entry point tanımla
    - Örnek: `venvstudio = "src.main:main"` — pipx bunu otomatik izole CLI app olarak kurar
  - **snap:** Snapcraft ile paketleme
    - `snapcraft.yaml` hazırla
    - `snapcraft` ile build → Snap Store'a yükle
    - Sonuç: `sudo snap install venvstudio`
  - **flatpak:** Flathub'a gönder
    - `com.github.bayramkotan.VenvStudio.yml` manifest hazırla
    - Flathub repo'suna PR aç
    - Sonuç: `flatpak install flathub com.github.bayramkotan.VenvStudio`
  - **AUR (Arch Linux):** PKGBUILD hazırla
    - `PKGBUILD` dosyası yaz → AUR'a yükle
    - Sonuç: `yay -S venvstudio` veya `paru -S venvstudio`
  - **Homebrew (macOS/Linux):** Formula hazırla
    - `venvstudio.rb` formula yaz → homebrew-core'a PR veya kendi tap oluştur
    - Sonuç: `brew install venvstudio` veya `brew install bayramkotan/tap/venvstudio`
  - **winget (Windows):** Microsoft Store / winget manifest
    - `manifests/b/bayramkotan/VenvStudio/` altına YAML manifest
    - winget-pkgs repo'suna PR aç
    - Sonuç: `winget install bayramkotan.VenvStudio`
  - **scoop (Windows):** Bucket manifest
    - JSON manifest hazırla → kendi bucket repo'su oluştur veya scoop extras'a PR
    - Sonuç: `scoop install venvstudio`
  - **npm (Node.js wrapper):** Opsiyonel — Python dependency gerektirir
  - **Öncelik sırası:** pipx (kolay) → conda-forge (geniş kitle) → AUR → Homebrew → winget → snap → flatpak → scoop
- **F84** — ✅ TAMAMLANDI (v1.4.36): Rename tooltip açıklamaları eklendi

- **B80** — 🔴 Rye Kaldırılacak (Artık Geliştirilmiyor)
  - Rye resmi olarak geliştirilmeyi bıraktı — uv'ye yönlendiriliyor
  - Kaldırılacak yerler: env_dialog.py, package_panel.py, venv_manager.py, constants.py, README'ler
  - Mevcut rye env'ler kalsın ama yeni oluşturma devre dışı
  - **5 env tipi kalacak:** venv, uv, poetry, conda, pipx

- **B81** — 🔴 Tool Environment (system_tools) Kaldırılacak
  - system_tools env tipi ayrı bir env olarak gereksiz — system app'ler zaten tüm env tiplerinden erişilebilir
  - Kaldırılacak yerler: env_dialog, package_panel, venv_manager, constants
  - System app kartları diğer env tiplerinde de gösterilecek
  - **5 env tipi kalacak:** venv, uv, poetry, conda, pipx

- **B82** — 🔴 pip dışı env'lerde Clone/Rename hata veriyor
  - uv, poetry, conda, pipx env'lerinde clone ve rename başarısız
  - Neden: clone/rename mantığı `python -m venv` + `pip freeze/install` varsayıyor
  - Çözüm: her env tipi için özel clone/rename stratejisi
    - uv: `uv venv` + `uv pip install -r`
    - poetry: `poetry new` + `poetry add` (pyproject.toml'dan)
    - conda: `conda create --clone` veya `conda list --export` + `conda install --file`
    - pipx: marker klasörü kopyala

- **F90** — Hardlink / Softlink Paylaşımlı Paket Deposu
  - Büyük kütüphaneler (torch, tensorflow, opencv) her env'e ayrı kurulunca disk israfı
  - Merkezi depo: `~/.venvstudio/shared-packages/` veya kullanıcı tanımlı path
  - Yeni env'e paket kurulurken depoda varsa hardlink/symlink kullan
  - Avantaj: 5 env × 2GB torch = 10GB yerine 2GB + 4 link
  - Settings'ten açıp kapatılabilir
  - Stratejiler: hardlink (aynı disk), symlink (farklı disk), copy (fallback)
  - Versiyon çakışması yönetimi gerekli (torch 2.1 vs 2.2)

- **F91** — Proje Görsel Haritası (Architecture Map)
  - Dosya/modül yapısı görselleştirmesi
  - Modül bağımlılık grafiği: import ilişkileri
  - Fonksiyon çağrı haritası: ana flow'lar (env create, package install, launch app)
  - Sınıf hiyerarşisi: QThread worker'lar, dialog'lar, panel'ler
  - Signal-slot bağlantıları, callback chain'ler
  - Araçlar: pydeps, pyreverse, mermaid, graphviz
  - Çıktı: `docs/architecture.md` + mermaid/svg diagram'lar

- **F92** — SDLC Uyumlu Proje Yapılandırması
  - Projeyi Software Development Life Cycle standartlarına uygun yapılandır
  - Dokümantasyon: `docs/` — architecture, contributing, changelog, API docs
  - Test altyapısı: `tests/` — pytest, unit/integration test, mock
  - CI/CD pipeline: GitHub Actions — lint, test, build, release
  - Code quality: pre-commit hooks, type hints (mypy), code coverage
  - Versiyonlama: Semantic versioning, CHANGELOG.md
  - Issue/PR template: `.github/` templates
  - Security: SECURITY.md, dependabot

- **F93** — Tool Registry (Kurulu Araç Takip Sistemi)
  - **Sorun:** uv, pipx, poetry, micromamba gibi tool'lar kurulunca nereye gittiği takip edilmiyor
  - Kullanıcı hangi tool'un nerede olduğunu, versiyonunu bilemiyor
  - **Çözüm:** Basit bir JSON registry dosyası — her tool kurulduğunda/bulunduğunda kaydedilir
  - **Registry dosyası:**
    - Windows: `%APPDATA%\VenvStudio\tool_registry.json`
    - Linux: `~/.config/venvstudio/tool_registry.json`
  - **Kayıt formatı:**
    ```json
    {
      "uv": {"path": "C:\\...\\uv.exe", "version": "0.6.0", "installed_by": "venvstudio", "installed_at": "2026-04-06"},
      "poetry": {"path": "C:\\...\\poetry.exe", "version": "1.8.0", "installed_by": "user", "installed_at": ""},
      "micromamba": {"path": "C:\\...\\micromamba.exe", "version": "2.0.0", "installed_by": "venvstudio"}
    }
    ```
  - **`installed_by`:** `"venvstudio"` (biz kurduk) vs `"user"` (sistemde zaten vardı, biz bulduk)
  - **Davranış:**
    - Tool kurulurken → registry'ye kaydet (path, version, tarih)
    - Tool aranırken → önce registry'ye bak, sonra `shutil.which`
    - Settings > Toolchain sayfasında → registry'den oku, göster
    - Kullanıcı custom path belirleyebilsin → registry'ye yaz
  - **Entegrasyon:**
    - `env_dialog.py` — tool kurulunca registry'ye kaydet
    - `package_panel.py` — install komutlarında registry'den tool path oku
    - F81 (Settings > Toolchain Manager) — registry'yi görsel olarak yönet
