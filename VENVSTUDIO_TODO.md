# VenvStudio TODO — v1.3.34+

## ✅ TAMAMLANDI

### Bug Fixes
- B1–B22: Önceki versiyonlar
- B23: ~~Çift Ekran DPI Crash~~ — devam ediyor
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

## 🔴 KRİTİK

### B23 — Çift Ekran DPI Crash
- [ ] Crash log sistemi mevcut — yeni crash logu bekleniyor
- [ ] `main.py`'ye QT env variable'ları eklenmeli (QApplication'dan önce):
  ```python
  os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
  os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
  ```
- [ ] `_apply_theme()` ekran geçişinde çağrılmamalı — crash yapar

---

## 🟡 ÖNEMLİ

### F29 — Jupyter Working Directory Ayarı
- [ ] Settings → Launch → "Jupyter Working Directory"
- [ ] Seçenekler: Home, Env klasörü, Custom path, Son kullanılan
- [ ] Windows farklı sürücü desteği (D:\, G:\...)
- [ ] Per-env ayar + global default
- [ ] --notebook-dir argümanı olarak geç
- [ ] package_panel._launch_app entegrasyonu

### F30 — CLI/TUI Tools (Detaylı Geliştirme)
**Starship:**
- [ ] Preset önizleme
- [ ] starship.toml inline editörü
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
- **M10:** ✅ Her release'de GitHub Release notes otomatik oluşturuluyor — önceki tag'den bu yana commit mesajları listeleniyor (fix/feat/chore)
- **M8:** Quick Launch — cache boşken ilk geçişte kısa gecikme (UX)

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

### Launcher Architecture
- `needs_console: True` → `CREATE_NEW_CONSOLE`
- `open_browser` + `browser_delay` → N saniye sonra browser açar
- `pick_logdir: True` → klasör seçici (TensorBoard)
- `script_launcher: True` → "📂 Open Script" butonu

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

**Mevcut versiyon:** v1.3.35
