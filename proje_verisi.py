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
import statistics


def agaci_kur():
    """
    SADECE ANKA-SÜRÜ WBS ağacını kurar: fazlar, iş paketleri, CPM
    bağımlılık zinciri (once_gelir). HİÇBİR hesaplama yapmaz —
    dönen görevlerin es/ef/ls/lf alanları hepsi None'dır.

    Bu fonksiyon her çağrıldığında TAMAMEN YENİ WorkPackage nesneleri
    yaratır. What-If senaryoları için bu önemli: orijinal ağaca hiç
    dokunmadan, sıfırdan taze bir ikinci ağaç kurmamızı sağlar.

    Döner: (proje_koku, tum_yaprak_gorevler)
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

    return proje, yapraklar


def hesapla(yapraklar):
    """
    Taze (henüz hesaplanmamış) bir yaprak listesi alır; CPM ileri/geri
    geçişini ve kaynak dengelemeyi bu liste üzerinde çalıştırır.

    Girdideki WorkPackage nesnelerini YERİNDE (in-place) günceller —
    yani es/ef/ls/lf/fiili_baslangic/fiili_bitis alanlarını doldurur.
    Aynı 'yapraklar' referansını geriye döner (zincirleme çağrı kolaylığı için).

    NOT: Bu fonksiyon zaten hesaplanmış (es dolu) bir listeye tekrar
    çağrılırsa hiçbir şey yapmaz — çünkü ileri_gecis()/geri_gecis()
    'if self.es is not None: return' ile kendini korur. Bu yüzden
    What-If senaryosunda MUTLAKA agaci_kur()'dan taze bir liste almalıyız.
    """
    for g in yapraklar:
        g.ileri_gecis()
    proje_bitis = max(g.ef for g in yapraklar)
    for g in yapraklar:
        g.geri_gecis(proje_bitis)

    kaynak_dengele(yapraklar)

    return yapraklar


def get_proje():
    """
    Geriye dönük uyumluluk için: agaci_kur() + hesapla()'yı sırayla
    çağırır. app.py ve mevcut testler bu fonksiyonu değişmeden kullanmaya
    devam edebilir — davranış birebir aynı.
    """
    proje, yapraklar = agaci_kur()
    hesapla(yapraklar)
    return proje, yapraklar


def monte_carlo_calistir(iterasyon_sayisi=1000):
    """
    Monte Carlo şema (schedule) risk simülasyonu.

    Her iterasyonda:
      1. agaci_kur() ile TAZE bir ağaç kurulur (önceki iterasyonu etkilemez)
      2. Her görevin süresi rastgele_sure() ile örneklenir (sabit
         beklenen_sure() DEĞİL — CPM'in ileri/geri geçişine bunu
         sure_hesapla parametresiyle söylüyoruz)
      3. O iterasyondaki proje bitiş günü (en son görevin EF'i) kaydedilir

    Kasıtlı olarak kaynak dengeleme (kaynak_dengele) ÇALIŞTIRILMAZ —
    burada sadece süre belirsizliğinin ağ/CPM yapısı üzerinden proje
    bitişine etkisini ölçüyoruz; kaynak kısıtları ayrı bir konu
    (ileride Critical Chain modülünde ele alınacak).

    Döner: dict {
        "sonuclar": [iterasyon1_bitis, iterasyon2_bitis, ...],  # ham liste, histogram için
        "p50": ..., "p80": ..., "p90": ...,
        "iterasyon_sayisi": ...
    }
    """
    sonuclar = []

    for _ in range(iterasyon_sayisi):
        _proje2, yapraklar2 = agaci_kur()

        # SADECE ileri geçiş çalıştırılıyor: proje bitiş günü (max EF) bunun
        # tek başına yeterli olduğu bir çıktı. Geri geçiş (LS/LF/float/kritik
        # yol) şu an hiçbir yerde kullanılmıyor (Criticality Index kapsam
        # dışı bırakıldı) — bu yüzden burada çalıştırmıyoruz. Not: eğer
        # ileride geri geçiş de eklenirse, süresi görev başına TEK SEFER
        # örneklenip hem ileri hem geri geçişte AYNI değer kullanılmalı
        # (iki ayrı rastgele_sure() çağrısı ileri/geri arasında tutarsızlık
        # yaratır — bu doğrulama sürecinde tespit edildi).
        for g in yapraklar2:
            g.ileri_gecis(sure_hesapla=lambda gorev: gorev.rastgele_sure())
        proje_bitis = max(g.ef for g in yapraklar2)

        sonuclar.append(proje_bitis)

    sonuclar.sort()
    # statistics.quantiles(n=100) veriyi 100 eşit parçaya böler;
    # p50/p80/p90 == 50./80./90. yüzdelik dilim sınırları
    yuzdelikler = statistics.quantiles(sonuclar, n=100, method="inclusive")

    return {
        "sonuclar": sonuclar,
        "p50": round(yuzdelikler[49], 1),   # 50. yüzdelik (index 49, çünkü 0-tabanlı)
        "p80": round(yuzdelikler[79], 1),
        "p90": round(yuzdelikler[89], 1),
        "iterasyon_sayisi": iterasyon_sayisi,
    }


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
