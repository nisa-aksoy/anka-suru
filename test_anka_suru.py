"""
ANKA-SÜRÜ Projesi - PMO Kontrol Paneli
OTOMATİK TESTLER (test_anka_suru.py)

Bu dosya, elle hesaplayıp doğruladığımız senaryoları (2., 3., 4. ve 6. Adımlar)
'assert' iddiaları haline getirir. Çalıştırmak için:

    pip install pytest
    pytest test_anka_suru.py -v

'-v' (verbose) bayrağı, her testin adını ve sonucunu tek tek gösterir.
"""

import statistics

from anka_suru_core import WorkPackage, kaynak_dengele, en_riskli_gorevler, kritik_zincir_belirle, tampon_hesapla
from proje_verisi import get_proje, agaci_kur, hesapla, monte_carlo_calistir, critical_chain_calistir
from karar_destek import (
    takvim_karti_uret, butce_karti_uret, risk_karti_uret,
    bilesik_risk_karti_uret, teslim_tarihi_karti_uret, kaynak_karti_uret,
    genel_durum_belirle, karar_destek_calistir,
)


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


def test_performans_endeksleri_ev_sifirken_cpi_spi_none_ile_karismiyor():
    """
    Düzeltilen bug: EV=0 (henüz ilerleme yok) ama AC>0 (harcama yapılmış)
    ve PV>0 (planlanan zaman geçmiş) olduğunda, gerçekte hesaplanabilen
    CPI=0.0 ve SPI=0.0 değerleri -- Python'da 0.0'ın 'falsy' olması
    yüzünden (eski kod: 'if cpi else None') yanlışlıkla None'a
    (sanki hiç veri yokmuş gibi) düşüyordu. Bu, en kötü performans
    sinyalini (sıfır ilerleme + harcama/planlanan süre geçmiş) tabloda
    gizliyordu. Artık 'is not None' kontrolü kullanıldığı için CPI/SPI
    gerçekten hesaplanabiliyorsa (ac>0, pv>0) -- değerleri 0.0 olsa
    bile -- olduğu gibi gösterilmeli.
    """
    gorev = WorkPackage("T", "Test görevi", iyimser=10, olasi=10, kotumser=10, butce=50_000)
    gorev.ileri_gecis()
    gorev.geri_gecis(proje_bitis=10)
    gorev.tamamlanma_yuzdesi = 0       # EV = 0
    gorev.gerceklesen_maliyet = 8_000  # AC > 0

    sonuc = gorev.performans_endeksleri(bugun=10)  # bugun >= ef -> PV = tam bütçe > 0

    assert sonuc["EV"] == 0.0
    assert sonuc["PV"] == 50_000
    assert sonuc["AC"] == 8_000
    assert sonuc["CPI"] == 0.0   # None DEĞİL
    assert sonuc["SPI"] == 0.0   # None DEĞİL

    # Karşı örnek: CPI ve SPI birbirinden BAĞIMSIZ iki farklı 'veri yok'
    # koşuluna bağlı -- CPI, AC=0 iken None olur (harcama verisi yok);
    # SPI ise PV=0 iken None olur (henüz zaman geçmemiş). AC=0 olması
    # SPI'yi etkilemez: bugun=10'da (görev bitmiş, PV>0) SPI=0.0 olarak
    # (gerçek, hesaplanabilir bir değer) dönmesi beklenir -- None'a hâlâ
    # yanlışlıkla düşmediğinin kanıtı.
    gorev2 = WorkPackage("T2", "Harcaması olmayan görev",
                          iyimser=10, olasi=10, kotumser=10, butce=50_000)
    gorev2.ileri_gecis()
    gorev2.geri_gecis(proje_bitis=10)
    sonuc2 = gorev2.performans_endeksleri(bugun=10)  # AC=0, ama PV>0
    assert sonuc2["CPI"] is None    # gerçekten veri yok (AC=0)
    assert sonuc2["SPI"] == 0.0     # veri VAR ve hesaplanan değer 0.0

    # PV=0 durumunda (görev henüz başlamamış) SPI gerçekten None olmalı.
    onceki = WorkPackage("H", "Önceki görev", iyimser=5, olasi=5, kotumser=5)
    henuz_baslamamis = WorkPackage("T4", "Henüz başlamamış görev",
                                    iyimser=10, olasi=10, kotumser=10, butce=50_000)
    onceki.once_gelir(henuz_baslamamis)
    for x in (onceki, henuz_baslamamis):
        x.ileri_gecis()
    proje_bitis = max(x.ef for x in (onceki, henuz_baslamamis))
    for x in (onceki, henuz_baslamamis):
        x.geri_gecis(proje_bitis)
    sonuc3 = henuz_baslamamis.performans_endeksleri(bugun=0)  # bugun <= es -> PV=0
    assert sonuc3["SPI"] is None


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


def test_kaynak_dengele_basit_senaryo():
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


def test_rastgele_sure_sinirlar_icinde():
    """
    rastgele_sure()'ün her örneği [iyimser, kotumser] aralığında olmalı VE
    bu aralığın ÜST UCUNA (kötümser) gerçekten yaklaşabilmeli.

    Önceki fixture (iyimser=4, olasi=6, kotumser=14) bunu güvenilir şekilde
    sınamıyordu: random.triangular()'a argümanlar YANLIŞ sırayla verilse
    bile (low=iyimser, high=olasi, mode=kotumser), o üçlüde ortaya çıkan
    dar/bozuk aralık ([~4, ~8.5]) yine de [iyimser, kotumser]=[4,14] alt
    kümesi kaldığı için "sınırlar içinde" testi YANLIŞLIKLA geçiyordu --
    üst sınıra hiç yaklaşmadığı hiç fark edilmiyordu.

    Bu yüzden burada belirgin şekilde asimetrik bir üçlü kullanıyoruz
    (olasi, kötümserden çok uzakta): doğru argüman sırasıyla (low=iyimser,
    high=kotumser, mode=olasi) binlerce örnekten en az birinin kötümsere
    ciddi biçimde yaklaşması gerekir. Argümanlar ters verilirse (bug)
    high=olasi=5 olacağından örnekler yapısal olarak ~9'u hiç geçemez --
    bu yüzden "max > 15" eşiği bug'ı güvenilir şekilde yakalar.
    """
    gorev = WorkPackage("X", "Örnek görev", iyimser=2, olasi=5, kotumser=20)
    ornekler = [gorev.rastgele_sure() for _ in range(3000)]

    for s in ornekler:
        assert 2 <= s <= 20

    # Üst sınıra (kötümser=20) gerçekten yaklaşılabiliyor mu?
    # Doğru argüman sırasında gözlenen maksimum tipik olarak ~19.3-19.9;
    # ters sırada (bug) yapısal olarak ~9.3'ü hiç geçmiyor. 15 eşiği
    # ikisi arasında geniş, güvenli bir marj bırakıyor.
    assert max(ornekler) > 15


def test_rastgele_sure_ortalamasi_dogru_triangular_formulune_yakinsiyor():
    """
    İstatistiksel tutarlılık kontrolü: rastgele_sure(), PERT'in ağırlıklı
    ortalamasını (beklenen_sure = (i+4o+k)/6) DEĞİL, ham bir üçgen
    (triangular) dağılımı örnekler. Bu yüzden yakınsaması gereken doğru
    referans, üçgen dağılımın kendi ortalama formülüdür:
        (iyimser + olasi + kotumser) / 3

    NOT -- önceki versiyon burada beklenen_sure()'e (PERT ortalaması)
    yakınsamayı kontrol ediyordu. Bu, iyimser=4/olasi=6/kotumser=14
    üçlüsünde YANLIŞLIKLA geçiyordu: argümanlar ters verildiğinde
    (low=iyimser, high=olasi, mode=kotumser) ortaya çıkan bozuk dağılımın
    ortalaması (~6.97) tesadüfen PERT ortalamasına (7.0) yakın çıkıyordu.
    Oysa doğru üçgen dağılımın gerçek ortalaması 8.0'dır (7.0'dan %14
    uzak) -- yani eski test, PERT ile üçgen dağılımın FARKLI formüller
    olduğunu göz ardı ederek bug'ı gizliyordu. Bu test artık doğru
    formülle karşılaştırıyor: argüman sırası bozuksa gözlenen ortalama
    (~6.97), doğru değerden (8.0) toleransın dışına düşüp testi
    başarısız kılar.
    """
    gorev = WorkPackage("X", "Örnek görev", iyimser=4, olasi=6, kotumser=14)
    dogru_ortalama = (gorev.iyimser + gorev.olasi + gorev.kotumser) / 3  # 8.0

    N = 5000
    ortalama = sum(gorev.rastgele_sure() for _ in range(N)) / N
    assert abs(ortalama - dogru_ortalama) < dogru_ortalama * 0.10


def test_rastgele_sure_sabit_gorevde_degismiyor():
    """
    iyimser=olasi=kotumser olan görevler (ör. süresi-0 risk kayıtları,
    ya da belirsizliği olmayan sabit süreli görevler) için rastgele_sure()
    her zaman o sabit değeri dönmeli — dağılımın genişliği 0 olduğunda
    örnekleme rastgelelik katmamalı.
    """
    sabit_gorev = WorkPackage("R", "Sabit süreli görev",
                               iyimser=5, olasi=5, kotumser=5)
    for _ in range(50):
        assert sabit_gorev.rastgele_sure() == 5


def test_kirpik_sure_olasi_degerini_donuyor():
    """
    kirpik_sure(), Critical Chain'in 'güvenlik paysız tahmin' kavramı için
    doğrudan PERT üçlüsündeki 'olasi' (en olası/mod) değerini dönmeli.
    """
    gorev = WorkPackage("X", "Örnek görev", iyimser=4, olasi=6, kotumser=14)
    assert gorev.kirpik_sure() == 6


def test_kirpik_sure_beklenen_sureden_kisa_veya_esit():
    """
    kirpik_sure(), kotumser'in içine gömülü güvenlik payını taşımadığı
    için beklenen_sure()'den (PERT ağırlıklı ortalaması) her zaman KISA
    veya EN FAZLA eşit olmalı — asla daha uzun olamaz. Bu, Critical
    Chain'in 'her görevden bir miktar süre kırpıyoruz' iddiasının
    matematiksel garantisidir.
    """
    ornekler = [
        WorkPackage("A", "İyimser-ağırlıklı", iyimser=2, olasi=4, kotumser=6),
        WorkPackage("B", "Kötümser-ağırlıklı", iyimser=3, olasi=5, kotumser=20),
        WorkPackage("C", "Simetrik", iyimser=5, olasi=5, kotumser=5),
    ]
    for gorev in ornekler:
        assert gorev.kirpik_sure() <= gorev.beklenen_sure()


def _abcd_agi_kur():
    """Yardımcı: A->B,A->C,B->D,C->D ağını kurar; B ve C aynı kaynağa
    atanmıştır (Zeynep K.), çakışma senaryosu için."""
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
    return a, b, c, d, gorevler


def test_kaynak_dengele_gecikme_zincire_yayiliyor():
    """
    D, hem B hem C'ye bağımlı. B kaynak çakışması yüzünden 15'te bitiyor
    (C'den sonra). D'nin gerçek başlangıcı, B'nin bu GERÇEK (fiili)
    bitişini görmeli — eski (hatalı) davranışta D, B'nin gecikmesini
    görmeden kendi orijinal CPM es'inden (12) başlıyordu.
    """
    a, b, c, d, gorevler = _abcd_agi_kur()
    assert c.fiili_baslangic == 5 and c.fiili_bitis == 12
    assert b.fiili_baslangic == 12 and b.fiili_bitis == 15
    assert d.fiili_baslangic == 15   # B'nin gecikmesini görüyor, C'nin değil
    assert d.fiili_bitis == 19


def test_kritik_zincir_belirle_gercek_darbogazi_buluyor():
    """
    CPM'in kritik yolu (float=0) A-C-D derdi (B'nin float'ı var çünkü
    ağ/bağımlılık açısından acelesi yok). Ama kaynak çakışması yüzünden
    asıl darboğaz B'dir (D'yi 15'e kadar bekletiyor). Critical Chain
    bunu doğru yakalayıp zincire B'yi (C'yi değil) dahil etmeli.
    """
    a, b, c, d, gorevler = _abcd_agi_kur()
    zincir_kodlari = [g.wbs_kodu for g in kritik_zincir_belirle(gorevler)]
    assert zincir_kodlari == ["A", "C", "B", "D"]


def test_tampon_hesapla_elle_hesapla_ile_eslesiyor():
    """
    tampon_hesapla(), zincirdeki her görevin (beklenen_sure()-kirpik_sure())
    farkını toplayıp yarısını dönmeli. A-B-C-D ağında iyimser=olasi=kotumser
    (sabit değerler) olduğu için beklenen_sure()==kirpik_sure()==olasi —
    yani bu senaryoda kırpılan pay SIFIR olmalı (belirsizlik yok ki
    kırpılacak bir şey olsun). Sıfır olmayan bir örnekle de kontrol ediyoruz.
    """
    a, b, c, d, gorevler = _abcd_agi_kur()
    zincir = kritik_zincir_belirle(gorevler)
    assert tampon_hesapla(zincir) == 0.0  # iyimser=olasi=kotumser -> kırpılacak pay yok

    # Belirsizliği olan (iyimser != kotumser) bir görevle elle doğrulama
    x = WorkPackage("X", "Belirsiz görev", iyimser=4, olasi=6, kotumser=14)
    y = WorkPackage("Y", "Belirsiz görev 2", iyimser=2, olasi=3, kotumser=10)
    # x: beklenen=(4+24+14)/6=7.0, kirpik=6 -> fark=1.0
    # y: beklenen=(2+12+10)/6=4.0, kirpik=3 -> fark=1.0
    # toplam=2.0, tampon=1.0
    assert tampon_hesapla([x, y]) == 1.0


# ==================== Karar Destek Sistemi (DSS) testleri ====================

def test_takvim_karti_uret_esige_gore_durum_belirliyor():
    """
    2. Adımdaki A-B-C-D-E ağı (test_cpm_kritik_yol'daki ile birebir aynı):
    kritik yol A-C-D-E, B'nin float'ı 4 gün. Varsayılan eşikle (2 gün)
    B 'kritiğe yakın' sayılmamalı (Yeşil); eşik 5 güne çıkarılınca B
    kritiğe yakın sayılmalı (Sarı).
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

    kartlar_varsayilan = takvim_karti_uret(gorevler)
    assert kartlar_varsayilan[0]["durum"] == "Yeşil"

    kartlar_genis_esik = takvim_karti_uret(gorevler, kritige_yakin_esik=5)
    assert kartlar_genis_esik[0]["durum"] == "Sarı"
    assert "B" in kartlar_genis_esik[0]["gerekce"]


def test_butce_karti_uret_esikleri_dogru_uyguluyor():
    """
    CPI/SPI eşiklerinin (<0.90 Sarı, <0.80 Kırmızı) doğru uygulandığını
    ve ikisinden HANGİSİ daha kötüyse onun kazandığını (worst-of)
    kontrol eder.
    """
    kart = butce_karti_uret(100_000, proje_cpi=0.95, proje_spi=0.95, proje_eac=100_000)
    assert kart[0]["durum"] == "Yeşil"

    kart = butce_karti_uret(100_000, proje_cpi=0.95, proje_spi=0.85, proje_eac=105_000)
    assert kart[0]["durum"] == "Sarı"

    kart = butce_karti_uret(100_000, proje_cpi=0.70, proje_spi=0.95, proje_eac=140_000)
    assert kart[0]["durum"] == "Kırmızı"


def test_butce_karti_uret_veri_yoksa_yesil_ama_belirtiyor():
    """
    CPI ve SPI ikisi de None ise (henüz harcama/ilerleme yok), kart
    Yeşil döner ama gerekçede bunun 'veri yok' anlamına geldiği açıkça
    yazmalı -- yanlış bir güvence vermemeli.
    """
    kart = butce_karti_uret(100_000, proje_cpi=None, proje_spi=None, proje_eac=100_000)
    assert kart[0]["durum"] == "Yeşil"
    assert "veri yok" in kart[0]["gerekce"]


def test_risk_karti_uret_seviyeye_gore_durum_belirliyor():
    """
    6. Adımdaki risk senaryosu (R1 Yüksek, R2/R3 Orta) tekrar kullanılıyor.
    En az bir Yüksek varsa Kırmızı; sadece Orta varsa Sarı; risk yoksa Yeşil.
    """
    r1 = WorkPackage("R1", "Sensör ihracat izni", olasilik=4, etki=5)
    r2 = WorkPackage("R2", "Mühendis istifası", olasilik=2, etki=4)
    r3 = WorkPackage("R3", "Hava koşulları", olasilik=5, etki=2)

    assert risk_karti_uret([r1, r2, r3])[0]["durum"] == "Kırmızı"
    assert risk_karti_uret([r2, r3])[0]["durum"] == "Sarı"
    assert risk_karti_uret([])[0]["durum"] == "Yeşil"


def test_bilesik_risk_karti_uret_kesisimi_buluyor():
    """
    Kritik (float=0) bir görev aynı zamanda Yüksek risk taşıyorsa,
    bileşik risk kartı bunu Kırmızı olarak yakalamalı -- CPM veya Risk
    Matrisi tek başına bunu göremezdi.
    """
    a = WorkPackage("A", "Gereksinim analizi", iyimser=5, olasi=5, kotumser=5)
    b = WorkPackage("B", "Alt sistem tasarımı", iyimser=3, olasi=3, kotumser=3)
    c = WorkPackage("C", "Yazılım kodlama", iyimser=7, olasi=7, kotumser=7,
                     olasilik=4, etki=5)  # kritik VE yüksek riskli
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

    kart = bilesik_risk_karti_uret(gorevler, riskliler=[c])
    assert kart[0]["durum"] == "Kırmızı"
    assert "C" in kart[0]["gerekce"]


def test_bilesik_risk_karti_uret_kesisim_yoksa_yesil():
    """
    Riskli görev, kritiğe yakın OLMAYAN (bolluğu yeterli) bir görevse,
    kesişim olmamalı -- Yeşil dönmeli. Aynı A-B-C-D-E ağı, bu sefer risk
    B'ye (float=4, varsayılan esik=2'nin üstünde) veriliyor.
    """
    a = WorkPackage("A", "Gereksinim analizi", iyimser=5, olasi=5, kotumser=5)
    b = WorkPackage("B", "Alt sistem tasarımı", iyimser=3, olasi=3, kotumser=3,
                     olasilik=4, etki=5)
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

    kart = bilesik_risk_karti_uret(gorevler, riskliler=[b])
    assert kart[0]["durum"] == "Yeşil"


def test_teslim_tarihi_karti_uret_bantlari_dogru():
    """P50/P80/P90 bantlarına göre üç durumun da doğru üretildiğini kontrol eder."""
    mc_sonuc = {"p50": 50, "p80": 55, "p90": 60, "iterasyon_sayisi": 1000}

    assert teslim_tarihi_karti_uret(mc_sonuc, hedef_gun=65)[0]["durum"] == "Yeşil"
    assert teslim_tarihi_karti_uret(mc_sonuc, hedef_gun=52)[0]["durum"] == "Sarı"
    assert teslim_tarihi_karti_uret(mc_sonuc, hedef_gun=45)[0]["durum"] == "Kırmızı"


def test_teslim_tarihi_karti_uret_veri_yoksa_kart_uretmiyor():
    """mc_sonuc veya hedef_gun verilmemişse (None) kart üretilmemeli."""
    mc_sonuc = {"p50": 50, "p80": 55, "p90": 60, "iterasyon_sayisi": 1000}
    assert teslim_tarihi_karti_uret(None, hedef_gun=60) == []
    assert teslim_tarihi_karti_uret(mc_sonuc, hedef_gun=None) == []


def test_kaynak_karti_uret_ayni_kaynagin_birden_fazla_gorevini_yakaliyor():
    """
    Kritik zincirde aynı kaynağa 2+ görev atanmışsa Sarı dönmeli, tek tek
    farklı kaynaklara atanmışsa Yeşil dönmeli.
    """
    a = WorkPackage("A", "Gereksinim analizi")
    b = WorkPackage("B", "Tasarım", atanan_kaynak="Zeynep K.")
    c = WorkPackage("C", "Kodlama", atanan_kaynak="Zeynep K.")
    d = WorkPackage("D", "Entegrasyon", atanan_kaynak="Can B.")

    cc_sonuc_darbogazli = {"kritik_zincir": [a, b, c, d], "proje_tamponu": 1.0}
    kart = kaynak_karti_uret(cc_sonuc_darbogazli)
    assert kart[0]["durum"] == "Sarı"
    assert "Zeynep K." in kart[0]["gerekce"]

    cc_sonuc_dengeli = {"kritik_zincir": [a, b, d], "proje_tamponu": 1.0}
    assert kaynak_karti_uret(cc_sonuc_dengeli)[0]["durum"] == "Yeşil"


def test_kaynak_karti_uret_veri_yoksa_kart_uretmiyor():
    """cc_sonuc verilmemişse (None) kart üretilmemeli."""
    assert kaynak_karti_uret(None) == []


def test_genel_durum_belirle_en_kotuyu_seciyor():
    """
    Worst-of mantığı: kartlar arasında en az bir Kırmızı varsa genel
    durum Kırmızı, yoksa en az bir Sarı varsa Sarı, hepsi Yeşilse Yeşil.
    Ağırlıklı ortalama YOK -- tek bir kırmızı diğerleri arasında
    gizlenmemeli.
    """
    assert genel_durum_belirle([{"durum": "Yeşil"}, {"durum": "Kırmızı"}, {"durum": "Sarı"}]) == "Kırmızı"
    assert genel_durum_belirle([{"durum": "Yeşil"}, {"durum": "Sarı"}]) == "Sarı"
    assert genel_durum_belirle([{"durum": "Yeşil"}, {"durum": "Yeşil"}]) == "Yeşil"
    assert genel_durum_belirle([]) == "Yeşil"


def test_karar_destek_calistir_gercek_projeyle_uctan_uca_calisiyor():
    """
    Uçtan uca entegrasyon testi: gerçek ANKA-SÜRÜ verisiyle
    karar_destek_calistir() hatasız çalışmalı. mc_sonuc/cc_sonuc/hedef_gun
    verilmediği için 'Teslim Tarihi' ve 'Kaynak' kartları ÜRETİLMEMELİ --
    diğer dördü (Takvim, Bütçe, Risk, Bileşik Risk) her zaman üretilir.
    """
    proje, yapraklar = get_proje()
    riskliler = en_riskli_gorevler(proje, adet=10)
    toplam_butce = sum(g.butce for g in yapraklar)
    toplam_ev = sum(g.kazanilan_deger() for g in yapraklar)
    toplam_pv = sum(g.planlanan_deger(15) for g in yapraklar)
    toplam_ac = sum(g.gerceklesen_maliyet for g in yapraklar)
    proje_cpi = toplam_ev / toplam_ac if toplam_ac else None
    proje_spi = toplam_ev / toplam_pv if toplam_pv else None
    proje_eac = toplam_butce / proje_cpi if proje_cpi else toplam_butce

    sonuc = karar_destek_calistir(yapraklar, riskliler, toplam_butce,
                                   proje_cpi, proje_spi, proje_eac)

    assert sonuc["genel_durum"] in ("Yeşil", "Sarı", "Kırmızı")
    kategoriler = {k["kategori"] for k in sonuc["kartlar"]}
    assert kategoriler == {"Takvim", "Bütçe", "Risk", "Bileşik Risk"}


# --------------------------------------------------------------------------
# Orkestrasyon / entegrasyon testleri (monte_carlo_calistir, critical_chain_
# calistir ve What-If akışı) -- gerçek ANKA-SÜRÜ verisiyle uçtan uca çalışır.
# Alt bileşenler (rastgele_sure, kirpik_sure, kritik_zincir_belirle,
# tampon_hesapla) yukarıda ayrı ayrı test edildi; buradaki testler onların
# gerçek projede DOĞRU SIRAYLA bir araya geldiğini doğruluyor.
# --------------------------------------------------------------------------

def test_monte_carlo_calistir_gercek_projeyle_tutarli_sonuc_uretiyor():
    """
    monte_carlo_calistir() her iterasyonda agaci_kur() ile TAZE bir ağaç
    kurup rastgele_sure() ile ileri_gecis() çalıştırır. Ağaç iterasyonlar
    arasında yeniden kullanılsaydı (ileri_gecis'in kendi kendini koruyan
    "if self.es is not None: return" mekanizması yüzünden), tüm sonuçlar
    donar ve birbirinin aynısı çıkardı -- yani varyans sıfır olurdu.

    Rastgele örneklemede iki iterasyonun nadiren aynı sonucu vermesi
    teorik olarak mümkün olduğundan "300 sonucun HEPSİ farklı" yerine,
    daha sağlam bir varyans kontrolü kullanılıyor: standart sapma
    sıfırdan büyük mü VE sonuçların en az %95'i birbirinden farklı mı.
    """
    sonuc = monte_carlo_calistir(300)

    assert sonuc["iterasyon_sayisi"] == 300
    assert len(sonuc["sonuclar"]) == 300

    # Fresh-tree-per-iteration garantisi: varyans sıfırdan büyük olmalı.
    assert statistics.pstdev(sonuc["sonuclar"]) > 0
    # Ek güvence: sonuçların büyük çoğunluğu (>= %95) birbirinden farklı.
    assert len(set(sonuc["sonuclar"])) >= round(300 * 0.95)

    assert sonuc["p50"] <= sonuc["p80"] <= sonuc["p90"]


def test_monte_carlo_calistir_kucuk_iterasyon_sayisinda_cokmuyor():
    """
    Edge case: statistics.quantiles() en az 2 veri noktası ister.
    monte_carlo_calistir(1) (hatta 0) eskiden StatisticsError ile
    çöküyordu. Uygulamadaki slider (min_value=100) bu durumu UI
    üzerinden hiç tetiklemez, ama fonksiyon genel kullanıma açık
    olduğu için (doğrudan çağrılırsa) çökmemeli -- burada "sonuçlar
    her zaman benzersiz olmalı" gibi bir beklenti YOK, sadece
    çökmediği ve mantıklı bir değer döndürdüğü kontrol ediliyor.
    """
    sonuc_bir = monte_carlo_calistir(1)
    assert sonuc_bir["iterasyon_sayisi"] == 1
    assert len(sonuc_bir["sonuclar"]) == 1
    # Tek örnekle gerçek bir yüzdelik hesaplanamaz -- en iyi tahmin
    # elimizdeki tek değerin kendisidir.
    assert sonuc_bir["p50"] == sonuc_bir["p80"] == sonuc_bir["p90"] == round(sonuc_bir["sonuclar"][0], 1)

    sonuc_iki = monte_carlo_calistir(2)
    assert len(sonuc_iki["sonuclar"]) == 2
    assert sonuc_iki["p50"] <= sonuc_iki["p80"] <= sonuc_iki["p90"]

    sonuc_on = monte_carlo_calistir(10)
    assert len(sonuc_on["sonuclar"]) == 10
    assert sonuc_on["p50"] <= sonuc_on["p80"] <= sonuc_on["p90"]


def test_critical_chain_calistir_gercek_projeyle_tutarli_sonuc_uretiyor():
    """
    Mevcut testler kritik_zincir_belirle() ve tampon_hesapla()'yı küçük,
    sentetik senaryolarla tek tek doğruluyor; ama bu parçaların gerçek
    proje verisiyle, doğru sırayla (kirpik_sure -> ileri_gecis ->
    geri_gecis -> kaynak_dengele -> kritik_zincir_belirle ->
    tampon_hesapla) bir araya geldiğini hiçbir test doğrulamıyor. Bu test
    tam o orkestrasyonu, dönen dict'in yapısını ve iç aritmetik
    tutarlılığını kontrol ediyor.
    """
    _baseline_proje, baseline_yapraklar = get_proje()
    baseline_suresi = max(g.ef for g in baseline_yapraklar)

    sonuc = critical_chain_calistir()

    assert set(sonuc.keys()) == {
        "yapraklar", "kritik_zincir", "proje_suresi_kirpik",
        "proje_tamponu", "proje_suresi_tamponlu",
    }
    assert len(sonuc["kritik_zincir"]) > 0

    # proje_suresi_tamponlu, kirpik süre + tamponun toplamı olmalı.
    assert sonuc["proje_suresi_tamponlu"] == round(
        sonuc["proje_suresi_kirpik"] + sonuc["proje_tamponu"], 1
    )

    # kirpik_sure ("olası" süre, iyimser bir tahmin) kullanıldığı için
    # kirpik süre, normal (beklenen_sure ile hesaplanan) baseline süreden
    # kısa ya da eşit olmalı -- kirpik_sure'nin gerçekten devreye
    # girdiğinin kanıtı.
    assert sonuc["proje_suresi_kirpik"] <= baseline_suresi


def test_what_if_senaryosu_baseline_agaci_mutate_etmiyor():
    """
    app.py'deki What-If akışının simülasyonu: agaci_kur() ile kurulan
    bağımsız bir ağaç üzerinde bir görevin PERT değerleri değiştirilip
    hesapla() çalıştırılıyor. Bu akış test suite'inde hiç kapsanmıyordu.

    İki şey kanıtlanıyor:
    1. PERT değişikliği gerçekten proje süresine yansıyor.
    2. Bu değişiklik, get_proje() ile kurulan AYRI bir baseline ağacın
       nesnelerini ETKİLEMİYOR -- agaci_kur()'un her çağrıda tamamen
       bağımsız yeni nesneler ürettiğinin kanıtı. Bu olmadan, uygulamada
       kullanıcı bir what-if senaryosu denediğinde asıl proje verisi
       sessizce bozulabilir.
    """
    _baseline_proje, baseline_yapraklar = get_proje()
    baseline_suresi_once = max(g.ef for g in baseline_yapraklar)

    _whatif_proje, whatif_yapraklar = agaci_kur()
    sensor = next(g for g in whatif_yapraklar if g.wbs_kodu == "2.2")
    sensor.iyimser, sensor.olasi, sensor.kotumser = 50, 60, 80
    hesapla(whatif_yapraklar)
    whatif_suresi = max(g.ef for g in whatif_yapraklar)

    assert whatif_suresi > baseline_suresi_once

    baseline_suresi_sonra = max(g.ef for g in baseline_yapraklar)
    assert baseline_suresi_sonra == baseline_suresi_once
