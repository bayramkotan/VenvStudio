# VENVSTUDIO_TODO.md

## 🔴 KRİTİK

- **B41** — ✅ ÇÖZÜLDÜ (v1.3.68–1.3.90): AppImage/EXE subprocess re-launch loop tamamen çözüldü
- **B42** — Python yükleyici güvenlik kontrolleri
- **B43** — Arch + Python 3.14 Orange3 crash
- **B44** — Arch'ta IPython çalışmıyor
- **B47** — 182 satır hardcoded dark renk
- **B48** — @safe_slot/SafeWorkerMixin henüz yaygınlaştırılmadı
- **B49** — Windows EXE: ilk açılışta Python kurulu değilse kullanıcıya sor, python.org installer indir
- **B50** — Linux AppImage: env oluşturduktan sonra VenvStudio çöküyor (araştırılacak)

---

## 🟡 PLANLI (öncelik sırasıyla)

### 1. 🎓 F38 — EĞİTİCİ ÖZELLİKLER (devam)
- [ ] `EDUCATIONAL_HINTS` UI'da göster — env oluşturmada "venv nedir?", paket yüklemede "pip nedir?"
- [ ] Onboarding wizard — ilk açılışta adım adım rehber
- [ ] "Arka planda ne çalışıyor" şeffaflık modu
- [ ] Settings'te her ayarın ne yaptığını anlatan ℹ️ info icon'ları

### 2. ⚡ Windows Startup Hızı
- [ ] `SettingsPage` lazy-load (ilk tıklamada oluşsun)
- [ ] `_scan_pythons()` cache'le veya lazy yap

### 3. 🗄️ Cache Performance Refactoring
- [ ] In-memory cache dict, tek VenvManager/ConfigManager instance
- [ ] Env geçişlerinde her şey cache'den gelsin
- [ ] Cache invalidate: sadece install/uninstall/remove sonrası

### 4. 🛡️ @safe_slot / SafeWorkerMixin Yaygınlaştırma

### 5. settings_page.py Duplicate Temizliği (6900+ satır)

### 6. B47 — Tema Refactoring (182 satır hardcoded renk)

### 7. F30 / F37 / F38 devam

---

## 🟢 İYİLEŞTİRME
- M5–M18 — README, CHANGELOG, Quick Launch UX, sütun genişliği vb.

---

## ✅ TAMAMLANANLAR

| Bug/Feat | Versiyon | Açıklama |
|----------|----------|----------|
| B41 | v1.3.68–1.3.90 | AppImage/EXE subprocess re-launch loop — tamamen çözüldü |
| — | v1.3.91 | Python versiyonları numerik sort |
| — | v1.3.90 | Windows EXE default Python: find_system_pythons()[0] |
| — | v1.3.79 | pip yoksa ensurepip ile kur (Python 3.14+) |
| — | v1.3.78 | Python 3.14 ensurepip breaking change fix |
| — | v1.3.75 | subprocess_args() appimage_clean_env() entegrasyonu |
| — | v1.3.67 | Update check background thread Linux ghost window fix |
| — | v1.3.66 | Env dialog Linux layout fix |
| — | v1.3.65 | main.py startup input() kaldırıldı |
| — | v1.3.64 | _run() CREATE_NO_WINDOW, platform_utils wt→PowerShell |
| — | v1.3.63 | Env dialog yatay layout, terminal paneli sağda |
| F38 | v1.3.62 | Preset descriptions, launcher tooltips, UI tooltips |
