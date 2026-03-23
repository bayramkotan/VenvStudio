# VENVSTUDIO_TODO.md

## 🔴 KRİTİK

- **B41** — ✅ ÇÖZÜLDÜ (v1.3.68–1.3.78): AppImage'da env oluşturunca ikinci VenvStudio açılıyordu
  - Kök neden 1: `subprocess_args()` AppImage env variable'larını temizlemiyordu → `appimage_clean_env()` eklendi
  - Kök neden 2: `sys.executable` AppImage'da AppImage binary'sini gösteriyordu → `/usr/bin/python3` kullanıldı
  - Kök neden 3: Python 3.14 `ensurepip --default-pip` flag'ini kaldırdı → `--without-pip` + manuel ensurepip

- **B42** — Python yükleyici güvenlik kontrolleri
- **B49** — Windows EXE: ilk açılışta Python kurulu değilse kullanıcıya sor ve python.org installer indirip çalıştır (venv dahil). Linux'taki _check_and_install_linux_deps() benzeri bir _check_and_install_windows_deps() fonksiyonu eklenecek.
- **B43** — Arch + Python 3.14 Orange3 crash
- **B44** — Arch'ta IPython çalışmıyor
- **B47** — 182 satır hardcoded dark renk
- **B48** — @safe_slot/SafeWorkerMixin henüz yaygınlaştırılmadı

---

## 🟡 PLANLI (öncelik sırasıyla)

### 1. 🎓 F38 — EĞİTİCİ ÖZELLİKLER (devam)
- [ ] `EDUCATIONAL_HINTS` UI'da göster — env oluşturmada "venv nedir?", paket yüklemede "pip nedir?"
- [ ] Onboarding wizard — ilk açılışta adım adım rehber
- [ ] "Arka planda ne çalışıyor" şeffaflık modu — toggle ile terminal komutlarını göster/gizle
- [ ] Settings'te her ayarın ne yaptığını anlatan ℹ️ info icon'ları

### 2. ⚡ Windows Startup Hızı
- [ ] `SettingsPage` lazy-load (ilk tıklamada oluşsun)
- [ ] `_scan_pythons()` cache'le veya lazy yap

### 3. 🗄️ Cache Performance Refactoring
- [ ] In-memory cache dict, tek VenvManager/ConfigManager instance
- [ ] `package_panel.py`'de her env geçişinde yeni VenvManager oluşturuluyor — tek instance'a geç
- [ ] Env geçişlerinde her şey cache'den gelsin
- [ ] Cache invalidate: sadece install/uninstall/remove sonrası

### 4. 🛡️ @safe_slot / SafeWorkerMixin Yaygınlaştırma
- [ ] Tüm dosyalara `@safe_slot` ve `SafeWorkerMixin` ekle

### 5. settings_page.py Duplicate Temizliği
- [ ] 6900+ satır, duplicate fonksiyonlar temizlenmeli

### 6. B47 — Tema Refactoring
- [ ] 182 satır hardcoded dark renk → CSS variable'larına taşı

### 7. F30 / F37 / F38 devam
- [ ] CLI/TUI Tools (F30)
- [ ] CLI Komut Seti (F37)
- [ ] F38 devam (yukarıda)

---

## 🟢 İYİLEŞTİRME

- **M5** — README güncelle
- **M6** — CHANGELOG güncelle
- **M7** — Quick Launch UX iyileştirmesi
- **M8** — Sütun genişliği ayarları
- **M9–M18** — Diğer küçük iyileştirmeler

---

## ✅ TAMAMLANANLAR

| Bug/Feat | Versiyon | Açıklama |
|----------|----------|----------|
| B41 | v1.3.68–1.3.78 | AppImage'da ikinci VenvStudio açılıyordu — tamamen çözüldü |
| — | v1.3.78 | Python 3.14 ensurepip breaking change fix |
| — | v1.3.77 | /usr/bin/python3 kullan, sys.executable değil |
| — | v1.3.75 | subprocess_args() appimage_clean_env() entegrasyonu |
| — | v1.3.67 | Update check background thread — Linux ghost window fix |
| — | v1.3.66 | Env dialog Linux layout fix (setFixedSize → setMinimumSize) |
| — | v1.3.65 | main.py startup input() kaldırıldı |
| — | v1.3.64 | _run() CREATE_NO_WINDOW, platform_utils wt→PowerShell |
| — | v1.3.63 | Env dialog yatay layout, terminal paneli sağda |
| F38 | v1.3.62 | Preset descriptions, launcher tooltips, UI tooltips, catalog sağ tık |
