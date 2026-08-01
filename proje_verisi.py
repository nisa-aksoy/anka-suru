"""
ANKA-SÜRÜ Projesi - PMO Kontrol Paneli
PROJE VERİSİ (proje_verisi.py)

Bu dosya, anka_suru_core.py'deki WorkPackage sınıfını kullanarak
GERÇEK ANKA-SÜRÜ WBS ağacını kurar: 6 ana faz, her birinin altında
iş paketleri, aralarında bağımlılıklar, kaynaklar, bütçeler ve risk verileri.

Streamlit arayüzü (bir sonraki adım) SADECE bu dosyadaki get_proje() 
fonksiyonunu çağırıp sonucu ekrana basacak.
"""

from anka_suru_core import WorkPackage, kaynak_dengele, en_riskli_gorevler


def get_proje():
    """
    Tam ANKA-SÜRÜ WBS ağacını kurar, CPM + kaynak dengelemeyi çalıştırır,
    ve (proje_koku, tum_yaprak_gorevler) ikilisini döner.
    """
    proje = WorkPackage("0.0", "ANKA-SÜRÜ Otonom Sürü İHA Sistemi")

    # --- 1.0 Sistem Mühendisliği ve Gereksinim Analizi ---
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
                                olasilik=2, etki=4)  # sadece risk kaydı, takvime girmez
    faz1.alt_gorev_ekle(istifa_riski)

    # --- 2.0 Havacılık Platformu Tasarımı ---
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
                          sorumlu="Tedarik Ekibi", olasilik=4, etki=5)  # R1
    sensor.tamamlanma_yuzdesi = 40
    sensor.gerceklesen_maliyet = 38_000
    faz2.alt_gorev_ekle(sensor)

    # --- 3.0 Otonom Uçuş Yazılımı ---
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

    # --- 4.0 Haberleşme ve Sürü Koordinasyon Sistemi ---
    haberlesme = WorkPackage("4.0", "Haberleşme ve Sürü Koordinasyon Sistemi",
                              iyimser=5, olasi=8, kotumser=15, butce=70_000,
                              sorumlu="İletişim Ekibi")
    proje.alt_gorev_ekle(haberlesme)

    # --- 5.0 Entegrasyon ve Test ---
    faz5 = WorkPackage("5.0", "Entegrasyon ve Test")
    proje.alt_gorev_ekle(faz5)
    entegrasyon = WorkPackage("5.1", "Sistem entegrasyonu",
                               iyimser=3, olasi=5, kotumser=10, butce=40_000,
                               sorumlu="Entegrasyon Ekibi")
    faz5.alt_gorev_ekle(entegrasyon)

    ucus_testi = WorkPackage("5.2", "Uçuş testi",
                              iyimser=2, olasi=4, kotumser=8, butce=35_000,
                              sorumlu="Test Ekibi", olasilik=5, etki=2)  # R3
    faz5.alt_gorev_ekle(ucus_testi)

    # --- 6.0 Sertifikasyon ve Teslimat ---
    sertifikasyon = WorkPackage("6.0", "Sertifikasyon ve Teslimat",
                                 iyimser=4, olasi=6, kotumser=10, butce=25_000,
                                 sorumlu="Kalite Ekibi")
    proje.alt_gorev_ekle(sertifikasyon)

    # --- CPM bağımlılık zinciri (sadece yaprak/iş paketi seviyesinde) ---
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

    # --- Tüm yaprak (iş paketi) görevleri topla ---
    yapraklar = [g for g in proje.tum_alt_agaci_dolas() if g.yaprak_mi()]

    # --- CPM: ileri/geri geçiş ---
    for g in yapraklar:
        g.ileri_gecis()
    proje_bitis = max(g.ef for g in yapraklar)
    for g in yapraklar:
        g.geri_gecis(proje_bitis)

    # --- Kaynak dengeleme ---
    kaynak_dengele(yapraklar)

    return proje, yapraklar


if __name__ == "__main__":
    proje, yapraklar = get_proje()

    print(f"Proje toplam süresi: {round(max(g.ef for g in yapraklar), 1)} gün\n")

    print("--- İş paketleri (CPM) ---")
    for g in yapraklar:
        print(f"{g.wbs_kodu:6} {g.isim:35} ES:{round(g.es,1):>5} EF:{round(g.ef,1):>5} "
              f"Float:{g.float_hesapla():>5} {'[KRİTİK]' if g.kritik_mi() else ''}")

    print("\n--- En riskli 3 görev ---")
    for g in en_riskli_gorevler(proje, adet=3):
        print(f"{g.wbs_kodu} {g.isim} | Skor:{g.risk_skoru()} ({g.risk_seviyesi()})")
