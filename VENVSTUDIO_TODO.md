# VENVSTUDIO_TODO.md

---

## 🔴 EN ÖNCELİKLİ (Sonraki Sprint)

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

---

### ✅ B141 — Windows pipx Launch App Yüklenince Tablo Güncellenmiyor (TAMAMLANDI v1.4.66)
- [x] `package_panel._on_app_install_finished` — success branch'inde `env_refresh_requested.emit()` çağrılıyor artık
- [x] Pipx path tespit edilirse `VenvManager.invalidate_all_caches()` çağrılıyor (pipx'te app'ler aynı cache tree'yi paylaşır)
- [x] `_on_system_install_finished` — conda installs için de aynı emit + cache invalidation eklendi
- [x] `_on_install_finished` zaten doğru emit ediyordu (önceden)
- Main window `env_refresh_requested` signal'ını `_refresh_env_list`'e bağlı tutuyor (mevcut wiring)

### ✨ F140 — Launcher'da Package Conflict/Version Ayarı
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

---

## 🔚 SON SIRA (ertelendi)

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
