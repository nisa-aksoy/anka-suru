"""
ANKA-SÜRÜ Projesi - PMO Kontrol Paneli
KARAR DESTEK SİSTEMİ (karar_destek.py)

Bu dosya HİÇBİR yeni hesaplama mantığı içermez ve anka_suru_core.py'den
proje_verisi.py'den HİÇBİR ŞEY import ETMEZ. Sadece, o dosyaların zaten
ürettiği sonuçları (WorkPackage nesneleri, monte_carlo_calistir() ve
critical_chain_calistir() dict'leri) okuyup YORUMLAR.

Görevi: mevcut 9 modülün (WBS/CPM/PERT/EVM/Kaynak/Risk/What-If/Monte
Carlo/Critical Chain) çıktılarını birbirine karşı okuyup, tek başına
hiçbirinin göremeyeceği bileşik durumları yakalamak ve bunları kısa,
gerekçeli "karar kartları" haline getirmek.

Kural tabanlı ve tamamen açıklanabilir -- makine öğrenmesi / kara kutu
tahmin YOK. Her kartın "durum"u (Yeşil/Sarı/Kırmızı), "gerekce" alanında
hangi sayıya dayandığını açıkça söyler.

Sınır: Simon'un klasik karar modelindeki "Intelligence" (bir şeyler ters
mi gidiyor, nerede) ve kısmen "Design" (hangi kategoride müdahale
gerekiyor) aşamalarını destekler. "Choice" (hangi eylemi seçeceğin)
kasıtlı olarak insana bırakılır -- sistem bir eylemi kendisi seçmez/
uygulamaz.

Her karar kartı şu şekildedir:
    {
        "kategori": "Takvim" | "Bütçe" | "Risk" | "Bileşik Risk"
                    | "Teslim Tarihi" | "Kaynak",
        "durum": "Yeşil" | "Sarı" | "Kırmızı",
        "baslik": str,        # kısa özet
        "gerekce": str,       # HANGİ sayıya dayandığı (açıklanabilirlik)
        "kaynak_modul": str,  # hangi mevcut modülden okunduğu
    }

app.py'nin "Karar Destek Paneli" bölümü SADECE karar_destek_calistir()'i
çağırır.
"""


def _dusuk_bolluklu_gorevler(yapraklar, esik=2):
    """
    Yardımcı: float'ı esik gün veya altında olan TÜM zamanlanmış
    görevleri döner (zaten kritik olanlar -- float=0 -- dahil).
    takvim_karti_uret() ve bilesik_risk_karti_uret() ortak kullanır,
    "az bolluk" tanımı tek yerde tutulur.

    Süresi 0 olan görevler (ör. sadece risk kaydı olarak eklenmiş,
    takvime girmeyen kalemler) hesaba katılmıyor -- app.py'deki CPM
    tablosundaki 'g.beklenen_sure() > 0' filtresiyle aynı mantık.
    """
    zamanlanan = [g for g in yapraklar if g.beklenen_sure() > 0]
    return [
        g for g in zamanlanan
        if g.float_hesapla() is not None and g.float_hesapla() <= esik
    ]


def takvim_karti_uret(yapraklar, kritige_yakin_esik=2):
    """
    CPM'den okur: kaç görev kritik yolda (float=0), kaç görev henüz
    kritik olmamasına rağmen bolluğu (float) kritige_yakin_esik gün
    veya altında.

    Durum SADECE iki kademeli: Yeşil / Sarı. Kırmızı burada
    ÜRETİLMİYOR -- kaç tane kritiğe yakın görev olduğu tek başına
    aciliyet ölçmez. Asıl aciliyet (Kırmızı), kritiğe yakın görev +
    yüksek risk KESİŞTİĞİNDE bilesik_risk_karti_uret() tarafından
    işaretlenecek.
    """
    dusuk_bolluklular = _dusuk_bolluklu_gorevler(yapraklar, kritige_yakin_esik)
    kritik_sayisi = sum(1 for g in dusuk_bolluklular if g.kritik_mi())
    kritige_yakinlar = [g for g in dusuk_bolluklular if not g.kritik_mi()]

    durum = "Sarı" if kritige_yakinlar else "Yeşil"

    if kritige_yakinlar:
        isimler = ", ".join(
            f"{g.wbs_kodu} ({g.float_hesapla()} gün)" for g in kritige_yakinlar
        )
        gerekce = (
            f"{kritik_sayisi} görev kritik yolda (float=0). Ayrıca "
            f"{len(kritige_yakinlar)} görev {kritige_yakin_esik} gün veya daha az "
            f"bolluğa sahip: {isimler}. Bunlardan risk taşıyanlar 'Bileşik "
            f"Risk' kartında ayrıca vurgulanacak."
        )
    else:
        gerekce = (
            f"{kritik_sayisi} görev kritik yolda (float=0), ancak kritik yol "
            f"dışındaki görevlerde bolluk {kritige_yakin_esik} günün altına "
            f"düşmüyor — yakın zamanda yeni bir kritik görev riski görünmüyor."
        )

    return [{
        "kategori": "Takvim",
        "durum": durum,
        "baslik": "Kritik yol ve bolluk durumu",
        "gerekce": gerekce,
        "kaynak_modul": "CPM",
    }]


def butce_karti_uret(toplam_butce, proje_cpi, proje_spi, proje_eac):
    """
    EVM'den okur (app.py'de zaten hesaplı -- toplam_ev/pv/ac'dan
    türetilen proje_cpi/proje_spi/proje_eac burada TEKRAR
    hesaplanmıyor, olduğu gibi kullanılıyor).

    Eşikler EVM literatüründeki yaygın sapma bantlarına dayanıyor:
    CPI veya SPI < 0.90 -> Sarı (izlenmesi gereken sapma)
    CPI veya SPI < 0.80 -> Kırmızı (ciddi/acil sapma)
    İkisinden HANGİSİ daha kötüyse durum ona göre belirlenir (worst-of).

    CPI ve/veya SPI henüz hesaplanamıyorsa (proje_cpi/proje_spi None
    ise) o metrik değerlendirmeye katılmaz. İkisi de yoksa kart Yeşil
    döner ama gerekçe metninde bunun "performans iyi" değil "henüz
    değerlendirecek veri yok" anlamına geldiği açıkça belirtilir.
    """
    def metrik_durumu(deger):
        if deger is None:
            return None
        if deger < 0.80:
            return "Kırmızı"
        if deger < 0.90:
            return "Sarı"
        return "Yeşil"

    siralama = {"Kırmızı": 2, "Sarı": 1, "Yeşil": 0}
    durumlar = [d for d in (metrik_durumu(proje_cpi), metrik_durumu(proje_spi))
                if d is not None]

    if not durumlar:
        return [{
            "kategori": "Bütçe",
            "durum": "Yeşil",
            "baslik": "Maliyet ve takvim performansı (CPI/SPI)",
            "gerekce": (
                "CPI ve SPI için henüz yeterli veri yok (harcama veya "
                "ilerleme girilmemiş) -- bu iyi bir performansı değil, "
                "henüz değerlendirilecek veri olmadığını gösterir."
            ),
            "kaynak_modul": "EVM",
        }]

    durum = max(durumlar, key=lambda d: siralama[d])

    cpi_metni = f"{proje_cpi:.2f}" if proje_cpi is not None else "—"
    spi_metni = f"{proje_spi:.2f}" if proje_spi is not None else "—"
    eac_farki = proje_eac - toplam_butce

    gerekce = (
        f"CPI={cpi_metni}, SPI={spi_metni} (eşik: <0.90 Sarı, <0.80 Kırmızı). "
        f"EAC {proje_eac:,.0f} TL, bütçeden (BAC) "
        f"{'+' if eac_farki >= 0 else ''}{eac_farki:,.0f} TL sapıyor."
    )

    return [{
        "kategori": "Bütçe",
        "durum": durum,
        "baslik": "Maliyet ve takvim performansı (CPI/SPI)",
        "gerekce": gerekce,
        "kaynak_modul": "EVM",
    }]


def risk_karti_uret(riskliler):
    """
    Risk matrisinden okur: en_riskli_gorevler() çıktısı (app.py'de
    zaten hesaplı).

    Yeni bir eşik İCAT EDİLMİYOR -- core'daki risk_seviyesi()
    sınıflandırması (Yüksek >=15, Orta >=7, Düşük >=1) olduğu gibi
    kullanılıyor.

    Durum: en az bir "Yüksek" varsa Kırmızı, yoksa en az bir "Orta"
    varsa Sarı, aksi halde (hepsi Düşük veya hiç risk yoksa) Yeşil.
    """
    yuksekler = [g for g in riskliler if g.risk_seviyesi() == "Yüksek"]
    ortalar = [g for g in riskliler if g.risk_seviyesi() == "Orta"]

    if yuksekler:
        durum = "Kırmızı"
    elif ortalar:
        durum = "Sarı"
    else:
        durum = "Yeşil"

    if not riskliler:
        gerekce = "Kayıtlı hiçbir risk yok (risk skoru > 0 olan görev bulunmuyor)."
    else:
        parcalar = []
        if yuksekler:
            isimler = ", ".join(f"{g.wbs_kodu} ({g.risk_skoru()})" for g in yuksekler)
            parcalar.append(f"{len(yuksekler)} Yüksek seviye risk: {isimler}.")
        if ortalar:
            isimler = ", ".join(f"{g.wbs_kodu} ({g.risk_skoru()})" for g in ortalar)
            parcalar.append(f"{len(ortalar)} Orta seviye risk: {isimler}.")
        if not parcalar:
            parcalar.append(f"Kayıtlı {len(riskliler)} risk var, hepsi Düşük seviyede.")
        gerekce = " ".join(parcalar)

    return [{
        "kategori": "Risk",
        "durum": durum,
        "baslik": "Risk kayıtları özeti",
        "gerekce": gerekce,
        "kaynak_modul": "Risk Matrisi",
    }]


def bilesik_risk_karti_uret(yapraklar, riskliler, kritige_yakin_esik=2):
    """
    DSS'in asıl "katma değer" fonksiyonu: tek başına ne CPM ne Risk
    Matrisi bu kesişimi göremiyordu.

    Az bolluklu (float <= esik -- zaten kritik olanlar dahil) görevler
    ile risk_seviyesi() "Yüksek" veya "Orta" olan görevlerin WBS kodu
    üzerinden KESİŞİMİNE bakar. Kesişimdeki bir görev hem takvim
    açısından toleranssız HEM DE gerçekleşme ihtimali/etkisi yüksek bir
    risk taşıyor demektir -- iki bilginin ayrı ayrı görünmesi yeterli
    değil, BİRLİKTE görünmesi asıl uyarı.
    """
    az_bolluklular = {g.wbs_kodu: g for g in _dusuk_bolluklu_gorevler(yapraklar, kritige_yakin_esik)}
    onemli_riskliler = {g.wbs_kodu: g for g in riskliler if g.risk_seviyesi() in ("Yüksek", "Orta")}

    ortak_kodlar = set(az_bolluklular) & set(onemli_riskliler)

    if ortak_kodlar:
        detaylar = [
            f"{kod} — float={az_bolluklular[kod].float_hesapla()} gün, "
            f"risk={az_bolluklular[kod].risk_seviyesi()} "
            f"(skor {az_bolluklular[kod].risk_skoru()})"
            for kod in sorted(ortak_kodlar)
        ]
        gerekce = (
            "Hem takvim açısından az toleranslı HEM DE önemli risk taşıyan "
            "görev(ler) var: " + "; ".join(detaylar) + "."
        )
        durum = "Kırmızı"
    else:
        gerekce = (
            "Az bolluklu görevler ile Yüksek/Orta seviye risk taşıyan "
            "görevler kesişmiyor -- bileşik (takvim + risk) bir tehdit "
            "görünmüyor."
        )
        durum = "Yeşil"

    return [{
        "kategori": "Bileşik Risk",
        "durum": durum,
        "baslik": "Takvim + risk kesişimi",
        "gerekce": gerekce,
        "kaynak_modul": "CPM + Risk Matrisi",
    }]


def teslim_tarihi_karti_uret(mc_sonuc, hedef_gun):
    """
    Monte Carlo'dan okur (monte_carlo_calistir() sonucu -- app.py'de
    kullanıcı butona bastığında session_state'e yazılıyor).

    hedef_gun: kullanıcının/sözleşmenin öngördüğü teslim günü. Sistemde
    daha önce hiç var olmayan TEK yeni girdi budur -- app.py'ye küçük
    bir number_input olarak eklenecek.

    mc_sonuc veya hedef_gun verilmemişse (henüz Monte Carlo
    çalıştırılmadıysa ya da kullanıcı hedef gün girmediyse) kart
    ÜRETİLMEZ, boş liste döner.

    Mantık: hedef_gun'un Monte Carlo dağılımında hangi güven bandına
    düştüğüne bakılır:
      hedef_gun >= P90        -> Yeşil  (yüksek güven)
      P50 <= hedef_gun < P90  -> Sarı   (orta güven)
      hedef_gun < P50         -> Kırmızı (düşük güven)
    """
    if mc_sonuc is None or hedef_gun is None:
        return []

    p50, p80, p90 = mc_sonuc["p50"], mc_sonuc["p80"], mc_sonuc["p90"]

    if hedef_gun >= p90:
        durum = "Yeşil"
        yorum = "Hedef, P90 eşiğini karşılıyor -- yüksek güvenle tutturulabilir."
    elif hedef_gun >= p50:
        durum = "Sarı"
        yorum = "Hedef, P50-P90 aralığında -- orta güven, yakından izlenmeli."
    else:
        durum = "Kırmızı"
        yorum = (
            "Hedef, P50'nin altında -- simülasyonların yarısından azı bu "
            "tarihte bitiyor, ciddi risk taşıyor."
        )

    gerekce = (
        f"Hedef teslim günü: {hedef_gun}. Monte Carlo ({mc_sonuc['iterasyon_sayisi']} "
        f"iterasyon) sonucu: P50={p50} gün, P80={p80} gün, P90={p90} gün. {yorum}"
    )

    return [{
        "kategori": "Teslim Tarihi",
        "durum": durum,
        "baslik": "Teslim tarihi güven düzeyi",
        "gerekce": gerekce,
        "kaynak_modul": "Monte Carlo",
    }]


def kaynak_karti_uret(cc_sonuc):
    """
    Critical Chain'den okur (critical_chain_calistir() sonucu --
    app.py'de kullanıcı butona bastığında session_state'e yazılıyor).

    cc_sonuc verilmemişse (henüz Critical Chain çalıştırılmadıysa) kart
    ÜRETİLMEZ, boş liste döner.

    Kritik zincirdeki (kritik_zincir_belirle() çıktısı -- hem bağımlılık
    hem kaynak çakışması dahil edilerek bulunan GERÇEK darboğaz zinciri)
    görevler arasında aynı kaynağa (atanan_kaynak) birden fazla görev
    atanmışsa, o kaynak potansiyel darboğaz sayılır.

    Durum SADECE iki kademeli (Yeşil/Sarı) -- takvim kartındaki gibi,
    "kaç görev" sayısına dayalı bir Kırmızı eşiği burada da icat
    etmiyoruz; bu sadece yapısal bir gözlem, tek başına aciliyet ölçmüyor.
    """
    if cc_sonuc is None:
        return []

    sayac = {}
    for g in cc_sonuc["kritik_zincir"]:
        if g.atanan_kaynak:
            sayac[g.atanan_kaynak] = sayac.get(g.atanan_kaynak, 0) + 1

    darbogazlar = {kaynak: adet for kaynak, adet in sayac.items() if adet >= 2}

    if darbogazlar:
        durum = "Sarı"
        detay = ", ".join(f"{kaynak} ({adet} görev)" for kaynak, adet in darbogazlar.items())
        gerekce = (
            f"Kritik zincirde aynı kaynağa birden fazla görev atanmış: {detay}. "
            f"Bu kaynak(lar), proje tamponunun ({cc_sonuc['proje_tamponu']} gün) "
            f"asıl tüketicisi olabilir."
        )
    else:
        durum = "Yeşil"
        gerekce = (
            "Kritik zincirde tek bir kaynağa yığılmış görev yok -- kaynak "
            "tarafında yapısal bir darboğaz görünmüyor."
        )

    return [{
        "kategori": "Kaynak",
        "durum": durum,
        "baslik": "Kritik zincirde kaynak yoğunlaşması",
        "gerekce": gerekce,
        "kaynak_modul": "Critical Chain",
    }]


def genel_durum_belirle(kartlar):
    """
    Tüm karar kartları arasından EN KÖTÜ durumu döner (worst-of).
    Ağırlıklı ortalama YAPILMIYOR -- bilinçli tercih: tek bir kırmızı,
    başka yeşillerin arasında ortalamayla gizlenmemeli.
    """
    siralama = {"Kırmızı": 2, "Sarı": 1, "Yeşil": 0}
    if not kartlar:
        return "Yeşil"
    return max((k["durum"] for k in kartlar), key=lambda d: siralama[d])


def karar_destek_calistir(yapraklar, riskliler, toplam_butce, proje_cpi,
                           proje_spi, proje_eac, mc_sonuc=None, cc_sonuc=None,
                           hedef_gun=None, kritige_yakin_esik=2):
    """
    Üst düzey orkestratör -- app.py'nin "Karar Destek Paneli" bölümü
    SADECE bu fonksiyonu çağıracak.

    Zorunlu parametreler: yapraklar, riskliler, toplam_butce, proje_cpi,
    proje_spi, proje_eac -- hepsi app.py'de zaten hesaplı.

    Opsiyonel parametreler (kullanıcı ilgili analizi henüz
    çalıştırmadıysa/girmediyse None geçilir): mc_sonuc, cc_sonuc,
    hedef_gun. Bu durumda ilgili kartlar sessizce atlanır.

    Döner: {"genel_durum": "Yeşil"/"Sarı"/"Kırmızı", "kartlar": [...]}
    """
    kartlar = []
    kartlar += takvim_karti_uret(yapraklar, kritige_yakin_esik)
    kartlar += butce_karti_uret(toplam_butce, proje_cpi, proje_spi, proje_eac)
    kartlar += risk_karti_uret(riskliler)
    kartlar += bilesik_risk_karti_uret(yapraklar, riskliler, kritige_yakin_esik)
    kartlar += teslim_tarihi_karti_uret(mc_sonuc, hedef_gun)
    kartlar += kaynak_karti_uret(cc_sonuc)

    return {
        "genel_durum": genel_durum_belirle(kartlar),
        "kartlar": kartlar,
    }


if __name__ == "__main__":
    # Hızlı bir doğrulama: gerçek ANKA-SÜRÜ verisiyle birlikte tutarlı
    # çalışıyor mu? (import'lar bilerek burada, __main__ bloğunun
    # içinde -- dosyanın modül seviyesinde hiçbir bağımlılığı yok.)
    from proje_verisi import get_proje, monte_carlo_calistir, critical_chain_calistir
    from anka_suru_core import en_riskli_gorevler

    proje, yapraklar = get_proje()
    riskliler = en_riskli_gorevler(proje, adet=10)

    toplam_butce = sum(g.butce for g in yapraklar)
    toplam_ev = sum(g.kazanilan_deger() for g in yapraklar)
    toplam_pv = sum(g.planlanan_deger(15) for g in yapraklar)
    toplam_ac = sum(g.gerceklesen_maliyet for g in yapraklar)
    proje_cpi = toplam_ev / toplam_ac if toplam_ac else None
    proje_spi = toplam_ev / toplam_pv if toplam_pv else None
    proje_eac = toplam_butce / proje_cpi if proje_cpi else toplam_butce

    mc_sonuc = monte_carlo_calistir(500)
    cc_sonuc = critical_chain_calistir()

    sonuc = karar_destek_calistir(
        yapraklar, riskliler, toplam_butce, proje_cpi, proje_spi, proje_eac,
        mc_sonuc=mc_sonuc, cc_sonuc=cc_sonuc, hedef_gun=90,
    )

    print(f"Genel durum: {sonuc['genel_durum']}\n")
    for kart in sonuc["kartlar"]:
        print(f"[{kart['durum']}] {kart['kategori']} — {kart['baslik']}")
        print(f"   {kart['gerekce']}\n")
