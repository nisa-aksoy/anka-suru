from anka_suru_core import (WorkPackage, kaynak_dengele, en_riskli_gorevler,
                             kritik_zincir_belirle, tampon_hesapla)
import statistics


def agaci_kur():
    proje = WorkPackage("0.0", "ANKA-SÜRÜ Otonom Sürü İHA Sistemi")

    faz1 = WorkPackage("1.0", "Sistem Mühendisliği ve Gereksinim Analizi")
    proje.alt_gorev_ekle(faz1)
    gereksinim = WorkPackage("1.1", "Gereksinim analizi",
                              iyimser=3, olasi=5, kotumser=8, butce=30_000,
                              sorumlu="Ahmet Y.")
    gereksinim.tamamlanma_yuzdesi = 100
    gereksinim.gerceklesen_maliyet = 29_000
    faz1.alt_gorev_ekle(gereksinim)

    istifa_riski = WorkPackage("1.2", "Kıdemli mühendis istifa riski",
                                iyimser=0, olasi=0, kotumser=0,
                                olasilik=2, etki=4)
    faz1.alt_gorev_ekle(istifa_riski)

    faz2 = WorkPackage("2.0", "Havacılık Platformu Tasarımı")
    proje.alt_gorev_ekle(faz2)
    airframe = WorkPackage("2.1", "Airframe tasarımı",
                            iyimser=5, olasi=8, kotumser=12, butce=60_000,
                            sorumlu="Mehmet T.")
    airframe.tamamlanma_yuzdesi = 80
    airframe.gerceklesen_maliyet = 52_000
    faz2.alt_gorev_ekle(airframe)

    sensor = WorkPackage("2.2", "Sensör modülü tedariki (yurt dışı)",
                          iyimser=6, olasi=10, kotumser=20, butce=80_000,
                          sorumlu="Tedarik Ekibi", olasilik=4, etki=5)
    sensor.tamamlanma_yuzdesi = 40
    sensor.gerceklesen_maliyet = 38_000
    faz2.alt_gorev_ekle(sensor)

    faz3 = WorkPackage("3.0", "Otonom Uçuş Yazılımı")
    proje.alt_gorev_ekle(faz3)
    davranis = WorkPackage("3.1", "Sürü Davranış Algoritması")
    faz3.alt_gorev_ekle(davranis)

    liderlik = WorkPackage("3.1.1", "Sürü liderlik protokolü",
                            iyimser=4, olasi=6, kotumser=14, butce=45_000,
                            atanan_kaynak="Zeynep K.", olasilik=3, etki=4)
    liderlik.tamamlanma_yuzdesi = 20
    liderlik.gerceklesen_maliyet = 12_000
    davranis.alt_gorev_ekle(liderlik)

    mesafe = WorkPackage("3.1.2", "Mesafe koruma algoritması",
                          iyimser=3, olasi=5, kotumser=9, butce=35_000,
                          atanan_kaynak="Zeynep K.")
    davranis.alt_gorev_ekle(mesafe)

    carpisma = WorkPackage("3.2", "Çarpışma Önleme Modülü",
                            iyimser=4, olasi=7, kotumser=12, butce=50_000,
                            sorumlu="Can B.")
    faz3.alt_gorev_ekle(carpisma)

    haberlesme = WorkPackage("4.0", "Haberleşme ve Sürü Koordinasyon Sistemi",
                              iyimser=5, olasi=8, kotumser=15, butce=70_000,
                              sorumlu="İletişim Ekibi")
    proje.alt_gorev_ekle(haberlesme)

    faz5 = WorkPackage("5.0", "Entegrasyon ve Test")
    proje.alt_gorev_ekle(faz5)
    entegrasyon = WorkPackage("5.1", "Sistem entegrasyonu",
                               iyimser=3, olasi=5, kotumser=10, butce=40_000,
                               sorumlu="Entegrasyon Ekibi")
    faz5.alt_gorev_ekle(entegrasyon)

    ucus_testi = WorkPackage("5.2", "Uçuş testi",
                              iyimser=2, olasi=4, kotumser=8, butce=35_000,
                              sorumlu="Test Ekibi", olasilik=5, etki=2)
    faz5.alt_gorev_ekle(ucus_testi)

    sertifikasyon = WorkPackage("6.0", "Sertifikasyon ve Teslimat",
                                 iyimser=4, olasi=6, kotumser=10, butce=25_000,
                                 sorumlu="Kalite Ekibi")
    proje.alt_gorev_ekle(sertifikasyon)

    gereksinim.once_gelir(airframe)
    gereksinim.once_gelir(sensor)
    airframe.once_gelir(liderlik)
    sensor.once_gelir(liderlik)
    liderlik.once_gelir(mesafe)
    mesafe.once_gelir(carpisma)
    carpisma.once_gelir(haberlesme)
    haberlesme.once_gelir(entegrasyon)
    entegrasyon.once_gelir(ucus_testi)
    ucus_testi.once_gelir(sertifikasyon)

    yapraklar = [g for g in proje.tum_alt_agaci_dolas() if g.yaprak_mi()]

    return proje, yapraklar


def hesapla(yapraklar):
    for g in yapraklar:
        g.ileri_gecis()
    proje_bitis = max(g.ef for g in yapraklar)
    for g in yapraklar:
        g.geri_gecis(proje_bitis)

    kaynak_dengele(yapraklar)

    return yapraklar


def get_proje():
    proje, yapraklar = agaci_kur()
    hesapla(yapraklar)
    return proje, yapraklar


def monte_carlo_calistir(iterasyon_sayisi=1000):
    sonuclar = []

    for _ in range(iterasyon_sayisi):
        _proje2, yapraklar2 = agaci_kur()

        for g in yapraklar2:
            g.ileri_gecis(sure_hesapla=lambda gorev: gorev.rastgele_sure())
        proje_bitis = max(g.ef for g in yapraklar2)

        sonuclar.append(proje_bitis)

    sonuclar.sort()

    # statistics.quantiles() en az 2 veri noktası ister; 0 veya 1 iterasyonla
    # gerçek bir yüzdelik dağılımı hesaplanamaz. Uygulamadaki slider
    # (min_value=100) bu durumu hiç tetiklemez, ama fonksiyon doğrudan
    # (ör. küçük bir n ile) çağrılırsa çökmek yerine elimizdeki tek veriyi
    # (varsa) en iyi tahmin olarak döner.
    if len(sonuclar) < 2:
        tek_deger = round(sonuclar[0], 1) if sonuclar else None
        return {
            "sonuclar": sonuclar,
            "p50": tek_deger,
            "p80": tek_deger,
            "p90": tek_deger,
            "iterasyon_sayisi": iterasyon_sayisi,
        }

    yuzdelikler = statistics.quantiles(sonuclar, n=100, method="inclusive")

    return {
        "sonuclar": sonuclar,
        "p50": round(yuzdelikler[49], 1),
        "p80": round(yuzdelikler[79], 1),
        "p90": round(yuzdelikler[89], 1),
        "iterasyon_sayisi": iterasyon_sayisi,
    }


def critical_chain_calistir():
    _proje, yapraklar = agaci_kur()

    for g in yapraklar:
        g.ileri_gecis(sure_hesapla=lambda gorev: gorev.kirpik_sure())
    proje_bitis_kirpik = max(g.ef for g in yapraklar)
    for g in yapraklar:
        g.geri_gecis(proje_bitis_kirpik, sure_hesapla=lambda gorev: gorev.kirpik_sure())

    kaynak_dengele(yapraklar, sure_hesapla=lambda gorev: gorev.kirpik_sure())

    kritik_zincir = kritik_zincir_belirle(yapraklar)
    tampon = tampon_hesapla(kritik_zincir)

    proje_suresi_kirpik = max(g.fiili_bitis for g in yapraklar)

    return {
        "yapraklar": yapraklar,
        "kritik_zincir": kritik_zincir,
        "proje_suresi_kirpik": round(proje_suresi_kirpik, 1),
        "proje_tamponu": tampon,
        "proje_suresi_tamponlu": round(proje_suresi_kirpik + tampon, 1),
    }
