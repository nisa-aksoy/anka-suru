"""
ANKA-SÜRÜ Projesi - PMO Kontrol Paneli
OTOMATİK TESTLER (test_anka_suru.py)

Bu dosya, elle hesaplayıp doğruladığımız senaryoları (2., 3., 4. ve 6. Adımlar)
'assert' iddiaları haline getirir. Çalıştırmak için:

    pip install pytest
    pytest test_anka_suru.py -v

'-v' (verbose) bayrağı, her testin adını ve sonucunu tek tek gösterir.
"""

from anka_suru_core import WorkPackage, kaynak_dengele, en_riskli_gorevler


def test_cpm_kritik_yol():
    """
    2. Adımdaki A-B-C-D-E senaryosu: kritik yol A-C-D-E olmalı,
    B'nin float'ı 4 gün olmalı, proje 19 günde bitmeli.
    """
    a = WorkPackage("A", "Gereksinim analizi", iyimser=5, olasi=5, kotumser=5)
    b = WorkPackage("B", "Alt sistem tasarımı", iyimser=3, olasi=3, kotumser=3)
    c = WorkPackage("C", "Yazılım kodlama", iyimser=7, olasi=7, kotumser=7)
    d = WorkPackage("D", "Entegrasyon", iyimser=4, olasi=4, kotumser=4)
    e = WorkPackage("E", "Test", iyimser=3, olasi=3, kotumser=3)

    a.once_gelir(b)
    a.once_gelir(c)
    b.once_gelir(d)
    c.once_gelir(d)
    d.once_gelir(e)

    gorevler = [a, b, c, d, e]
    for g in gorevler:
        g.ileri_gecis()
    proje_bitis = max(g.ef for g in gorevler)
    for g in gorevler:
        g.geri_gecis(proje_bitis)

    assert proje_bitis == 19
    assert a.kritik_mi() is True
    assert c.kritik_mi() is True
    assert d.kritik_mi() is True
    assert e.kritik_mi() is True
    assert b.kritik_mi() is False
    assert b.float_hesapla() == 4


def test_pert_beklenen_sure():
    """
    3. Adımdaki PERT örneği: O=4, M=6, P=14 için TE=7, sigma=1.67 olmalı.
    """
    gorev = WorkPackage("X", "Örnek görev", iyimser=4, olasi=6, kotumser=14)
    assert gorev.beklenen_sure() == 7.0
    assert round(gorev.standart_sapma(), 2) == 1.67


def test_evm_endeksleri():
    """
    4. Adımdaki EVM senaryosu: BAC=100.000, %35 tamamlanmış, AC=45.000,
    bugün gün 10, süre 20 gün -> PV=50.000, EV=35.000, CPI≈0.78, SPI=0.70.
    """
    gorev = WorkPackage("G", "Sürü Davranış Algoritması",
                         iyimser=20, olasi=20, kotumser=20, butce=100_000)
    gorev.ileri_gecis()
    gorev.geri_gecis(proje_bitis=20)
    gorev.tamamlanma_yuzdesi = 35
    gorev.gerceklesen_maliyet = 45_000

    sonuc = gorev.performans_endeksleri(bugun=10)

    assert sonuc["PV"] == 50_000
    assert sonuc["EV"] == 35_000
    assert sonuc["AC"] == 45_000
    assert sonuc["SPI"] == 0.7
    assert round(sonuc["CPI"], 2) == 0.78


def test_risk_skoru_ve_seviyesi():
    """
    6. Adımdaki risk senaryosu: R1 (4x5=20, Yüksek), R2 (2x4=8, Orta), R3 (5x2=10, Orta).
    """
    r1 = WorkPackage("R1", "Sensör ihracat izni", olasilik=4, etki=5)
    r2 = WorkPackage("R2", "Mühendis istifası", olasilik=2, etki=4)
    r3 = WorkPackage("R3", "Hava koşulları", olasilik=5, etki=2)

    assert r1.risk_skoru() == 20
    assert r1.risk_seviyesi() == "Yüksek"
    assert r2.risk_skoru() == 8
    assert r2.risk_seviyesi() == "Orta"
    assert r3.risk_skoru() == 10
    assert r3.risk_seviyesi() == "Orta"


def test_en_riskli_gorevler_siralama():
    """en_riskli_gorevler(), skorları büyükten küçüğe sıralı döndürmeli: R1 > R3 > R2."""
    proje = WorkPackage("0.0", "Proje")
    r1 = WorkPackage("R1", "Sensör ihracat izni", olasilik=4, etki=5)
    r2 = WorkPackage("R2", "Mühendis istifası", olasilik=2, etki=4)
    r3 = WorkPackage("R3", "Hava koşulları", olasilik=5, etki=2)
    for r in [r1, r2, r3]:
        proje.alt_gorev_ekle(r)

    siralı = en_riskli_gorevler(proje, adet=3)
    assert [g.wbs_kodu for g in siralı] == ["R1", "R3", "R2"]


def test_yuzde_yuz_kurali_roll_up():
    """
    WBS'in '%100 Kuralı': bir fazın toplam bütçesi, kendi başına
    girilmez — altındaki tüm iş paketlerinin bütçe toplamı olmalı.
    """
    proje = WorkPackage("0.0", "Proje")
    faz = WorkPackage("1.0", "Sistem Mühendisliği")
    proje.alt_gorev_ekle(faz)

    ip1 = WorkPackage("1.1", "Gereksinim analizi", butce=30_000)
    ip2 = WorkPackage("1.2", "Sistem tasarımı", butce=20_000)
    faz.alt_gorev_ekle(ip1)
    faz.alt_gorev_ekle(ip2)

    # Fazın kendi 'butce' alanı hiç girilmedi (varsayılan 0),
    # ama toplam_butce() otomatik olarak 30.000 + 20.000 = 50.000 dönmeli.
    assert faz.toplam_butce() == 50_000
    assert proje.toplam_butce() == 50_000  # kök de aynı toplamı yansıtmalı
    assert ip1.toplam_butce() == 30_000    # yaprak, kendi değerini döner



    """
    5. Adımdaki kaynak dengeleme senaryosu: B ve C aynı kaynağa (Zeynep K.)
    atanmışsa, kritik olan (C, float=0) önce çalışmalı, B onun ardına kaymalı.
    """
    a = WorkPackage("A", "Gereksinim analizi", iyimser=5, olasi=5, kotumser=5)
    b = WorkPackage("B", "Tasarım", iyimser=3, olasi=3, kotumser=3, atanan_kaynak="Zeynep K.")
    c = WorkPackage("C", "Kodlama", iyimser=7, olasi=7, kotumser=7, atanan_kaynak="Zeynep K.")
    d = WorkPackage("D", "Entegrasyon", iyimser=4, olasi=4, kotumser=4)

    a.once_gelir(b)
    a.once_gelir(c)
    b.once_gelir(d)
    c.once_gelir(d)

    gorevler = [a, b, c, d]
    for g in gorevler:
        g.ileri_gecis()
    proje_bitis = max(g.ef for g in gorevler)
    for g in gorevler:
        g.geri_gecis(proje_bitis)

    kaynak_dengele(gorevler)

    # C, float'ı düşük olduğu için önce çalışmalı (5-12), B onun ardına kaymalı (12-15)
    assert c.fiili_baslangic == 5
    assert c.fiili_bitis == 12
    assert b.fiili_baslangic == 12
    assert b.fiili_bitis == 15
