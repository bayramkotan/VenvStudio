# VenvStudio TODO — v1.3.34+

> **📌 Bu proje Eğitimi ön planda tutmak için geliştirmeler yapacaktır.**

## ✅ TAMAMLANDI

### Bug Fixes
- B1–B22: Önceki versiyonlar
- B23: ~~Çift Ekran DPI Crash~~ — ✅ TAMAMLANDI (v1.3.38)
  - `main.py`'ye `QT_ENABLE_HIGHDPI_SCALING` + `QT_SCALE_FACTOR_ROUNDING_POLICY` env variables eklendi
  - `_apply_theme()` re-entrant guard + RuntimeError try/catch eklendi
  - `screenChanged` signal'ı bağlandı → 150ms delay ile güvenli theme re-apply
  - `showEvent` override ile windowHandle bağlantısı garanti edildi
- B31: System Python registry PATH'den tespit (config'e bağımlılık kaldırıldı)
- B32: Set Default PATH güvenlik fix (winget/omp silmiyordu)
- B33: Streamlit browser iki kez açılıyordu — `--server.headless true` fix
- B34: TensorBoard log dizini olmadan crash — `pick_logdir` fix
- B35: Refresh butonu UI'ı donduruyordu — ThreadPoolExecutor ile paralel worker
- B36: CLI Tools dropdown'larında checkbox yoktu
- B37: Log folder butonu crash — `get_log_dir` import fix
- B38: `delete_venv` callback parametresi eksikti
- B39: `sync_cache_with_disk` / `invalidate_all_caches` eksikti

### Features
- F1–F24: Önceki versiyonlar
- F25: Verify pip butonu (Settings → Python Versions)
- F26: Yeni launcher tools (Gradio, Dash, Panel, Voilà, MLflow, TensorBoard, FastAPI, Datasette)
- F27: Open Script butonu (framework launcher kartlarında)
- F28: macOS ARM build (Rosetta 2 ile Intel'de de çalışır)

### Releases
- v1.3.27–1.3.29: PATH fix, registry scan, Source fix
- v1.3.30: Verify pip, Streamlit fix, yeni launcher tools
- v1.3.31: Registry detection, CLI checkboxes, log folder fix, parallel Refresh
- v1.3.32: System Python registry fix (B31)
- v1.3.33: delete_venv callback, parallel Refresh, macOS universal binary
- v1.3.34: Intel macOS build kaldırıldı, ARM-only (Rosetta 2)

---

## 🟡 ÖNEMLİ

### ✅ F29 — Jupyter Working Directory Ayarı (TAMAMLANDI)
- Settings → "🚀 Launch Settings" bölümü eklendi
- 3 seçenek: 🏠 Home / 📁 Env Folder / 📂 Custom Path
- `--notebook-dir` argümanı ile Jupyter'a geçiliyor
- Config'e `jupyter_workdir` + `jupyter_workdir_custom` kaydediliyor

### F30 — CLI/TUI Tools (Detaylı Geliştirme)
**Starship:** ✅ TAMAMLANDI (v1.3.41)
- [x] Preset önizleme (açıklamalı dropdown + description hint)
- [x] starship.toml inline editörü (syntax-highlighted dialog, save/reload/open folder)
- [x] "Test in terminal" butonu (yeni terminal açar, starship init ile)

**Oh My Posh:**
- [ ] Tema önizleme görseli
- [ ] Aktif tema göstergesi

**Nerd Fonts:**
- [ ] Yüklü fontları göster (sistemden oku)
- [ ] Font önizlemesi
- [ ] Multi-select

**Genel:**
- [ ] Shell detection (bash/zsh/fish/pwsh)
- [ ] Shell config backup (.bak)
- [ ] "Remove from shell config" butonu

### F31 — Custom Prompt Sets (Prompt Yöneticisi)
- [ ] Settings → "⚡ Prompt Manager" bölümü
- [ ] Shell türüne göre şablonlar (bash/zsh/fish/pwsh)
- [ ] Değişkenler: {env_name}, {python_version}, {git_branch}, {time}
- [ ] Hazır presetler (Classic, Minimal, Full, Catppuccin)
- [ ] Import/Export (.json)

## 🟢 İYİLEŞTİRME
- **M5:** Global default Python gösterimi (Settings)
- **M6:** Env tablosunda sütun genişliği kaydetme
- **M7:** CHANGELOG.md tutulması
- **M11:** ✅ About (ℹ️) bölümü Settings'te her zaman en altta — tüm bölümlerden sonra
- **M12:** Settings'e eklenen her dropdown önüne mutlaka checkbox konulmalı — checkbox işaretlenmeden combo disabled olmalı — Launch Settings dahil tüm bölümlerden sonra
- **M10:** ✅ Her release'de GitHub Release notes otomatik oluşturuluyor — önceki tag'den bu yana commit mesajları listeleniyor (fix/feat/chore)
- **M8:** Quick Launch — cache boşken ilk geçişte kısa gecikme (UX)
- **M13:** README'ye Linux kurulum rehberi ekle:
  - `--break-system-packages` parametresi açıklaması
  - pip kurulumu: Arch (`sudo pacman -S python-pip`), Debian (`sudo apt install python3-pip`), Fedora/CentOS (`sudo dnf install python3-pip`), openSUSE (`sudo zypper install python3-pip`), NixOS (`nix-env -iA nixpkgs.python3Packages.pip`)
  - `pip install venvstudio` yerine `python -m pip install venvstudio -U` öner
  - Windows ARM + macOS Apple Silicon notları
- **M14:** README'ye `python3-venv` paket kurulumu da ekle (Debian/Ubuntu: `sudo apt install python3-venv`)

## 🔴 KRİTİK BUG'LAR
- **B41:** Linux'te Python yüklendikten sonra Settings'te görünmüyor — program yeniden başlatılana kadar. `_scan_pythons()` install sonrası otomatik tetiklenmeli
- **B42:** Python yükleyici sorunları:
  - System Install hâlâ lokal path (`AppData\VenvStudio\pythons`) veriyor — `C:\Program Files` kullanmalı
  - Dialog'da "astral-sh/python-build-standalone" linki gereksiz, kaldırılmalı veya sadeleştirilmeli
  - Sistemi çökertme riski — güvenlik kontrolleri eklenmeli
- **B43:** Arch Linux'te Orange3 crash — `chardet.universaldetector` modülü bulunamıyor (Python 3.14 + chardet uyumsuzluğu). `chardet<4.0` pin'i yeterli değil, `charset-normalizer` fallback gerekebilir
- **B44:** Arch Linux'te IPython çalışmıyor — detaylı hata logu gerekli
- **B45:** QThread SIGABRT crash — "QThread: Destroyed while thread is still running" — her kapanışta oluyor. Muhtemelen `EnvDetailWorker` veya `_QLWorker` parent destroy edilirken hâlâ çalışıyor. `closeEvent` ve dialog kapanışlarında tüm worker'lar `wait()` edilmeli
- **B46:** Oh My Posh "command not found" — fish shell'de `~/.local/bin/VenvStudio/bin/` PATH'e eklenmiyor. `config.fish`'e PATH inject kontrolü gerekli. Ayrıca "Open Terminal" ile açılan shell'de PATH henüz yüklenmemiş olabilir
- **B47:** Yeni temalar çalışmıyor — 182 satır hardcoded dark renk var. Tam refactor gerekli (sonraki chat'te). Kısmi fix: `startswith("light")` + **live preview** (dropdown değişince anında tema değişiyor, Save gerekmez)
- **B48:** Uygulama genel stabilite sorunu — çok sık crash ediyor. Kapsamlı crash analizi ve defensive coding gerekli

### B48 — Stabilite ve Log Sistemi İyileştirme Planı
- [ ] **Detaylı log seviyesi:** Her fonksiyon girişine `logger.debug()` ekle — hangi fonksiyon ne zaman çağrıldı, parametreler ne
- [ ] **Exception handler wrapper:** Tüm QThread `run()` metotları `try/except` ile sarılmalı — catch edilen hata loglanmalı, sessiz crash olmamalı
- [ ] **Global exception hook:** `sys.excepthook` ve `threading.excepthook` ile yakalanmamış exception'ları logla + crash dialog göster
- [ ] **QThread safety audit:** Tüm QThread subclass'lar incelenmeli:
  - `EnvDetailWorker` — `closeEvent`'te `wait()` ediliyor mu?
  - `DeleteWorker`, `CloneWorker`, `RenameWorker` — dialog kapanınca ne oluyor?
  - `_QLWorker` (inline class) — parent destroy edilince?
  - `CliToolWorker` — settings page kapanınca?
- [ ] **Signal/Slot safety:** Thread'den UI update yapan signal'lar `Qt.QueuedConnection` mi?
- [ ] **Null/None guard'lar:** `pip_manager`, `venv_path`, `selected_env` None olabilecek her yerde kontrol
- [ ] **Subprocess timeout:** Tüm `subprocess.run()` çağrılarında timeout var mı? Timeout sonrası ne oluyor?
- [ ] **Crash log iyileştirme:** Mevcut crash log'a ek olarak:
  - Son 50 log satırını crash dosyasına dahil et
  - Sistem bilgisi (OS, Python ver, Qt ver, RAM, disk) crash log'a ekle
  - Crash sonrası "Bug Report" butonu — GitHub Issues'a otomatik template ile yönlendir
- [ ] **Startup diagnostics:** Uygulama açılışında kısa self-check — PySide6 import, config dosyası okuma, venv dizini erişim
- [ ] **Graceful degradation:** Bir bileşen crash ederse tüm uygulama kapanmasın — hatalı bileşen devre dışı bırakılsın

## 🟡 PLANLI GELİŞTİRMELER (öncelik sırasıyla)

### 1️⃣ F30 — CLI/TUI Tools tamamlama (devam)
*(Oh My Posh, Nerd Fonts, Genel — Starship tamamlandı)*

### 2️⃣ F37 — CLI Komut Seti Genişletme
- [ ] `vs create <name>` — yeni env oluştur
- [ ] `vs delete <name>` — env sil
- [ ] `vs activate <name>` — env aktif et (shell'e inject)
- [ ] `vs list` — tüm env'leri listele
- [ ] `vs install <pkg>` — aktif env'e paket kur
- [ ] `vs run <command>` — env içinde komut çalıştır
- [ ] `vs info <name>` — env detayları (python ver, paket sayısı, boyut)
- [ ] `vs export <name>` — requirements.txt oluştur
- [ ] `venvstudio --help` gelişmiş yardım çıktısı

### 3️⃣ F38 — Eğitici Özellikler (Education-First)
- [ ] Her ekranda contextual tooltip'ler — "Bu ne işe yarar?" açıklamaları
- [ ] İlk açılış rehberi (onboarding wizard) — adım adım VenvStudio turu
- [ ] Paket kartlarında "Bu paket ne yapar?" kısa açıklamalar
- [ ] Launcher'larda "Bu araç nedir?" bilgi butonları
- [ ] Terminal komutlarını göster — "Arka planda şu komut çalışıyor: ..." şeffaflık modu
- [ ] Venv kavramı açıklaması — "Virtual Environment nedir?" yardım sayfası
- [ ] pip vs uv karşılaştırma bilgi kutusu
- [ ] Hata mesajlarında çözüm önerileri (educational error messages)

### 4️⃣ Diğer Bug Fix'ler ve İyileştirmeler
*(B41–B47, M13–M18)*

## 🟢 İYİLEŞTİRME
- **M5:** Global default Python gösterimi (Settings)
- **M6:** Env tablosunda sütun genişliği kaydetme
- **M7:** CHANGELOG.md tutulması
- **M8:** Quick Launch — cache boşken ilk geçişte kısa gecikme (UX)
- **M10:** ✅ Her release'de GitHub Release notes otomatik oluşturuluyor
- **M11:** ✅ About (ℹ️) bölümü Settings'te her zaman en altta
- **M12:** Settings'e eklenen her dropdown önüne mutlaka checkbox konulmalı
- **M13:** README'ye Linux kurulum rehberi ekle:
  - `--break-system-packages` parametresi açıklaması
  - pip kurulumu: Arch (`sudo pacman -S python-pip`), Debian (`sudo apt install python3-pip`), Fedora/CentOS (`sudo dnf install python3-pip`), openSUSE (`sudo zypper install python3-pip`), NixOS (`nix-env -iA nixpkgs.python3Packages.pip`)
  - `pip install venvstudio` yerine `python -m pip install venvstudio -U` öner
  - Windows ARM + macOS Apple Silicon notları
- **M14:** README'ye `python3-venv` paket kurulumu da ekle (Debian/Ubuntu: `sudo apt install python3-venv`)
- **M15:** Package Info sabit panel olsun — "More" butonu ile detaylı bilgi açılsın. Catalog kısmında da Package Info gösterilsin
- **M16:** Manual Install parsing iyileştirmesi:
  - `pandas==1.0.1`, `pandas=1.0.1`, `pandas 1.0.1` hepsi geçerli olsun
  - Paket adı case-insensitive (`PandAS` → `pandas`)
  - Versiyon formatı: `1`, `1.0`, `1.0.0`, `1.000` hepsi kabul edilsin
- **M17:** Yeni sürümlerde eski env'i kaldırmayı teklif et — farklı kütüphane versiyonlarından doğan hataları önlemek için
- **M18:** Dil desteği README'de güncellenmeli — 11 dil varsa hepsini README'de göster (şu an sadece English/Turkish yazıyor)
- **F32:** Yeni Launcher adayları: Locust (yük testi), Flower (Celery izleme), Pytest (test dashboard), Pdoc/Sphinx (dokümantasyon)
- **F33:** Port Killer butonu — asılı kalmış servis portlarını temizle
- **F34:** Cache Cleaner — `__pycache__` + pip cache temizliği
- **F35:** Bağımlılık ağacı (pipdeptree entegrasyonu) — hangi paket neye bağlı görselleştirme
- **F36:** requirements.txt algılama — klasörde varsa "Bağımlılıkları kur?" uyarısı

## 📋 TEKNİK NOTLAR
- Cache: `%APPDATA%\VenvStudio\env_cache.json`
- Logs: `%APPDATA%\VenvStudio\logs\venvstudio.log`
- Crash logs: `%APPDATA%\VenvStudio\logs\crash_YYYYMMDD_HHMMSS.log`
- PyPI: https://pypi.org/project/venvstudio/
- GitHub: https://github.com/bayramkotan/VenvStudio

---

## 📌 ÖNEMLİ TEKNİK NOTLAR

### Orange3 Bağımlılıkları
- Orange3, AnyQt üzerinden çalışır → **PyQt5 + PyQtWebEngine gerektirir**, PySide6 desteklenmez
- `chardet>=4.0` ile uyumsuz → `chardet<4.0` zorunlu
- Python 3.9 ve altı: `orange3<=3.36.2`; Python 3.10+: `orange3` latest
- **Arch Linux + Python 3.14:** `chardet.universaldetector` bulunamıyor hatası — `chardet<4.0` pin'i yetmiyor, `charset-normalizer` fallback araştırılmalı

### Launcher Architecture
- `needs_console: True` → `CREATE_NEW_CONSOLE`
- `open_browser` + `browser_delay` → N saniye sonra browser açar
- `pick_logdir: True` → klasör seçici (TensorBoard)
- `script_launcher: True` → "📂 Open Script" butonu

### GitHub Release Notes Kuralı
- Commit'ler otomatik kategorize edilir: ✨ feat / 🐛 fix / 🔧 chore,refactor,build,ci / 📌 diğer
- Release body: centered başlık + badge'ler + kategorize changelog + download tablosu (boyutlarla) + star CTA
- **Kural:** Release notes her zaman çok gösterişli ve profesyonel olmalı

---

## 🚀 YENİ VERSİYON RELEASE KOMUTU

```powershell
(Get-Content src\utils\constants.py) -replace '1.3.OLD', '1.3.NEW' | Set-Content src\utils\constants.py
(Get-Content pyproject.toml) -replace 'version = "1.3.OLD"', 'version = "1.3.NEW"' | Set-Content pyproject.toml
git add .
git commit -m "release: v1.3.NEW - <kısa özet>"
git tag v1.3.NEW
git push origin main
git push origin v1.3.NEW
```

**Mevcut versiyon:** v1.3.44
