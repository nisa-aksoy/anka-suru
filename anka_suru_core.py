"""
ANKA-SÜRÜ Projesi - PMO Kontrol Paneli
CEKIRDEK MODUL (anka_suru_core.py)

Bu dosya, önceki 6 adımda ayrı ayrı yazdığımız tüm mantığı
TEK bir WorkPackage sınıfında birleştirir:
  1. WBS      -> alt_gorevler / ust_gorev, yaprak_mi()
  2. CPM      -> onceki/sonraki_gorevler, ileri_gecis(), geri_gecis(), float
  3. PERT     -> beklenen_sure(), standart_sapma()
  4. EVM      -> planlanan_deger(), kazanilan_deger(), performans_endeksleri()
  5. Kaynak   -> atanan_kaynak, kaynak_dengele()
  6. Risk     -> olasilik, etki, risk_skoru(), risk_seviyesi()

Streamlit arayüzü (bir sonraki adım) bu dosyayı import edip
sadece EKRANA BASMAKLA ilgilenecek — hesaplama mantığının tamamı burada.
"""

import random

class WorkPackage:
    def __init__(self, wbs_kodu: str, isim: str,
                 iyimser: float = 0, olasi: float = 0, kotumser: float = 0,
                 butce: float = 0, sorumlu: str = None,
                 atanan_kaynak: str = None,
                 olasilik: int = 0, etki: int = 0):
        self.wbs_kodu = wbs_kodu
        self.isim = isim
        self.sorumlu = sorumlu
        self.atanan_kaynak = atanan_kaynak

        # PERT
        self.iyimser = iyimser
        self.olasi = olasi
        self.kotumser = kotumser

        # EVM
        self.butce = butce
        self.tamamlanma_yuzdesi = 0
        self.gerceklesen_maliyet = 0

        # Risk
        self.olasilik = olasilik
        self.etki = etki

        # WBS
        self.alt_gorevler = []
        self.ust_gorev = None

        # CPM
        self.onceki_gorevler = []
        self.sonraki_gorevler = []
        self.es = None
        self.ef = None
        self.ls = None
        self.lf = None

        # Kaynak dengeleme sonrası gerçek takvim
        self.fiili_baslangic = None
        self.fiili_bitis = None

    # ---------------- WBS ----------------
    def alt_gorev_ekle(self, cocuk: "WorkPackage"):
        cocuk.ust_gorev = self
        self.alt_gorevler.append(cocuk)

    def yaprak_mi(self) -> bool:
        return len(self.alt_gorevler) == 0

    def tum_alt_agaci_dolas(self):
        yield self
        for cocuk in self.alt_gorevler:
            yield from cocuk.tum_alt_agaci_dolas()

    def toplam_butce(self) -> float:
        """
        WBS'in '%100 Kuralı'nın gerçek uygulaması:
        Bir fazın bütçesi kendi başına girilmez, altındaki TÜM iş
        paketlerinin bütçe toplamından türetilir (roll-up).
        Yaprak (iş paketi) ise zaten kendi butce'sini döner.
        """
        if self.yaprak_mi():
            return self.butce
        return sum(cocuk.toplam_butce() for cocuk in self.alt_gorevler)

    # ---------------- PERT ----------------
    def beklenen_sure(self) -> float:
        return (self.iyimser + 4 * self.olasi + self.kotumser) / 6

    def standart_sapma(self) -> float:
        return (self.kotumser - self.iyimser) / 6

    def rastgele_sure(self) -> float:
        """
        Monte Carlo simülasyonu için: beklenen_sure()'ün aksine SABİT bir
        ortalama değil, üçgen dağılımdan TEK BİR RASTGELE ÖRNEK döner.

        Aynı (iyimser, olasi, kotumser) üçlüsünü kullanır — yeni veri
        girişi gerekmez. iyimser=olasi=kotumser olan görevlerde (ör. sadece
        takvime giren süresi-0 riskler) random.triangular otomatik olarak
        her seferinde o sabit değeri döner, hata vermez.
        """
        return random.triangular(self.iyimser, self.olasi, self.kotumser)

    def kirpik_sure(self) -> float:
        """
        Critical Chain için: beklenen_sure()'ün aksine kotumser'in içine
        gömülü fazladan güvenlik payını TAŞIMAZ. PERT üçlüsündeki 'olasi'
        (en olası/mod değeri), tanım gereği zaten güvenlik payı eklenmemiş
        tahmindir — bu yüzden yeni bir veri modeli icat etmek yerine
        doğrudan onu kullanıyoruz.

        beklenen_sure() ile farkı: beklenen_sure() üçünün ağırlıklı
        ortalaması (kotumser'in etkisini taşır), kirpik_sure() ise
        sadece 'en olası' senaryoyu yansıtır — CPM'i bu süreyle
        çalıştırdığımızda ortaya çıkan fazladan gün, kritik zincirin
        sonundaki proje tamponuna aktarılacak.
        """
        return self.olasi

    # ---------------- CPM ----------------
    def once_gelir(self, sonraki: "WorkPackage"):
        sonraki.onceki_gorevler.append(self)
        self.sonraki_gorevler.append(sonraki)

    def ileri_gecis(self, sure_hesapla=None):
        """
        sure_hesapla: görev süresini nasıl hesaplayacağını belirten
        opsiyonel bir fonksiyon (bir WorkPackage alır, bir sayı döner).
        Verilmezse (normal/deterministik kullanım — get_proje, What-If)
        varsayılan olarak beklenen_sure() (sabit PERT ortalaması) kullanılır.
        Monte Carlo simülasyonunda bunun yerine rastgele_sure() verilir.
        """
        if sure_hesapla is None:
            sure_hesapla = lambda g: g.beklenen_sure()

        if self.es is not None:
            return
        if not self.onceki_gorevler:
            self.es = 0
        else:
            for onceki in self.onceki_gorevler:
                onceki.ileri_gecis(sure_hesapla)
            self.es = max(o.ef for o in self.onceki_gorevler)
        self.ef = self.es + sure_hesapla(self)

    def geri_gecis(self, proje_bitis: float = None, sure_hesapla=None):
        if sure_hesapla is None:
            sure_hesapla = lambda g: g.beklenen_sure()

        if self.lf is not None:
            return
        if not self.sonraki_gorevler:
            self.lf = proje_bitis
        else:
            for sonraki in self.sonraki_gorevler:
                sonraki.geri_gecis(proje_bitis, sure_hesapla)
            self.lf = min(s.ls for s in self.sonraki_gorevler)
        self.ls = self.lf - sure_hesapla(self)

    def float_hesapla(self) -> float:
        if self.es is None or self.ls is None:
            return None
        return round(self.ls - self.es, 2)

    def kritik_mi(self) -> bool:
        f = self.float_hesapla()
        return f is not None and f == 0

    # ---------------- EVM ----------------
    def planlanan_deger(self, bugun: float) -> float:
        sure = self.beklenen_sure()
        if sure == 0:
            return self.butce if bugun >= self.ef else 0
        if bugun <= self.es:
            gecen = 0
        elif bugun >= self.ef:
            gecen = sure
        else:
            gecen = bugun - self.es
        return self.butce * (gecen / sure)

    def kazanilan_deger(self) -> float:
        return self.butce * (self.tamamlanma_yuzdesi / 100)

    def performans_endeksleri(self, bugun: float) -> dict:
        ev = self.kazanilan_deger()
        pv = self.planlanan_deger(bugun)
        ac = self.gerceklesen_maliyet
        cpi = ev / ac if ac else None
        spi = ev / pv if pv else None
        return {"EV": round(ev, 2), "PV": round(pv, 2), "AC": round(ac, 2),
                "CPI": round(cpi, 2) if cpi else None,
                "SPI": round(spi, 2) if spi else None}

    def tahmini_bitis_maliyeti(self, bugun: float) -> float:
        endeksler = self.performans_endeksleri(bugun)
        cpi = endeksler["CPI"]
        if not cpi:
            return self.butce
        return round(self.butce / cpi, 2)

    # ---------------- Risk ----------------
    def risk_skoru(self) -> int:
        return self.olasilik * self.etki

    def risk_seviyesi(self) -> str:
        skor = self.risk_skoru()
        if skor >= 15:
            return "Yüksek"
        elif skor >= 7:
            return "Orta"
        elif skor >= 1:
            return "Düşük"
        return "Tanımsız"


def kaynak_dengele(gorevler: list, sure_hesapla=None):
    """
    Kaynak-kısıtlı ileri geçiş (resource-constrained forward pass /
    'serial schedule generation scheme'). Görevleri, HEM bağımlılık
    HEM kaynak müsaitliğini birlikte gözeterek zamanlar.

    Önceki (basit) sürüm sadece aynı kaynağa atanmış görevleri kendi
    grubu içinde sıralıyordu — bir görevin kaynak çakışmasıyla ötelenmesi,
    ondan sonra gelen (farklı kaynaklı) görevlere YANSIMIYORDU. Bu sürüm
    bunu düzeltiyor: her görev, öncüllerinin GERÇEK (fiili) bitişini baz
    alıyor, sadece orijinal CPM es'ini değil.

    sure_hesapla: ileri_gecis()/geri_gecis() ile aynı desen — verilmezse
    beklenen_sure() kullanılır.
    """
    if sure_hesapla is None:
        sure_hesapla = lambda g: g.beklenen_sure()

    for g in gorevler:
        g.fiili_baslangic = None
        g.fiili_bitis = None

    kaynak_musait = {}
    kalanlar = list(gorevler)

    while kalanlar:
        # Hazır görevler: tüm bağımlılık öncülleri zaten zamanlanmış olanlar
        hazirlar = [g for g in kalanlar
                    if all(o.fiili_bitis is not None for o in g.onceki_gorevler)]
        if not hazirlar:
            break  # döngüsel bağımlılık gibi beklenmedik bir durum; güvenlik için çık

        # Float'ı en düşük (en kritik) olan önce zamanlanır
        hazirlar.sort(key=lambda g: g.float_hesapla() if g.float_hesapla() is not None else 0)
        secilen = hazirlar[0]

        network_hazir = max((o.fiili_bitis for o in secilen.onceki_gorevler), default=0)
        kaynak_hazir = kaynak_musait.get(secilen.atanan_kaynak, 0) if secilen.atanan_kaynak else 0
        secilen.fiili_baslangic = max(network_hazir, kaynak_hazir)
        secilen.fiili_bitis = secilen.fiili_baslangic + sure_hesapla(secilen)

        if secilen.atanan_kaynak:
            kaynak_musait[secilen.atanan_kaynak] = secilen.fiili_bitis

        kalanlar.remove(secilen)


def kritik_zincir_belirle(yapraklar: list) -> list:
    """
    Kaynak dengelemesi sonrası ortaya çıkan GERÇEK en uzun zinciri
    (Critical Chain) belirler. CPM'in kritik yolunun (float=0 görevler)
    kopyası DEĞİL — hem bağımlılık hem kaynak çakışmasını hesaba katarak
    geriye doğru izler.

    Önkoşul: yapraklar listesi hem CPM (ileri_gecis/geri_gecis) hem
    kaynak_dengele() ile işlenmiş olmalı (fiili_baslangic/fiili_bitis
    dolu olmalı).

    Mantık: projenin en son biten görevinden başlanır. Her adımda,
    'bu görevi gerçekten hangi görev geciktirdi?' sorusu soruluyor —
    aday iki türde: (a) bağımlılık önceli, (b) aynı kaynağa atanmış,
    hemen önce biten görev. Hangisinin bitiş günü mevcut görevin
    başlangıcıyla tam örtüşüyorsa, gerçek sebep odur.

    Döner: zincirdeki görevler, projenin başından sonuna doğru sıralı.
    """
    if not yapraklar:
        return []

    mevcut = max(yapraklar, key=lambda g: g.fiili_bitis)
    zincir = [mevcut]

    while True:
        adaylar = list(mevcut.onceki_gorevler)
        if mevcut.atanan_kaynak:
            adaylar += [g for g in yapraklar
                        if g is not mevcut and g.atanan_kaynak == mevcut.atanan_kaynak]

        gercek_onceki = None
        for aday in adaylar:
            if aday.fiili_bitis is not None and abs(aday.fiili_bitis - mevcut.fiili_baslangic) < 0.01:
                if gercek_onceki is None or aday.fiili_bitis > gercek_onceki.fiili_bitis:
                    gercek_onceki = aday

        if gercek_onceki is None:
            break
        zincir.append(gercek_onceki)
        mevcut = gercek_onceki

    zincir.reverse()
    return zincir


def tampon_hesapla(kritik_zincir: list) -> float:
    """
    Kritik zincirdeki her görevden kırpılan güvenlik payını
    (beklenen_sure() - kirpik_sure()) toplar, klasik Critical Chain
    kuralına göre bunun YARISINI proje tamponu olarak döner.

    Neden yarısı: kırpılan payın TAMAMINI tampon olarak geri koymak,
    güvenlik payını hiç kırpmamış gibi olurdu — kırpmanın amacı
    (Student Syndrome/Parkinson Kanunu'nun yol açtığı israfı önlemek)
    ortadan kalkardı. Diğer yarısı kasıtlı olarak feda edilir.
    """
    toplam_kirpilan = sum(g.beklenen_sure() - g.kirpik_sure() for g in kritik_zincir)
    return round(toplam_kirpilan / 2, 1)


def en_riskli_gorevler(proje_koku: WorkPackage, adet: int = 5) -> list:
    tumu = list(proje_koku.tum_alt_agaci_dolas())
    riskliler = [g for g in tumu if g.risk_skoru() > 0]
    riskliler.sort(key=lambda g: g.risk_skoru(), reverse=True)
    return riskliler[:adet]


def s_egrisi_pv(yapraklar: list, proje_suresi: float = None) -> list:
    """
    S-Curve'ün PV (planlanan değer) eğrisi: proje başından (gün 0)
    proje sonuna kadar HER GÜN için, o güne kadar planlanan kümülatif
    bütçeyi hesaplar.

    Yeni bir hesaplama mantığı DEĞİL — zaten var olan
    planlanan_deger(bugun) metodunu (tek bir gün için tanımlı) sadece
    bir döngüyle her gün için çağırıp topluyor. EV/AC'nin aksine PV
    tamamen plana dayalı olduğu için (gerçek ilerleme verisi
    gerektirmediği için) her gün için hesaplanabiliyor.

    Döner: [(gun, kumulatif_pv), (gun, kumulatif_pv), ...] — gün 0'dan
    proje_suresi'ne kadar, 1'er gün aralıklarla.
    """
    if proje_suresi is None:
        proje_suresi = max(g.ef for g in yapraklar)
    proje_suresi = int(round(proje_suresi))

    egri = []
    for gun in range(proje_suresi + 1):
        kumulatif_pv = sum(g.planlanan_deger(gun) for g in yapraklar)
        egri.append((gun, kumulatif_pv))
    return egri


if __name__ == "__main__":
    # Hızlı bir doğrulama: 6 modül birlikte tutarlı çalışıyor mu?
    a = WorkPackage("A", "Gereksinim analizi", iyimser=3, olasi=5, kotumser=8, butce=20000)
    b = WorkPackage("B", "Alt sistem tasarımı", iyimser=2, olasi=3, kotumser=5,
                     butce=15000, atanan_kaynak="Zeynep K.", olasilik=2, etki=3)
    c = WorkPackage("C", "Yazılım kodlama", iyimser=4, olasi=6, kotumser=14,
                     butce=40000, atanan_kaynak="Zeynep K.", olasilik=4, etki=5)
    a.once_gelir(b)
    a.once_gelir(c)

    for g in [a, b, c]:
        g.ileri_gecis()
    proje_bitis = max(g.ef for g in [a, b, c])
    for g in [a, b, c]:
        g.geri_gecis(proje_bitis)

    kaynak_dengele([a, b, c])

    for g in [a, b, c]:
        print(f"{g.wbs_kodu} | TE:{round(g.beklenen_sure(),1)} | "
              f"Fiili:{g.fiili_baslangic}-{g.fiili_bitis} | "
              f"Risk:{g.risk_skoru()} ({g.risk_seviyesi()})")
