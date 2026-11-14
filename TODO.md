# Günlük küçük geliştirmeler

Her gün bir madde: kodu yaz, `.venv/bin/python -m pytest -q` ile test et, commit at, push et.
Commit mesajı kısa ve ne yaptığını anlatsın (Fransızca, mevcut commit'ler gibi).

## 1. gün: testler + GitHub'a yükleme
- [x] `tests/test_nettoyer.py` içindeki 2 boş testi tamamla (`pytest.skip` satırını sil, `assert` yaz).
- [ ] GitHub'da **public** `analyse-immobilier-paris-dvf` reposu aç (README ekleme, boş olsun), sonra:
      ```
      git add tests pytest.ini requirements-dev.txt TODO.md
      git commit -m "Ajout des tests unitaires du nettoyage"
      git remote add origin https://github.com/EmecaNemo/analyse-immobilier-paris-dvf.git
      git push -u origin main
      ```

## 2. gün: CI
- [ ] `.github/workflows/tests.yml`: Python 3.12, `pip install -r requirements.txt -r requirements-dev.txt`,
      `python -m pytest -q`. Actions sekmesinde yeşil tik + README'ye rozet.

## 3. gün: modelin testi
- [ ] `src/modele.py` → `scores()` için bir test: `y_true == y_pred` iken MAE 0 olmalı.
- [ ] `add_features()` için bir test: hangi sütunları ekliyor? Önce fonksiyonu oku, sonra test et.

## 4. gün: SQL testleri
- [ ] `sql/prix_par_taille.sql`'i DuckDB'de 5 satırlık sahte bir `transactions` tablosu üzerinde çalıştıran
      bir test yaz (`duckdb.connect()` + `CREATE TABLE transactions AS SELECT * FROM df`).

## 5. gün: README
- [ ] "Tests" bölümü ekle; Streamlit uygulamasının ekran görüntüsünü `docs/` altına koy, README'de göster.

## Sonra (fikirler)
- Streamlit Community Cloud'a ücretsiz yayın, README'ye canlı link.
- Bu projenin temizleme kuralları, **A-paris-immo-data-platform**'da dbt ile SQL'e taşınıyor: README'de bağlantı ver.
