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


def kaynak_dengele(gorevler: list):
    """Aynı kaynağa atanmış çakışan görevleri, float önceliğiyle sıralayıp yerleştirir."""
    kaynak_gruplari = {}
    for g in gorevler:
        if g.atanan_kaynak:
            kaynak_gruplari.setdefault(g.atanan_kaynak, []).append(g)

    for kaynak, liste in kaynak_gruplari.items():
        liste.sort(key=lambda g: g.float_hesapla())
        musait = 0
        for g in liste:
            baslangic = max(g.es, musait)
            g.fiili_baslangic = baslangic
            g.fiili_bitis = baslangic + g.beklenen_sure()
            musait = g.fiili_bitis

    for g in gorevler:
        if g.fiili_baslangic is None:
            g.fiili_baslangic = g.es
            g.fiili_bitis = g.ef


def en_riskli_gorevler(proje_koku: WorkPackage, adet: int = 5) -> list:
    tumu = list(proje_koku.tum_alt_agaci_dolas())
    riskliler = [g for g in tumu if g.risk_skoru() > 0]
    riskliler.sort(key=lambda g: g.risk_skoru(), reverse=True)
    return riskliler[:adet]


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
