# VENVSTUDIO_TODO.md

## 📐 BÜYÜK DOSYA BÖLME REFACTOR — İLERLEME (güncel)

**Kural:** dışa açık API + import yolu değişmez. Saf veri → ast auto-script. Mantık → mixin (+ dependency-free `*_common.py` ile döngüsel import önle). Her bölmeden sonra `python3 main.py` + GERÇEK fonksiyonel test (create/clone/rename/delete) BEFORE commit. Satır sonu tipini (CRLF/LF) koru.

**✅ Tamamlanan (hepsi push edildi, versiyon bump yok):**
- ✅ i18n.py 1492 → 52 (→ `src/utils/i18n_data/<lang>.py` ×11)
- ✅ learn_page.py 3318 → 765 (→ `src/gui/learn_content.py`, LEARN_CATEGORIES)
- ✅ venv_manager.py 2108 → 1262 (mixin: `_common`/`_cache`/`_clone`/`_rename`)
- ✅ CreateWorker → workers.py (env_dialog 1538 → 1504; 6 worker tek yerde)
- ✅ settings_page.py 1708 → 325 (mixin: appearance/python/toolchain/catalog/advanced + yeni `settings_editors.py`, `settings_common.py`)
- ✅ env_dialog.py 1504 → 111 (yeni `env_dialog_ui.py`, `env_dialog_tools.py`, `env_dialog_create.py` — `_create` dispatcher'a indirgendi, 3 alt metoda ayrıldı)
- ✅ main_window.py 3645 → 1213 (yeni `widgets.py`, `env_list.py`, `env_operations.py`, `env_export.py`, `quicklaunch.py`, `window_theme.py`, `window_menu.py`, `linux_fixes.py`) — fonksiyonel test geçti
- ✅ package_panel.py 5390 → 615 (yeni `package_panel_common.py`, `launcher_ui.py`, `launcher_run.py`, `launcher_shortcuts.py`, `tab_builders.py`, `env_state.py`, `package_ops.py`, `package_export.py`, `package_misc.py`) — fonksiyonel test geçti (poetry/uv/venv create/install/clone/delete hepsi ✅)

## 🎉 BÜYÜK DOSYA BÖLME REFACTOR PROJESİ TAMAMLANDI

8 dosya, toplam ~16.700 satır bölündü, 30+ yeni mixin/common dosyası oluşturuldu. Uygulanan metodoloji `VenvStudio_Handoff.md`'de **"🧩 BÜYÜK DOSYA BÖLME — YÖNTEM"** başlığı altında kalıcı olarak belgelendi — gelecekte benzer bir ihtiyaç olursa oradaki adımlar takip edilecek.

**Kalan büyük dosya yok.** Sıradaki öncelik için TODO'nun geri kalanına bak (aşağıdaki bug/feature maddeleri).

**⚠️ Refactor'da öğrenilen tuzaklar (venv_manager mixin'den):**
- Mixin'de class-level attribute → `type(self).foo`, `ClassName.foo` DEĞİL (isim tanımlı değil).
- Her mixin kendi importlarını içermeli (os/json/_run vb. kolayca kaçar).
- import+MRO+parite testi YETMEZ — runtime path'lerini gerçekten çalıştır (fonksiyonel test).
- **main_window.py bölmesinde 2 kez eksik import kaçtı** (`tr` → `env_list.py`, `Signal` → `quicklaunch.py`, ikisi de metod içinde tanımlı local class'ta kullanılıyordu, elle grep taramasında gözden kaçtı). Çözüm: `py_compile` YETMEZ (sadece syntax kontrol eder, isim çözümlemez) — bundan sonra her mixin dosyasında **`python3 -m pyflakes <dosya>.py`** çalıştırılacak (undefined-name/F821 tespiti için), package_panel.py bölmesinde ilk adım olsun.

---

## ✅ FIX YAPILDI — Toolchain Manager: `venv` satırında Install/Upgrade crash

**Nerede:** `settings_toolchain.py` → `_tc_do_install` (Toolchain Manager sekmesi).
**Bulunduğu tarih:** settings_page.py refactor sonrası fonksiyonel testte ortaya çıktı, sonra env_dialog.py refactor testinde tekrar reprodüklendi.

**Gerçek sebep (ilk teşhis — `_spa()` eksikliği — YANLIŞTI, düzeltiyorum):**
`_TC_TOOLS` listesinde `("venv", None, "venv", "🐍")` — `venv`'in `pkg` değeri `None`, çünkü venv pip ile ayrı kurulan bir paket değil, Python stdlib'inin parçası. `venv` satırında **Upgrade (System scope)** butonuna basılınca `None` değeri `_pip_cmd` listesine (`[py_exe, "-m", "pip", "install", None, ...]`) karışıyor, `subprocess.run()` bunu bir path/str bekleyen argüman olarak açmaya çalışınca:
```
TypeError: expected str, bytes or os.PathLike object, not NoneType
```
`_tc_do_remove`'da zaten `if tool in ("pip", "venv"): return False, "...core Python component"` guard'ı vardı — ama `_tc_do_install`'da eşdeğeri yoktu.

**Fix (v3 — gerçek update-checker):** v2'de buton direkt genel "Download Python" dialogunu açıyordu, gerçek bir karşılaştırma yapmıyordu — kullanıcı bunun yeterli olmadığını belirtti. Yeni `_tc_check_python_update()` metodu:
- Tablodaki venv satırının Version kolonundan mevcut seçili Python sürümünü okuyor (örn. "3.14.6")
- `get_available_versions()` ile (aynı fonksiyon, `PythonDownloadDialog`'un kullandığı — yeni indirme mantığı YOK) mevcut en yeni standalone build'i çekiyor
- Sürüm karşılaştırması yapıyor: daha yeni bir sürüm varsa "Update Available: X mevcut, indirmek ister misin?" (Yes → download dialogunu açar); zaten en güncelse "Up to Date" mesajı gösteriyor
- Ağ çağrısı `WorkerThread` ile arka planda yapılıyor (UI donmuyor), `QProgressDialog` ile "Checking for newer Python versions..." gösteriliyor

Mock testte iki senaryo da (eski sürüm → update önerisi, güncel sürüm → "up to date") doğrulandı.

**Not (v3.1):** İlk teslimde `_do()` fonksiyonu parametresiz tanımlanmıştı, ama bu dosyadaki `WorkerThread` her zaman `self.func(callback=...)` şeklinde çağırıyor (dosyadaki diğer 6 `_do(callback=None)` ile de doğrulandı) — `TypeError: got an unexpected keyword argument 'callback'` ile crash oluyordu. `_do(callback=None)` yapılarak düzeltildi.

---

## ✅ v1.5.0 → v1.6.0'da ÇÖZÜLEN (AppImage tam çözümü + refactor + fix'ler)

**AppImage (yıllardır bozuktu — hepsi Bayram'ın makinesinde kanıtlandı):**
- **Fork bomb (v1.5.2):** `main.py::_check_qt_xcb_deps` frozen modda `sys.executable -c "..."` çağırıp GUI'yi recursive relaunch ediyordu → 90+ process → donma. Frozen guard'la çözüldü. AppImage artık **açılıyor**. (B110 AppImage Quick Launch ve genel AppImage-açılmıyor durumu bununla düzeldi.)
- **Renkli emoji (v1.5.7):** bundle libfreetype+libharfbuzz+libpng16 silindi → sistem kütüphaneleriyle CBDT PNG renkli emoji render ediliyor. (B140/B152/F125 emoji sorunlarının AppImage kısmı.)
- **Emoji Font Missing dialog (v1.5.6):** `main_window._apply_linux_emoji_fix` frozen'da atlanıyor.
- **Font monospace/jagged (v1.6.0):** bundled fonts.conf artık host config include + strong `sans-serif→Cantarell` alias + hinting içeriyor; apprun-hook APPDIR'i `BASH_SOURCE`'tan türetip FONTCONFIG_FILE'ı doğru set ediyor.

**Refactor (main_window.py bölme — 1. adım):**
- 5 QThread worker → yeni `src/gui/workers.py` (~127 satır azaldı). Junk "(a copy from computer KTN)" dosyaları silindi. Bu, aşağıdaki "main_window.py — BEKLIYOR" REFACTOR maddesinin ilk adımıdır (worker kısmı ✅, env/ql kısmı hâlâ açık).

**Log (logger.py):** RichHandler'a `log_time_format` verildi — konsol banner MM/DD/YY tutarsızlığı düzeldi.

**Rename/Clone (venv_manager.py):** folder-only rename artık `_relocate_venv_paths` ile pyvenv.cfg + bin/ scriptlerini yeni path'e yazıyor (B51 "Windows Only Name Rename sonrası pip bozuluyor" + genel folder-rename-pip-kırılması çözüldü). clone_venv kırık/dangling pip symlink'e karşı `python -m pip freeze` fallback'i aldı.

**Kalan refactor adımları:** `PathElideMiddleDelegate`+`SidebarButton` → `widgets.py`; export metodları (7 tane) → mixin/`env_export.py`; main_window env/ql metodları → ayrı modül.

---

## ✅ v1.4.98'de ÇÖZÜLEN (Windows PowerShell 7 + Themes)

- **PowerShell 7+ (pwsh) terminal listesine eklendi:** Windows combo'da `shutil.which("pwsh")` ile sürümden bağımsız algılama. `open_terminal_at` pwsh terminal_type desteği. "PowerShell" → "Windows PowerShell" etiketi (5.1 vs 7+ ayrımı).
- **"CLI/TUI Operations" → "🎨 Themes":** GroupBox başlığı değişti.

## 🆕 AÇIK İŞLER — Terminal Tema & Görünüm

- **[Yeni özellik] Terminal açıldığında TUI + temasını göster:** Üst bilgi satırında font ve emoji font gösteriliyor; yanına varsa aktif TUI (oh-my-posh / starship) ve seçili temasını da ekle.
- **[Yeni özellik] Settings'teki seçili tema neyse onu göster:** Görünen tema, Settings altında kayıtlı/aktif tema ile tutarlı olmalı.
- **[Bug — Linux] `sudo: a terminal is required to read the password`:** `_detect_terminals` (settings_appearance.py) GUI'den `sudo apt-get install` doğrudan çağrılıyor; askpass yok → patlıyor. pkexec'e düş veya `SUDO_ASKPASS`/`-S` ile çöz.
- **[Bug — Windows] oh-my-posh kurulumu eski Windows PowerShell profiline yazıyor:** pwsh 7 profiline (`~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1`) yazmalı. pwsh artık algılandığı için çözülebilir.

---

## ✅ v1.4.94'te ÇÖZÜLEN BUG'LAR (Settings > Python Versions > Download Python)

- **python.org Windows MSI/EXE artık sessizce kuruluyor:** `msiexec /qn` + per-user flags (UAC yok). v1.4.64'te eklenen "manuel kurulum yap" placeholder davranışı silindi.
- **Bozuk install_dir kalıntısı:** `install_dir.exists()` kontrolü yetersizdi — bozuk EXE kalıntısı duruyorsa "already installed" yalanı çıkıyordu. Artık `get_python_exe(install_dir)` ile içerde gerçek python varlığı doğrulanıyor, yoksa wipe + retry.
- **PowerShell BOM:** `Out-File -Encoding utf8` Windows'ta BOM prepend ediyordu, `startswith("OK")` False döndürüyordu → System Install başarılı olsa bile "System install failed: OK" hatası çıkıyordu. Fix: `encoding='utf-8-sig'` (BOM otomatik kırp).
- **`pip_exe` NameError:** Set System Default fonksiyonunda `pip_exe` kullanılıyor ama hiç tanımlanmamıştı (cross-platform tanım eklendi).

**Detaylar:** Handoff v1.4.94 oturum.

### ⚠️ Açık Konu (gelecek versiyon)
- python.org indirilebilir versiyonlar listesi **"0 MB"** gösteriyor. python.org HTML scrape ettiği için size yok. HEAD request veya release notes parse ile çekilebilir.

---

## ✅ v1.4.92'de ÇÖZÜLEN BUG'LAR + DAVRANIŞ DEĞİŞİKLİĞİ

- **Pipx Silme = Klasörü Tamamen Sil + Boş Kurulum (davranış değişikliği):** Eski B182 davranışı sadece marker dosyasını siliyordu, kullanıcı GUI'de "Delete" basıp 1.8 GB klasörün yerinde kalmasıyla şaşırıyordu. Yeni davranış: `_robust_rmtree(venv_path)` ile tüm `~/.local/share/pipx/` silinir, ardından `ensure_pipx_env()` ile boş bir pipx home kurulur. Confirm dialog metni güncellendi.
- **Pipx Size = ~0 B Bug'ı:** `venv_manager.py::list_venvs_fast` pipx size hesaplaması `venvs/` only + symlink filter kullanıyordu — ama pipx symlink kullanır (`venvs/<pkg>/lib/.../site-packages/` `shared/`'a link). Çözüm: tüm `_pipx_home_path` (venvs + shared + py) symlink filter olmadan tara. `write_cache` çağrı sırası da düzeltildi (önce hesapla, sonra yaz). Aynı bloğun **duplicate kopyası** vardı, doğru sonucu eziyordu — silindi.
- **Pipx Readd Sonrası Header Refresh Yapılmıyordu:** `_readd_empty_pipx_row` `Size` hücresine `"—"` yazıyordu, üst istatistik bandı `pipx • 1 env(s) • 199.8 MB` (eski değer) gösteriyordu. Fix: Size `"0.0 B"` (klasör silindi, gerçekten boş) + `_update_env_summary()` çağrısı (`hasattr` korumalı).

**Detaylar:** Handoff v1.4.92 oturum + KESİN KURALLAR #14 alt-kurallar F/G/H.

---

## ✅ v1.4.91'de ÇÖZÜLEN EK BUG'LAR (numara verilmemiş — buraya kayıt)

Bu oturumda numarasız ama önemli bug'lar fix edildi. İleride benzer sorun çıkarsa buradan çözüm yolu bulunabilir:

- **B185 — Windows Kapanış 5-10sn Kasma:** `closeEvent`'te worker `wait()` süreleri 3000/1000ms idi → 500/500ms (B186 fix'iyle birleştirildi). Worker'lar event loop'lu olmadığı için `quit()` zaten no-op, bekleme boşa.
- **B186 — `QThread: Destroyed while thread '' is still running` FATAL:** `settings_toolchain.py`'deki 6 `WorkerThread(_do)` çağrısı `parent=None` ile yaratılıyordu → `findChildren(QThread)` bulamıyordu → orphan teardown → FATAL. Çözüm: `WorkerThread.__init__`'a keyword-only `parent=None` ekledik, settings_toolchain çağrılarını `parent=self` ile düzelttik. Ek olarak `_UpdateWorker(self)` parent eklendi ve `_check_update_timer` üye değişkeni `closeEvent`'te `stop()` çağrılıyor.
- **Path kolonu kesik gösterim:** `PathElideMiddleDelegate(QStyledItemDelegate)` eklendi (`main_window.py`), env tablosu Path kolonu için `setItemDelegateForColumn(2, ...)`. Drive harfi + env adı görünür kalır, orta `…` ile kısalır.
- **Pipx Routing Bozuk (`[Errno 2]` patlaması):** Pipx tracker marker writer (`main_window.py::_readd_empty_pipx_row`) `"env_type": "pipx"` yazıyordu ama reader (`package_panel.py::set_venv`) `"type"` arıyordu → fallback `"system_tools"` → pip yoluna düşüş → `<pipx>/bin/python` yok → patlama. Writer `"type"`'a alındı, reader **geriye uyumlu** yapıldı: `_m.get("type") or _m.get("env_type") or "system_tools"`. Ek olarak `_install_packages` pre-flight check'leri pipx için skip edildi (`if _env_type != "pipx":`).
- **Pipx Preset/Catalog Library Install:** `_do_pipx_install`'da `cmd.append("--include-deps")` eklendi. Pipx default'ta sadece CLI tool yükler ("No apps associated with package X"); `--include-deps` library paketleri için pipx'in **kendi tasarımcılarının** sağladığı resmi workaround. ML Starter (numpy/pandas/sklearn/...) artık çalışıyor.

**Detaylar:** Handoff'ta v1.4.91 oturum kaydı + KESİN KURALLAR #14 (pipx).

---

## 🧪 ÖNCELIK #0 — SİSTEMATİK BUTON & SEKME TEST TURU

**Amaç:** Tüm UI butonlarının ve sekmelerinin her env tipi için çalıştığından emin olmak. Hatalar bulundukça düzeltilecek.

**Test yöntemi:** Bayram tek tek butonlara basar, hataları aşağıdaki formatla bildirir. Claude düzeltir.

### Hata Bildirme Formatı

```
Buton: [hangi buton/sekme/aksiyon]
Env Tipi: [venv / uv / Poetry / Conda / pipx]
Beklenen: [ne olmalıydı]
Gerçekleşen: [ne oldu]
Traceback: [varsa terminal çıktısı]
```

---

### 📍 Environments Sayfası — Butonlar

Her buton, her env tipi için ayrı ayrı test edilecek.

| # | Buton | venv | uv | Poetry | Conda | pipx |
|---|-------|------|----|--------|-------|------|
| 1 | Manage Packages | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 2 | Open Terminal | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 3 | Clone | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 4 | Rename (Name) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 5 | Rename (Full) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 6 | Export ▾ | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 7 | Make Default | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 8 | Delete | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| 9 | Refresh | ⏳ | — | — | — | — |

**Durum işaretleri:** ⏳ test edilmedi · ✅ çalışıyor · ❌ hata var · ⚠ kısmen çalışıyor

---

### 📍 Export ▾ — Alt Seçenekler

Her format, her env tipi için test edilecek.

| Format | venv | uv | Poetry | Conda | pipx |
|--------|------|----|--------|-------|------|
| requirements.txt | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| environment.yml | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| pyproject.toml | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Dockerfile | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| (diğer formatlar) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

---

### 📍 + New Environment — Tüm Backend'ler

| Backend | Test |
|---------|------|
| venv | ⏳ |
| uv | ⏳ |
| Poetry | ⏳ |
| Conda | ⏳ |
| pipx | ⏳ |

---

### 📍 Packages Sayfası — Sekmeler

#### Launch Sekmesi
Her launcher kartı (JupyterLab, Jupyter Notebook, Orange Data Mining, Spyder IDE, IPython, Streamlit, Gradio, Dash, Panel, vb.) için:

| Aksiyon | Test |
|---------|------|
| ► Launch | ⏳ |
| Uninstall | ⏳ |
| 📌 Create Desktop Shortcut | ⏳ |
| 📋 Copy Install Command | ⏳ |
| 📋 Copy Run Command | ⏳ |
| 🔗 Links toggle | ⏳ |
| Not-installed → Launch (auto-install) | ⏳ |

#### Installed Sekmesi
| Aksiyon | Test |
|---------|------|
| Paket listesini görüntüle | ⏳ |
| Sağ-tık → Package Info | ⏳ |
| Sağ-tık → Uninstall | ⏳ |
| Sağ-tık → Update | ⏳ |
| Multi-select uninstall | ⏳ |
| Search/filter | ⏳ |

#### Catalog Sekmesi
| Aksiyon | venv | uv | Poetry | Conda | pipx |
|---------|------|----|--------|-------|------|
| Paket arama | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Kategori filtreleme | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Install butonu | ⏳ | ⏳ | ⏳ | ⏳ | ✅ (v1.4.91) |
| Package Info dialog | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Home/PyPI link butonları (B171 ile bağlantılı) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

#### Presets Sekmesi
| Aksiyon | venv | uv | Poetry | Conda | pipx |
|---------|------|----|--------|-------|------|
| Preset listesi görünüyor | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| "Install Preset" çalışıyor | ⏳ | ⏳ | ⏳ | ✅ (v1.4.91) | ✅ (v1.4.91) |
| "Installed" badge doğru | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Preset içeriği görüntüleniyor | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

#### Manual Install Sekmesi
| Aksiyon | venv | uv | Poetry | Conda | pipx |
|---------|------|----|--------|-------|------|
| Paket adıyla install | ⏳ | ⏳ | ⏳ | ⏳ | ✅ (v1.4.91 — `black`) |
| Versiyon belirterek install (`pkg==1.2.3`) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Multiple paket aynı anda | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Hatalı paket adı hata mesajı | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

---

---

### 📍 Settings Sayfası — Tüm Bölümler

#### ⚙️ General
| Aksiyon | Test |
|---------|------|
| Default base directory değiştir | ⏳ |
| Auto-refresh toggle | ⏳ |
| Confirm before delete toggle | ⏳ |
| Create Desktop Shortcut butonu | ⏳ |
| Reset to defaults | ⏳ |

#### 🎨 Appearance
| Aksiyon | Test |
|---------|------|
| Theme combo (dark / light-latte / light-github / vb.) | ⏳ |
| Font family değiştir | ⏳ |
| Font size değiştir | ⏳ |
| UI Scale (varsa F168) | ⏳ |
| Theme persist (kapat-aç) | ⏳ |

#### 🐍 Python Versions
| Aksiyon | Test |
|---------|------|
| Yüklü Python versiyonları listele | ⏳ |
| Yeni Python versiyonu indir (Astral CDN) | ⏳ |
| Python uninstall | ⏳ |
| Python set as default | ⏳ |
| Mirror seçimi (F123) | ⏳ |

#### 📦 Package Managers (KRİTİK)
| Tool | Detect | Install | Update | Uninstall | Path doğru |
|------|--------|---------|--------|-----------|-----------|
| pip | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| uv | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| poetry | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| pipx | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| conda / micromamba | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| mamba | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| virtualenv | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| pixi (varsa) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |

**Kontrol noktaları:**
- User vs System install scope toggle (PEP668)
- Module-only fallback (`python -m pipx`) çalışıyor mu
- pkexec / UAC şifre dialog'u çıkıyor mu
- Install başarısızsa açık terminal komutu gösteriyor mu

#### 🖥️ Terminal Emulators (F135)
| Tool | Detect | Install | Uninstall | Launch |
|------|--------|---------|-----------|--------|
| WezTerm | ⏳ | ⏳ | ⏳ | ⏳ |
| Alacritty | ⏳ | ⏳ | ⏳ | ⏳ |
| Tabby | ⏳ | ⏳ | ⏳ | ⏳ |
| Ghostty | ⏳ | ⏳ | ⏳ | ⏳ |
| Hyper | ⏳ | ⏳ | ⏳ | ⏳ |
| Kitty (varsa) | ⏳ | ⏳ | ⏳ | ⏳ |

#### 🎨 CLI/TUI Tools (KRİTİK — F171, F172, F173, F174)
| Tool | Detect | Install | Configure | Uninstall | Theme switch |
|------|--------|---------|-----------|-----------|--------------|
| oh-my-posh | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| Starship | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| zoxide | ⏳ | ⏳ | — | ⏳ | — |
| fzf | ⏳ | ⏳ | — | ⏳ | — |
| eza / lsd | ⏳ | ⏳ | — | ⏳ | — |
| bat | ⏳ | ⏳ | — | ⏳ | — |
| ripgrep | ⏳ | ⏳ | — | ⏳ | — |
| fd | ⏳ | ⏳ | — | ⏳ | — |
| btop / htop | ⏳ | ⏳ | — | ⏳ | — |
| tmux / zellij | ⏳ | ⏳ | ⏳ | ⏳ | — |
| neovim | ⏳ | ⏳ | — | ⏳ | — |

**oh-my-posh özel testleri (B181 v3 sonrası):**
- Install sonrası `~/.posh/oh-my-posh` ve `~/.posh/themes/` doğru mu
- 122 tema themes.zip'ten indi mi
- Auto-configure çalıştı mı (default tema)
- `.bashrc` / `$PROFILE` marker block'u eklendi mi
- Theme değiştirme: eski block siliniyor, yenisi yazılıyor mu
- Uninstall: `~/.posh/` siliniyor + shell init satırları temizleniyor mu

**Terminal restart popup (F174):**
- Configure sonrası popup çıkıyor mu
- Platform-specific komutlar doğru mu
- 📋 Komutu Kopyala çalışıyor mu

#### 🔤 Nerd Fonts (F172 ile bağlantılı)
| Aksiyon | Test |
|---------|------|
| Yüklü font listesi | ⏳ |
| Font kurulum (FiraCode, JetBrainsMono, Hack, vb.) | ⏳ |
| Font uninstall | ⏳ |
| Kurulum sonrası terminal profili dialog'u (F172) | ⏳ |
| "Default yap" işaretle | ⏳ |
| gnome-terminal / mate-terminal / konsole / alacritty / kitty / wezterm adapter'ları | ⏳ |
| macOS Terminal.app / iTerm2 (henüz yok) | ❌ |
| Windows Terminal (henüz yok) | ❌ |

#### 🛠️ Editor Integration
| Editor | Detect | Open in editor | Add as launcher |
|--------|--------|----------------|-----------------|
| VS Code | ⏳ | ⏳ | ⏳ |
| Cursor | ⏳ | ⏳ | ⏳ |
| Windsurf | ⏳ | ⏳ | ⏳ |
| Zed | ⏳ | ⏳ | ⏳ |
| PyCharm | ⏳ | ⏳ | ⏳ |
| Spyder (F136 — eklenecek) | ❌ | ❌ | ❌ |

#### 📚 Catalog Yönetimi
| Aksiyon | Test |
|---------|------|
| Catalog yenile | ⏳ |
| Custom paket ekle | ⏳ |
| Paket bilgisi düzenle (F124) | ⏳ |

#### 🌐 Channels / Mirrors (F175 — yoksa not düş)
| Aksiyon | Test |
|---------|------|
| pip index URL ayarla | ⏳ |
| conda channel ekle/sil | ⏳ |
| Per-env channel override | ⏳ |

---

### 🐛 Bulunan Buglar

(Bayram test ettikçe buraya eklenecek)

---

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

---

## 🚨🚨 ACİL — KULLANICI BİLDİRİMLERİ (Birden çok platformda kritik buglar)

### 🚨 B180 — KRİTİK: Installed Tab Açılınca Crash (Win 11 + Debian, Python 3.13.0)

**Bildiren:** Eyüp (Win 11, Python 3.13.0) ve Debian (Python 3.13.x) — v1.4.88

**Hata:**
```
SystemError: ../Objects/longobject.c:1481: bad argument to internal function
File "package_panel.py", line 2454, in _create_installed_tab
    self.packages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
```

**Senin makinende çalışıyor (Win 11, Python 3.13.13)** — sebep büyük ihtimalle **PySide6 6.10.2 + Python 3.13.0/3.13.x eski patch sürümleri** uyumsuzluğu. `setSectionResizeMode(0, QHeaderView.Stretch)` C-level int dönüşümünde patlıyor.

**Yan etki:** sys.excepthook da `RecursionError` veriyor (logger.py:546 → traceback.format_exception → ast import → shibokensupport recursion).

**Olası çözümler:**
1. **`int` cast ekle:** `setSectionResizeMode(0, int(QHeaderView.ResizeMode.Stretch))` — enum int dönüşümünü explicit yap
2. **Try/except ile sarmala:** Header resize fail olursa default davranışla devam et
3. **PySide6 minimum sürüm bump:** 6.10.2 → 6.10.3+ (eğer patch varsa)
4. **Python 3.13.0/3.13.1 desteğini düş:** README'de "Python 3.13.5+" iste

**Excepthook fix de lazım:** `logger.py:546` `traceback.format_exception` shibokensupport ile sonsuz döngüye giriyor. Onu da güvenli hale getir.

**Dosyalar:** `src/gui/package_panel.py:2454` (ve diğer setSectionResizeMode çağrıları), `src/utils/logger.py:546`

**Öncelik:** 🚨 KRİTİK — birden çok kullanıcı etkileniyor, uygulama tamamen kullanılamaz hale geliyor

---

### 🚨 B181 — KRİTİK: TUI (oh-my-posh) Linux'ta Yükleme Crash

**Hata:**
```
File "settings_appearance.py", line 248, in _cli_install
    self.cli_log.clear()
AttributeError: 'SettingsPage' object has no attribute 'cli_log'
```

**Sebep:** `_cli_install` metodu `self.cli_log` widget'ına erişmeye çalışıyor ama o widget tanımlanmamış (SettingsPage'de yok).

**Fix:** Ya `self.cli_log` widget'ını init'te oluştur, ya da `_cli_install` içinde varlığını kontrol et:
```python
if hasattr(self, 'cli_log') and self.cli_log:
    self.cli_log.clear()
```

**Dosyalar:** `src/gui/settings_appearance.py:248` (ve `cli_log` referans eden tüm yerler)

**Öncelik:** 🚨 KRİTİK — TUI tools yüklenemiyor

---

### ✅ B182 — pipx Silme Sonrası Tablo Cache'den Yenilenmiyor (TAMAMLANDI v1.4.90)

**Sorun:** pipx env silindikten sonra env tablosunda hâlâ görünüyor. **Uygulama kapatılıp tekrar açılınca** kayboluyor → cache invalidation eksik.

**ASIL BUG ÇOK DAHA KÖTÜ ÇIKTI:** `delete_venv` pipx için `shutil.rmtree(~/.local/share/pipx)` yapıyordu → pipx'i tamamen + tüm kurulu app'leri (black, ruff, vs.) **siliyordu**!

**Fix v1.4.90 (`src/core/venv_manager.py`):**
- pipx için sadece `.venvstudio_env` marker dosyası silinir, dizin korunur
- Confirm dialog: "pipx itself and apps NOT removed"

**Fix v1.4.90 (`src/gui/main_window.py`):**
- `_remove_env_row_inplace` — surgical row removal (full refresh yok)
- `_readd_empty_pipx_row` — silme sonrası boş pipx satırı otomatik geri eklenir
- `_refresh_current_env_row(pkg_count)` — install/uninstall sonrası sadece o satır güncellenir
- Race condition fix: `Signal(int)` ile authoritative pkg_count taşınır, async refresh sonrası emit edilir

**Test edildi:** Linux (Bayram). macOS/Windows test bekleniyor.

---

### 🟡 F168 — Scale / Zoom Özelliği (Genel UI Boyutlandırma)

**Hedef:** Tüm UI bileşenleri (butonlar, label'lar, fontlar) tek bir scale değeriyle büyütülüp küçültülebilsin. Bazı ekranlarda sığmıyor, bazılarında çok küçük kalıyor.

**Kapsam:**
- View → Scale slider (50% – 200%)
- Veya Settings → Appearance → "UI Scale: [50% — 200%]"
- Tüm widget boyutlarına çarpan uygulanır
- Settings'e kaydedilir, açılışta uygulanır
- Min/max sınırlar (50%-200%)
- Reset Scale (Ctrl+0) — F154 ile entegre

**F154 (Zoom) ile fark:** F154 sadece font, F168 her şey (padding, margin, button height, icon size). Birlikte düşünülebilir veya tek özellik.

**Öncelik:** 🔴 Yüksek — erişilebilirlik kritik, çok ekran çeşitliliği var

---

### 🟡 F169 — FreeBSD / BSD Desteği + AppImage Benzeri Dağıtım

**Hedef:** BSD ailesi için (FreeBSD, OpenBSD, NetBSD) destek + portable paketleme (AppImage benzeri).

**Kapsam:**
- FreeBSD'de test: `freebsd-version`, paket yöneticisi `pkg`, Python ports
- BSD path'leri farklı olabilir (`/usr/local/bin/python3` vs `/usr/bin/python3`)
- `platform_utils.py`'ye BSD detection ekle
- Paketleme: AppImage (Linux only) veya benzer **portable bundle** (PyInstaller `--onefile`)
- BSD için `.txz` paketi (FreeBSD pkg format)

**Mevcut destek:** Linux ✅, macOS ✅, Windows ✅. BSD ❌.

**Öncelik:** 🟡 Orta — niche kullanıcı, ama tamamlayıcı

---

### 🟡 F170 — Conda Sistem Çapında Kurulum (Global Path)

**Hedef:** Conda yüklerken **sadece local user'a** değil, **sistem geneline** de yüklenebilsin. Global PATH'e ekle.

**Şu an:** Conda local'e (`~/miniconda3` veya `~/.conda`) yükleniyor, global yok.

**Kapsam:**
- Conda install dialog'unda checkbox: "Install system-wide (requires admin/sudo)"
- Linux/macOS: `/opt/conda` veya `/usr/local/conda` + `/etc/profile.d/conda.sh`
- Windows: `C:\ProgramData\miniconda3` + sistem PATH'e ekle (admin)
- Sudo/admin elevation: Linux `pkexec`, Windows UAC prompt

**Öncelik:** 🟡 Orta — multi-user makinelerde faydalı

---

### 🟡 F171 — oh-my-posh Theme Yönetimi + .bashrc Otomatik Setup

**Hedef:** oh-my-posh kurulumundan sonra:
1. Theme dropdown'dan seç
2. `.bashrc` (Linux/macOS) veya PowerShell `$PROFILE` (Windows) otomatik düzenle
3. Tema değiştirme Settings altından yapılabilsin
4. "Restart your terminal" mesajı göster

**Mevcut sorun:**
- Theme'lerin önünde gereksiz tick var (zaten TUI/CLI Tools onunde tick var)
- Otomatik kurulum sonrası `.bashrc`'ye eklenmiyor

**.bashrc örneği:**
```bash
####### entered by VenvStudio ########
export PATH="/home/bayram/.posh:$PATH"
eval "$(oh-my-posh init bash --config /home/bayram/.posh/themes/<tema_adi>.omp.json)"
######################################
```

**Windows PowerShell `$PROFILE` örneği:**
```powershell
####### entered by VenvStudio ########
$env:PATH = "$env:USERPROFILE\.posh;$env:PATH"
oh-my-posh init pwsh --config "$env:USERPROFILE\.posh\themes\<tema_adi>.omp.json" | Invoke-Expression
######################################
```

**Kurulum yolu:**
- Linux/macOS: `~/.posh/` ve `~/.posh/themes/`
- Windows: `%USERPROFILE%\.posh\` ve `%USERPROFILE%\.posh\themes\`
- `~` yerine tam path kullan (script güvenliği)

**Settings → Appearance → "Posh Theme" dropdown:**
- Yüklü tema listesi
- Değiştir → `.bashrc` / `$PROFILE` güncelle → "Terminali yeniden başlatın" toast

**UI temizlik:**
- Theme'lerin önündeki tick kaldırılsın (TUI/CLI Tools'ta zaten var)

**Dosyalar:** `src/gui/settings_appearance.py`, `src/core/posh_theme_manager.py` (yeni), `src/utils/shell_profile.py` (yeni — .bashrc/$PROFILE editing)

**Öncelik:** 🟡 Orta — UX katmanı, oh-my-posh kullanıcılarını mutlu eder

---

### 🧪 F172 — Terminal Otomatik Profil Kurulumu (KISMEN YAPILDI v1.4.89, TEST AŞAMASINDA)

**Durum:** Linux'ta gnome-terminal/mate-terminal/konsole/alacritty/kitty/wezterm için adapter'lar yazıldı (`src/core/terminal_profile_setup.py`). Nerd Font kurulduktan sonra otomatik dialog açılıyor: "Terminalin algılandı, profil oluşturayım mı?" + "Default yapayım mı?".

**Test edilmesi gerekenler:**
- Linux: gnome-terminal ✅ (Bayram Debian'da test etti, kabul edildi gibi — kesin doğrulama bekleniyor)
- Linux: mate-terminal, konsole, alacritty, kitty, wezterm — test edilmedi
- macOS: **HİÇ DESTEK YOK** — Terminal.app ve iTerm2 için adapter eklenmeli
- Windows: **HİÇ DESTEK YOK** — Windows Terminal (`settings.json` JSON edit) ve cmd/PowerShell adapter'ları eklenmeli

**Yapılacak:**
- macOS Terminal.app için plist yazıcı (`~/Library/Preferences/com.apple.Terminal.plist`)
- macOS iTerm2 için plist yazıcı (`~/Library/Preferences/com.googlecode.iterm2.plist`)
- Windows Terminal: `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbcw\LocalState\settings.json` JSON edit
- Tüm terminallerde test edip bug'ları topla

**Dosyalar:** `src/core/terminal_profile_setup.py` (var, genişletilecek)

---

### 🟡 F173 — Tema Değiştirme (Change Theme) Butonu

**Hedef:** TUI tools yüklendikten **sonra** Uninstall butonunun yanında veya combo'nun yanında **"Apply" / "Change Theme" / "Switch"** gibi bir buton olsun. Configure butonu zaten var ama install öncesi de görünüyor — kafa karıştırıcı olabilir.

**Mevcut akış (v1.4.88'den sonra):**
- Install → otomatik default tema configure ediliyor (jandedobbeleer / Tokyo Night)
- Kullanıcı tema değiştirmek isterse → Combo'dan seç → Configure'a bas → eski init satırı silinip yenisi yazılıyor (`_inject_shell_config` overwrite)

**Sorulacak:** Bu yeterli mi yoksa Configure butonunun adı/davranışı değişmeli mi?
- Seçenek A: Mevcut (Configure her zaman aktif)
- Seçenek B: Install öncesi sadece "Install", sonrası "Apply theme" (ad değişir)
- Seçenek C: İki ayrı buton (Apply / Reset)

**Otomatik aktivasyon:**
- `.bashrc` güncelleniyor ama yeni terminal açmadan etki yok (subprocess shell'i izole)
- VenvStudio içindeki açık terminallere otomatik uygulanamaz (Linux/macOS'ta `source` subprocess'te işe yaramaz)
- F174 (popup) ile "Yeni terminal aç" mesajı gösterilecek

**Dosyalar:** `src/gui/settings_appearance.py`

**Öncelik:** 🟡 Orta — UX iyileştirmesi, kullanıcıya net mesaj

---

### 🟡 F174 — TUI Yükleme/Configure Sonrası "Terminali Yeniden Başlat" Pop-up

**Hedef:** oh-my-posh / Starship / herhangi bir TUI tool kurulduktan veya tema değiştirildikten sonra kullanıcıya bilgilendirici bir pop-up:

```
✅ oh-my-posh configured with theme: jandedobbeleer

Etkili olması için terminalinizi yeniden başlatın.

Veya mevcut terminal oturumunda:
  • Linux/macOS bash: source ~/.bashrc
  • Linux/macOS zsh:  source ~/.zshrc
  • Linux/macOS fish: source ~/.config/fish/config.fish
  • Windows PowerShell: . $PROFILE
  • Windows cmd: yeni cmd aç (source desteği yok)

[ 📋 Komutu Kopyala ]   [ Tamam ]
```

**Platform-specific komutlar:**
- Linux/macOS bash: `source ~/.bashrc`
- Linux/macOS zsh: `source ~/.zshrc`
- Linux/macOS fish: `source ~/.config/fish/config.fish`
- Windows PowerShell: `. $PROFILE`
- Windows cmd: yok (yeni cmd açmak gerek)

**Otomatik source mümkün mü?**
- VenvStudio içinden `subprocess.run(["bash", "-c", "source ~/.bashrc && bash"])` çalıştırılabilir ama sadece o subprocess'i etkiler, kullanıcının açtığı diğer terminalleri etkilemez
- En temiz yol: pop-up + kopyala butonu + "yeni terminal aç"

**Dosyalar:** `src/gui/settings_appearance.py` (`_after_nerd_font_install` ve `_cli_done` callback'leri), yeni helper `src/utils/shell_reload_helper.py` olabilir

**Öncelik:** 🟡 Orta — kullanıcı şu an "neden çalışmıyor?" diye düşünüyor, terminal restart gerektiğini bilmiyor

---

### ✅ B183 — Learn Sayfası ve Settings'teki Yeni Bloklar Light Tema'ya Geçmiyor (TAMAMLANDI v1.4.90)

**Sorun:** Tema değiştirildiğinde Learn sayfası, Settings'teki yeni bloklar, Packages tab'ları, code block'lar dark tema'da kalıyordu. Hatta env tablosu light tema'da okunaksızdı.

**Çözüm — Generic Palette Sweep:**
- `_refresh_styles` (settings_page) ve `apply_theme` (package_panel, learn_page) artık eski palette renklerini yenisiyle **otomatik değiştirir** — hardcoded widget listesi yok
- `_last_palette` snapshot tutulur, sonraki tema değişiminde swap yapılır
- Yeni widget eklenince kod güncellemeye gerek yok

**Hardcoded renkler temizlendi:**
- env_selector, sidebar launcher button, Presets "Installed" button (`#1e1e2e`, `#cdd6f4`, `#a6e3a1`, `#313244`, `#89b4fa`)
- Code block'lar (`#11111b`, `#181825`, `#cdd6f4`)
- Tip/Note/Warning callout box'ları (sabit dark renkler → palette + 22 alpha tint)

**Env tablosu light tema:**
- Font 16px hardcoded + bold (QSS ile zorla)
- Light theme detection (perceived luminance)
- Light için koyu kontrast renkler: uv `#8a6d00`, poetry `#5b2c6f`, pipx `#0c5a72`, conda `#1b5e20`
- `_apply_theme` artık env_table'ı re-render eder

**Dosyalar:** `src/gui/main_window.py`, `src/gui/settings_page.py`, `src/gui/package_panel.py`, `src/gui/learn_page.py`

**Test:** Linux (Bayram). macOS/Windows test bekleniyor.

---

### ✅ B184 — View Menüsü Tema Disk'e Kaydetmiyordu (TAMAMLANDI v1.4.90)

**Asıl bug:** Settings'teki theme checkbox **default işaretsiz** açılışta. Settings sayfasına geçince `_on_theme_cb_toggled(False)` tetikleniyor → `self.config.set("theme", "dark")` çağrılıyor → kullanıcının seçtiği tema dark'a geri yazılıyor.

**Fix v1 (`src/gui/settings_appearance.py`):**
- `_on_theme_cb_toggled` artık unchecked olunca theme'i dark'a geri yazmıyor

**Bug v2:** View menüsü `_set_theme("light")` çağırıyordu ama theme module sadece `light-latte`, `light-github`, `dark` gibi spesifik isimleri tanır. Bare `"light"` sessizce dark'a fallback.

**Fix v2 (`src/gui/main_window.py`):**
- `_set_theme` "light" → "light-latte" map'liyor
- Init'te legacy "light" config değeri auto-migrate

**Test:** Linux + Windows (Bayram).

---

## 🏆 ANACONDA'DAN İYİ OLMA YOL HARİTASI (3 Faz, ~2-3 yıl)

**Strateji C (Hybrid):** Niche'e odaklan + en kritik 10-15 Anaconda özelliğini ekle.

### Pozisyon Analizi

**VenvStudio'nun Anaconda'dan üstün olduğu yerler:**
- 5 backend desteği (venv + uv + poetry + pipx + conda) — Anaconda Navigator sadece conda
- Hafiflik (~MB) vs Anaconda (~3GB)
- Açık kaynak LGPL — Anaconda kurumsal kullanıcıdan ücret alıyor
- Modern UI (13 tema)
- Hızlı başlangıç (5-15s vs 30-60s)
- Çoklu dil (TR/EN, genişletilebilir)
- Learn sayfası

**Anaconda'nın eksikleri (VenvStudio'da olmayan):**
- Conda channels yönetimi
- Mamba (hızlı conda)
- Workspace/Project konsepti
- Notebook kernel manager
- Plugin sistemi
- Cloud sync
- GPU/CUDA detection
- License compliance dashboard
- Built-in REPL/playground

### FAZ 1 — "Anaconda kullanıcısını çekecek" temeller (3-6 ay hedef)

---

### 🔴 F175 — Conda Channels Yönetimi (FAZ 1)

**Hedef:** Anaconda Navigator'daki gibi UI'dan channel ekle/kaldır/öncelik belirle.

**Kapsam:**
- Settings → Channels sekmesi (yeni)
- Liste: defaults, conda-forge, bioconda, pytorch, nvidia, ...
- Ekle butonu: URL veya kısa ad ("conda-forge")
- Sırala (drag-drop): öncelik düzenleme
- Per-env override: bir env için özel channel set
- `~/.condarc` dosyasını otomatik yönet
- Pip için de aynısı: extra-index-url, trusted-host

**Dosyalar:** `src/gui/settings_channels.py` (yeni), `src/core/channel_manager.py` (yeni)

**Öncelik:** 🔴 Yüksek — conda kullanıcıları için kritik

---

### 🔴 F176 — Mamba Backend Desteği (FAZ 1)

**Hedef:** conda yerine mamba kullanma seçeneği. Mamba aynı conda komutlarını destekler ama 10-50x hızlı (paralel paket çözümlemesi).

**Kapsam:**
- Backend listesine "mamba" ekle (conda alt-tipi)
- Yüklü ise otomatik tespit et, kullanıcıya öner
- `conda install` çağrılarını `mamba install`'a yönlendir
- Sürüm karşılaştırma: conda 10s, mamba 1s gibi UI gösterimi
- Settings: "Prefer mamba over conda" toggle (default: yes)

**Dosyalar:** `src/core/conda_manager.py` (mevcut, mamba alt sınıf), `src/utils/constants.py` (yeni sabit)

**Öncelik:** 🔴 Yüksek — kullanıcıyı çok mutlu eder, conda'nın en büyük şikayeti

---

### 🔴 F177 — Workspace / Project Konsepti (FAZ 1)

**Hedef:** Bir "workspace" = env + klasör + git repo + favorite paketler. VS Code'un workspace mantığı gibi. Hızlı switch.

**Kapsam:**
- File → New Workspace (Ctrl+Shift+N)
- Workspace metadata: `<klasör>/.venvstudio/workspace.json`
  - Env adı + path
  - Çalışma klasörü
  - Git repo varsa branch info
  - Favorite paketler/launcher'lar
  - Son açılan dosyalar
- Recent workspaces listesi (File menu → Open Recent)
- Workspace açılınca env otomatik seç + klasörü VS Code/Cursor'da aç
- Workspace export/import (.vsws dosyası — taşıma için)

**Dosyalar:** `src/core/workspace_manager.py` (yeni), `src/gui/workspace_dialog.py` (yeni), `src/gui/main_window.py` (File menu)

**Öncelik:** 🔴 Yüksek — modern IDE'lerin hepsinde var, VenvStudio'da olması kritik

---

### 🟡 F178 — environment.yml / requirements.txt Import-Export (FAZ 1)

**Hedef:** Conda env'i veya pip env'i bir tıkla taşı.

**Kapsam:**
- File → Export environment...
  - Format: `requirements.txt`, `environment.yml`, `pyproject.toml`, `pipfile`
  - Sadece direct deps mi yoksa pinned (== version) mı seçeneği
  - Platform-spesifik mi (her OS için ayrı YAML) yoksa generic mi
- File → Import environment...
  - Dosya seç → otomatik backend tespit et (yml → conda, txt → pip, lock → poetry)
  - Yeni env oluştur + paketleri kur
  - Progress bar + hata raporu
- Catalog'dan da export edilebilir: "Bu listeyi yml olarak kaydet"

**Dosyalar:** `src/core/env_io.py` (yeni), `src/gui/import_export_dialog.py` (yeni)

**Öncelik:** 🟡 Orta — Anaconda kullanıcıları için temel feature, eksik olması büyük eksiklik

---

### 🟡 F179 — Notebook Kernel Manager (FAZ 1)

**Hedef:** VenvStudio kendi env'lerini Jupyter'e otomatik kaydetsin. Kullanıcı Jupyter'de "Kernel: ml-env" görsün.

**Kapsam:**
- Env oluştururken otomatik checkbox: "Register as Jupyter kernel" (default kapalı)
- Manuel: sağ tık env → "Register as Jupyter kernel" / "Unregister kernel"
- `python -m ipykernel install --user --name=<env> --display-name="<env> (VenvStudio)"`
- ipykernel paketi yoksa otomatik kurulum öner
- Tools menüsünde "Manage Jupyter kernels" — tüm kayıtlı kernel'leri listele, sil
- Bu kernel'leri VenvStudio'nun yarattığını işaretle (hangi kernel hangi VenvStudio env'i)

**Dosyalar:** `src/core/jupyter_kernel_manager.py` (yeni), `src/gui/main_window.py` (context menu), `src/gui/kernel_manager_dialog.py` (yeni)

**Öncelik:** 🟡 Orta — Jupyter kullanıcıları için zorunlu, az kullananlar için opsiyonel

---

### FAZ 2 — "Anaconda'yı geride bırakacak" özellikler (6-12 ay hedef)

---

### 🔴 F180 — Plugin Sistemi (FAZ 2)

**Hedef:** Kullanıcı kendi launcher/preset/check yazabilsin. Üçüncü parti araçlar VenvStudio'ya entegre olabilsin.

**Kapsam:**
- `~/.venvstudio/plugins/` klasörü
- Plugin yapısı: `plugin.json` + `plugin.py`
- Plugin türleri:
  - **Launcher plugin** — yeni uygulama Launch sekmesine ekle (örn. PyCharm community)
  - **Preset plugin** — yeni preset paketi (örn. "Climate Science")
  - **Check plugin** — env üzerinde özel kontrol (örn. "Has CUDA-compatible torch?")
  - **Action plugin** — sağ-tık menüsüne yeni eylem ekle
- Plugin marketplace (sonra) — GitHub'dan plugin keşfetme/yükleme
- Plugin signing/güvenlik (sonra)

**Dosyalar:** `src/core/plugin_manager.py` (yeni), `src/core/plugin_api.py` (yeni — kullanıcı plugin'leri için public API), `src/gui/plugin_dialog.py` (yeni)

**Öncelik:** 🔴 Yüksek — VenvStudio'yu platform haline getirir, ekosistem kurar

---

### 🟡 F181 — AI Asistanlı Env Oluşturma (FAZ 2)

**Hedef:** "ML için env yarat" deyince AI öner.

**Kapsam:**
- File → New Environment → "Ask AI" sekmesi
- Doğal dil input: "Bana scikit-learn ile çalışacak bir ML env yarat"
- AI önerir:
  - Backend: uv (hızlı)
  - Python: 3.11
  - Paketler: numpy, pandas, scikit-learn, matplotlib, seaborn, jupyter
  - Açıklama: "Veri bilimi için temel kurulum, jupyter notebook hazır"
- Kullanıcı düzenler veya direkt onaylar
- Backend: Claude API (kullanıcının API key'i veya local Ollama)
- Privacy: opt-in, default kapalı

**Dosyalar:** `src/core/ai_assistant.py` (yeni), `src/gui/ai_env_dialog.py` (yeni), `src/utils/llm_client.py` (yeni — Claude/Ollama abstraction)

**Öncelik:** 🟡 Orta — wow factor, ama birçok kullanıcı API key vermek istemez

---

### 🟡 F182 — Cloud Sync (FAZ 2)

**Hedef:** Env'leri GitHub Gist / Drive / Dropbox'a yedekle, başka makineden çek.

**Kapsam:**
- Settings → Cloud Sync sekmesi
- Provider seçimi: GitHub Gist (gh auth), Google Drive, Dropbox, Self-hosted (URL)
- Auto-sync toggle: env yarat/sil/değiştirildikçe otomatik upload
- "Restore from cloud": başka makinede aynı env'leri kur
- Conflict resolution: aynı isimde env iki yerde varsa birleştir/seç
- Şifreleme: env adlarını ve metadata'yı şifrele (opsiyonel)

**Dosyalar:** `src/core/cloud_sync.py` (yeni), `src/gui/settings_cloud.py` (yeni)

**Öncelik:** 🟡 Orta — niche feature, ama power user'lar bayılır

---

### 🔗 F159, F161, F162, F163, F165 — Mevcut TODO'da var (FAZ 2'ye dahil)

- **F159** Vulnerability Scanner — yukarıda detaylı
- **F161** Snapshot/Restore — yukarıda detaylı
- **F162** Compare envs (diff) — yukarıda detaylı
- **F163** License Checker — yukarıda detaylı
- **F165** Command Palette — yukarıda detaylı

Bunlar Faz 2'nin parçası. Detayı yukarıdaki ilgili madde başlıklarında.

---

### FAZ 3 — "Anaconda'nın hayal edemediği" şeyler (1-2 yıl hedef)

---

### 🟡 F183 — GPU / CUDA / Hardware Detection (FAZ 3)

**Hedef:** Env'in GPU/CUDA gereksinimlerini otomatik tespit et, uyumlu kurulum öner.

**Kapsam:**
- System Info paneli: NVIDIA GPU var mı? CUDA sürümü? cuDNN? ROCm (AMD)? Apple MPS?
- Env'e PyTorch/TensorFlow kurulurken: "GPU desteği mi CPU only mi?" sor
- CUDA sürüm uyumluluğu kontrol (PyTorch 2.5 + CUDA 11.8 vs 12.1)
- Otomatik doğru index URL: `--index-url https://download.pytorch.org/whl/cu121`
- Settings → Hardware sekmesi (yeni) — algılanan donanım listesi

**Dosyalar:** `src/core/hardware_detector.py` (yeni), `src/gui/settings_hardware.py` (yeni)

**Öncelik:** 🟡 Orta — ML/Data Science kullanıcıları için kritik, diğerleri için bonus

---

### 🔵 F184 — Docker Export (FAZ 3 — KULLANICI ERTELEDI)

**Durum:** Bayram bunu daha önce listeden çıkardı. Eklenmeyecek bir not.

**Eğer ileride istenirse:** Env → Dockerfile üret. Tek tık.

---

### 🔵 F185 — Kubernetes Deployment Generator (FAZ 3)

**Durum:** Önceden konuşulup TODO'ya eklenmemişti.

**Hedef:** Env → K8s Deployment YAML üret.

**Kapsam:**
- Env seç → "Export to K8s"
- Otomatik üret: Deployment + Service + ConfigMap + Secrets (env vars)
- Helm chart üretebilme (opsiyonel)
- Image build kısmı F184'e bağlı (Docker)

**Öncelik:** 🔵 Düşük — niche kullanıcı, F184 olmadan anlamsız

---

### 🟡 F186 — Built-in REPL / Python Playground (FAZ 3)

**Hedef:** F165 (Command Palette) ile birlikte. Mini REPL VenvStudio içinde, env içinde direkt kod çalıştır.

**Kapsam:**
- Tools menüsü → "Open Python Playground" (Ctrl+`)
- Embedded terminal/REPL widget (QTextEdit + subprocess)
- Seçili env'de çalışır (env'in Python'unu kullanır)
- Syntax highlighting (qtpy/Pygments)
- Multi-line input (Shift+Enter)
- History (Up/Down arrows)
- "Send to playground" — Catalog'dan paket seç → import et + örnek snippet
- Save session → .py dosyasına

**Dosyalar:** `src/gui/playground_widget.py` (yeni), `src/utils/python_runner.py` (yeni)

**Öncelik:** 🟡 Orta — Anaconda Navigator'da yok, VenvStudio için özgün feature

---

### 📊 ÖZET TABLO

| Kod | Faz | İsim | Öncelik | Süre |
|-----|-----|------|---------|------|
| F175 | 1 | Conda Channels | 🔴 | 2-3 hafta |
| F176 | 1 | Mamba Backend | 🔴 | 1-2 hafta |
| F177 | 1 | Workspace | 🔴 | 4-6 hafta |
| F178 | 1 | Import/Export YAML | 🟡 | 2-3 hafta |
| F179 | 1 | Jupyter Kernel | 🟡 | 1-2 hafta |
| F180 | 2 | Plugin Sistemi | 🔴 | 6-8 hafta |
| F181 | 2 | AI Assistant | 🟡 | 3-4 hafta |
| F182 | 2 | Cloud Sync | 🟡 | 4-6 hafta |
| F159 | 2 | Vulnerability (TODO'da) | 🟡 | 2-3 hafta |
| F161 | 2 | Snapshot (TODO'da) | 🔴 | 3-4 hafta |
| F162 | 2 | Compare (TODO'da) | 🟡 | 2 hafta |
| F163 | 2 | License (TODO'da) | 🟡 | 1-2 hafta |
| F165 | 2 | Command Palette (TODO'da) | 🔴 | 2-3 hafta |
| F183 | 3 | GPU/CUDA Detection | 🟡 | 3-4 hafta |
| F185 | 3 | K8s Generator | 🔵 | 4-6 hafta |
| F186 | 3 | REPL/Playground | 🟡 | 4-6 hafta |

**Toplam tahmini süre:** ~70-100 hafta full-time. Tek başına yapılırsa ~2-3 yıl.

**Ön koşul:** Mevcut bug'lar (B180 final test, B181 macOS/Win test, B183 light tema, performans) önce kapanmalı. Aksi halde yeni özellikler eski bug'ların üstüne biner.

---

### 🟡 F157 — Settings → Performance Sekmesi

**⚠️ SIRA:** Önce F158 (alt yapı) → sonra F157 (UI). Aksi halde Cache stats boş görünür.

**Hedef:** Settings altında yeni "Performance" bölümü. Tüm performans/cache/threading ayarları tek yerde.

**İçerik:**

**📊 Cache İstatistikleri (read-only panel)**
- Env cache: X entry, Y KB
- Pkg list cache: X entry, Y KB
- QSS/style cache: hits/misses, hit rate %
- Toplam cache disk kullanımı

**🗑 Cache Yönetimi**
- "Clear all caches" butonu (env + pkg + qss + chip + ...)
- "Clear pkg list cache only" (selektif)
- "Clear style cache only"
- Onay dialog'u (geri alınamaz)

**⚙️ Cache Davranışı**
- ☐ Mtime-based invalidation (Aşama 5 ile gelecek)
- ☐ Time-based stale detection (default >7 gün)
- Sürgü: Cache TTL (saat) — varsayılan 168 (7 gün)
- Sürgü: Max cache size (MB) — varsayılan 50 MB

**🧵 Threading**
- Sürgü: Subprocess timeout (saniye) — varsayılan 30s
- Sürgü: Background worker count — varsayılan 4 (CPU bağımlı)
- ☐ Parallel env scan (birden çok env aynı anda taransın)

**🔬 Diagnostik**
- ☐ Enable performance logging (DEBUG seviyesinde startup ve switch süreleri)
- ☐ Show cache hit/miss in status bar
- "Run profile" butonu — cProfile çalıştır, raporu file'a kaydet

**💤 Lazy Loading**
- ☐ Launcher cards lazy load (Aşama 3 sonrası)
- ☐ Tabs lazy build (sadece tıklanınca)
- ☐ Module lazy import (learn_page, settings_*)

**Dosya:** `src/gui/settings_performance.py` (yeni), `src/gui/settings_page.py` (sekme ekle), `src/utils/config_manager.py` (yeni keys)

**Öncelik:** 🟡 Orta — power user feature, ama çok değerli (debugging için kritik)

---

### 🟡 F158 — Kütüphane (Pkg Catalog) Cache İyileştirmeleri

**⚠️ SIRA:** ÖNCE bu yapılır (alt yapı), SONRA F157 (UI bunun üstüne).

**Hedef:** Catalog tab'ındaki kütüphane bilgilerini cache'le. PyPI'a bağlı her şey local cache'e alınsın.

**Şu an:**
- Pkg list (kurulu paketler) → cache'leniyor (v1.4.87 sonrası ✓)
- Pkg metadata (description, homepage, version, license, deps) → her seferinde subprocess `pip show` veya PyPI request
- Pkg search (Catalog'da arama) → muhtemelen her keyword için yeniden taranıyor
- Pkg version listesi → her "version" tıklamada PyPI request

**Yapılacak:**

**A) Pkg metadata cache (yeni)**
- `pkg_meta_cache.json` — `pip show <pkg>` çıktısı cache'lenir
- TTL: 7 gün (paket sürümü değişince doğal güncelleme zaten olur)
- Anahtar: `(env_path, pkg_name, version)` → `{description, homepage, license, deps, ...}`

**B) PyPI metadata cache (yeni)**
- `pypi_meta_cache.json` — PyPI JSON API çağrıları (`https://pypi.org/pypi/<pkg>/json`)
- TTL: 24 saat (paket sürümleri sık güncellenir)
- Anahtar: `pkg_name` → `{latest_version, all_versions, summary, project_urls, ...}`

**C) Search index (yeni)**
- Catalog'daki PACKAGE_CATALOG sabit zaten — JSON dosyaya çevrilebilir
- İlk açılışta indexlensin (full-text search için sqlite FTS5 veya basit dict-of-words)
- Search anlık olur, her keyword için liste taraması yapma

**D) Pkg detail dialog cache**
- Bir paket detayını ilk açtığında PyPI'dan çek + cache'le
- Sonraki açılışlarda cache'den anında göster
- "Refresh" butonu manuel re-fetch için

**E) Görsel cache (icon, thumbnail)**
- Catalog'daki paket icon'ları (varsa)
- Disk cache, RAM'de QPixmapCache

**F) Cache invalidation**
- F157'deki Settings paneli ile entegre
- Her cache türü için ayrı clear butonu

**Etki:**
- Catalog ilk açılış: birkaç saniye yerine anında
- Pkg detail dialog: 1-2s yerine anında
- Search: yazarken instant filter

**Dosyalar:**
- `src/core/pkg_metadata_cache.py` (yeni)
- `src/core/pypi_client.py` (yeni — PyPI API + caching wrapper)
- `src/gui/package_panel.py` (Catalog tab → use cache)
- `src/utils/constants.py` (cache TTL sabitleri)

**Öncelik:** 🔴 Yüksek — Catalog kullanılabilirliği için kritik

---

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
### ✅ B174 — Windows'ta `QFont::setPointSize: Point size <= 0 (-1)` Spam Uyarısı (TAMAMLANDI v1.4.91)

**Çözüm (v1.4.91):** Boş `QFont()` constructor Windows'ta default sistem fontunu alıyor; bu font pixel-size based, `pointSize()` `-1` döner. Tablo widget'ının QSS'i `font-size: 13px` (pixel) olduğu için Qt internal cascade `setPointSize(-1)` çağırıyor → uyarı.

**Fix (4 nokta):**
- `main_window.py` env_table satırları × 3: `QFont()` → `QFont(self.env_table.font())`
- `package_panel.py` catalog_table × 1: `QFont()` → `QFont(self.catalog_table.font())`

Tablonun mevcut font'unu kopyala (zaten QSS pixel-size ile uyumlu), sadece `setBold(True)` ekle.

**Detaylı handoff:** v1.4.91 oturum kayıtları.

---
**[Aşağıdaki bölüm orijinal teşhis kaydı — referans için saklanır]**

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

## 💎 Yeni Özellik Önerileri (Power User / Pro)

### 🔒 F159 — Vulnerability Scanner (Güvenlik Açığı Taraması)

**Hedef:** `pip-audit` veya `safety` entegrasyonu. Kurulu paketlerde bilinen güvenlik açıkları varsa kullanıcıyı uyar.

**Kapsam:**
- Env tablosunda badge: 🔴 3 güvenlik açığı
- Env detail panelinde liste: hangi paket, hangi CVE, severity, fix version
- "Update vulnerable packages" tek-tık butonu
- Settings → "Scan on startup" toggle (default kapalı, manuel)
- Cache: scan sonucu 24h tutulsun (PyPI Advisory DB güncellemesi yavaş)

**Backend desteği:**
- pip/uv/poetry/pipx → `pip-audit` (önerilir, modern)
- conda → `mamba audit` veya pip-audit fallback
- Scan komutunu env içinde subprocess olarak çalıştır

**Dosyalar:** `src/core/vuln_scanner.py` (yeni), `src/gui/package_panel.py` (badge + dialog)

**Öncelik:** 🟡 Orta — kurumsal kullanıcı için kritik, bireysel için bonus

---

### 📊 F160 — Outdated Paket Göstergesi (UI)

**Hedef:** `pip list --outdated` cache'le, env tablosunda "5 güncellenebilir" badge göster.

**Şu an:** `Ctrl+U` kısayolu var ama UI'da görünür gösterim yok — kullanıcı kısayolu bilmiyorsa hiç görmez.

**Kapsam:**
- Env tablosunda Packages kolonunun yanına: "171 (5 ↑)" formatı
- Tooltip: hangi paketler outdated, current → latest sürümler
- Catalog/Installed tab'ında outdated paket satırı sarı highlight
- Cache: outdated listesi 12h tutulsun
- Bulk update: "Update all outdated" butonu

**Dosyalar:** `src/core/pip_manager.py` (outdated metodu var mı kontrol), `src/gui/main_window.py` (env tablo render), `src/gui/package_panel.py` (Installed tab)

**Öncelik:** 🟡 Orta — kullanıcı farkındalığı için önemli

---

### 🔄 F161 — Env Snapshot / Restore

**Hedef:** Bir env'in paket listesini "snapshot" al, sorun çıkınca eski hale geri dön.

**Kapsam:**
- Sağ tık env → "Take snapshot" → ad/tarih ile kaydet
- `~/.venvstudio/snapshots/<env>/<timestamp>.json` (paket listesi + sürümler)
- Sağ tık env → "Restore from snapshot" → liste göster, seç → uygula
- Restore = mevcut env'i temizle, snapshot'taki paketleri kur (uzun sürer, progress göster)
- "Auto-snapshot before bulk install" toggle (Settings)
- Snapshot listesi: tarih, paket sayısı, boyut tahmini

**Use case:**
- "TensorFlow 2.15 kurdum, bir şey bozuldu" → 2 dakika önce snapshot'a dön
- "ML env'imi başka makineye taşıyacağım" → snapshot al, transfer et

**Dosyalar:** `src/core/snapshot_manager.py` (yeni), `src/gui/main_window.py` (context menu), `src/gui/snapshot_dialog.py` (yeni)

**Öncelik:** 🔴 Yüksek — workflow safety net, çok değerli

---

### 📦 F162 — İki Env Karşılaştır (Diff)

**Hedef:** Env A vs Env B → paket farkı tablosu.

**Kapsam:**
- Tools menüsü → "Compare environments..."
- İki env seç (dropdown)
- Side-by-side tablo:
  - Sadece A'da olan paketler (yeşil)
  - Sadece B'de olan paketler (mavi)
  - İkisinde de var, sürüm aynı (gri)
  - İkisinde de var, sürüm farklı (sarı, A→B sürüm değişimi)
- Filtre: sadece farkları göster / hepsini göster
- "Sync A → B" butonu (B'ye eksikleri kur, fazlaları kaldır) — uyarı dialog'lu

**Dosyalar:** `src/gui/env_compare_dialog.py` (yeni), `src/gui/main_window.py` (Tools menüsü)

**Öncelik:** 🟡 Orta — geliştirici için faydalı, sık kullanılmayabilir

---

### ⚖️ F163 — License Checker

**Hedef:** Kurulu paketlerin lisanslarını listele. Ticari proje için kritik (GPL bulaşıcı, MIT serbest).

**Kapsam:**
- Tools menüsü → "License report"
- Tablo: paket adı | sürüm | lisans | risk
- Risk kategorileri:
  - 🟢 Düşük: MIT, BSD, Apache-2.0, ISC
  - 🟡 Orta: LGPL, MPL
  - 🔴 Yüksek: GPL, AGPL (ticari kapalı kaynak için sorunlu)
  - ❓ Bilinmeyen: lisans bulunamadı
- Filter: sadece yüksek risk göster
- Export: CSV / Markdown
- Cache: lisans sabit, paket sürümüne bağlı, uzun TTL OK

**Veri kaynağı:** `pip show <pkg>` çıktısında "License" alanı, ya da PyPI metadata

**Dosyalar:** `src/core/license_analyzer.py` (yeni), `src/gui/license_dialog.py` (yeni)

**Öncelik:** 🟡 Orta — ticari kullanıcı için kritik

---

### 💾 F164 — Per-Package Disk Usage Analyzer

**Hedef:** Bir env içinde hangi paket kaç MB? "pip-sizes" benzeri.

**Şu an:** Env'in toplam disk kullanımı tablonun üstünde gösteriliyor (env bazlı). Ama paket bazlı yok.

**Kapsam:**
- Sağ tık env → "Disk usage report"
- Tablo: paket adı | sürüm | boyut | yüzde
- Sırala: en büyük üstte
- Top 10 görselleştirme: pasta grafik veya horizontal bar chart
- "Cleanup suggestions": eski sürümler, __pycache__ klasörleri, test dosyaları
- "Reclaim space" butonu — pip cache temizle, __pycache__ sil
- Cache: paket boyutları yavaş hesaplanır, 24h cache

**Algoritma:** `site-packages/<pkg>` klasörü için `os.walk` → toplam boyut. Background thread'de çalıştır.

**Dosyalar:** `src/core/disk_analyzer.py` (yeni), `src/gui/disk_usage_dialog.py` (yeni)

**Öncelik:** 🟡 Orta — debug ve cleanup için faydalı

---

### ⌨️ F165 — Command Palette (Ctrl+Shift+P)

**Hedef:** VS Code / Notion / Sublime tarzı evrensel komut paleti. Klavye odaklı her şeye erişim.

**Kapsam:**
- `Ctrl+Shift+P` veya `Ctrl+K` ile aç
- Fuzzy search: "create env", "delete", "install pandas", "switch theme dark", "open settings", "compare envs", ...
- Komut kategorileri:
  - Environment: create, delete, switch to, open terminal, open folder
  - Package: install, uninstall, update all, search catalog
  - Settings: theme, language, font size, perform tab
  - View: zoom in/out, switch page, toggle sidebar
  - Tools: snapshot, compare, license report
- Recent commands üstte
- Sonuç seç → enter → çalıştır
- Plugin friendly (gelecekte kullanıcı kendi komutlarını ekleyebilsin)

**Implementation:** `QLineEdit` + `QListWidget` + fuzzy match (rapidfuzz library)

**Dosyalar:** `src/gui/command_palette.py` (yeni), `src/gui/main_window.py` (kısayol bind)

**Öncelik:** 🔴 Yüksek — çok güçlü UX katar, power user'lar bayılır

---

### ↩️ F166 — Undo / Redo (Ctrl+Z / Ctrl+Y)

**Hedef:** Yanlış paketi sildim, env'i sildim, ayar değiştirdim → Ctrl+Z ile geri al.

**Kapsam:**
- Action history stack (son 50 işlem)
- Undo'lanabilen işlemler:
  - Paket yükle/kaldır → tersini yap
  - Env oluştur → sil (uyarı dialog'lu — büyük iş)
  - Env sil → snapshot'tan restore (F161 ile entegre)
  - Settings değiştir → eski değere dön
- Status bar'da "Last action: Installed pandas" + Undo butonu
- Dialog: undo'ya basınca onay iste ("Bu pandas paketi kaldırılacak, emin misin?")

**Risk:** Bazı işlemler doğal olarak geri alınamaz (örn. cache temizle). Onlar undo stack'e girmesin.

**Implementation:** Command pattern. Her action `do()` ve `undo()` metodlarını implement etsin.

**Dosyalar:** `src/core/action_history.py` (yeni), tüm action tetikleyici yerlere entegrasyon

**Öncelik:** 🟡 Orta — koruma katmanı, ama büyük refactor (her action'ı command pattern'e dönüştürmek)

---

### 🪟 F167 — Çoklu Pencere / Sekme (Multi-Window)

**Hedef:** Aynı anda iki env ile çalış. İki ayrı VenvStudio penceresi veya tek pencerede sekmeler.

**Kapsam:**
- File menüsü → "New Window" (Ctrl+N veya Ctrl+Shift+N)
- Yeni pencere = aynı uygulama, farklı state
- Pencereler birbirinden bağımsız: farklı env seçili olabilir
- Cache + config paylaşımlı (singleton)
- Pencere konumu/boyutu her pencere için ayrı kaydedilir (`window_state_<n>.json`)

**Alternatif yaklaşım:** Tek pencerede sekme sistemi (her sekme bir env workspace'i). Daha az invasive ama daha az esnek.

**Dosyalar:** `src/gui/main_window.py` (multi-instance support), `src/utils/config_manager.py` (per-window state)

**Öncelik:** 🟡 Orta — power user feature, gerçek workflow değer katar

---



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

**Karar notu (2026-07-08):** Yeni backend olarak yalnızca **pixi** ciddi aday. **hatch/pdm** backend olarak EKLENMEYECEK — en fazla "tespit et + listele" (read-only, F192 ile birlikte). **virtualenv/pipenv/rye** hiç eklenmeyecek (F137'deki virtualenv/pip-env maddeleri bu karara göre revize edilmeli).

---

### 🟡 F197 — Yeni Launcher Kartları (eklendi: 2026-07-08)

**Ön adım:** `src/gui/launcher_links.json`'daki mevcut 22 kartla diff al — aşağıdakilerden zaten var olanları çıkar.

**Güçlü adaylar (yüksek talep):**
- **Marimo** — reaktif notebook, Jupyter'in modern rakibi (Learn'de var, launcher kartı yok)
- **Quarto** — bilimsel yayıncılık, `quarto preview`
- **Datasette** — veri keşfi, tek komutla çalışır
- **Ollama** (+ **Open WebUI**) — local LLM; AI/LLM kitlesi için güçlü kart

**İkinci halka:**
- **NiceGUI** — yeni nesil Python web UI framework
- **Reflex** — yeni nesil Python web UI framework
- **Shiny for Python** — Posit destekli, data science tarafında büyüyor
- **napari** — bilimsel görüntü analizi (mikroskopi/CV)
- **Label Studio** — ML veri etiketleme, `label-studio start`
- **Locust** — yük testi, web geliştirici kitlesi
- **ptpython** — zengin REPL (IPython alternatifi, ucuz kart)
- **bpython** — zengin REPL (IPython alternatifi, ucuz kart)

**Eklenmeyecekler:** JupyterHub (çok kullanıcılı sunucu), Superset/Metabase (pip kurulumu sancılı, launcher'a uymaz).

**Notlar:**
- Her kart için: install komutu, run komutu, resmi linkler (launcher_links.json formatı), `needs_console` / `preferred_backend` alanları (B144 deseni)
- Kart sayısı artacağı için PERF: launcher card lazy load (mevcut TODO maddesi) bu işten ÖNCE yapılmalı
- İlgili dosyalar: `src/gui/launcher_ui.py`, `src/gui/launcher_run.py`, `src/gui/launcher_links.json`
- Öncelik: 🟡 Orta (güçlü adaylar önce, ikinci halka sonra)

---

### 🔴 F198 — Özel Konumda Env Oluşturma & Takip (Custom Location Envs) (eklendi: 2026-07-08)

**Hedef:** Env'ler yalnızca base_dir'de değil — kullanıcının seçtiği HERHANGİ bir konumda (proje klasörü, ikinci disk, USB, network drive) oluşturulabilsin ve VenvStudio bunları kalıcı olarak takip etsin.

**Kapsam:**
- **Oluşturma:** Env dialog'a "Location" alanı — Default (base_dir) / Custom path (klasör seç). venv, uv, poetry (`.venv in-project`), conda (`--prefix`) destekler; pipx hariç (kendi home'una bağlı).
- **Kayıt sistemi (registry):** `~/.venvstudio/registered_envs.json` — base_dir dışındaki her env'in path + backend + created_at kaydı. Uygulama her açılışta registry'deki path'leri doğrular.
- **Dışarıdan ekleme:** "Add Existing Environment" — kullanıcı mevcut bir env klasörünü gösterir → backend otomatik tespit (pyvenv.cfg / conda-meta / poetry) → registry'e eklenir. F192 (Orphan Env Keşfi) bulduklarını da buraya kaydeder.
- **UI:** Environments listesinde konum gösterimi — base_dir env'leri normal, custom env'ler 📁 ikonu + path tooltip ile; opsiyonel "Group by location" görünümü.
- **Stale yönetimi:** Path artık yoksa (disk çıkarıldı/klasör silindi) env kırmızı/soluk gösterilir — "Remove from list" veya "Locate..." (yeni path göster → `_relocate_venv_paths` ile onar).
- **Tüm işlemler çalışmalı:** install/uninstall/export/clone/rename/delete custom-location env'lerde de aynı davranmalı (cache key'ler absolute path bazlı olduğundan mimari uygun).

**İlişkili maddeler:** F140 (Proje İçine Env — bunun alt-durumu olur), F192 (Orphan keşfi → registry'e besler), F177 (Workspace — workspace.json custom env path'i referans alabilir).

**İlgili dosyalar:** `src/core/venv_manager.py` (registry + path doğrulama), `src/gui/env_dialog.py` (Location alanı), `src/gui/env_list.py` (konum gösterimi), yeni `src/core/env_registry.py`

**Öncelik:** 🔴 Yüksek — "tüm env'ler tek yerde" iddiasının tamamlayıcısı; F192 ile birlikte VenvStudio'yu disk-geneli env merkezi yapar.

---

### 🔴 F199 — Local LLM Environment Studio (eklendi: 2026-07-08)

**Hedef:** Local LLM env kurulumunu (ekosistemin en sancılı kurulumu: CUDA, torch wheel, quantization) tek tıkla, donanım-farkında hale getir. İlişkili: F141/F181 (AI entegrasyonu), F183 (GPU detection), F197 (Ollama kartı).

**1. LLM Presets (en ucuz, en hızlı kazanım):**
- Catalog'a yeni "🤖 Local LLM" preset kategorisi:
  - **llama.cpp stack:** `llama-cpp-python` (CUDA/Metal/CPU varyantı donanıma göre)
  - **Transformers stack:** `torch` + `transformers` + `accelerate` + `bitsandbytes`
  - **vLLM** (Linux+CUDA), **MLX** (macOS Apple Silicon), **Ollama client** (`ollama` paketi)
  - **UI araçları:** `open-webui`, `text-generation-webui` gereksinimleri

**2. Donanım-farkında kurulum (F183 ile birleşir):**
- LLM preset seçilince donanım tespiti → doğru varyant önerisi:
  - NVIDIA → doğru CUDA index-url (`--index-url .../whl/cu121`)
  - AMD → ROCm wheel; Apple Silicon → MLX/Metal; hiçbiri → CPU/GGUF yolu
- VRAM bazlı bilgi notu: "GPU'n 8 GB — 7B quantized modeller uygun"

**3. Ollama entegrasyonu (F197 kartının derinleşmesi):**
- Ollama kurulu mu tespit, `ollama list` ile indirilen modelleri göster
- Popüler modelleri (llama3, qwen, mistral...) tek tıkla `ollama pull` — indirme progress'iyle

**4. Learn içeriği — "Local LLM" kategorisi:**
- GGUF nedir, quantization seviyeleri (Q4/Q5/Q8), VRAM hesabı
- llama.cpp vs Ollama vs vLLM karşılaştırması (mevcut Learn formatında)

**5. F141'e köprü:**
- Ollama kuruluysa F141 AI asistan özellikleri API key gerektirmeden local modeli kullanır

**Rekabet notu:** Anaconda "AI Navigator" kapalı ekosisteme bağlı — "açık kaynak, donanımını tanıyan, local LLM env'ini tek tıkla kuran GUI" farklılaştırıcı konum.

**Öncelik sırası:** (1)+(4) ucuz → v1.6.x-1.7; (2) F183'e bağlı; (3) orta; (5) F141'le birlikte.

**İlgili dosyalar:** `src/gui/settings_catalog.py` (preset kategorisi), `src/core/hardware_detector.py` (yeni, F183 ortak), yeni `src/core/ollama_manager.py`, `src/gui/learn_content.py`

---

### 🔴 F200 — AI/LLM Workbench (Full Paket) (eklendi: 2026-07-08)

**Vizyon:** VenvStudio klasik data science'ın yanında modern LLM mühendisliğini de kapsasın — hem akademik hem pratik. Konum: "From classic data science to modern LLM engineering — one GUI for every Python environment." F199'u 4 iş akışına genişletir.

**İş Akışı 1 — Inference (F199'da büyük ölçüde var):**
- F199 preset'lerine ek: **SGLang** (vLLM rakibi), quantization araçları (GPTQ/AWQ)
- ⚠️ vLLM ve SGLang **Linux+CUDA only** — Windows/macOS'ta preset gri + "bu platformda desteklenmiyor" notu

**İş Akışı 2 — Fine-tuning (YENİ):**
- Preset: `transformers + peft + trl + bitsandbytes + accelerate + datasets` (LoRA/QLoRA standart stack)
- Ayrı preset: **Unsloth** (tek GPU hızlı fine-tune)
- VRAM rehberliği (F199-2/F183 ile): "8 GB → QLoRA 7B olur, full fine-tune olmaz"
- ⚠️ Unsloth/bitsandbytes CUDA sürüm eşleşmesi nazlı — F187/F188 conflict altyapısı bu preset'lerden ÖNCE hazır olmalı

**İş Akışı 3 — RAG & Agents (YENİ — en pratik iş yükü):**
- RAG preset: `langchain / llamaindex + chromadb + sentence-transformers + faiss`
- Agents preset: `anthropic + openai + pydantic-ai + langgraph + mcp` (MCP SDK dahil)
- Launcher: **Chainlit** (yeni kart), Streamlit (var), Open WebUI (F197)

**İş Akışı 4 — Evaluation & Akademik (YENİ):**
- Eval preset: `lm-eval-harness + ragas + deepeval`
- Deney takibi: `wandb` + MLflow (launcher var); Learn'de "deney loglama" konusu
- Reproducibility hikâyesi: lockfile export + F178 (environment.yml) + F179 (Jupyter kernel) = "makaledeki deneyi aynen kur"
- Quarto launcher'ı (F197) makale/rapor tarafını kapatır

**Learn — yeni kategoriler (F144 formatında):**
- 🔧 Fine-tuning (LoRA/QLoRA, PEFT, Unsloth, dataset hazırlama)
- 📚 RAG (chunking, embedding, vector DB karşılaştırma, reranking)
- 🤝 Agents & MCP (tool use, MCP server yazma, langgraph)
- 📏 LLM Evaluation (benchmark'lar, ragas metrikleri, eval tasarımı)

**Fizibilite notu:** Preset'ler + Learn + launcher kartları = mevcut altyapı üzerine SADECE VERİ (settings_catalog custom preset + learn_content.py + launcher_links.json) — düşük risk. Yeni kod sadece F183 hardware_detector ve ollama_manager.
**İçerik eskime riski:** LLM ekosistemi 6 ayda değişiyor → Learn/preset verisini online güncellenebilir yapma fikri (content-as-data, F180 sonrası) stratejik önkoşul değil ama güçlü tamamlayıcı.

**Dalga planı:**
1. 🌊 RAG/Agents/Eval preset'leri + Learn içeriği + Chainlit kartı (ucuz, hemen)
2. 🌊 F183 GPU detection + fine-tuning preset'leri + VRAM rehberliği
3. 🌊 Ollama derin entegrasyon + platform-özel inference preset'leri (vLLM/SGLang/MLX)

**İlgili dosyalar:** `src/gui/settings_catalog.py`, `src/gui/learn_content.py`, `src/gui/launcher_links.json`, `src/core/hardware_detector.py` (F183), `src/core/ollama_manager.py` (F199)

**Öncelik:** 🔴 Yüksek — ürün vizyonunun ana ekseni; F199 ile birlikte planlanmalı.

---

### 🟡 F201 — Tüm Launcher Kartları için Learn Sekmesi (eklendi: 2026-07-08)

**Hedef:** Her launcher kartının (mevcut 22 + F197 ile gelecekler) Learn'de karşılığı olan bir konusu olsun ve karttan tek tıkla o konuya gidilsin. F149'un (ertelenmişti) kapsamlı hali.

**Kapsam:**
- **Learn tarafı:** Her launcher uygulaması için bir Learn konusu — "nedir, ne zaman kullanılır, temel komutlar, resmi linkler" formatında. Eksik olanlar yazılır (mevcut Learn'de bazıları zaten var: Jupyter, Spyder, Streamlit, MLflow vb. — önce diff al).
- **Launcher tarafı:** Karta "📖 Learn" butonu/ikonu → tıklayınca Learn sayfası açılır ve ilgili konuya scroll/focus olur.
- **Bağlantı mekanizması:** `launcher_links.json`'a `learn_topic_id` alanı ekle; Learn konularına stabil `id` verilmemişse önce o (topic id altyapısı, F200 Learn kategorileriyle ortak temel).
- **Ters yön (opsiyonel):** Learn konusundan launcher'a "🚀 Launch" butonu — uygulama kuruluysa başlat, değilse Install akışına götür.

**İlgili dosyalar:** `src/gui/launcher_links.json` (learn_topic_id alanı), `src/gui/launcher_ui.py` (kart butonu), `src/gui/learn_page.py` (konuya scroll/focus API'si), `src/gui/learn_content.py` (eksik konular + topic id'ler)

**İlişkili maddeler:** F149 (bunun öncüsü — kapatılıp F201'e devredilebilir), F197 (yeni kartlar da bu deseni izler), F200 (Learn kategori genişlemesi)

**Öncelik:** 🟡 Orta — F197 ile aynı dalgada yapılırsa tek seferde biter.

---

### 🔵 F202 — BSD için Binary Dağıtım (eklendi: 2026-07-08)

**Hedef:** Windows (.exe) / Linux (AppImage) / macOS gibi, BSD ailesi (öncelik: FreeBSD) için de kurulabilir paket.

**Gerçekçilik notları (araştırılacak):**
- BSD'de AppImage/exe muadili tek-dosya format YOK — doğal dağıtım yolu **FreeBSD ports/pkg** (`py-venvstudio` portu). PyInstaller'ın FreeBSD desteği zayıf/resmi değil; tek-dosya binary yerine port en sağlıklısı.
- PySide6/Qt6 FreeBSD ports'ta mevcut (`misc/py-PySide6`) — bağımlılık tarafı çözülebilir görünüyor.
- Kod tarafı kısmen hazır: `platform_utils.open_folder` FreeBSD dalını zaten tanıyor; `get_platform()` BSD dönüşleri gözden geçirilmeli (backend'ler: venv/uv/pipx BSD'de çalışır, conda/micromamba FreeBSD'de RESMİ DESTEKSİZ — kartlar gri gösterilmeli).
- CI: GitHub Actions'ta FreeBSD native runner yok — `vmactions/freebsd-vm` action ile VM içinde smoke test mümkün (F195 CI matrisine opsiyonel ayak).

**Adımlar:**
1. FreeBSD VM'de `pip install venvstudio` smoke testi (muhtemelen bugüne kadar hiç denenmedi)
2. `get_platform()` / platform-özel yolların BSD denetimi; conda backend'ini BSD'de devre dışı bırak
3. FreeBSD port iskeleti (`Makefile` + `pkg-descr`) hazırla, ports'a PR
4. README'ye BSD kurulum bölümü

**İlişkili:** F195 (CI matrisi), F196 (dağıtım kanalları — BSD ayağı olarak buraya bağlanır)

**Öncelik:** 🔵 Düşük-orta — niş kitle ama Pardus/CachyOS çeşitliliğine uygun "her yerde çalışır" kimliğini güçlendirir.

---

## 🆕 F187–F196 — Conflict Yönetimi, Kalite & Dağıtım (eklendi: 2026-07-08)

**Öncelik önerisi:** F188 + F189 kısa vade (v1.6.x, düşük maliyet) → F187 + F193 FAZ 1'e → kalanlar arkasına.

### 🔴 F187 — Conflict Preview (Kurulum Öncesi Çakışma Önizleme)
- Kur butonuna basılınca önce `pip install --dry-run --report` (pip 23+) veya uv resolve çalıştır
- "Bu kurulum numpy'ı 2.1'e yükseltecek, scipy ile çakışacak" uyarısını **kurulum başlamadan** göster
- Kullanıcı seçenekleri: Devam Et / İptal / Sürümü Değiştir
- uv'de resolve saniyeler sürer → F193 konumlanmasıyla birebir örtüşür
- İlgili dosyalar: `src/gui/package_ops.py`, `src/core/venv_manager.py`
- Öncelik: 🔴 FAZ 1

### 🔴 F188 — Conflict Hata Dialogu (Okunur Çakışma Ekranı)
- Kurulum `ResolutionImpossible` / dependency conflict ile patlarsa ham log yerine parse edilmiş dialog:
  hangi paket → hangi paketi → hangi sürüm aralığında istiyor, çakışan kim
- Önerilen çözüm butonları: sürüm pinle, ayrı env oluştur, `--upgrade` dene
- Mevcut CommandHintDialog / eğitici hata deseniyle uyumlu
- İlgili dosya: `src/gui/package_ops.py` (hata yakalama noktası)
- Öncelik: 🔴 Kısa vade (v1.6.x)

### 🔴 F189 — Env Doctor (Sağlık Taraması)
- Seçili env'i tara: `pip check` (kırık bağımlılıklar), kırık symlink, dangling pip,
  EOL Python sürümü uyarısı, disk şişkinliği
- Her sorun satırının yanında "Fix" butonu (onarılabilenler için)
- Mevcut fix altyapısı çekirdek olur (`_relocate_venv_paths`, pip freeze fallback vb.)
- Yeni dosyalar: `src/core/env_doctor.py`, `src/gui/doctor_dialog.py`
- Öncelik: 🔴 Kısa vade (v1.6.x)

### 🟡 F190 — Bağımlılık Ağacı Görünümü
- Env paketlerini ağaç olarak göster: hangi paket neyi getirdi (pipdeptree mantığı,
  `importlib.metadata` ile subprocess'siz)
- Çakışan/kırık dallar kırmızı işaretli
- Yeni dosya: `src/gui/deptree_widget.py`
- Öncelik: 🟡 Orta

### 🟡 F191 — Vulnerability Scan (pip-audit Entegrasyonu)
- F159'un pratik hali: env'i `pip-audit` ile tara, bilinen CVE'leri listele
- "Güvenli sürüme yükselt" butonu
- Env Doctor'ın (F189) bir sekmesi olarak da uygulanabilir
- Öncelik: 🟡 Orta

### 🟡 F192 — Orphan Env Keşfi
- Diski tara: VenvStudio'nun bilmediği `.venv` / conda / poetry env'lerini bul
- Boyutlarıyla listele → İçe Aktar veya Sil
- Sonuç özeti: "X GB kazandın"
- Yeni dosya: `src/core/env_discovery.py`
- Öncelik: 🟡 Orta

### 🔴 F193 — uv Derinleşmesi ("uv'nin GUI'si" konumu)
- uv.lock görüntüleme, `uv python` ile Python sürüm yönetimi, `uv tool` listesi
- PEP 723 inline-metadata'lı scriptleri tek tıkla `uv run` ile çalıştırma
- Stratejik not: uv'nin resmi GUI'si yok — bu boşluğu VenvStudio doldurur
- İlgili dosyalar: `src/core/venv_manager.py`, `src/gui/settings_python.py`, yeni `src/core/uv_manager.py`
- Öncelik: 🔴 FAZ 1

### 🟡 F194 — Opt-in Crash Reporter
- Hata olunca "Rapor Oluştur" butonu: traceback + sistem bilgisi →
  panoya kopyala / GitHub issue şablonu aç
- B180 gibi bugların erken haber alınmasını sağlar; telemetri yok, tamamen opt-in
- İlgili dosya: `src/utils/logger.py` (excepthook)
- Öncelik: 🟡 Orta

### 🔴 F195 — CI Test Matrisi
- GitHub Actions: Windows/Linux/macOS × Python 3.10–3.13
- pytest-qt smoke test: uygulama açılıyor mu, ana sekmeler build oluyor mu
- B180 sınıfı "başkasının makinesinde patlıyor" buglarını release öncesi yakalar
- Yeni dosya: `.github/workflows/ci.yml` + `tests/` dizini
- Öncelik: 🔴 Yüksek (altyapı — tüm gelecek işlerin sigortası)

### 🟡 F196 — Dağıtım Kanalları
- winget + Scoop (Windows), Flathub + AUR (Linux), sonra Homebrew (macOS)
- CI'dan (F195) otomatik beslenebilir
- Keşfedilebilirlik: PyPI'dan çok daha geniş kitle
- Öncelik: 🟡 Orta (F195 sonrası)
