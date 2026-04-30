# VENVSTUDIO_TODO.md

## 🔴 ÖNCELIK #1 — Startup Hız Optimizasyonu (Hedef: 3-5 saniye)

### PERF-001 — Açılış süresi (güncel durum)

**Windows:** ~26 saniye (hedef: 3-5s) — hâlâ çalışılıyor
**Linux:**   ~8 saniye  (hedef: 3-5s) — iyileşti, devam ediliyor

Profiling (Windows, 6 env):
  __init__ started → _refresh_env_list = 10s   (PackagePanel.__init__ + _setup_ui)
  _refresh_env_list → __init__ complete = 13s  (sync_cache + subprocess'ler)

Profiling (Linux, 6 env):
  __init__ started → _refresh_env_list =  7s   (PackagePanel.__init__ + _setup_ui)
  subprocess: pipx list --short                 (pipx cache siliniyordu — DÜZELTILDI v1.4.83)
  subprocess: pip list --format=json            (poetry cache siliniyordu — DÜZELTILDI v1.4.83)
  [Cache] HIT: conda_env, ml, nlp, uv_env      (bunlar zaten çalışıyor)

✅ Tamamlanan düzeltmeler (v1.4.82 - v1.4.83):
  - Cache key fix: Windows pathlib.resolve() /C:/... → C:/... (venv_manager.py)
  - sync_cache_with_disk: artık sadece base_dir içini temizliyor
    (pipx ~/.local/share/pipx, poetry ~/.cache/pypoetry/... korunuyor)
  - PackagePanel lazy tabs: Installed/Catalog/Presets/Manual ilk tıklamada build
  - Stub widgets: packages_table, catalog_table vs. __init__'te boş oluşturuluyor
  - _all_cache class-level memory dict: env_cache.json tek seferinde okunuyor
  - conda/uv/poetry/pipx için cache check eklendi (subprocess öncesi)
  - settings_catalog.py debug print'leri kaldırıldı
  - package_panel: _system_tool_cache, _cfg_cache, _vm_cache in-memory

✅ Tamamlanan (v1.4.82-v1.4.85):
  - Cache key fix (Windows /C:/... → C:/...)
  - sync_cache_with_disk: dış env'ler (pipx/poetry/conda) korunuyor
  - Poetry direct loop cache check eklendi
  - PackagePanel lazy tabs (Installed/Catalog/Presets/Manual)
  - Env create/delete sonrası invalidate_all_caches() + refresh
  - Delete progress popup kaldırıldı
  - Log detaylandırıldı (print → _log.debug/info)

⚠️ Hâlâ açık:
  1. PackagePanel._setup_ui ~7-10s — Launcher card'ları lazy yapılabilir
  2. Windows'ta açılış ~26-31s — Linux'ta tüm HIT'ler OK, Windows test gerekli
  3. [Cache] HIT/MISS/STALE logları production'da DEBUG seviyesinde — OK
  4. conda env için python --version subprocess — marker'dan version okunabilir

⚠️ EN SON ÖLÇÜM (v1.4.85, Windows 11, AMD64, Python 3.13.13, Qt 6.10.2, 6 env):
  - 11:20:17 → MainWindow.__init__ started
  - 11:20:35 → _refresh_env_list called  (18s — PackagePanel.__init__ + _setup_ui)
  - 11:20:36 → tüm cache HIT (1s — cache çalışıyor ✓)
  - 11:20:48 → MainWindow.__init__ complete (13s — env_selected + post-setup)
  - **TOPLAM: 31 saniye** (hedef 3-5s — 6-10x daha yavaş)
  - Linux aynı sistem profilinde ~8s — Windows 4x daha yavaş
  - Tüm cache'ler HIT olmasına rağmen yavaş → UI build pahalı, subprocess değil
  - Windows-specific darboğazlar:
    * Python module import (Qt, PySide6) Windows'ta yavaş
    * QSS stylesheet parse — Windows'ta GDI font lookup yavaş
    * Launcher card render — 22 kart × QPixmap/QIcon load
    * QFont uyarısı (B174 — aşağıda) bir döngünün/yeniden çiziminin işareti olabilir

  İlgili dosyalar:
    src/core/venv_manager.py  — cache key, sync_cache, lazy subprocess
    src/gui/package_panel.py  — lazy tabs, stub widgets, launcher cards
    src/gui/main_window.py    — startup sequence, defer heavy ops


---

## 🔴 EN ÖNCELİKLİ (Sonraki Sprint)

### 🟡 F156 — Terminal Çıktıları Anlamlı/Görsel Olsun (Rich Box)

**Hedef:** Anlaşılmaz log satırları yerine kullanıcı dostu kutucuklar.

**Örnek:**
```
╭──────────────────────────────────────╮
│ 🚀  Deleting environment 'tsssss'    │
│    • Type: venv                      │
│    • Path: C:\venv\tsssss            │
╰──────────────────────────────────────╯
╭──────────────────────────────────────╮
│ ✅  Environment 'tsssss' deleted     │
│    • Removed: C:\venv\tsssss         │
╰──────────────────────────────────────╯
```

**Nerede uygulanacak:**
- Env oluştur/sil/değiştir
- Paket yükle/kaldır
- Launch app yükle/kaldır/çalıştır
- Komut kopyalama
- Tab değiştirme
- Preset yükleme
- Manual install

**Teknik:** Rich library zaten dependency (`rich.console.Console` + `rich.panel.Panel`). Logger formatter'ında özel event'ler için Panel render et.

**Dosya:** `src/utils/logger.py`, ilgili event'leri tetikleyen yerler

**Öncelik:** 🟡 Orta — UX iyileştirmesi, çok değer katar

---

### 🟡 F155 — Create Env Dialog: Diğer Backend'lerde de "Pip Upgrade / system-site-packages" Var mı?

**Sorun:** Create Env dialog'unda venv için `--system-site-packages` ve `pip upgrade` seçenekleri var. **uv, conda, pipx, poetry** için bu seçenekler de uygun mu? Ekrana çıkıyor mu? Çıkıyorsa anlamlı mı?

**Yapılacak:**
- Her backend için Create dialog'u test et
- venv: `--system-site-packages` ✓ var
- uv: `--system-site-packages` desteği var mı? `uv venv --system-site-packages` çalışıyor mu?
- conda: env oluştururken site-packages'a paralel kavram var mı? (`--clone base` belki)
- pipx: tek-paket tool, system-site-packages anlamsız
- poetry: `poetry env use` — ayar farklı
- Pip upgrade: uv/conda/pipx/poetry için anlamı var mı?

**Sonuç:** Backend-aware seçenek seti. Uygun olmayanları gizle veya disable et + tooltip'le açıkla.

**Dosya:** `src/gui/env_dialog.py`

---

### 🟡 B178 — Env Silerken Form Bazen Donuyor

**Sorun:** Env silme operasyonu sırasında ana form bazen donuyor (yanıt vermiyor görünüyor). v1.4.85'te delete progress popup kaldırıldı ama tam çözülmemiş — silme hâlâ UI thread'de bir şey yapıyor olabilir.

**Yapılacak:**
- Silme operasyonunu profile et
- `shutil.rmtree` UI thread'inde mi koşuyor? (Büyük env'lerde 5-10 saniye sürebilir)
- `_on_delete_finished` callback'inde pahalı bir iş var mı?
- Solution: Silme tamamen background QThread'de + UI'da progress göstergesi (alt panel)

**Dosya:** `src/gui/main_window.py` veya `src/core/venv_manager.py` (delete_env)

---

### 🟡 B179 — Launch App Yükle/Sil Sonrası Form Tazelenmiyor mu?

**Sorun:** Launch sekmesinde bir uygulama yüklenip kaldırılınca env paket sayısı / size güncelleniyor mu? Tablo/UI tazeleniyor mu? Test edip doğrula.

**Yapılacak:**
- Launch'tan JupyterLab yükle → env tablosunda paket sayısı güncellendi mi?
- Launch'tan JupyterLab kaldır → "Installed" badge "Not installed" oluyor mu?
- Env size yeniden hesaplanıyor mu? (cache invalidate edilmeli)
- Aynı şey paket yükle/kaldır için de geçerli (Catalog, Manual Install, Presets)

**Beklenen davranış:** Her install/uninstall sonrası:
- Env'in pkg_list cache invalidate
- Env'in size cache invalidate
- UI tabloları refresh

**Dosya:** `src/gui/package_panel.py` (install/uninstall callback'leri)

---

### 🔴 PERF-002 — Hedef: Her Platformda < 3sn Cold Start

**Mevcut:**
- Windows 11: ~15-16s (v1.4.86 fix sonrası, eskiden 31s)
- Linux: ~5-6s

**Hedef:** Her ikisinde de **< 3 saniye**

**Bu hedef için PERF-001'de planlanan tüm aşamalar gerekli:**
- ✅ Aşama 1: Pkg cache fix (v1.4.87) — 5.9s tasarruf
- ✅ Aşama 1.5: QSS stylesheet cache (v1.4.88)
- ⏳ Aşama 2: Chip widget cache (env table render — 11.8s tasarruf hedefi)
- ⏳ Aşama 3: Launcher card lazy load (22 kart — 3-5s tasarruf hedefi)
- ⏳ Aşama 4: Module lazy import (learn_page, settings_*)
- ⏳ Aşama 5: Mtime-based cache invalidation
- ⏳ Aşama 6: Final profile + polish

**Ölçüm aralığı:** Her aşamadan sonra Windows + Linux ölçümü tekrarla, hedef yaklaşımını izle.

**Öncelik:** 🔴 Yüksek — kullanıcı deneyimi için kritik

---
### 🔴 B174 — Windows'ta `QFont::setPointSize: Point size <= 0 (-1)` Spam Uyarısı

**Sorun:** Windows'ta uygulama açılışından itibaren, env değiştirince ve page switch yapınca terminale şu uyarı düşüyor:
```
QFont::setPointSize: Point size <= 0 (-1), must be greater than 0
```

**Reproduce (Windows 11, Python 3.13.13, Qt 6.10.2, PySide6 6.10.2, v1.4.85):**
```
11:20:36 │ HIT: C:/venv/uv_env (cache OK)
QFont::setPointSize: Point size <= 0 (-1), must be greater than 0  ← ilk uyarı
11:20:43 │ _on_env_selected: env='dev'
11:20:48 │ MainWindow.__init__ complete
QFont::setPointSize: Point size <= 0 (-1), must be greater than 0  ← her seferinde
11:20:58 │ _switch_page → Packages
11:20:58 │ _on_env_selected: env='ml'
QFont::setPointSize... × 8  ← page switch'te 8 kez!
11:21:12 │ _switch_page → Environments
QFont::setPointSize... × 2
11:21:14 │ _on_env_selected: env='uv_env'
11:21:15 │ _on_env_selected: env='pipx'
QFont::setPointSize... × 2
11:21:16 │ _on_env_selected: env='p1'
QFont::setPointSize... × 2
```

Linux'ta (CachyOS, Pardus) bu uyarı **YOK** — sadece Windows'ta. Bu Windows-specific bir kod yolu var demektir, ya da Qt'nin Windows backend'i pixel-size font'lardan point-size'a çevirirken `-1` döndürüyor.

**Kök neden hipotezleri:**

1. **`QFont().pointSize()` → `-1` döndüğünde başka bir QFont'a kopyalanıyor**
   - Bir widget'ın font'u pixel-size based (`setPixelSize()`) olarak set edilmiş
   - Sonra `font.pointSize()` çağrılıyor → `-1` dönüyor (pixel size kullanıyorsa point size yok)
   - Bu `-1` değeri başka bir `setPointSize()` çağrısına gidiyor → uyarı
   - Çözüm: `font.pointSize()` yerine `font.pointSizeF()` veya pixel-size kontrolü yap (`font.pixelSize() > 0`)

2. **Stylesheet font merge hatası**
   - QSS'te bazı widget'larda `font-size: 12px` (pixel)
   - Python'da `widget.font().pointSize()` çağrılıyor → pixel-size'lı font için `-1` dönüyor
   - Fontu yeniden uygularken `setPointSize(-1)` çağrılıyor

3. **3-level font sistemi (v1.4.26)** — Headings/UI&Menus/Details
   - `_refresh_styles` veya benzer fonksiyon font cascade yaparken bir widget'ta font default `-1` oluyor olabilir
   - Özellikle env-selected callback'inde font güncellemesi yapılıyorsa (her env tıklamada uyarı çıktığı için muhtemel)

4. **Launcher card icon font**
   - Launcher card'larında 22 kart var, her birinde bir QLabel/QPushButton font'u
   - Windows'ta default QPushButton font size `-1` olabiliyor (Qt theme'e göre değişir)

**Hangi widget? — Bulma stratejisi:**
- v1.4.86'da `main.py`'ye geçici debug:
  ```python
  # GEÇİCİ — B174 teşhisi için, çözünce KALDIR
  import os
  if os.environ.get("VENVSTUDIO_FONT_TRACE"):
      from PySide6.QtGui import QFont
      _orig_setPointSize = QFont.setPointSize
      def _traced_setPointSize(self, size):
          if size <= 0:
              import traceback
              print(f"[FONT TRACE] setPointSize({size}) called from:")
              traceback.print_stack(limit=10)
          _orig_setPointSize(self, size)
      QFont.setPointSize = _traced_setPointSize
  ```
- Sonra `VENVSTUDIO_FONT_TRACE=1 python main.py` ile çalıştır
- Stack trace'ten hangi dosya/satır olduğu çıkar

**Olası dosyalar (öncelik sırası):**
1. `src/utils/styles.py` — global font setup
2. `src/gui/main_window.py` — `_refresh_styles`, `_on_env_selected`, `_switch_page` (uyarı bunlarla korelasyonlu)
3. `src/gui/package_panel.py` — Launcher card font'ları, env değişikliği callback
4. `src/gui/settings_appearance.py` — 3-level font sistemi (Headings/UI&Menus/Details)
5. `src/gui/syntax_highlighter.py` — Catppuccin highlighter font set'i

**Etkisi:**
- ✅ Crash yapmıyor — sadece terminal'e uyarı düşüyor
- ⚠️ Performans: Her uyarı bir başarısız Qt çağrısı — Windows'taki 31s startup'a katkıda bulunuyor olabilir
- ⚠️ Logları kirletiyor — gerçek hatalar bu spam'in arasında kayboluyor
- ⚠️ Production'da kullanıcılar `python main.py` ile başlatınca görüyor

**Kural #12 (Verbose Logging) ile ilişki:**
- Bu uyarı Qt C++ tarafından `stderr`'e yazılıyor — Python logger'ı yakalayamaz
- Çözüm: kök nedeni bul ve düzelt, log'u "bastırmak" değil

**Öncelik:** 🔴 Yüksek — Windows kullanıcılarını rahatsız ediyor, performans sorununu maskeliyor olabilir

---

### 🟡 B175 — Windows Startup ~31s + Env Switch Kasması (KISMİ ÇÖZÜLDÜ v1.4.86)

**v1.4.86'da çözülen kısım — Env Switch Kasması:**
Profile (cProfile, 44.5s ölçüm) net konuştu:
- `_on_env_selected` 8 kez çağrılmış, her biri ~3s, toplam 23.9s
- En büyük suçlu: `_update_env_info_bar` içinde `os.walk` UI thread'inde (12s — 43,066 walk çağrısı, 345,853 stat çağrısı!)
- Aynı env'e tekrar tıklayınca tüm reload tekrarlanıyordu

**v1.4.86 fix (`src/gui/package_panel.py`):**
1. `_EnvSizeWorker` — yeni QThread sınıfı; env size hesaplaması arka plana alındı
2. `set_venv` early-return — aynı env'e tekrar tıklayınca anında dön
3. Hesaplanan size venv cache'e yazılıyor → bir sonraki açılış anında

**Hâlâ Açık — Windows Startup ~31s:**

**Sorun:** Windows 11'de v1.4.85 startup ölçümü:
- 18s: `MainWindow.__init__` başladı → `_refresh_env_list` çağrıldı (PackagePanel.__init__ + _setup_ui)
- 1s: tüm cache HIT (cache çalışıyor ✓)
- 13s: env_selected + post-setup → init complete
- **TOPLAM: 31 saniye**

Linux aynı sistem profilinde (6 env, hepsi cache HIT) ~8s. **Windows 4x daha yavaş.**

**Profile'da bulunan diğer darboğazlar (HÂLÂ AÇIK):**
- `pip list` subprocess — 5.9s (10 çağrı), pkg_list cache HIT olsa bile bazen tekrar koşuyor
- `selectRow` Qt render — 11.8s (12 çağrı), her tıklamada tablo yeniden render
- `setCellWidget` — 1.2s (3,425 çağrı)
- `subprocess.run` toplam — 10.5s

**Yapılacaklar:**
1. **pkg_list cache logic'i** — `_async_refresh_packages` cache HIT olunca neden bazen pip list çağırıyor? Bug var, bul
2. **selectRow render** — env tablosunda her tıklamada `setCellWidget` × 3,425 — chip widget'ları yeniden mi yaratılıyor? Cache'le
3. **Launcher card lazy load** — 22 launcher kartı ilk açılışta build ediliyor; sadece görünür olanları (ilk 6-8) build et
4. **QSS stylesheet parse** — Windows'ta GDI font lookup yavaş, parse'ı minify et
5. **Module import deferred** — `learn_page`, `settings_*` lazy import (sadece tıklanınca)
6. **QPixmap/QIcon caching** — launcher icon'ları paylaşılan cache kullan

**Öncelik:** 🔴 Yüksek — Windows kullanıcı deneyimi çok kötü; PERF-001'in Windows-spesifik kısmı

---

### ✅ B177 — TAMAMLANDI (v1.4.87): Pkg Cache Hiç Yazılmıyordu

**Bug:** `_get_venv_manager` `VenvManager`'a `str` veriyordu, `VenvManager.__init__` ise `base_dir.mkdir()` çağırıyor — string'de mkdir yok. Sessiz `try/except` exception'ı yutuyordu, **pkg_list cache hiç yazılamıyordu** v1.4.86 öncesinde de.

**Fix:** `VenvManager(Path(base_dir))` — tek satır.

**Etki:** Profile'daki 5.9s `pip list` kasması ortadan kalktı. Pkg list cache artık çalışıyor — ilk env switch MISS+SAVED, sonraki açılışlar HIT.

**Dosya:** `src/gui/package_panel.py` — `_get_venv_manager`

---

### 🟡 B176 — TEKRAR AÇIK: Launch Copy Command Tek Satır Kopyalıyor

**Sorun:** Launch sekmesindeki 📋 butonu install + run komutlarını `\n` ile birleştirip clipboard'a koyuyor. Terminale yapıştırınca `\n` ENTER olarak yorumlanıyor → ilk komut çalışıyor, ikinci komut kayboluyor. Tüm terminallerde (PowerShell, cmd, bash, zsh, fish) aynı.

**v1.4.86'da denendi → kullanıcı izni olmadan UI değiştiği için geri alındı.** Tek 📋 buton korundu.

**Yapılacak:** Önce kullanıcıyla UI seçeneği üzerinde anlaş, sonra implement et.

**Olası çözümler:**
1. Tek buton, sadece install komutu kopyala (run gizli)
2. İki ayrı buton (📋 Install + 📋 Run) — geri alınan yaklaşım
3. Tek buton, dialog aç, kullanıcı seçsin
4. Tek buton, uzun-tıkla → run, kısa-tıkla → install
5. Tek buton, platform-aware separator (`;` Windows, `&&` Linux)

**Dosya:** `src/gui/package_panel.py`

---

### 🟡 F154 — View Menüsünden Zoom In/Out (Font Büyüt/Küçült)

**Hedef:** View menüsüne "Zoom In", "Zoom Out", "Reset Zoom" eklensin. Tüm uygulama fontları büyütülüp küçültülebilsin.

**Kapsam:**
- View → Zoom In (Ctrl++ veya Ctrl+=)
- View → Zoom Out (Ctrl+-)
- View → Reset Zoom (Ctrl+0)
- Zoom level config'e kaydedilir (`ui_zoom_level`, default 1.0)
- Font sistemine uygulanır: `font_size`, `primary_size`, `tertiary_size` zoom_level ile çarpılır
- Stylesheet yeniden yüklenir + tüm widget font'ları refresh edilir
- Min/max sınır: 0.6x – 2.0x (60% - 200%)
- Status bar'da geçici mesaj: "Zoom: 110%"

**İlgili dosyalar:**
- `src/gui/main_window.py` — View menüsü + zoom action'lar + handler'lar
- `src/gui/styles.py` — `get_theme()` `zoom_level` parametresi alır
- `src/utils/config_manager.py` — `ui_zoom_level` key'i
- `src/utils/constants.py` — DEFAULT_UI_ZOOM, MIN/MAX sabitleri

**Notlar:**
- 3-level font sistemi (Headings/UI&Menus/Details) zoom'la birlikte ölçeklenmeli
- Settings → Appearance → Font Size ile birlikte çalışmalı (zoom çarpan, font_size taban)
- Reset zoom Settings'teki font değerlerini değiştirmemeli, sadece zoom'u 1.0 yapmalı

**Öncelik:** 🟡 Orta — kullanıcı erişilebilirliği için

---

### 🔴 F151 — Detaylı Conflict Management System (Paket Uyumluluk Önkontrolü)

**Hedef:** Tek paket veya preset (paket serisi) kurulmadan ÖNCE detaylı uyumsuzluk/uyumluluk kontrolü yap, sonra kur. Orange3, MLflow, TensorFlow gibi karmaşık dependency'lere sahip paketler için kritik.

**Sorun:** Şu an pip/uv `pip install <pkg>` çalıştırılıyor → paket fail olunca kullanıcı hata mesajını görüyor. Pre-flight check yok.

**Kapsam — Üç katman:**

1. **Static Compatibility Rules (constants.py)** — bilinen incompatibility'ler
   - `INCOMPATIBLE_PAIRS`: `[("orange3", "pyqt6"), ("tensorflow", "numpy>=2.0"), ...]`
   - `BACKEND_REQUIREMENTS`: paket → tercih edilen backend (`{"orange3": "pip", "jupyter": "pip", "black": "pipx", "mlflow": "pip-not-pipx"}`)
   - `PYTHON_VERSION_CONSTRAINTS`: `{"tensorflow": ">=3.9,<3.13", "orange3": ">=3.10"}`
   - `SYSTEM_DEPENDENCIES`: `{"orange3": {"linux": ["libxcb-cursor0"], "all": ["PyQt5"]}}`

2. **Dynamic Resolution Check (subprocess)** — `pip install --dry-run --report`
   - Kurulum öncesi: `pip install --dry-run --report report.json <pkg>` çalıştır
   - JSON'dan: hangi paketler downgrade/upgrade olacak, conflict var mı
   - uv için: `uv pip install --dry-run` (uv 0.4+ destekliyor)
   - Conda için: `micromamba install --dry-run`

3. **Pre-flight Dialog (yeni dialog)**
   - Tablo: `Paket | Şu anki versiyon | Kurulacak versiyon | Etkilenen | Aksiyon`
   - Çakışma varsa kırmızı uyarı satırı
   - Python versiyon uyumsuzluğu → "Bu env Python 3.9, ama TensorFlow 3.10+ ister"
   - Backend uyumsuzluğu → "Orange3 pipx env'de çalışmaz, venv seç"
   - System dep eksikliği → "libxcb-cursor0 sistemde yok, install komutu: ..."
   - Butonlar: "Yine de Kur", "İptal", "Önerilen Env'e Geç"

**Akış:**
```
User clicks Install / Launch App
  ├─ 1. Static check (constants.py rules) — milisaniyeler
  │    └─ Hard block (Python version, OS) varsa dur, dialog göster
  ├─ 2. Dynamic check (pip --dry-run) — birkaç saniye
  │    ├─ Spinner: "Checking compatibility..."
  │    └─ Conflict varsa dialog göster
  ├─ 3. User onaylar veya iptal eder
  └─ 4. Asıl install çalıştırılır
```

**Preset için özel akış:**
- Preset = N paket → her birini sırayla resolve et
- "ML Basics" presetinde conflict varsa hangi paketin sorun olduğunu göster
- "Atlayarak devam et" / "Sırayı değiştir" / "İptal" seçenekleri

**Dosyalar:**
- `src/core/conflict_resolver.py` — YENİ — static + dynamic check logic
- `src/gui/conflict_dialog.py` — YENİ — pre-flight dialog
- `src/utils/constants.py` — `INCOMPATIBLE_PAIRS`, `BACKEND_REQUIREMENTS`, `PYTHON_VERSION_CONSTRAINTS`, `SYSTEM_DEPENDENCIES` dictleri
- `src/gui/package_panel.py` — install/launch öncesi conflict_resolver çağrısı
- `src/gui/env_dialog.py` — preset install öncesi conflict_resolver çağrısı
- `src/core/venv_manager.py` — `check_compatibility(env, packages) -> ConflictReport` API

**İlgili eski TODO'lar (BU MADDE TARAFINDAN BİRLEŞTİRİLDİ):**
- F140 — Launcher Package Conflict/Version Ayarı
- F65 — Conflict Detection (pip --dry-run --report)
- B144 — Pipx-uygun olmayan paketler (MLflow, Orange3) — bu sistem `BACKEND_REQUIREMENTS` ile çözülecek

**Öncelik:** 🔴 Yüksek — Orange3 ve preset fail'leri kullanıcıyı zorluyor

---

### 🔴 B173 — uv env'inde Time Series (Deep Learning) Preset Yüklenmiyor (Linux)

**Sorun:** Linux'ta uv env oluşturup "Time Series (Deep Learning)" presetini kurmaya çalışınca install fail oluyor. Diğer presetler kontrol edilmedi, Windows'ta hiç test edilmedi.

**Reproduce:**
1. Linux (CachyOS/Pardus) → New Environment → Type: uv → Create
2. Packages → Presets → "Time Series (Deep Learning)" → Install
3. Hata mesajı al (terminal/log'a düşmeli)

**Yapılacaklar:**
- [ ] Hangi paket fail ediyor — log/stderr göster (B142 kapsamında verbose log lazım)
- [ ] Diğer presetleri uv env'inde test et (ML Basics, NLP, CV, Data Science vb.)
- [ ] Aynı testleri Windows'ta yap
- [ ] Aynı testleri venv (klasik) ve conda env'lerinde de yap — kıyaslama için
- [ ] uv özel davranışları araştır:
  - uv `--break-system-packages` istemiyor (kendi env'i)
  - PyTorch CUDA wheels için extra index URL gerekiyor olabilir (`--extra-index-url https://download.pytorch.org/whl/cu121`)
  - TensorFlow Linux'ta GLIBC sürümüne hassas
- [ ] `_PRESETS` dict'inde Time Series (DL) preseti incelensin (`src/utils/constants.py`)

**Muhtemel sebepler:**
- TensorFlow / PyTorch / Keras için Python sürümü uyumsuzluğu
- uv default `--no-deps` davranışı?
- darts / sktime gibi paketlerin geçici dep çakışması
- prophet derleme zorunluluğu (cmdstanpy + C++ compiler gerekiyor)

**İlgili dosyalar:**
- `src/utils/constants.py` — `_PRESETS` dict
- `src/core/venv_manager.py` — preset install
- `src/gui/package_panel.py` — Presets tab
- `src/core/pip_manager.py` — install command building

**Related:** F151 (conflict management) — bu bug F151 implementasyonuyla otomatik teşhis edilecek

**Öncelik:** 🔴 Yüksek — preset install'ın temel akışı kırık

---

### 🔴 F152 — SSL Verify Toggle (Paket Kurulumu + Env Oluşturma)

**Hedef:** Kullanıcı SSL doğrulamasını paket kurulumunda VE env oluşturma sırasında açıp kapatabilsin. Şirket içi proxy, MITM proxy, kendi imzalı sertifika kullanan ortamlarda kritik.

**Mevcut durum:**
- v1.4.15'te `--cert` ile sistem SSL eklendi (Windows EXE için)
- v1.4.50'de Check for Updates → urllib SSL fix yapıldı
- Ama kullanıcının "şu an SSL'i kapat/aç" diye toggle'ı yok

**Kapsam:**

**A) Settings → Network bölümü (yeni alt-bölüm)**
- ☐ "Disable SSL verification (insecure)" checkbox
  - Açıklama: "Use only on trusted networks (corporate proxy, self-signed certs). Insecure!"
  - Ⓘ Tooltip: PyPI'a `--trusted-host` ekleneceğini açıkla
- 📁 "Custom CA bundle path" (path picker — opsiyonel)
  - Açıklama: "Path to custom certificate file (PEM format)"
- 🌐 "Proxy" alanı (opsiyonel — HTTP_PROXY/HTTPS_PROXY env vars)
- Config keys:
  - `ssl_verify_disabled` (bool, default False)
  - `ssl_ca_bundle_path` (str, default "")
  - `http_proxy` (str), `https_proxy` (str)

**B) Env Oluşturma Dialog'u — SSL toggle**
- Env Create dialog → Advanced section → "SSL settings (optional)" expandable
- Settings'teki global ayarı override edebilen local toggle
- Bu env için kalıcı (env metadata'da saklanır — `~/.venvstudio/env_settings.json`)
- "Use global SSL settings" / "Disable for this env" / "Custom CA for this env"

**C) Install komutuna SSL flag inject**

| Tool | Disable SSL | Trusted Host | Custom CA |
|------|-------------|--------------|-----------|
| pip | `--trusted-host pypi.org --trusted-host files.pythonhosted.org` | ↑ aynı | `--cert /path/to/ca.pem` |
| uv | `--native-tls` (system) veya `--allow-insecure-host pypi.org` | ↑ | `SSL_CERT_FILE=/path` env var |
| poetry | `poetry config certificates.pypi.cert /path` | — | ↑ |
| pipx | `--pip-args="--trusted-host pypi.org"` | ↑ | ↑ |
| conda/micromamba | `--insecure` veya `ssl_verify: False` config | — | `ssl_verify: /path` |

**D) Env oluştururken de SSL gerekiyor**
- venv: Python `ensurepip` → `pip install setuptools wheel` çalışıyor → SSL gerekli
- uv: `uv venv` → Python download → `--native-tls` veya custom cert
- conda: micromamba download için SSL
- poetry: poetry kendi pip'i ile + cache server

**E) UI feedback**
- SSL kapalıyken statusbar'da uyarı: "⚠ SSL verification disabled"
- Install dialog'unda da görünmeli (ne ile kuracağız belli olsun)

**Dosyalar:**
- `src/gui/settings_advanced.py` veya yeni `src/gui/settings_network.py` — Network section
- `src/utils/constants.py` — config keys
- `src/core/pip_manager.py` — install komutuna SSL flag inject
- `src/core/venv_manager.py` — env create'te SSL flag inject
- `src/gui/env_dialog.py` — Advanced SSL toggle
- `src/utils/config_manager.py` — `ssl_verify_disabled`, `ssl_ca_bundle_path`, proxy keys

**Güvenlik notu:**
- Kullanıcı bilinçli olarak SSL'i kapatmalı — checkbox'ın yanında ⚠ uyarı
- Default değer her zaman: SSL **AÇIK**
- "Disable" seçilince onay dialog'u: "Are you sure? This is insecure on public networks."

**Öncelik:** 🟡 Orta — kurumsal kullanıcılar için elzem, bireysel için opsiyonel

---

### 🟡 F153 — Presets Paket Detay Hover/Click Bilgisi

**Hedef:** Presets tabında preset içindeki kütüphanelere tıklayınca / hover'da o kütüphane ile ilgili detay görünsün. Mevcut Package Info dialog'unun **üstünde / yanında** sade bir tooltip/info card.

**Hiyerarşi:**
1. **Hover (1 satır):** Paketin desc'i — "numpy: Numerical computing with N-dimensional arrays"
2. **Tek tık (info card):** Sağ panel veya inline expandable — desc + version range + linkler + install size estimate
3. **Çift tık veya "Details" butonu:** Mevcut Package Info dialog'u (zaten var — B171'de düzeltilecek Home/PyPI sorunu)

**Kapsam:**

**Görsel tasarım:**
- Preset card'ında paket listesi: `numpy, pandas, scikit-learn, ...` — şu an plain text
- Yeni: her paket adı **chip/badge** olur (clickable)
- Hover → tooltip: paket adı + 1 satır desc
- Tek tık → preset card altında **info row** açılır (slide animasyonu):
  - 📝 Desc (2-3 satır)
  - 🏷 Latest version (PyPI'dan lazy fetch)
  - 🔗 Linkler (PyPI, Docs, GitHub) — F74 launcher_links pattern'i
  - 📦 Install size (eğer cache'de varsa) — "~14 MB"
  - 🔍 "More details" butonu → mevcut Package Info dialog (B171 fix sonrası)

**Veri kaynağı:**
- `PACKAGE_CATALOG` (`src/utils/constants.py`) — desc, links zaten var
- F133 (Catalog Override) ile kullanıcı overrideleri de uygulanır
- Latest version → PyPI JSON API (lazy, cache'lenir)

**Dosyalar:**
- `src/gui/package_panel.py` — Presets tab → preset card render güncelle
- `src/gui/preset_card.py` — yeni custom widget olabilir (preset card'ı standalone widget'a böl)
- `src/utils/constants.py` — PACKAGE_CATALOG (mevcut)

**İlgili eski TODO'lar (BU MADDE TARAFINDAN BİRLEŞTİRİLDİ / GENİŞLETİLDİ):**
- F144 — Presets'te Paket Bilgi Penceresi (popup formatı önerilmişti — bu madde inline + popup'ı birleştiriyor)

**Hiyerarşi özet:**
```
Preset Card (ML Basics)
  ├─ [numpy] [pandas] [scikit-learn] ...  ← chip'ler
  │    ├─ hover → tooltip: "numpy: Numerical computing..."
  │    └─ click → expandable info row (desc + version + links + size)
  │         └─ "More details" → Package Info Dialog (mevcut, B171 fix sonrası)
```

**Öncelik:** 🟡 Orta — UX iyileştirmesi, mevcut akışı kırmaz

---

### 🔴 REFACTOR — Büyük Dosyaları Parçala (500+ satır)
Settings dosyaları gibi Mixin/modül pattern uygulanacak. Öncelik sırasına göre:

| Dosya | Satır | Hedef Bölünme |
|-------|-------|---------------|
| `src/gui/package_panel.py` | **4791** | `package_panel_launcher.py`, `package_panel_catalog.py`, `package_panel_install.py`, `package_panel_export.py` |
| `src/gui/main_window.py` | **2754** | `main_window_workers.py` (Worker thread'ler), `main_window_env.py` (env işlemleri), `main_window_learn.py` (learn akışı), `main_window_toolbar.py` (toolbar/sidebar) |
| `src/gui/learn_page.py` | **2051** | `learn_content.py` (LEARN_CATEGORIES verisi), `learn_page_renderer.py` (render), `learn_page_ui.py` (UI setup) |
| `src/core/venv_manager.py` | **1837** | `venv_manager_clone.py`, `venv_manager_rename.py`, `venv_manager_cache.py` |
| `src/gui/env_dialog.py` | **1538** | `env_dialog_conda.py`, `env_dialog_poetry.py`, `env_dialog_pipx.py` |
| `src/utils/i18n.py` | **1492** | Veri dosyası — `i18n_tr.py`, `i18n_en.py`, `i18n_de.py` vb. dillere böl |
| `src/gui/settings_toolchain.py` | **1286** | Zaten mixin — gerekirse `settings_toolchain_install.py` / `settings_toolchain_ui.py` |
| `src/utils/platform_utils.py` | **850** | `platform_utils_terminal.py`, `platform_utils_path.py` |
| `src/core/system_tools_installer.py` | **938** | `system_tools_linux.py`, `system_tools_windows.py`, `system_tools_macos.py` |

**Kural:** Her bölünmede mevcut dışa açık API (metod adları, import yolları) değişmez — sadece dosya içi organizasyon değişir. `__init__.py` re-export'ları güncellenir.



### 🧠 F130 — AI / ML AKADEMİSİ (Learn Sayfasına Derinlik)
**Hedef:** Çocukların bile anlayabileceği bir dille AI/ML kavramlarını görsel+interaktif anlatmak. Learn sayfasına yeni iki büyük bölüm eklenecek.

#### Bölüm A — "Yapay Zeka Nedir?" (Konseptler)
Her kavram bir topic card olur. Her kartta:
- 👶 **Çocuk Modu** açıklaması (analoji + günlük hayattan örnek)
- 🎓 **Detay** — teknik açıklama
- 📊 **Görsel** — inline SVG/Canvas animasyonu veya matplotlib statik grafik (snippet içinde çalıştırılabilir)
- 🧪 **Deneyin** — kullanıcı env'inde çalıştırabileceği mini kod
- 🔗 **Daha fazla** — kaynak linkleri (3Blue1Brown, StatQuest, Distill.pub)

**Konu listesi (25 kart):**
1. Yapay Zeka (AI) nedir? — "Bilgisayara insan gibi düşünmeyi öğretmek"
2. Makine Öğrenmesi (ML) — "Örneklerle öğrenme"
3. Derin Öğrenme (DL) — "Beyin taklit eden katmanlı öğrenme"
4. Sinir Ağı (Neural Network) — "Neuron benzeri düğümler zinciri"
5. Supervised Learning — "Öğretmenli öğrenme (cevap anahtarı var)"
6. Unsupervised Learning — "Öğretmensiz öğrenme (kendi grupla)"
7. Reinforcement Learning — "Ödül/ceza ile öğrenme (oyun oynayarak)"
8. Classification vs Regression — "Kategori vs sayı tahmini"
9. Clustering — "Benzer şeyleri gruplama"
10. Overfitting & Underfitting — "Ezberleme vs anlama"
11. Train/Val/Test split — "Ders, ara sınav, final"
12. Feature Engineering — "Doğru soruları sorma"
13. Loss Function — "Ne kadar yanlış olduğu"
14. Gradient Descent — "Eğimden aşağı yuvarlanma"
15. Backpropagation — "Hatayı geriye yayma"
16. Activation Functions — "Sinir hücresinin anahtarı" (ReLU, sigmoid, tanh görsel)
17. CNN (Convolutional NN) — "Resmi anlayan ağ"
18. RNN / LSTM — "Sırayı hatırlayan ağ"
19. Transformer & Attention — "Neye dikkat edeceğini öğrenen ağ"
20. Embedding — "Kelimeleri sayıya çevirme"
21. Transfer Learning — "Başkasının öğrendiğini kullanma"
22. Regularization (L1, L2, Dropout) — "Ezberlemeyi önleme"
23. Confusion Matrix & Metrics — "Doğru/yanlış haritası" (precision, recall, F1)
24. ROC & AUC — "Eşik ayarlama hikayesi"
25. GAN / Diffusion — "Görüntü üreten AI"

#### Bölüm B — "Temel Kütüphaneler" (Detaylı Rehberler)
Her kütüphane için uzun bir dedike sayfa. Mevcut tek-snippet formatını **genişlet**:
- Kütüphanenin **ne işe yaradığı** (1 paragraf + analoji)
- **Kurulum** komutları (env-type'a göre: pip, conda, uv)
- **5-10 alt konu**, her biri kod + görsel + çıktı
- **İleri seviye** tarifler (performans, best practices)
- **Ekosistem** — hangi diğer lib'lerle birlikte kullanılır
- **Gerçek dünya örneği** — mini proje önerisi

**20-30 kütüphane (öncelik sırası):**

*Veri Temelleri*
- NumPy — N-boyutlu array, broadcasting, linear algebra
- Pandas — DataFrame, groupby, merge, pivot
- Polars — Rust-powered, lazy evaluation

*Görselleştirme*
- Matplotlib — her şeyi çizmek
- Seaborn — istatistiksel güzel plotlar
- Plotly — interaktif, web için
- Bokeh — büyük veri interaktif
- Altair — grammar of graphics

*Klasik ML*
- Scikit-learn — hepsi (regression, classification, clustering, pipeline)
- XGBoost — gradient boosting kralı
- LightGBM — hızlı boosting
- CatBoost — categorical için

*Deep Learning*
- PyTorch — dinamik, araştırma
- TensorFlow / Keras — production
- JAX — autodiff + GPU
- Hugging Face Transformers — NLP ve öteki

*Spesifik*
- OpenCV — bilgisayarlı görü
- Pillow — görüntü işleme
- NLTK / spaCy — doğal dil
- Gensim — topic modeling, word2vec
- statsmodels — istatistik modelleri, ekonometri
- Prophet — zaman serisi
- Optuna — hyperparameter optimizasyon
- MLflow — model lifecycle
- Weights & Biases — deney takibi
- Streamlit — model demosu
- FastAPI — model serving
- LangChain — LLM aplikasyonları
- LlamaIndex — RAG

#### Teknik Gereksinimler
- [ ] Her topic card için **child_mode** ve **detail_mode** alanları şemaya eklenecek (mevcut `body` yanına)
- [ ] **Toggle switch** — "👶 Çocuk Modu / 🎓 Detay" card başlığında
- [ ] **Inline matplotlib** — `exec_in_env` butonu: topic kartından seçili env'de snippet çalıştırıp SVG/PNG output'u kart altında göster
- [ ] **Animasyonlu SVG** — gradient descent, neural network forward pass, attention pattern için hazır SVG'ler
- [ ] **Search bar** — "hangi kavramı öğrenmek istiyorsun?" — cross-category arama
- [ ] **Progress tracking** — "26 / 50 kavram tamamlandı" — kullanıcının okuduğu kartları işaretle (opsiyonel, config'de sakla)
- [ ] **Türkçe/İngilizce çeviri** — kavramların iki dilli açıklaması (tr_body, en_body)
- [ ] Mini **quiz** her kategori sonunda — "3 soru: hangisi supervised learning örneğidir?"
- [ ] **Linkler** — her konu için resmi doc + YouTube video + Distill.pub makale

#### Dosya Yapısı
- `src/gui/learn_page.py` → sadece UI + LEARN_CATEGORIES referansı
- `src/gui/learn_content/` → YENİ DİZİN:
  - `ai_concepts.py` — 25 kavram kartı
  - `libs_data.py` — NumPy/Pandas/Polars
  - `libs_viz.py` — Matplotlib/Seaborn/Plotly/Bokeh/Altair
  - `libs_ml.py` — Scikit-learn/XGBoost/LightGBM/CatBoost
  - `libs_dl.py` — PyTorch/TF/JAX/HuggingFace
  - `libs_cv_nlp.py` — OpenCV/Pillow/NLTK/spaCy/Gensim
  - `libs_misc.py` — statsmodels/Prophet/Optuna/MLflow/W&B
  - `libs_serve.py` — Streamlit/FastAPI/LangChain/LlamaIndex
  - `assets/svg/` — animasyonlu SVG'ler (gradient descent, NN, attention vs.)

#### Yol Haritası
- **v1.4.6X** — `learn_content/` dizini + ai_concepts.py (25 kavram, çocuk modu + detay, statik görseller)
- **v1.4.6X+1** — libs_data/viz/ml (ilk 10 kütüphane detaylı)
- **v1.4.6X+2** — libs_dl + libs_cv_nlp (DL + spesifik)
- **v1.4.6X+3** — exec_in_env butonu (snippet çalıştır, çıktı göster)
- **v1.4.6X+4** — Search bar + progress tracking + quiz
- **v1.4.6X+5** — TR çeviri + animasyonlu SVG'ler

---

## 🆕 YENİ TOPLANAN NOTLAR (v1.4.62 sonrası)

### 🐛 B138 — Windows EXE'de başlangıçta terminal yanıp sönüyor
- Form yüklenince **3-5 kez terminal penceresi** açılıp kayboluyor (flash)
- `subprocess.Popen/run` çağrıları `CREATE_NO_WINDOW` flag'i eksik
- `settings_page.py`'deki PowerShell scan için B96'da düzeltilmişti, ama başka yerlerde kalmış
- **Çözüm:** Tüm subprocess çağrılarına `subprocess_args()` (platform_utils) kullanılmasını zorla — Windows'ta otomatik `CREATE_NO_WINDOW` ekliyor
- Grep: `subprocess.run(` / `subprocess.Popen(` / `_run(` → `subprocess_args(**kwargs)` ile sarılmamış olanları bul ve düzelt

### ✅ F131 — Sağ Click → Open Folder (TAMAMLANDI v1.4.63)
- [x] Context menu'ya "📁 Open Folder" action eklendi
- [x] `platform_utils.open_folder()` — Windows (explorer), macOS (open -R), Linux (xdg-open + fallbacks: gio, nautilus, dolphin, thunar, pcmanfm, nemo, caja)
- [x] Gerçek env path kullanılıyor (pipx/poetry dahil)
- [x] AppImage env temizlemesi Linux'ta

### 🐛 B139 — Open Terminal GNOME'da çalışmadı (openSUSE)
- `platform_utils.py::open_terminal_at` — GNOME terminal açılmadı openSUSE'de
- `gnome-terminal`'un çağırma argümanları dağıtıma göre farklı olabilir
- **Çözüm:** `--` vs `-e` vs `-x` combinations dene; başarısız olursa otomatik bir sonraki terminal'e fallback yap (zaten var ama gnome-terminal başarılı sayılıp hata veriyor olabilir)
- Log: Popen.returncode kontrol et, sessiz fail olmasın

### ✅ F132 — Python Download: Mirror Seçimi (TAMAMLANDI v1.4.63)
- [x] Astral (python-build-standalone) — varsayılan, önerilen
- [x] GitHub Releases (direkt) — Astral ile aynı data, alternatif label
- [x] python.org — resmi kaynak. Linux/macOS source tarball, Windows .exe installer
- [x] SourceForge — placeholder (şu an "Custom URL kullanın" yönlendirmesi, ileride doldurulabilir)
- [x] Custom URL — kullanıcı kendi download URL'ini yapıştırır
- [x] Mirror dropdown + description satırı + custom URL input (sadece Custom seçilince görünür)
- [x] Refetch butonu (🔄)
- [x] Seçilen mirror Config'e kaydediliyor (`python_download_mirror`, `python_download_custom_url`)
- [x] Otomatik fallback (Astral → GitHub → python.org)
- [x] Strategy pattern: her mirror `MirrorBackend` sınıfından türer
- [x] Windows'ta python.org .exe/.msi indirilir ama otomatik install yapılmaz — kullanıcı manuel çalıştırır

### ✨ F133 — Catalog Override (Settings)
- Kütüphanelerin description ve linklerini kullanıcı değiştirebilsin
- Settings altında yeni sekme: **"📦 Package Catalog"** 
- Her paket için: description, website, docs, GitHub, YouTube alanları düzenlenebilir
- Override'lar `~/.config/VenvStudio/catalog_overrides.json`'a yazılır
- Reset butonu → default'lara dön
- `package_panel.py` ve `learn_page.py` catalog'u okurken önce override kontrol eder

### 🐛 B140 — Fedora 43 + Qt 6.11'de Emoji/İkonlar Render Edilemiyor (AÇIK, ERTELENDİ)

**Status**: Önceki v1.4.64'teki "fix" revert edildi — çalışmadı, ayrıca tüm platformlarda font rendering'i bozdu. v1.4.65 main.py ile eski (original) haline döndürüldü.

**Etkilenen sistem** (teşhis edilen):
- Fedora 43 (kernel 6.19.12)
- PySide6: 6.11.0 / Qt: 6.11.0
- Python: 3.14.3

**CachyOS (Arch) ile çalışıyor, Windows OK** — sorun Fedora'ya özgü.

#### Teşhis özetı

1. **Font kurulu** — `fc-list` hem `Noto-COLRv1.ttf: Noto Color Emoji` hem `NotoEmoji-Regular.ttf: Noto Emoji` gösteriyor
2. **fontconfig yanlış font seçiyordu** — `fc-match "sans-serif:charset=1F680"` eskiden `Symbola.ttf` dönüyordu. `sudo dnf remove gdouros-symbola-fonts` + `rm -rf ~/.cache/fontconfig && fc-cache -fv` sonrası artık `Noto-COLRv1.ttf` dönüyor ✅
3. **Ama Qt hala emoji çizemiyor** — `QLabel("TEST: 🔄 ⭐ 📁")` + `QFont("Noto Color Emoji", 24)` ile test penceresi açıldı; "TEST:" görünüyor, emoji'ler boş/kutu
4. **Kök neden muhtemelen**: PySide6 6.11'in Fedora build'i **COLRv1 color emoji glyph** render etmiyor. Fedora sadece COLRv1 paketliyor (COLRv0/CBDT yok). Qt eski emoji rendering backend'i bu yeni formatı henüz desteklemiyor olabilir.
5. **İndirmiş olduğumuz CBDT versiyonu da işe yaramadı** — `~/.local/share/fonts/NotoColorEmoji_CBDT.ttf` yüklendikten sonra `fc-match` hala system COLRv1'i dönüyor (ismi aynı olduğu için sistem öncelikli). `fc-scan` ile family kontrolü yapılmadı.

#### Sonraki oturumda denenecek yaklaşımlar

**Yaklaşım 1: Unicode sembol sadeleştirme (önerilen, en güvenli)**
- VenvStudio'daki renkli emoji ikonları (`📦 🔄 ⭐ 📁 ⚙ 🐍`) **tek-renk Unicode sembollere** değiştirilsin:
  - 📦 → ◼ veya ▣
  - 🔄 → ↻
  - ⭐ → ★
  - 📁 → ▤
  - ⚙ → ⚙ (zaten Unicode sembol)
  - 🐍 → Py (metin)
  - ✅ → ✓
  - ❌ → ✗
  - ▶ → zaten çalışıyor
- Test et: Qt basit Unicode sembolleri her sistemde render eder. `▶ ● ■ □ ◆ ★ ✓ ✗` gibi karakterler DejaVu Sans / Noto Sans'ta var.
- Dosyalar: `main_window.py`, `package_panel.py`, `env_dialog.py`, `learn_page.py`, `settings_*.py` — tüm stylesheet/label/button text'leri gözden geçirilip emoji → sembol değişimi yapılır.
- Avantaj: Tüm platformlarda garantili çalışır, cross-platform, font-free.
- Dezavantaj: Renkli emoji'lerin estetik kaybı (Windows/macOS/CachyOS şu an güzel görünüyordu).

**Yaklaşım 2: Font fallback tablosu (riskli, daha önce bozdu)**
- `QFont.setFamilies([...])` ile family chain kurmak — **daha önce yapıldı, tüm platformlarda font'ları bozdu, revert edildi**. Bir daha yapılırsa çok dikkatli test edilmeli, özellikle CachyOS ve Windows'ta.

**Yaklaşım 3: Embed emoji font (orta)**
- CBDT formatlı Noto Color Emoji'yi **uygulama içine embed** et (`QFontDatabase.addApplicationFont(path)`)
- Resources (`.qrc`) olarak paketlenir, sistem font'larına dokunmaz
- Qt `addApplicationFont()` yüklenen font'a benzersiz family name verir → çakışma olmaz
- Ama yine de Fedora'nın COLRv1 render bug'ı varsa embed eden COLRv0 yükler, Qt onu da renderleyememişse işe yaramaz

**Yaklaşım 4: İkonları SVG olarak paketle (büyük refactor)**
- Emoji kullanımını tamamen bırak, SVG icon set'e geç (Fluent UI, Lucide, Material Symbols gibi)
- Her button/label'da `QIcon` kullan, text'e emoji gömme
- En profesyonel çözüm ama büyük refactor — 100+ yer değişecek

**Yaklaşım 5: Qt runtime env var**
- `QT_HARFBUZZ=old` veya `QT_ENABLE_COLOR_FONTS=1` gibi env var'lar test edilmeli (Fedora Qt build'inin flags'larına göre çalışabilir/çalışmaz)

#### Test komutu (hangi yaklaşım çalıştığını anlamak için)

```python
# Fedora'da çalıştır — Unicode sembol rendering test
python -c "
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QFont
import sys
app = QApplication(sys.argv)

# Renkli emoji
lbl1 = QLabel('Emoji: 🔄 ⭐ 📁')
lbl1.setFont(QFont('Noto Sans', 24))
lbl1.show()

# Unicode semboller (renkli değil)
lbl2 = QLabel('Symbols: ↻ ★ ▤ ⚙ ✓ ✗')
lbl2.setFont(QFont('Noto Sans', 24))
lbl2.show()

app.exec()
"
```
Eğer Fedora'da ikinci pencere (semboller) görünüyorsa, **Yaklaşım 1** kesin çözüm. İkisi de görünmüyorsa Qt'nin kendisiyle derin bir sorun var.

#### Geçici workaround (kullanıcı için manuel)
Fedora kullanıcısı şimdilik:
1. `sudo dnf remove gdouros-symbola-fonts`
2. `sudo dnf install -y twitter-twemoji-fonts` (monokrom SVG emoji font dener)
3. `rm -rf ~/.cache/fontconfig && fc-cache -fv`

#### Dosya yerleri
- `main.py` — font setup (şu an **original v1.4.65 hali, dokunulmamış**, doğrudan Segoe UI set ediyor; Fedora spesifik hiçbir kod yok)
- `src/utils/platform_utils.py` — `get_platform()` var, `_detect_linux_distro()` eklenebilir

---

### ✨ F134 — İlk Kurulum Sihirbazı (Welcome Wizard)
- İlk çalıştırmada wizard açılsın → sistem kontrolleri + gerekli paketleri kur
- **Linux adımları:**
  1. `python-is-python3` paketi var mı? Yoksa kur
  2. `python3-virtualenv` / `python-virtualenv` var mı?
  3. `python3-pip` / `python-pip` var mı?
  4. İkon teması (Fedora/openSUSE için)
  5. Terminal emülatörü (gnome-terminal / konsole / xterm)
- **macOS adımları:**
  1. Xcode Command Line Tools (`xcode-select -p`)
  2. Homebrew opsiyonel
- **Windows adımları:**
  1. Python.org / Microsoft Store Python kontrol
  2. Windows Terminal opsiyonel (eski: cmd)
- Distro-aware paket yöneticisi komutları (apt/dnf/pacman/zypper)
- **"Skip All"** butonu — wizard tekrar açılmasın (`welcome_shown` config)
- Settings altında "🧙 Run Setup Wizard Again" butonu

### ✅ F135 — Terminal Log Mirror (KISMEN TAMAMLANDI v1.4.62+)
- [x] TTY tespit edilirse console handler otomatik açılır
- [x] `_run()` wrapper her subprocess çağrısını loglar (▶ cmd + exit code)
- [x] create/delete/clone/rename/display_name — INFO level giriş log'ları
- [x] `VENVSTUDIO_QUIET=1` ile opt-out
- [x] Global `sys.excepthook` + `threading.excepthook` (B137 için)
- [ ] Settings altında "Show commands in console" GUI toggle
- [ ] `--verbose` / `--quiet` CLI flag'leri
- [ ] package_panel.py, settings_*.py, env_dialog.py da logger ile donatılacak (şu an sadece core + main_window)
- [ ] Terminal log'larda renkli output (Rich ile) — hata/uyarı ayırt edilsin

### ✨ F136 — Python Temel Dersleri (Learn'e ek)
Learn sayfasına yeni kategori: **"🐍 Python Temelleri"** — F130'un önünde yer almalı (yeni başlayanlar için)
- [ ] Değişkenler, veri tipleri (int, float, str, bool, None)
- [ ] Listeler, tuple, dict, set — ne zaman hangisi
- [ ] Fonksiyonlar, *args, **kwargs, default/keyword arguments
- [ ] Kontrol akışı: if/elif/else, for, while, match-case
- [ ] List/dict/set comprehensions
- [ ] Lambda, map, filter, reduce
- [ ] Decorator'lar (basit örnekler)
- [ ] Context manager (with statement) ve generator (yield)
- [ ] Sınıflar, inheritance, dunder methods
- [ ] Exception handling (try/except/finally/else)
- [ ] Dosya I/O (open, pathlib, json, csv)
- [ ] Modüller, paketler, `__init__.py`, relative vs absolute imports
- [ ] Type hints (typing modülü, Optional, List, Dict, Callable)
- [ ] async/await temelleri
- [ ] Python'un iç işleyişi: GIL, reference counting, garbage collection
- Her konsept 👶 çocuk modu + 🎓 detay + interaktif snippet ile anlatılacak
- Hedef: Programlamaya hiç başlamamış biri bile bu kategoriyi bitirip F130'a geçebilmeli

### ✨ F137 — İstatistik & Matematik Dersleri (Learn'e ek)
Data Science ve ML'in matematik temellerini anlatan ayrı kategori: **"📐 Matematik & İstatistik"**
- [ ] **İstatistik:**
  - Merkezi eğilim (ortalama, medyan, mod)
  - Dağılım (varyans, standart sapma, IQR)
  - Korelasyon vs nedensellik
  - Hipotez testi (t-test, chi-square, ANOVA)
  - p-değeri nedir, ne değildir
  - Güven aralığı, örneklem büyüklüğü
  - Bayesian vs frequentist yaklaşım
  - Dağılımlar: Normal, Binomial, Poisson, Exponential (görsel!)
  - Central Limit Theorem (simülasyon ile)
- [ ] **Doğrusal Cebir:**
  - Vektör, matris, matris çarpımı
  - Öz değer / öz vektör — görsel (PCA'nın temeli)
  - Transpoz, determinant, ters matris
  - Dot product, cross product (geometrik anlam)
  - Norm (L1, L2, infinity)
- [ ] **Kalkülüs:**
  - Türev — eğim, değişim hızı (gradient descent'in temeli)
  - Integral — altında kalan alan, kümülatif
  - Kısmi türev — çok değişkenli fonksiyonlar için
  - Chain rule — backpropagation'ın kalbi
- [ ] **Olasılık:**
  - Koşullu olasılık, Bayes teoremi
  - Bağımsız olaylar, Markov property
  - Beklenen değer
  - Entropy ve cross-entropy (loss function için)
- [ ] **Optimizasyon:**
  - Convex vs non-convex problems
  - Gradient descent varyantları (SGD, Adam, RMSprop — görsel animasyon)
  - Learning rate, momentum
- Her konu: SymPy + NumPy + matplotlib görsel, interaktif slider'lar (Streamlit / ipywidgets), çocuk modu analojileri

### ✨ F138 — Visualization Detaylı Kategori (Learn'e ek)
F130'da kısaca geçiyor, ayrı bir büyük kategori olsun: **"📊 Görselleştirme Atölyesi"**
- [ ] **Matplotlib** — temelden ileri:
  - figure, axes, subplot anatomi
  - Line, scatter, bar, histogram, heatmap, contour, 3D surface
  - Stil (rcParams, style sheets, seaborn-style)
  - Twin axes, colorbars, legends
  - Animasyon (FuncAnimation)
  - Kaydetme: PNG vs SVG vs PDF, dpi, transparent
- [ ] **Seaborn** — istatistik için:
  - distplot, kdeplot, violinplot, boxplot, stripplot, swarmplot
  - pairplot, jointplot, heatmap, clustermap
  - FacetGrid, catplot
  - Color palettes (categorical, sequential, diverging)
- [ ] **Plotly** — interaktif:
  - Express vs Graph Objects
  - Scatter, line, bar, pie, sunburst, treemap
  - 3D: scatter_3d, surface, mesh3d
  - Geo: choropleth, scatter_geo, scatter_mapbox
  - Dashboards: Dash framework örneği
  - Animation frames (time series için)
- [ ] **Bokeh** — büyük veri + web:
  - ColumnDataSource, tools, HoverTool
  - LinkedBrushing, LinkedAxes
  - Server apps
- [ ] **Altair** — Grammar of Graphics (declarative):
  - Vega-Lite tabanlı
  - Encoding channels (x, y, color, size, shape)
  - Compound charts: layer, concat, repeat, facet
- [ ] **PyVista / VTK** — 3D scientific viz:
  - Volume rendering
  - Mesh visualization
  - CFD/FEM sonuçları
- [ ] **Networkx + plotly/pyvis** — graph visualization
- [ ] **Holoviews + DataShader** — çok büyük veri (milyarlarca nokta)
- Her kütüphane için:
  - Hangi durumda tercih edilir (karar ağacı)
  - 5-10 "gallery" örneği — tam çalışan kod + çıktı
  - Performans ipuçları
  - Kitap önerileri (Fundamentals of Data Viz, Storytelling with Data)

### ✅ F139 — Learn'den Install Yaparken Env Sorusu (TAMAMLANDI v1.4.66)
- [x] `src/gui/learn_install_dialog.py` — yeni `LearnInstallDialog` widget
- [x] Dialog içinde:
  - Radio: Current selected env (varsa, default olarak işaretli)
  - Radio: Default env (varsa ve current'tan farklıysa)
  - Radio: Dropdown'dan tüm env'lerden seç (env name + type + Python version gösterir)
  - Radio: Yeni env oluştur (inline name input, validasyon: boşluk/path separator/duplicate yok)
  - Radio: pipx install (sadece paket pipx-friendly ise görünür — streamlit, httpie, black, ruff, jupyter vb.)
- [x] pipx-friendly tespit: `_PIPX_FRIENDLY` set (24+ common CLI tool)
- [x] Paket listesi tepede yeşil monospace font ile gösteriliyor, 6+ ise "+ N more" şeklinde kısaltılıyor
- [x] "Switch to Packages tab after install" checkbox (default: açık)
- [x] Cancel + Install butonları, Catppuccin-style
- [x] `main_window.py::_on_learn_install` refactored:
  - Env listesini topluyor (type + python version dahil)
  - Dialog'u açıyor
  - `_perform_learn_install` → decision mode'a göre: MODE_EXISTING / MODE_NEW_VENV / MODE_PIPX
  - MODE_NEW_VENV → önce env oluştur, sonra packages yükle
  - MODE_PIPX → package_panel'in pipx handler'ına delege et

### ✅ B147 — Terminal Banner Görünümü Bozuk + Env Tipi Tutarsızlığı (TAMAMLANDI v1.4.68)
- [x] `logger.py` — `_visual_width()` helper eklendi (emoji=2 cell, CJK=2 cell, ZWJ/VS16/combining=0)
- [x] `banner()` ANSI fallback path'te `len()` → `_visual_width()` değiştirildi
- [x] `env_dialog.py` — conda create (`_do_conda_create` öncesi + `_on_conda_done`)
- [x] `env_dialog.py` — uv/poetry/pipx create (`_do_alt_create` öncesi + `_on_alt_done`)
- Artık tüm env tipleri için banner_start/success/error terminal'de gözüküyor ve sağ kenar hizalı

### ✅ B158 — Open Folder Context Menu Kaybı + subprocess_args Import Hatası (TAMAMLANDI v1.4.71)
- **Kayıp 1**: v1.4.69 push sırasında `main_window.py`'de "📁 Open Folder" context menu action yanlışlıkla silindi (e409244 commit'indeki kod sonraki rewrite'larda kayboldu)
- **Fix**: e409244 commit'inden kod geri alındı:
  - Context menu'ye "📁 Open Folder" QAction (Open Terminal'dan sonra)
  - Yeni `_open_env_folder()` method — `platform_utils.open_folder()` çağırıyor
  - `_open_package_manager` ve `_open_terminal` real_path sync (pipx/poetry gerçek path için)
- **Hata 2**: v1.4.69 startup'ta `NameError: name 'subprocess_args' is not defined` — `_check_linux_venv_module` fonksiyonunda `subprocess_args` kullanıyordu ama import eksikti
- **Fix**: `_check_linux_venv_module` fonksiyonu içine `from src.utils.platform_utils import subprocess_args` eklendi
- **Dosya**: `src/gui/main_window.py`

### ✅ B157 — Linux venv Detection Yanlış Distro + Yanlış Paket Önerisi (TAMAMLANDI v1.4.69)
- **Sorun**: CachyOS'ta VenvStudio "python3-venv missing" popup'ı gösterdi — ama zaten vardı
- **3 ayrı hata bir arada**:
  1. **Detection hatalı**: `subprocess.run(["python3", ...])` çağrılıyor. Arch/CachyOS'ta `/usr/bin/python3` symlink'i olmayabilir, sadece `/usr/bin/python` var. FileNotFoundError → popup tetikleniyor
  2. **Yanlış install komutu**: Distro ne olursa olsun `sudo apt-get install python3-venv` deniyor (CachyOS'ta apt yok tabii)
  3. **Yanlış manual instructions**: `sudo pacman -S python-virtualenv` öneriyordu — Arch'ta venv zaten `python` paketinin içinde, ayrı paket yok
- **Fix**:
  - `shutil.which("python3") or shutil.which("python")` ile doğru executable bulunuyor
  - `_detect_linux_distro()` helper'ı eklendi — `/etc/os-release` okuyup ID ve ID_LIKE alanlarına bakıyor
  - Distro-aware install komutu:
    - **Arch family** (arch, cachyos, manjaro, endeavouros): `pacman -S --needed python` (venv zaten içinde)
    - **Fedora family** (fedora, rhel, centos): `dnf install python3-virtualenv`
    - **openSUSE**: `zypper install python3-virtualenv`
    - **Debian family** (debian, ubuntu, pardus, mint): `apt install python3-venv`
    - **Fallback**: PATH'te hangi package manager varsa onu kullan
  - Manual instructions mesajı da distro-aware
  - `apt-get` yerine `apt` kullanılıyor (modern Debian/Ubuntu)
- **Dosya**: `src/gui/main_window.py::_check_linux_venv_module` + yeni `_detect_linux_distro` helper

### ✅ B149 — venv create exit=1 stderr='' olunca boş error mesajı (TAMAMLANDI v1.4.68)
- Debian 13 (ve başka sistemlerde de olabilir): `python3 -m venv /path` komutu exit=1 döndürüyor ama **stderr boş**, hata mesajı stdout'a gidiyor
- Sonuç: UI'da "Failed to create environment:" kutusu açılıyor, yanında hiçbir şey yok — kullanıcı ne olduğunu anlayamıyor
- **Sebep**: `venv_manager.py::create_venv` sadece `result.stderr`'i kontrol ediyor ve gösteriyordu; stdout atılıyordu
- **Fix**:
  - Hata detection: `_combined = stderr + "\n" + stdout` — iki stream'i birleştir
  - Hata mesaj gösterme: `_combined` içeriği göster, her iki stream'i de dahil et
  - `"python3-venv"` ve `"ensurepip is not available"` substring'leri detection'a eklendi (yeni varyasyonları tetiklesinler)
  - Fallback error mesajı: eğer stdout+stderr tamamen boşsa, failure komutu ve platform-specific ipuçları göster (Debian apt, Windows Store alias, macOS xcode-select)
- Artık kullanıcı tam olarak ne hata olduğunu görecek, hangi platforma göre ne yapacağını bilecek

### 🐛 B148 — Poetry Env Oluştururken Random Suffix Eklenir
- Kullanıcı env adı "pppp" girer → Poetry `pppp-GwxGrfX--py3.14` klasörü oluşturur
- Environments tablosunda `pppp-GwxGrfX` görünür, kullanıcı şaşırır
- **Sebep**: `poetry new <name>` + `poetry install` Poetry'nin varsayılan venv isolation davranışı — kendi hash-based suffix ekler (`POETRY_VIRTUALENVS_PATH`'de `.cache/pypoetry/virtualenvs/<name>-<hash>-py<ver>`)
- **Çözüm seçenekleri**:
  - **A) Display name override** (önerilen): `.venvstudio_env` marker dosyasında `"display_name": "pppp"` tut, tabloda onu göster, Path sütununda gerçek path'i göster. Silme/kopyala operasyonlarında gerçek path kullanılır.
  - **B) `POETRY_VIRTUALENVS_IN_PROJECT=true` env var** ile Poetry'yi `<project>/.venv` kullanmaya zorla, suffix oluşturmasın. Ama bu global ayar, diğer Poetry projelerini etkiler. İsolation da kaybolur.
  - **C) Yarın A+B hibrit**: Sadece VenvStudio'nun oluşturduğu env'ler için `POETRY_VIRTUALENVS_PATH=<venvstudio_dir>/<name>` ayarla, subprocess'e pass et
- **Öncelik**: Orta — kullanıcıyı confuse ediyor ama işlevsel hata değil
- **Etkilenen dosya**: `env_dialog.py` (_do_alt_create içindeki poetry bloğu), `venv_manager.py` (list_venvs — display_name okumalı), main_window table render

### ✅ B150 — VenvStudio Sürekli Çöküyor (ÇÖZÜLDÜ — v1.4.67)
- Crash log analizi sonucu tüm crash'ler aynı hatayı gösteriyordu:
  ```
  File "settings_page.py", line 920, in _register_editor
      venv_dir = VenvManager().base_dir
  TypeError: VenvManager.__init__() missing 1 required positional argument: 'base_dir'
  ```
- En son crash: **2026-04-18 08:30** (v1.4.66)
- Bu hata v1.4.67'de düzeltildi (`_get_editor_venv_dir()` helper eklendi, `VenvManager()` parametresiz çağrılmıyor artık)
- v1.4.67 ve v1.4.68 ile kullanımda **yeni crash oluşmadı** (24 Nisan test edildi)
- `%appdata%/VenvStudio` silmenin çözüm olarak görünmesi aslında tesadüf değil — eski config'te bir şey yoktu, sadece zamanla yeni sürüme geçilince hatalar kayboldu
- **Kapatıldı — reproduce edilemiyor**

### ✅ B151 — Windows EXE Subprocess Terminal Flash (TAMAMLANDI v1.4.69)
- Windows'ta uygulama açılırken bir sürü siyah terminal penceresi flash ediyordu
- **Sebep**: `logger.logged_subprocess` wrapper + `platform_utils` pipx/mamba probe'ları + `main_window` pip list thread + `env_dialog` Python version probe hepsi `CREATE_NO_WINDOW` flag'siz subprocess çağırıyordu
- **Fix** — 4 dosyada toplam 9 noktada `subprocess_args()` helper veya inline `creationflags=0x08000000`:
  - `logger.py::logged_subprocess` — Windows'ta CREATE_NO_WINDOW flag'ı ekleniyor (`sys` import + conditional kwarg). **En kritik fix** — birçok subprocess bundan geçer.
  - `platform_utils.py` — `get_pipx_executable` (`-m pipx --version`), `get_pipx_home` (`pipx environment`), mamba shell init (×2 cmd.exe + powershell) subprocess_args'a sarıldı
  - `main_window.py` — pip list background thread + python3 -m venv --help check subprocess_args ile sarıldı
  - `env_dialog.py` — Python version probe (dialog her açıldığında), Windows pip install --user branch'ı subprocess_args ile sarıldı; modül seviyesinde import eklendi
- **Dokunulmayanlar** (kasıtlı):
  - `open_terminal_at` Popen çağrıları — kullanıcı terminal açmak istiyor, flash kapatmak istemediği yer
  - Linux-only gnome-terminal/konsole/xfce4-terminal Popen çağrıları — Linux'ta creationflags ignore ediliyor
  - `main.py` 6 subprocess — `if sys.platform == "linux"` guard altında, Windows'ta asla çalışmıyor
  - Kalan env_dialog subprocess'leri — Linux apt/pacman/dnf/zypper komutları (`sudo` kullanan, Windows'ta etkisiz)
- **Test**: Windows EXE açılışında subprocess flash sayısı minimum olmalı artık
- **Dosya**: `src/utils/logger.py`, `src/utils/platform_utils.py`, `src/gui/main_window.py`, `src/gui/env_dialog.py`

### 🟡 B156 — Windows EXE Startup Latency (B151 sonrası kalan)
- B151 terminal flash'ı düzeltti ama **startup latency** (EXE açılır açılmaz gelen kasılma) kalabilir
- Splash screen yok — kullanıcı boşluğa bakıyor
- Heavy imports (PySide6, pandas-like modüller) startup'ta senkron yükleniyor
- **Çözüm önerileri**:
  - Splash screen (QSplashScreen) — logo + "Loading..." progress
  - Lazy load: Settings, Learn sayfası ilk tıklandığında yüklensin (QTimer.singleShot(0, ...))
  - Paralel startup probes: `concurrent.futures.ThreadPoolExecutor(max_workers=4)` ile Python detection, pipx detection, tool detection eş zamanlı
  - `main.py` içinde import sırasını optimize et — PySide sadece Qt lazım olunca gelsin
- **Dosya**: `main.py`, `src/gui/main_window.py` (lazy page setup), potansiyel yeni: `src/gui/splash_screen.py`
- **Öncelik**: Orta — B151 flash fix sonra test edip kalan latency hissini ölç

### 🟡 B152 — Fedora Linux Terminalde Emojiler OK, VenvStudio'da Görünmüyor
- Fedora 43'te terminal'de emoji çıkıyor (Noto Color Emoji kurulu)
- Aynı sistemde VenvStudio GUI'sinde emoji kutu olarak görünüyor
- **Related**: B140 — aynı sorun, Qt 6.11 + Fedora PySide6 build'i COLRv1 renderleyemiyor
- B140 altında detaylı dokümantasyon var, 5 çözüm önerisi mevcut
- **Öncelik**: Düşük — CachyOS, Windows, diğer Linux'lar OK

### 🔴 B153 — SUSE Linux: env Yaratıldıktan Sonra Çöküyor
- openSUSE'de bir env oluşturulduktan sonra VenvStudio çöküyor
- Log lazım — env create sonrası hangi callback/refresh çağrısı crash ediyor
- **Araştırılacak**:
  - `python main.py 2>&1 | tee /tmp/suse.log` ile terminal çıktısı
  - Crash sonrası log kontrol
  - `_refresh_env_list` veya `_on_env_selected` içinde SUSE-spesifik path/glob sorunu olabilir
- **Muhtemel sebep**: openSUSE'nin alternatif Python path'leri (`/usr/lib64/python3.x`), glob pattern'ı uyumsuz

### 🟡 B154 — Bazı Editör "Yüklü" Gösteriliyor Ama Aslında Kaldırılmış
- Editor Integration panelinde (v1.4.67) bazı editörler "● Installed" gösterilirken aslında sistemden uninstall edilmiş
- **Sebep**: `detect_editors()` fonksiyonu iki kriterle kontrol ediyor:
  - Binary PATH'te var mı
  - Config dir (örn. `~/.config/Code/`) var mı
- Kullanıcı editörü kaldırsa bile config dir kalıyor — detection "installed" diyor
- **Çözüm**:
  - Sadece binary kontrolü yeterli olabilir (config dir opsiyonel)
  - Veya: her ikisi de gerekli → config dir varsa binary'yi de zorunlu kıl
  - "Config orphan" durumu için özel ikon: "○ Config exists but binary missing"
- **Dosya**: `src/core/editor_integration.py::detect_editors`

### ✅ B155 — Terminal'den Başlatıldığında Ctrl+C / Ctrl+D VenvStudio'yu Kapatmıyor (TAMAMLANDI v1.4.71)
- `python main.py` ile başlatıldığında Ctrl+C veya Ctrl+D tuşu terminal'de etkisizdi — Qt event loop Python sinyalini yakalamıyordu
- **Fix** — `main.py`'de `QApplication` oluşturulduktan hemen sonra:
  - `signal.signal(SIGINT, lambda *_: app.quit())` — Ctrl+C QApplication.quit tetikler
  - `signal.signal(SIGTERM, lambda *_: app.quit())` — bonus: `kill <pid>` de çalışır
  - QTimer noop hack (200ms interval) — Qt event loop Python yorumlayıcısına periyodik kontrol şansı verir, sinyal gecikmesini önler
  - Main thread değilse (embedded) sessizce atla (ValueError/OSError try/except)
- Terminal'den başlatanlar için klasik Qt/Python problemi çözümü

---

### ✨ F141 — First-Run Kurulum Sihirbazı (Paket Bağımlılıkları)
- VenvStudio ilk açılışta tüm sistemlerde gerekli paketleri yüklemek için soracak
- **Linux**:
  - `python-is-python3` (Debian/Ubuntu'da çoğu script `python` bekler)
  - `python3-venv`, `python3.X-venv` (tüm yüklü Python versiyonları için)
  - `python3-pip`
  - `python3-virtualenv` (opsiyonel)
  - İkon teması (Adwaita/Papirus/Breeze)
  - Terminal emulator check
- **macOS**: Xcode Command Line Tools kontrolü (`xcode-select --install`)
- **Windows**: python.org check — Store alias uyarısı, Python yoksa indir butonu
- **Tüm sistemler**: Python yüklü değilse Python indirmek için soracak (exe, appimage installer'ı bile dahil)
- Kutucuklu check listesi, "Hepsini Kur" / "Seç" / "Atla" butonları
- `~/.venvstudio/first_run_completed` marker dosyası ile bir kez çalıştır
- **F134** ile aynı konsept — birleştirilebilir

### ✨ F142 — VenvStudio'nun Kendi Gereksinimlerini AppImage/EXE İçinde Tut + Settings'te Yükle
- Bazı Linux distrolarında VenvStudio çalışması için şu komutları gerekiyor:
  ```
  pip install shiboken6 --break-system-packages -U
  sudo pip install PySide6 --break-system-packages -U
  ```
- AppImage/EXE içinde PySide6 + shiboken6 wheel'leri embed edilmeli
- Sistem Python'unda yoksa: Settings altında "Install missing dependencies" butonu
- Buton: `pip install --break-system-packages shiboken6 PySide6` komutunu subprocess olarak çalıştırır
- Hedef: kullanıcı VenvStudio'yu çalıştırabilsin, önceden terminal'de elle komut koşmak zorunda kalmasın

### ✨ F143 — Settings'te Spyder Yorumcu Ayarı
- Spyder yüklüyse Settings altına bir bölüm: "Spyder → Use VenvStudio-selected venv as interpreter"
- Spyder config dosyası: `~/.config/spyder-py3/config/spyder.ini` (Linux), `%APPDATA%/spyder-py3/config/spyder.ini` (Windows)
- `[main_interpreter]` section'ında `custom_interpreter = /path/to/venv/bin/python`
- Editor Integration paneline Spyder satırı eklenmeli (mevcut 7 editörün yanına)

### ✨ F144 — Presets'te Paket Bilgi Penceresi
> ⚠️ **F153 (Presets Paket Detay Hover/Click Bilgisi) TARAFINDAN KAPSANIYOR ve GENİŞLETİLDİ** — F153 popup'a ek olarak hover tooltip + inline info row da getiriyor.
- Preset'lere tıklandığında yüklenecek kütüphanelerin **açıklamaları + isimleri alt alta** bir info/liste olsun
- Launch'daki "Links ›" gibi benzer bir görünüm ama pencere açılsın
- İçerik: paket adı, 1-2 satır açıklama, versiyon (varsa)
- Örnek "ML Basics" presetine tıkla → popup: numpy (numerical computing), pandas (data analysis), scikit-learn (ML algorithms)...
- **Dosya**: `src/gui/package_panel.py` Presets tab, `src/utils/constants.py::PACKAGE_CATALOG`

### ✨ F145 — View → Dependencies → Launch Apps Tablosu
- View menüsüne yeni menu item: "Dependencies"
- Alt menü: "Launch Apps" — her Launcher app'inin bağımlılıklarını listeleyen tablo
- Tablo: App Name | Required Packages | Versions
- **Düzenlenebilir** olursa daha iyi (kullanıcı kendi versiyon constraint'i ekleyebilir)
- **JSON'da tutulursa AppData altında transferi daha rahat**
- Dosya: `~/.venvstudio/launch_deps.json` (user override) + default `src/utils/constants.py::LAUNCH_APPS`
- Launch öncesi bu JSON okunup install komutuna versiyonlar eklenir

### ✨ F146 — Open Terminal → Eğitici Komutlarla Aç
- Env seçiliyken "Open Terminal" → normal terminal açılır
- Yeni davranış: terminal açılıp env aktive edildikten sonra **eğitici komutlar prompt olarak** gelsin:
  ```bash
  # Try these commands:
  pip list                    # list installed packages
  pip show <package>          # info about a package
  python --version
  deactivate                  # exit the environment
  ```
- Bash/Zsh için `.bashrc` rcfile, Fish için `fish --init-command`, PowerShell için `-NoExit -Command`
- Conda için: `conda list`, `micromamba list`
- Poetry için: `poetry show --tree`, `poetry add <pkg>`
- uv için: `uv pip list`, `uv pip install <pkg>`

### ✨ F147 — Learn Bookmark (Quick Launch Bölgesine Eklenebilir)
- Learn topic'inde bookmark/favorite butonu
- Bookmark'lar sidebar'da Quick Launch'ın olduğu bölgede listelenir
- Tek tıkla Learn topic'ine hızlı geçiş
- `~/.venvstudio/learn_bookmarks.json` ile persistent

### ✨ F148 — Learn'den Proje Hazırla Butonu (Editör Entegrasyonu)
- Learn → bir topic seçili → kod snippet'inin yanında yeni buton: "Open in Editor" veya "Prepare Project"
- İki mod:
  - **Path seçerek**: Kullanıcı path belirler, snippet `.py` olarak yazılır + editör açılır
  - **Direkt**: Geçici dosya açılır, kullanıcı editor içinde "Save As" ile yol belirler
- Editör seçimi: Settings'teki default editor (Editor Integration panelinden)
- Workflow: Learn topic → "Prepare Project" → VS Code açılır + kod dosyası hazır + VenvStudio venv'i aktif

### ✨ F150 — "Verify Python/venv" Sırasında Progress Bar
- Settings → Python Versions → Verify butonuna basınca Windows sanki donuyor gibi
- Aslında arkada subprocess çalışıyor ama UI feedback yok
- **Çözüm**: İşlem sırasında progress bar veya indeterminate spinner göster
- "Verifying Python installations... (this may take a minute)" gibi status mesajı
- İşlem async olmalı, UI donmamalı (QThread veya QRunnable)
- **Dosya**: `src/gui/settings_page.py::_verify_python_installations`

---

### ✅ B141 — Windows pipx Launch App Yüklenince Tablo Güncellenmiyor (TAMAMLANDI v1.4.66)
- [x] `package_panel._on_app_install_finished` — success branch'inde `env_refresh_requested.emit()` çağrılıyor artık
- [x] Pipx path tespit edilirse `VenvManager.invalidate_all_caches()` çağrılıyor (pipx'te app'ler aynı cache tree'yi paylaşır)
- [x] `_on_system_install_finished` — conda installs için de aynı emit + cache invalidation eklendi
- [x] `_on_install_finished` zaten doğru emit ediyordu (önceden)
- Main window `env_refresh_requested` signal'ını `_refresh_env_list`'e bağlı tutuyor (mevcut wiring)

### ✨ F140 — Launcher'da Package Conflict/Version Ayarı
> ⚠️ **F151 (Detaylı Conflict Management System) TARAFINDAN KAPSANIYOR** — F151'in launcher entegrasyonu bu maddenin yerini alacak. Aşağıdaki notlar F151 içinde de uygulanacak.
- Launcher bir uygulamayı yüklerken paket çakışmaları olabiliyor (ör. `streamlit==1.30` ama mevcut env'de `streamlit==1.28`)
- **Talep**: Install başlamadan önce kullanıcıya **"versiyon değiştirmek ister misin?"** mini dialog
- Dialog içinde:
  - Uygulamanın önerdiği paketler tablosu: `name | requested | currently installed | action`
  - Her satır için: Skip / Use requested / Use current / Pick custom version
  - "Versiyon dropdown" (PyPI'den versiyonları çek — `pip index versions <pkg>` veya pypi JSON API)
  - Conflict uyarısı (kırmızı): "Bu değişiklik 3 başka paketi etkiler"
- **Akış**:
  1. Launch App butonuna basılınca → dependency resolution (`pip install --dry-run ...`)
  2. Conflict varsa dialog aç
  3. Kullanıcı onayından sonra install
- Dosya: `src/gui/install_conflict_dialog.py` — yeni dialog
- `launcher.py` (ya da package_panel'deki install fonksiyonu) → pre-install hook ekle

### 🐛 B142 — Launcher Install Terminal'e Log Düşmüyor
- VenvStudio terminal'den (`python main.py`) çalıştırıldığında:
  - Env create/delete → terminal'de banner + log görünüyor ✅
  - **Launcher'dan uygulama install → terminal'de hiçbir şey görünmüyor** ❌
- Install komutu da terminale düşmeli:
  ```
  ▶ subprocess: /path/to/pip install streamlit pandas
    ↳ exit=0
  ╭────────────────────────────╮
  │ ✅ streamlit installed       │
  │    • Packages: streamlit, pandas │
  │    • Env: ml                │
  ╰────────────────────────────╯
  ```
- **Sebep**: Launcher'ın install fonksiyonu subprocess'leri muhtemelen `_run` wrapper'ı kullanmıyor, direkt `subprocess.run`
- **Çözüm**:
  - `package_panel.py::_install_launcher_app` (veya ilgili metod) → `venv_manager._run` veya kendi module logger'ı kullansın
  - Her install öncesi `banner_start("Installing <app>", details=[...])` çağır
  - Install sonucu `banner_success` / `banner_error`
- Handoff kural #12 kapsamında — verbose logging **her yerde** olmalı, launcher dahil

### 🐛 B143 — Export Requirements pipx/conda env'lerinde fail ediyor
- Virtual Environments tablosundan pipx veya conda satırı seçiliyken "Export" (requirements.txt) butonuna basınca hata:
  ```
  Error: pip not found in this environment.
  ```
- **Sebep**: Export kodu env-type agnostik — her env için `pip freeze` çalıştırıyor. Ama:
  - **pipx** env'inde pip başka yerde (`~/.local/share/pipx/venvs/<app>/bin/pip`), kullanıcı app seçmeli
  - **conda** env'inde pip micromamba tarafından yönetilir, farklı konumda
  - **poetry** env'inde pyproject.toml'dan okumak gerek
- **Beklenen çözüm**: env-type aware export
  - **venv/uv** → `pip freeze > requirements.txt` (mevcut)
  - **pipx** → `pipx list --short > pipx_apps.txt` veya `pipx runpip <app> freeze` per-app
  - **conda** → `micromamba env export -n <name> > environment.yml` (conda format)
  - **poetry** → `cp pyproject.toml requirements-poetry.toml` veya `poetry export -f requirements.txt`
- UI: Export butonu dropdown'u env-type'a göre değişmeli
  - venv: "Export requirements.txt"
  - conda: "Export environment.yml" + "Export requirements.txt (pip-only)"
  - pipx: "Export pipx_apps.txt"
  - poetry: "Open pyproject.toml" + "Export requirements.txt (poetry export)"
- **Dosya**: `src/gui/package_panel.py` veya `main_window.py`'deki export handler

### 🐛 B144 — pipx'e uygun olmayan paket install çalıştırılıyor (MLflow, Orange3, vb.)
- Launcher → MLflow UI → Launch'a basınca `pipx install mlflow` denendi ve fail etti
- **YENİ KANIT**: Orange3 de pipx'te fail: `pipx install failed for: PyQtWebEngine` — Orange3 PyQt5 + PyQtWebEngine'e bağımlı, pipx isolation'da bu GUI dependency chain kurulmuyor
- **Sebep**: MLflow, Orange3, Jupyter, TensorBoard, Spyder gibi paketler **library-first + GUI** — pipx için uygun değil:
  - Ağır dependency tree (sqlalchemy, pandas, scipy, PyQt5, docker, vb.)
  - Library imports hem app hem kullanıcı kodundan kullanılıyor
  - GUI bileşenleri sistem kütüphanelerine (Qt, X11) ihtiyaç duyuyor
  - pipx normalde saf CLI-only (entry-point) app'ler için: black, httpie, ruff, streamlit (standalone)
- **Pipx-friendly tespit edilen (OK)**: `_PIPX_FRIENDLY` set'teki 24 CLI tool
- **Pipx-düşmanı (bu listeye eklenmeli ve pipx'e yönlendirmemeli)**:
  - `orange3` (PyQt5 + PyQtWebEngine)
  - `mlflow` (sqlalchemy + pandas chain)
  - `jupyter`, `jupyterlab`, `notebook` (ipywidgets + kernel system)
  - `spyder` (PyQt5 + qtconsole)
  - `tensorboard` (tensorflow chain)
  - `dash`, `gradio`, `panel`, `streamlit` (web framework + runtime sistemleri)
  - `voila` (jupyter-dependent)
- **Çözüm adımları**:
  1. `constants.py` PACKAGE_CATALOG içinde her paket için `preferred_backend: "pip" | "pipx" | "conda"` field'ı ekle
  2. Launcher'da Launch butonuna basılınca:
     - Paket zaten yüklü mü (hem pipx hem pip env'inde kontrol)
     - preferred_backend pipx ise ve env pipx değilse → uyarı
     - preferred_backend pip ise ve env pipx ise → "Pipx env seçtin ama bu paket venv'e gider. Bir venv seç ya da yeni oluştur" dialogu
  3. Pre-install dependency check: `pip install --dry-run <pkg>` ile pipx'in halledebileceği mi bak
  4. pipx fail olursa fail mesajı tam göster + "Retry in a venv?" butonu sun
  5. Default: pip (safer fallback), pipx ancak explicit "CLI tool" olarak işaretlenmiş paketler için
- **Related**: F140 (Launcher conflict/version dialog) — pre-install validation'ın bir parçası

### 🐛 B145 — Pipx env'de "Installed" görünen app Launch'ta sessiz fail
- Pipx env seçili, Launch'da Orange3 "Installed" badge'i ile görünüyor (B141 refresh çalışıyor ✓)
- "Launch Orange Data Mining" butonuna basınca status bar "Launched..." diyor, ama pencere açılmıyor, hata mesajı yok
- **Muhtemel sebepler**:
  - Launch komutu subprocess olarak çalıştırılıyor ama exit code kontrol edilmiyor
  - `subprocess.Popen` ile başlatıldı ve hemen exit etti (import hatası, missing GUI lib, segfault)
  - pipx venv'in Python'u kullanılıyor ama uygulamanın beklediği Python env değil
  - Terminal'e hata düşmüyor (stdout/stderr redirect edilmemiş)
- **Bu oturumda eklenen B142 fix ile birlikte**: Launcher komutu da terminal'e loglanmalı — hangi subprocess çalıştı, exit kodu, stderr
- **Çözüm**:
  1. `package_panel.py::_launch_app` — subprocess output'unu file'a veya log'a yaz
  2. `Popen` kullanılıyorsa `.poll()` ile hemen exit edip etmediğini kontrol et (1-2 saniye sonra)
  3. Exit non-zero ise stderr'i kullanıcıya QMessageBox ile göster
  4. Pipx için özellikle: `pipx list` ile app'in gerçekten yüklü olduğunu doğrula, entry point path'ini logla
  5. Banner_start/banner_error ekle (verbose logging kuralı #12)
- **Terminal output kritik**: Kullanıcı `python main.py 2>&1 | tee /tmp/vs.log` ile çalıştırıp traceback görebilmeli

### 🐛 B146 — Pipx launch app yüklendikten sonra badge doğru, ama "3 packages installed" count tuhaf
- Screenshot'ta pipx env'de "3 packages installed" yazıyor ama sadece 2 app yüklü (Orange3, bir tane daha?)
- Quick Launch sidebar'da sadece 2 satır görünüyor (pipx, Orange Data Mining)
- pipx'in kendi venv metadata sistemi ile VenvStudio'nun package sayımı arasında fark olabilir
- **Araştırılacak**:
  - `list_pipx_apps()` app sayısını mı, bağımlılık sayısını mı döndürüyor?
  - Pipx'in her app'i kendi venv'inde paket, VenvStudio toplam package count için hepsini topluyor olabilir
- Öncelik düşük — sadece cosmetic, işlevsel etkisi yok

---

### 🎓 F52 — EĞİTİMSEL UYGULAMALAR MENÜSÜ (v1.4.60+)
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

### ✅ B121 — Yüksek DPI / Ölçek > 100% Form Elemanları Sağa Kayıyor (v1.4.57)
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

### 🟡 F119 — Klavye Kısayolları (Keyboard Shortcuts)
- Tüm ana işlemler için klavye kısayolları eklenecek
- **Navigasyon:**
  - `Ctrl+1` → Packages sayfasına git
  - `Ctrl+2` → Environments sayfasına git
  - `Ctrl+3` → Settings sayfasına git
- **Environment işlemleri:**
  - `Ctrl+N` → New Environment dialog'u aç
  - `Delete` → Seçili env'i sil (onay ile)
  - `F2` → Seçili env'i rename (Name Only)
  - `Ctrl+F2` → Seçili env'i rename (Full)
  - `Ctrl+D` → Seçili env'i duplicate/clone
  - `Ctrl+R` veya `F5` → Refresh env listesi
  - `Ctrl+T` → Seçili env için Open Terminal
  - `Ctrl+Shift+F` → Seçili env klasörünü aç (Open Folder — F118 ile bağlantılı)
- **Paket işlemleri:**
  - `Ctrl+I` → Install package (paket arama kutusuna odaklan)
  - `Ctrl+U` → Outdated paketleri güncelle
  - `Ctrl+E` → Export requirements
- **Genel:**
  - `Ctrl+,` → Settings sayfasına git
  - `Ctrl+Q` → Uygulamayı kapat
  - `Ctrl+F` → Env listesinde arama/filtre
  - `Escape` → Açık dialog'u kapat / arama kutusunu temizle
- **Uygulama:**
  - `main_window.py` → `QShortcut` veya `QAction` ile tanımlanacak
  - Kısayollar `Help > Keyboard Shortcuts` menüsünde listelenecek
  - Tüm kısayollar platform uyumlu (Windows/Linux/macOS)


### ✅ B130 — Poetry Open Terminal Yanlış Path (v1.4.57)
- Poetry env'e Open Terminal yapıldığında yanlış path açılıyor (Linux'ta test edildi, Windows'ta bilinmiyor)
- Neden: `open_terminal_at` poetry için proje klasörünü kullanıyor, gerçek venv path'ini (`%LOCALAPPDATA%\pypoetry\Cache\virtualenvs\...`) değil
- Fix: `platform_utils.py` → `open_terminal_at` içinde poetry env için marker'daki `poetry_venv_path` okunmalı
- **Her iki platformda da test edilmeli (Windows + Linux)**


### ✅ B136 — PEP 668 Toolchain Uninstall Hatası (v1.4.57)
- uv/poetry/pipx kaldırılırken "externally-managed-environment" hatası alınıyordu
- Fix: binary direkt siliniyor (`~/.local/bin/`, `~/.cargo/bin/`), fallback: `--break-system-packages`

### ✅ B131 — Remove All Data Sonrası Config Hatası (v1.4.57)
- Settings > Remove All Data'ya tıklanınca `settings.json` siliniyor
- Uygulama terminal'den çalışıyorsa sonraki kaydetme işleminde hata veriyor:
  `Error saving config: [Errno 2] No such file or directory: '~/.config/VenvStudio/settings.json'`
- Fix: `config_manager.py` → `save()` içinde dosya yoksa önce dizini ve dosyayı oluştur (`os.makedirs` + yeni boş config yaz)

### ✅ B132 — Eski/Bozuk JSON'da Clean Start (v1.4.57)
- Eğer `settings.json` içindeki versiyon çalışan uygulama versiyonundan düşükse (ya da JSON bozuksa) tüm config silinip sıfırdan oluşturulmalı
- Şu an bozuk JSON varsa uygulama hata veriyor
- Fix: `config_manager.py` → `load()` içinde versiyon kontrolü ekle; eski/bozuk JSON → yedekle (`settings.json.bak`) + sıfırdan oluştur

### 🔴 B133 — pipx Env Silme Akışı Yanlış
- Environments tablosunda pipx seçilip Delete'e basıldığında direkt silmeye çalışıyor
- Doğru akış:
  1. Önce uyarı: "pipx kaldırılmadan önce Settings > Toolchain Manager > Uninstall yapın veya `pipx uninstall-all` çalıştırın"
  2. Eğer pipx executable yoksa (zaten kaldırılmışsa): klasörü tamamen sil
  3. Eğer pipx hâlâ kuruluysa: silmeyi engelle, kullanıcıyı yönlendir
- `main_window.py` → `_delete_env()` içinde pipx için özel akış

### 🟡 B134 — Default Python Mantığı (Settings > Python Versions)
- "Default Python for new environments" ayarı sistem default dışında bir Python seçilince otomatik set edilmeli
- Şu an kullanıcı her seferinde manuel seçiyor
- Fix: `env_dialog.py` → Create Environment'ta Python seçilince bu seçim default olarak kaydedilsin (isteğe bağlı checkbox ile)

### 🔴 B135 — Export — pip Dışı Env'lerde Çalışmıyor
- uv, poetry, conda, pipx env'lerinde Export işlemi başarısız veya boş çıktı veriyor
- Neden: export kodu `pip freeze` / `pip list` kullanıyor, pip dışı env'lerde pip yok
- Fix: her env tipine özel export stratejisi:
  - **uv:** `uv pip freeze`
  - **poetry:** `poetry export -f requirements.txt` veya `pyproject.toml`
  - **conda:** `conda list --export` veya `environment.yml`
  - **pipx:** `pipx list --json`
- `settings_advanced.py` → `_export_env_requirements()` ve ilgili metodlar

### 🟡 F120 — Export'ta Podman Desteği
- Export > Dockerfile yanına Podman desteği ekle (Podman uyumlu Containerfile)
- Podman rootless çalıştığı için `USER` direktifi farklı olabilir
- `settings_advanced.py` → export dialog'a "Podman (Containerfile)" seçeneği ekle

### 🟡 F121 — Tools > Create Necessary Shortcuts
- AppImage / EXE / pip kurulumunda masaüstü ve uygulama menüsüne kısayol oluşturma
- **Linux:** `.desktop` dosyası oluştur → `~/.local/share/applications/`
- **Windows:** Başlat Menüsü + Masaüstü `.lnk` kısayolu
- **macOS:** `/Applications/` altına `.app` bundle veya Dock kısayolu
- Settings veya Tools menüsü altında "Create Desktop Shortcut" butonu
- pip install ile kurulanlar için de geçerli (`venvstudio` CLI entry point üzerinden)

### 🟡 F122 — Tools > Install VS Code CLI (User / Global)
- Settings'teki mevcut VS Code CLI toggle'ı genişletilecek
- **User kurulum:** `%APPDATA%\Code\User\` (Windows) / `~/.config/Code/User/` (Linux) altına
- **Global kurulum:** `C:\ProgramData\` (Windows) / `/usr/local/` (Linux) altına (sudo gerekir)
- Seçim dialog'u: "Install for current user" vs "Install for all users (admin/sudo required)"
- `settings_catalog.py` → `_toggle_vs_cli()` genişletilecek

### 🟡 F123 — Python Download Kaynakları (Mirror Seçimi)
- Settings > Python Versions > Download Python bölümüne kaynak seçimi ekle
- **Yerleşik kaynaklar:**
  - 🚀 **Astral CDN** (varsayılan) — `https://downloads.astral.sh/` — hızlı CDN
  - 🐙 **GitHub Releases** — `https://github.com/astral-sh/python-build-standalone/releases` — her zaman güncel
  - 🐍 **python.org** — `https://www.python.org/ftp/python/` — sadece Windows/macOS (MSI/PKG)
  - 📦 **SourceForge Mirror** — `https://sourceforge.net/projects/python-standalone.mirror/` — resmi olmayan kopya
- **Özel URL desteği:**
  - Kullanıcı kendi mirror URL'sini girebilir (şirket içi mirror, hava boşluklu ağ vb.)
  - Opsiyonel parametreler eklenebilir (auth header, proxy vb.)
  - URL doğrulama: bağlantı testi butonu
- **Uygulama:**
  - `settings_python.py` → Download Python bölümüne kaynak combo + custom URL input ekle
  - `src/core/python_downloader.py` → indirme URL'si seçilen kaynaktan oluşturulsun
  - Seçim `config` altında `python_download_source` ve `python_download_custom_url` olarak saklanır
  - python.org seçilince format uyarısı göster (portable değil, installer format)

### 🟡 F124 — Catalog Paket Bilgilerini Düzenleme (Settings)
- Settings > Catalog bölümüne mevcut catalog paketlerini düzenleme imkânı ekle
- **Özellikler:**
  - Mevcut paketleri listele (tüm kategoriler)
  - Her paket için düzenlenebilir alanlar:
    - `desc` — açıklama
    - `links` — PyPI, Docs, GitHub, YouTube linkleri
    - `category` — kategori değiştirme
  - **Override sistemi:** `constants.py`'deki orijinal veri değişmez, kullanıcı overrideleri `config`'e kaydedilir (`catalog_overrides` dict)
  - Orijinal değere sıfırlama butonu (her satırda)
  - Tüm overrideleri sıfırlama butonu
  - Arama/filtre
- **Uygulama:**
  - `settings_catalog.py` → yeni "Edit Catalog" bölümü
  - `package_panel.py` → `_populate_catalog()` önce `catalog_overrides`'a bakıp override varsa onu kullansın
  - Override format: `{"numpy": {"desc": "...", "links": {...}}, ...}`
  - `config_manager.py` → `catalog_overrides` key'i

### 🟡 F125 — Emoji/İkon Desteği (openSUSE, Fedora)
- openSUSE ve Fedora'da emoji ikonlar görünmüyor (🐍 ⚡ 📦 🦎 vb.)
- Neden: Bu distrolarda `fonts-noto-color-emoji` veya eşdeğeri kurulu değil
- **Settings > Appearance** altına "Install Emoji Font" butonu ekle:
  - **Debian/Ubuntu/Pardus:** `sudo apt install fonts-noto-color-emoji`
  - **Arch/CachyOS:** `sudo pacman -S noto-fonts-emoji`
  - **Fedora:** `sudo dnf install google-noto-emoji-fonts`
  - **openSUSE:** `sudo zypper install noto-coloremoji-fonts`
  - pkexec ile grafik şifre dialog'u
- Kurulum sonrası uygulama yeniden başlatma önerisi
- Zaten kuruluysa buton "✅ Emoji font installed" göstersin
- `settings_appearance.py` → `_install_nerd_font` benzeri yapı

### 🟡 F74b — Launch Kartları Linkleri Tamamlama
- Kalan tüm uygulamalara YouTube/Docs/Site/GitHub linkleri ekle:
  - TensorBoard, MLflow, Voilà, Panel, Spyder, RStudio, QGIS, vb.
  - Tüm system_app'ler dahil
- Link butonlarının görünümü iyileştir (ikon boyutu, hover efekti)
- GitHub linki de ekle ilgili uygulamalar için

### 🟡 F52b — Learn Sayfası Geliştirme
- **Tasarım:** Daha iyi görsel tasarım — kart hover animasyonları, kategori renkleri
- **Syntax Highlight:** Kod snippet'lerinde syntax highlighting (Pygments veya basit regex)
- **Arama/Filtre:** Tüm topic'lerde arama yapabilme
- **Daha fazla içerik:**
  - Django, SQLAlchemy, Celery (Web kategorisi)
  - NumPy, Polars, Plotly (Data Science)
  - TensorFlow, Keras, ONNX (ML/DL)
  - Click, Typer, Rich (CLI Tools)
  - Docker, Git, SSH (DevOps)
  - asyncio, threading, multiprocessing (Concurrency)
- **"Install & Try" butonu** → direkt aktif env'e kur, terminal aç
- **Bookmark/Favori** sistemi — beğenilen topic'leri kaydet
- **Progress tracking** — hangi topic'leri okuduğunu işaretle
- **Arama** — topic başlığı ve içeriğinde full-text search

### 🔴 B136 — env_dialog Komutlar Küçük Görünüyor
- Sağ panel (Progress/hints) çok dar — komutlar kısalıyor
- Dialog boyutu 1120x680 yapıldı, stretch 3:7 ama hâlâ küçük görünüyor
- Olası çözüm: QScrollArea içine al, ya da font daha da büyüt (18px?)
- Veya hints paneli ayrı bir scrollable widget olsun

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
> ⚠️ **F151 (Detaylı Conflict Management System) TARAFINDAN KAPSANIYOR** — F151'in dynamic resolution check katmanı bu maddenin yerini alıyor.
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
    - [ ] `com.github.bayramkotan.VenvStudio.yml` manifest hazırla
      - Runtime: `org.freedesktop.Platform` veya `org.kde.Platform`
      - Build sistemi: pip tabanlı — tüm PySide6 + bağımlılık wheel'ları tanımlanacak
      - İzinler: `--filesystem=home`, `--share=network`, `--talk-name=org.freedesktop.Notifications`
      - Sandbox kısıtı: `uv`, `pipx`, `poetry` gibi sistem araçlarına erişim için `--filesystem=host` gerekebilir
    - [ ] Yerel test:
      ```bash
      flatpak-builder build-dir com.github.bayramkotan.VenvStudio.yml --force-clean
      flatpak-builder --run build-dir com.github.bayramkotan.VenvStudio.yml venvstudio
      ```
    - [ ] `flathub/flathub` GitHub repo'sunu fork et
    - [ ] `com.github.bayramkotan.VenvStudio/` klasörü oluştur, manifest ekle
    - [ ] PR aç → Flathub ekibi review (~1-2 hafta)
    - ⚠️ **Zorluklar:** PySide6 büyük bağımlılık; sandbox subprocess kısıtları; AppImage zaten çalışıyor
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

- **B159** — ✅ TAMAMLANDI (v1.4.73): Learn sayfası → Install butonu 3 ayrı hata:
  - `QTimer` import eksikti → `from PySide6.QtCore import QTimer` eklendi
  - `_install_packages_by_name` → `_install_packages` olarak düzeltildi
  - `LearnInstallDialog` hiç kullanılmıyordu → `_on_learn_install` tamamen yeniden yazıldı
  - `dlg.Accepted` → `QDialog.Accepted` olarak düzeltildi

- **B162** — ✅ TAMAMLANDI (v1.4.73): LearnInstallDialog UI iyileştirmeleri
  - "Current env" ve "Default env" radio butonları kaldırıldı
  - Dropdown'da Python path yerine kısa versiyon gösteriyor (e.g. `Python 3.12`)
  - "Create new env" altına Type seçimi eklendi (venv/uv/conda/poetry)
  - `LearnInstallDecision`'a `new_env_type` field'ı eklendi

- **B160** — ✅ TAMAMLANDI (v1.4.74-v1.4.76): openSUSE/SUSE Open Folder/Terminal donuyor
  - `platform_utils.py` — tüm Linux `subprocess.Popen` çağrılarına `start_new_session=True` eklendi
  - `open_folder`: openSUSE için `/usr/bin`, `/usr/local/bin` manuel path araması eklendi
  - `auto_order`'a `yakuake` eklendi

- **B169** — 🔴 Settings → Manual Install → PM'e göre farklı içerik
  - Şu an Poetry seçiliyken "uv install..." gibi yanlış komutlar çıkıyor
  - Her PM için doğru install/uninstall komutu gösterilmeli:
    - pip:    pip install X / pip uninstall X
    - uv:     uv pip install X / uv pip uninstall X
    - conda:  conda install X / conda remove X
    - poetry: poetry add X / poetry remove X
    - pipx:   pipx install X / pipx uninstall X
  - İlgili dosya: `src/gui/package_panel.py` → Manual Install tab

- **B170** — ✅ TAMAMLANDI (v1.4.79): CLI/TUI Tools Uninstall tüm sistemlerde
  - get_tool_version: PATH + bin_dir + pip show fallback
  - Uninstall butonu her zaman görünür, yüklü değilse disabled
  - Yüklü olan araçlarda Uninstall butonu aktif olmalı
  - Tüm sistemlerde (Linux/Windows/macOS) ve tüm araçlar için (Starship, Oh My Posh, Rich, Textual, Prompt Toolkit)
  - Yüklü değilse Uninstall butonu gizli/disabled
  - İlgili dosyalar: `src/gui/settings_page.py`, `src/gui/settings_toolchain.py`, `src/gui/settings_appearance.py`

- **F133** — 🔴 Harici Python projesi içine env kurma
  - Kullanıcı mevcut bir Python projesinin klasörünü seçebilmeli
  - O klasör içine env oluşturulabilmeli (.venv/ veya kullanıcının seçtiği isim)
  - Recent Envs altında bu env'ler de görünsün
  - Packages sayfasında tıklandığında detaylar (paketler, path, python version) görünsün
  - Environments sayfasında "External / Project Envs" bölümü veya filtresi olsun
  - İlgili dosyalar: `src/gui/env_dialog.py`, `src/gui/main_window.py`, `src/core/venv_manager.py`

- **B166** — 🔴 Settings → Save butonunda progress bar/feedback yok
  - Kaydetme işlemi sırasında form takılmış gibi görünüyor
  - Çözüm: Save butonuna basınca buton disabled + "Saving..." text, işlem bitince "✅ Saved!" toast veya status label
  - İlgili dosya: `settings_advanced.py` → `_save_settings`

- **B167** — 🟡 Settings → Python Versions → "System Scan" butonu ne yapıyor?
  - Kullanıcıya açıklama yok — tooltip veya açıklama label eklenmeli
  - Davranışı dokümante edilmeli: hangi path'leri tarar, sonucu nereye yazar?
  - İlgili dosya: `settings_python.py`

- **B168** — 🟡 Settings → General → Checkbox'lar düzgün çalışıyor mu?
  - Checkbox'ların config'e doğru kaydedilip kaydedilmediği test edilmeli
  - Özellikle "restart required" olan ayarlar için uyarı gösterilmeli mi?
  - İlgili dosya: `settings_advanced.py` → `_save_settings`

- **F131** — ✅ TAMAMLANDI (v1.4.78): Learn 72 → 114 topic, 3 yeni kategori (Core Libraries, Data & Finance, AI/LLM)
  - ✅ 72 → 98 topic tamamlandı (v1.4.77)
  - Eklenecek yeni kategoriler:
    - 📦 Core Libraries: NumPy, Pandas, Matplotlib, Seaborn, Plotly, Requests, Pillow
    - 📈 Data & Finance: yfinance, pandas-datareader, TA-Lib, Prophet, statsmodels
    - 🤖 AI / LLM: OpenAI, LangChain, LlamaIndex, HuggingFace, Ollama, ChromaDB
    - ⏱ Time Series: pandas resample, ARIMA, Prophet, darts, sktime

- **F132** — ✅ TAMAMLANDI (v1.4.78): Learn Bookmark sistemi
  - Her topic card'ında 🔖 butonu (toggle — basınca ekle/çıkar)
  - Bookmark'lar config'e kaydedilir (`bookmarked_topics` key, list of topic titles)
  - Quick Launch sayfasında "📌 Bookmarks" bölümü — kayıtlı topic'lere direkt erişim
  - Quick Launch'ta Learn ve Settings boş kalıyor — bu bölüm dolduracak
  - İlgili dosyalar: `learn_page.py`, `main_window.py` (Quick Launch bölümü)
  - Mevcut konu sayısı yetersiz
  - Eklenecek kategoriler/konular belirlenmeli
  - Her konuya daha fazla alt başlık, kod örneği, install butonu
  - İlgili dosya: `src/gui/learn_page.py`, `src/gui/learn_content/`

- **B165** — 🟡 Wayland: `qt.qpa.wayland.textinput` uyarıları terminale dökülüyor
  - `qt.qpa.wayland.textinput: ...zwp_text_input_v3_leave...` ve `remaining: 0` mesajları
  - Qt'nin Wayland implementasyonundaki bug, VenvStudio'nun hatası değil
  - Çözüm: `main.py`'de `os.environ["QT_LOGGING_RULES"] = "qt.qpa.wayland*=false"` set et
  - Sadece Wayland'da set edilmeli (`WAYLAND_DISPLAY` env var kontrolü ile)

- **B163** — ✅ TAMAMLANDI (v1.4.77): Noto emoji dialog her açılışta tekrar soruyordu
  - Yes/No her ikisinde de `show_emoji_missing_warning = False` kaydediliyor
  - Settings'e "⬇️ Install Noto Color Emoji" butonu eklendi

- **B164** — 🔴 Kali Linux: VenvStudio her başlatıldığında `postgresql.service` authentication isteniyor
  - VenvStudio startup'ta bir şey postgresql servisini tetikliyor
  - Şüpheli: `system_tools_installer.py` veya toolchain manager servis durumu kontrolü
  - Çözüm: servis durum kontrollerini `subprocess` ile değil pasif yöntemle yap (socket/file check)
  - Wayland ortamında `xdg-open` + terminal komutu askıda kalıyor
  - `open_terminal_at` ve `_open_env_folder` fonksiyonları etkileniyor
  - Çözüm: openSUSE'de varsayılan terminal ve file manager tespiti + Wayland için `nohup` / `setsid` kullanımı

- **B161** — ✅ TAMAMLANDI (v1.4.77): CLI/TUI araçları dropdown'a taşındı
  - "🛠 CLI / TUI Tools:" checkbox + QComboBox + QStackedWidget
  - Oh My Posh ilk sırada, yüklü araçlarda ✅ suffix
  - Checkbox işaretlenmeden dropdown ve card görünmüyor

- **F90** — ✅ TAMAMLANDI (v1.4.73): Shared Package Cache (pip / uv)
  - Settings → Paths'e toggle + cache dir + Browse + Reset + Clear Cache eklendi
  - pip: `--cache-dir <path>`, uv: `UV_CACHE_DIR` env var inject
  - conda/poetry/pipx etkilenmiyor
  - Config keys: `shared_cache_enabled` (bool), `shared_cache_dir` (str)
  - Default path: `~/.venvstudio/pkg-cache`

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

---

## 🔚 SON SIRA (ertelendi)

### ✨ F149 — Launch Uygulamalarının Üstünde Learn'e Link (GELECEK — Learn Tam Bitince)
- Launch'daki her uygulama kartının üstünde bir "Learn" linki
- Örneğin: Jupyter kartında "📖 Learn about Jupyter" → Learn → Jupyter topic'ine atar
- **Şimdi değil — Learn tamamen bitince yapılacak** (yeterli topic içeriği olunca)
- Jamovi, JASP, Ollama, JupyterLab... tüm Launch uygulamaları için Learn içerikleri lazım:
  - "Jupyter nedir, nasıl kullanılır"
  - "JASP — istatistiksel analiz için GUI"
  - "Ollama — lokal LLM çalıştırma"
  - "JupyterLab vs Jupyter Notebook farkı"
  - "Jamovi — SPSS alternatifi istatistik GUI'si"
  - "Spyder IDE nedir, kimler için uygun"
  - "Streamlit nasıl demo yapılır"
  - "Gradio ML model demo framework"
  - vb.
- Learn içeriği yeterince dolunca bu kart üstü link eklenecek
- **Related**: F137 Stats/Math, F136 Python Basics zaten var — Launch uygulamaları için ayrı kategori gerekir

### 🐛 B137 — Form yüklenmeden hareket ettirince çöküyor (ERTELENDİ)
- Uygulama ilk açıldığında ana pencereyi form elemanları yüklenmeden sürüklemeye çalışınca crash oluyor
- Muhtemelen env listesi async yüklenirken main thread'de event loop meşgul
- **Önceki işler:**
  - v1.4.62'de `main.py`'ye global `sys.excepthook` + `threading.excepthook` eklendi
  - Yani crash olursa artık traceback terminal'e + crash report'a düşecek
  - `venv_manager._run` subprocess loglamasıyla hangi background worker'ın çalıştığı görünür
- **Reproduce:** Bayram CachyOS'ta çalışıyor ve bu crash orada gözükmüyor. Fedora'da test yapılamadı (başka sorunlar vardı). Windows'ta EXE build'de görülmüş, terminal'den Python ile değil.
- **Sonraki oturum için:**
  1. Windows'ta EXE ile test → pencereyi hemen sürükle → crash report path'ini kontrol et (`%APPDATA%\VenvStudio\logs\crash_*.log`)
  2. Traceback olmadan tahminle kod yazma — bekle, bana traceback gelsin, o zaman çöz
  3. Traceback gelirse muhtemel çözümler:
     - **Splash screen / loading overlay** — pencere tam hazır olana kadar interaktif olmasın
     - `QTimer.singleShot(0, ...)` ile background loading'i batch'lere böl
     - MainWindow `__init__` içindeki async operasyonları `show()` sonrasına ertele
     - `setFixedSize()` veya `setEnabled(False)` ile pencereyi tam yüklenene kadar sabit tut


## ✅ F135 — TAMAMLANDI (v1.4.80): Terminal Emülatör Kurulum Desteği

Settings → CLI/TUI Tools altına "Terminal Emulators" dropdown bölümü eklenecek.
Tüm platformlarda (Windows, macOS, Linux) çalışan terminaller:

| Terminal | Dil | Özellik | Platform |
|----------|-----|---------|----------|
| WezTerm | Rust | GPU hızlandırmalı, Lua config, dahili multiplexer | Win/Mac/Linux |
| Alacritty | Rust | En hızlı, GPU ivmeli, sade (tmux/zellij ile kullanılır) | Win/Mac/Linux |
| Tabby | Electron | SSH/Telnet/Serial dahili, eklenti desteği, modern UI | Win/Mac/Linux |
| Ghostty | Zig | Native feel, Alacritty hızında, modern UX | Win/Mac/Linux |
| Hyper | Electron/JS | JS/CSS ile tam özelleştirme, web dev dostu | Win/Mac/Linux |

Her terminal için:
- Yüklü mü? → versiyonu göster + Uninstall butonu
- Yüklü değil mi? → Install butonu (platform'a göre doğru komut)
- Launch butonu (yüklüyse)
- Kısa açıklama + resmi site linki

Kurulum yöntemleri:
- WezTerm:   winget / brew / apt/pkg
- Alacritty: winget / brew / cargo install alacritty
- Tabby:     GitHub releases (.exe/.deb/.AppImage/.dmg)
- Ghostty:   GitHub releases / brew
- Hyper:     GitHub releases / brew

İlgili dosyalar: `src/gui/settings_page.py`, `src/gui/settings_toolchain.py`, `src/core/cli_tools_manager.py`


## 🔴 Öncelikli Yeni Özellikler

### B171 — Packages → Catalog → Package Info: Home ve PyPI aynı adresi gösteriyor
  - Sağ tık → Package Info diyince Home butonu ile PyPI butonu aynı URL'yi açıyor
  - Home URL'si PyPI yerine paketin kendi sitesine (GitHub, docs sitesi vb.) yönlenmeli
  - İlgili dosya: `src/gui/package_panel.py` → package info dialog

### F136 — Editor Integration: Spyder ekle
  - Mevcut editörler: VS Code, Cursor, Windsurf, Zed, PyCharm...
  - Spyder da bilimsel Python IDE olarak eklenecek
  - Spyder'ın env discovery mekanizması: `~/.spyder-py3/config/python_path_manager.ini`
  - İlgili dosya: `src/gui/settings_page.py` → _setup_vscode_ui_section

### F137 — Yeni Env Yöneticileri: pipx, uv, virtualenv, conda-forge, pip-env
  - Env oluşturma dialog'una eklenecek seçenekler:
    - pipx (uygulama izolasyonu — zaten var ama geliştirilebilir)
    - virtualenv (venv'in öncüsü, daha fazla seçenek)
    - pip-env (Pipfile + otomatik venv yönetimi)
  - Her biri için: oluşturma, paket kurma, export, import
  - İlgili dosyalar: `src/gui/env_dialog.py`, `src/core/venv_manager.py`

### F138 — pyenv Entegrasyonu
  - pyenv: Python version yöneticisi — birden fazla Python versiyonu kur/yönet
  - VenvStudio'da kullanım: Settings → Python Versions'da pyenv ile kurulu versiyonları göster
  - pyenv install X.Y.Z → VenvStudio'dan tetiklenebilir
  - pyenv local → proje dizinine Python versiyonu pinle
  - https://github.com/pyenv/pyenv
  - İlgili dosya: `src/gui/settings_python.py`, `src/core/python_downloader.py`

### F139 — Docker/Container Entegrasyonu
  - VenvStudio'dan direkt container oluşturma
  - Seçilen Python versiyonu + paketlerden Dockerfile oluştur
  - docker build / docker run entegrasyonu
  - Container içinde Jupyter, FastAPI vb. başlatma
  - Mevcut env'den Dockerfile export etme
  - İlgili dosya: yeni `src/core/docker_manager.py`

### F140 — Proje İçine Env Kurma (Geliştirme)
  - Mevcut F133'ü genişlet
  - Klasör seç → .venv oluştur → pyproject.toml/requirements.txt varsa otomatik kur
  - Recent Envs'te "📁 Project Envs" bölümü
  - Environments sayfasında proje env'leri ayrı göster
  - İlgili dosyalar: `src/gui/env_dialog.py`, `src/core/venv_manager.py`

### F141 — VenvStudio'ya Yapay Zeka Entegrasyonu
  - Olası kullanım alanları:
    - Paket önerileri: "numpy, pandas kurulu, ne önerisin?" → AI suggestion
    - Hata analizi: kurulum hatalarını AI ile açıkla
    - Env description: env içeriğini AI ile özetle
    - Learn sayfası: konuları AI ile genişlet / soru sor
    - Package search: doğal dil ile paket arama
  - LLM: Ollama (local) veya OpenAI API (kullanıcı kendi key'ini girer)
  - İlgili dosya: yeni `src/core/ai_assistant.py`

### F142 — README Güncellemesi
  - Ana README.md: yeni özellikler, ekran görüntüleri, kurulum
  - TR/EN her iki dil
  - Yeni kategoriler: Terminal Emulators, Learn sayfası, Bookmark sistemi
  - Badges güncelle (versiyon, PyPI, platform)

### F143 — Kod Mimarisi Haritası (büyük dosyalar parçalandıktan sonra)
  - Tüm modüller ve aralarındaki bağımlılıkları gösteren diagram
  - Her dosyanın sorumluluğu (tek cümle)
  - `docs/architecture.md` dosyası
  - Mermaid diagram ile görsel harita
  - Büyük dosyalar önce parçalanacak (REFACTOR TODO'su mevcut)


### F144 — Learn: Package Manager Konuları
  - pip, uv, poetry, conda, mamba, micromamba, pipx, virtualenv için detaylı Learn topics
  - Her PM için: kurulum, temel komutlar, lockfile mantığı, karşılaştırma diyagramı
  - Konular: "pip — Python Package Installer", "uv — Ultra Fast Package Manager",
    "Poetry — Dependency Management", "conda vs pip farkı",
    "pipx — Application Isolation", "Lockfiles & Reproducibility"
  - İlgili dosya: src/gui/learn_page.py → Scientific Computing veya yeni "Package Managers" kategorisi

### B172 — Linux Terminal Kurulumunda pkexec Yerine GUI Şifre Sorma
  - Yeni terminal yüklerken şifre terminalde soruluyor, popup olarak gelmeli
  - pkexec çalışıyor ama bazı sistemlerde (KDE/Wayland) farklı davranıyor
  - Alternatif: `pkexec` → `kdesu` (KDE) veya `gksudo`/`zenity` (GNOME) fallback
  - Veya: terminal emülatör aç + sudo komutu çalıştır
  - İlgili dosya: src/core/cli_tools_manager.py → install_terminal() / uninstall_terminal()

### ✅ F145 — TAMAMLANDI (v1.4.81): Desktop Shortcut (Tools menüsü + Settings)
  - Settings → General bölümüne "Create Desktop Shortcut" butonu
  - Help menüsüne "Create Desktop Shortcut" seçeneği
  - Windows: .lnk dosyası oluştur (winshell veya win32com veya PowerShell)
  - Linux:   ~/.local/share/applications/venvstudio.desktop (XDG) +
             ~/Desktop/venvstudio.desktop (masaüstü kısayolu)
  - macOS:   ~/Desktop/VenvStudio.command veya .app alias
  - Kısayol terminalsiz çalışmalı (GUI launcher)
  - İlgili dosyalar: src/gui/settings_page.py, src/gui/main_window.py (Help menüsü)

## 🔵 GELECEK — Yeni Paket/Env Yöneticileri

### F134 — pixi, conda, mamba, pyenv, conda-forge tam implementasyonu

Araştırılacak ve implemente edilecek:

- **pixi** — Rust tabanlı, pyproject.toml ile çalışan modern conda alternatifi
  - https://pixi.sh
  - conda-forge + PyPI paketleri birlikte
  
- **conda** — Gerçek conda (Anaconda/Miniconda) desteği
  - Şu an VenvStudio her zaman kendi micromamba'sını kullanıyor
  - Kullanıcının sisteminde conda varsa onu kullanma seçeneği
  
- **mamba** — Kullanıcının sisteminde mamba kuruluysa kullanma
  - conda'dan 10-100x hızlı
  - https://mamba.readthedocs.io
  
- **micromamba** — Mevcut implementasyon iyileştirilecek
  - Şu an çalışıyor ama UI'da daha net açıklama
  
- **pyenv** — Python version yöneticisi
  - Birden fazla Python versiyonu kurma/yönetme
  - https://github.com/pyenv/pyenv
  - Şu an Settings > Python Versions ile benzer iş yapılıyor
  
- **conda-forge** — Kanal yönetimi
  - Hangi kanaldan paket kurulacağını seçme
  - Özel kanal ekleme

**Not:** Tüm bu araçlar için env oluşturma, paket kurma, ve VenvStudio UI entegrasyonu yapılacak.
