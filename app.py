"""
ANKA-SÜRÜ Projesi - PMO Kontrol Paneli
STREAMLIT DASHBOARD (app.py)

Bu dosya HİÇBİR hesaplama yapmaz — sadece proje_verisi.py'den gelen
hazır sonuçları ekrana (web sayfasına) döker. Tüm "akıl" önceki
dosyalarda (anka_suru_core.py, proje_verisi.py) zaten var.

Çalıştırmak için (terminalde, bu dosyanın olduğu klasörde):
    pip install streamlit pandas
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from proje_verisi import get_proje
from anka_suru_core import en_riskli_gorevler

st.set_page_config(page_title="ANKA-SÜRÜ PMO Paneli", layout="wide")
st.title("ANKA-SÜRÜ — Otonom Sürü İHA Projesi PMO Kontrol Paneli")

proje, yapraklar = get_proje()
proje_suresi = max(g.ef for g in yapraklar)

# --- Kenar çubuğu: "bugün" hangi gün, EVM hesapları buna göre değişir ---
bugun = st.sidebar.slider("Bugün (proje günü)", 0, int(proje_suresi), 15)

# --- Üst özet metrikler (proje geneli) ---
toplam_butce = sum(g.butce for g in yapraklar)
toplam_ev = sum(g.kazanilan_deger() for g in yapraklar)
toplam_pv = sum(g.planlanan_deger(bugun) for g in yapraklar)
toplam_ac = sum(g.gerceklesen_maliyet for g in yapraklar)
proje_cpi = toplam_ev / toplam_ac if toplam_ac else None
proje_spi = toplam_ev / toplam_pv if toplam_pv else None
proje_eac = toplam_butce / proje_cpi if proje_cpi else toplam_butce

c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam bütçe (BAC)", f"{toplam_butce:,.0f} TL")
c2.metric("CPI — maliyet performansı", f"{proje_cpi:.2f}" if proje_cpi else "—")
c3.metric("SPI — takvim performansı", f"{proje_spi:.2f}" if proje_spi else "—")
c4.metric("EAC — tahmini bitiş maliyeti", f"{proje_eac:,.0f} TL")

st.divider()

# --- WBS ağacı ---
st.subheader("WBS ağacı")
def agac_yazdir(gorev, seviye=0):
    girinti = "&nbsp;&nbsp;&nbsp;&nbsp;" * seviye
    etiket = "[İş paketi]" if gorev.yaprak_mi() else "[Faz]"
    st.markdown(f"{girinti}**{gorev.wbs_kodu}** — {gorev.isim} &nbsp;`{etiket}`", unsafe_allow_html=True)
    for cocuk in gorev.alt_gorevler:
        agac_yazdir(cocuk, seviye + 1)

with st.expander("WBS ağacını göster/gizle", expanded=False):
    agac_yazdir(proje)

st.divider()

# --- CPM tablosu ---
st.subheader("İş paketleri — kritik yol (CPM)")
df_cpm = pd.DataFrame([{
    "WBS": g.wbs_kodu,
    "İş paketi": g.isim,
    "Sorumlu / kaynak": g.atanan_kaynak or g.sorumlu or "-",
    "ES": round(g.es, 1), "EF": round(g.ef, 1),
    "Float": g.float_hesapla(),
    "Kritik mi?": "Evet" if g.kritik_mi() else ""
} for g in yapraklar if g.beklenen_sure() > 0])
st.dataframe(df_cpm, use_container_width=True, hide_index=True)

# Gantt şeması: her görev bir yatay çubuk, kritik olanlar farklı renkte.
# Plotly'nin timeline fonksiyonu tarih bekler, bizim elimizde "gün sayısı"
# olduğu için bir referans tarihe (2026-01-01) ekleyip gerçek tarihe çeviriyoruz.
df_gantt = pd.DataFrame([{
    "İş paketi": f"{g.wbs_kodu} — {g.isim}",
    "Başlangıç": pd.Timestamp("2026-01-01") + pd.to_timedelta(g.fiili_baslangic, unit="D"),
    "Bitiş": pd.Timestamp("2026-01-01") + pd.to_timedelta(g.fiili_bitis, unit="D"),
    "Durum": "Kritik" if g.kritik_mi() else "Bolluklu"
} for g in yapraklar if g.beklenen_sure() > 0])

fig_gantt = px.timeline(
    df_gantt, x_start="Başlangıç", x_end="Bitiş", y="İş paketi", color="Durum",
    color_discrete_map={"Kritik": "#D85A30", "Bolluklu": "#888780"}
)
fig_gantt.update_yaxes(autorange="reversed")  # ilk görev en üstte görünsün
st.plotly_chart(fig_gantt, use_container_width=True)

st.divider()

# --- Kaynak dengeleme tablosu ---
st.subheader("Kaynak dengeleme sonrası gerçek takvim")
df_kaynak = pd.DataFrame([{
    "WBS": g.wbs_kodu, "İş paketi": g.isim, "Kaynak": g.atanan_kaynak,
    "Fiili başlangıç": round(g.fiili_baslangic, 1),
    "Fiili bitiş": round(g.fiili_bitis, 1)
} for g in yapraklar if g.atanan_kaynak])
if len(df_kaynak) > 0:
    st.dataframe(df_kaynak, use_container_width=True, hide_index=True)
else:
    st.caption("Henüz belirli bir kaynağa atanmış görev yok.")

st.divider()

# --- EVM tablosu ---
st.subheader(f"Kazanılmış değer (EVM) — gün {bugun} itibarıyla")
df_evm = pd.DataFrame([{
    "WBS": g.wbs_kodu, "İş paketi": g.isim,
    "% Tamamlanma": g.tamamlanma_yuzdesi,
    **g.performans_endeksleri(bugun)
} for g in yapraklar if g.butce > 0])
st.dataframe(df_evm, use_container_width=True, hide_index=True)

st.divider()

# --- EAC / Bütçe trend takibi ---
st.subheader("EAC / bütçe trend takibi — kontrol noktaları")
st.caption(
    "Her kontrol noktasında (ör. her hafta), o güne kadarki genel ilerlemeyi "
    "ve harcamayı gir. Sistem CPI ve EAC'yi otomatik hesaplayıp aşağıdaki "
    "trend grafiğine ekleyecek."
)

# session_state: sayfa her yeniden çalıştığında (ör. slider hareket ettirince)
# eklenen kontrol noktalarının SİLİNMEMESİ için kullanılıyor.
if "kontrol_noktalari" not in st.session_state:
    st.session_state.kontrol_noktalari = []

with st.form("kontrol_noktasi_formu", clear_on_submit=True):
    col_a, col_b, col_c = st.columns(3)
    girilen_gun = col_a.number_input("Gün", min_value=0, max_value=int(proje_suresi), step=1)
    girilen_yuzde = col_b.number_input("Proje geneli % tamamlanma", min_value=0, max_value=100, step=5)
    girilen_ac = col_c.number_input("O güne kadar harcanan toplam maliyet (TL)", min_value=0, step=1000)
    eklendi = st.form_submit_button("Kontrol noktası ekle")

if eklendi:
    ev = toplam_butce * (girilen_yuzde / 100)
    cpi = ev / girilen_ac if girilen_ac else None
    eac = toplam_butce / cpi if cpi else toplam_butce
    st.session_state.kontrol_noktalari.append({
        "Gün": girilen_gun,
        "% Tamamlanma": girilen_yuzde,
        "AC": girilen_ac,
        "EV": round(ev, 0),
        "CPI": round(cpi, 2) if cpi else None,
        "EAC": round(eac, 0),
    })

if st.session_state.kontrol_noktalari:
    df_trend = pd.DataFrame(st.session_state.kontrol_noktalari).sort_values("Gün")
    st.dataframe(df_trend, use_container_width=True, hide_index=True)

    fig_trend = px.line(df_trend, x="Gün", y="EAC", markers=True)
    fig_trend.add_hline(
        y=toplam_butce, line_dash="dash", line_color="#888780",
        annotation_text="Orijinal bütçe (BAC)", annotation_position="top left"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    if st.button("Tüm kontrol noktalarını sıfırla"):
        st.session_state.kontrol_noktalari = []
        st.rerun()
else:
    st.caption("Henüz kontrol noktası eklenmedi.")

st.divider()

# --- Risk matrisi tablosu ---
st.subheader("Risk kayıtları — en riskliden en düşüğe")
riskliler = en_riskli_gorevler(proje, adet=10)
df_risk = pd.DataFrame([{
    "WBS": g.wbs_kodu, "Risk": g.isim,
    "Olasılık": g.olasilik, "Etki": g.etki,
    "Skor": g.risk_skoru(), "Seviye": g.risk_seviyesi()
} for g in riskliler])
st.dataframe(df_risk, use_container_width=True, hide_index=True)

# Olasılık-Etki scatter plot: X=Etki, Y=Olasılık, nokta büyüklüğü=Skor, renk=Seviye
fig_risk = px.scatter(
    df_risk, x="Etki", y="Olasılık", size="Skor", color="Seviye",
    color_discrete_map={"Düşük": "#4a7c59", "Orta": "#a66a1e", "Yüksek": "#993c1d"},
    hover_name="Risk", text="WBS",
    range_x=[0, 6], range_y=[0, 6]
)
fig_risk.update_traces(textposition="top center")
st.plotly_chart(fig_risk, use_container_width=True)
