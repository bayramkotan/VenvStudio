# VenvStudio TODO — v1.3.28+

## ✅ TAMAMLANDI

### Bug Fixes
- B1–B12: Önceki versiyonlar (env silme crash, Linux terminal, PATH, emoji, theme...)
- B13: updater.py — email module → http.client geçişi
- B14: QComboBox import eksikliği
- B15: Quick launch callback eksikliği
- B16: refresh_packages sync → async
- B17: _invalidate_pkg_cache AttributeError
- B18: updater.py — socket+ssl ile yeniden yazıldı (http.client/urllib PyInstaller'da çalışmıyor)
- B19: User-level Python "User Install" etiketi
- B20: Settings → About bölümü her zaman en altta
- B21: CLI Tools preset dropdown'ları — checkbox olmadan değişiyordu, diğer dropdown'lar gibi yapıldı
- B22: Nerd Fonts dropdown'u da checkbox ile korundu

### Features
- F1–F16: Önceki versiyonlar
- F17: Quick Launch sidebar
- F18: Default Env (tablo kolonu, Make Default, startup auto-open)
- F19: Quick Launch env dropdown senkron
- F20: Right-click → pip show dialog
- F21: PyPI/Docs linkleri Catalog tablosunda (70+ paket)
- F22: CLI/TUI Tools altyapısı (Starship, Oh My Posh, Rich, Textual, Prompt Toolkit, Nerd Fonts)
- F23: Quick Launch 3-yönlü tam sync (QL dropdown ↔ Env tablosu ↔ Sağ panel)
- F24: Logging sistemi (AppData/VenvStudio/logs/ — venvstudio.log + crash_*.log)

### Docs
- M1: README v1.3.8 için tamamen yenilendi (tüm screenshot'larla)
- M2: Output log syntax highlighting
- M3: Sidebar sırası → Packages, Environments, Settings
- M4: Quick Launch cache

### Releases
- v1.3.22: Package cache, custom terminals, preset manager
- v1.3.23: Quick Launch, Default Env, pip show, catalog links, CLI Tools altyapısı
- v1.3.24: QL 3-yönlü sync fix, output highlighting, sidebar sırası
- v1.3.25–26: updater fix denemeleri (başarısız)
- v1.3.27: updater socket+ssl fix, About en alta (B20)
- v1.3.28: CLI dropdown checkbox fix (B21, B22), logging sistemi

---

## 🔴 KRİTİK

### B23 — Çift Ekran DPI Crash
- [ ] Aynı ekranda da çöküyor — kök sebep henüz tespit edilemedi
- [ ] Crash log sistemi eklendi (v1.3.28) — bir sonraki crash'ten sonra log paylaşılacak
- [ ] `main.py`'ye QT env variable'ları eklenmeli (QApplication'dan önce):
  ```python
  os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
  os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
  ```
- [ ] **NOT:** `_apply_theme()` ekran geçişinde çağrılmamalı — crash yapar

---

## 🟡 ÖNEMLİ

### F25 — CLI/TUI Tools (Detaylı Geliştirme)
**Starship:**
- [ ] Preset önizleme
- [ ] starship.toml inline editörü
- [ ] Shell detection göstergesi
- [ ] "Test in terminal" butonu

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
- [ ] Catalog'a "🖥️ CLI/TUI" kategorisi

### F26 — Custom Prompt Sets (Prompt Yöneticisi)
- [ ] Settings → "⚡ Prompt Manager" bölümü
- [ ] Shell türüne göre şablonlar (bash/zsh/fish/pwsh)
- [ ] Değişkenler: {env_name}, {python_version}, {git_branch}, {time}
- [ ] Hazır presetler (Classic, Minimal, Full, Catppuccin)
- [ ] Preset önizleme (simüle terminal çıktısı)
- [ ] Import/Export (.json)

### F27 — Jupyter Working Directory Ayarı
- [ ] Settings → Launch → "Jupyter Working Directory"
- [ ] Seçenekler: Home, Env klasörü, Custom path, Son kullanılan
- [ ] Windows farklı sürücü desteği (D:\, G:\...)
- [ ] Per-env ayar + global default
- [ ] --notebook-dir argümanı olarak geç
- [ ] package_panel._launch_app entegrasyonu

## 🟢 İYİLEŞTİRME
- **M5:** Global default Python gösterimi (Settings)
- **M6:** Env tablosunda sütun genişliği kaydetme
- **M7:** CHANGELOG.md tutulması
- **M8:** Quick Launch — cache boşken ilk geçişte kısa gecikme (UX)

## 📋 TEKNİK NOTLAR
- Cache: `%APPDATA%\VenvStudio\env_cache.json`
- Logs: `%APPDATA%\VenvStudio\logs\venvstudio.log`
- Crash logs: `%APPDATA%\VenvStudio\logs\crash_YYYYMMDD_HHMMSS.log`
- PyPI: https://pypi.org/project/venvstudio/
- GitHub: https://github.com/bayramkotan/VenvStudio
