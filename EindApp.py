# app.py
# Eenvoudige Streamlit-app: schooladvies, buurtwelvaart en leerling-leraarratio
# Starten met:  streamlit run app.py

import matplotlib
matplotlib.use("Agg")  # veilige plot-backend voor Streamlit
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

# ---------------------------------------------------------
# Pagina-instellingen
# ---------------------------------------------------------
st.set_page_config(page_title="Schooladvies en buurtwelvaart", layout="wide")

st.title("Schooladvies en buurtwelvaart")
st.write(
    "Deze app laat zien hoe het schooladvies in groep 8 (basisschool) "
    "samenhangt met buurtwelvaart, de leerling-leraarratio, provincie en "
    "schooltype. Gebruik de keuzes om de data te verkennen."
)

# ---------------------------------------------------------
# 1. Data laden
# ---------------------------------------------------------
try:
    df = pd.read_csv("merged.csv")
except FileNotFoundError:
    st.error("merged.csv is niet gevonden. Zet het bestand in dezelfde map als app.py.")
    st.stop()

# De tien schooladvies-kolommen en de drie adviesgroepen
advice_cols = [
    "PRO", "VMBO_B", "VMBO_B_K", "VMBO_K",
    "VMBO_K_GT", "VMBO_GT", "VMBO_GT_HAVO",
    "HAVO", "HAVO_VWO", "VWO"
]
lower = ["PRO", "VMBO_B", "VMBO_B_K", "VMBO_K"]
middle = ["VMBO_K_GT", "VMBO_GT", "VMBO_GT_HAVO", "HAVO"]
higher = ["HAVO_VWO", "VWO"]
advice_groups = ["Lager advies", "Middelbaar advies", "Hoger advies"]

# Kolommen voor buurtwelvaart
wealth_6 = "buurt_avg_GemiddeldePercentielgroep_6"    # financiële welvaart
wealth_14 = "buurt_avg_GemiddeldePercentielgroep_14"  # huishoudelijk vermogen

# Controleer of alle benodigde kolommen in merged.csv staan
needed_cols = advice_cols + [
    "JAAR", "SOORT_PO", "PROVINCIE", "DENOMINATIE_VESTIGING",
    "LEERLING_LERAAR_RATIO", "center_lon", "center_lat",
    wealth_6, wealth_14,
]
missing_cols = [col for col in needed_cols if col not in df.columns]
if len(missing_cols) > 0:
    st.error("Deze kolommen ontbreken in merged.csv: " + ", ".join(missing_cols))
    st.stop()

# Zorg dat de getalkolommen echt getallen zijn
number_cols = advice_cols + [
    "JAAR", "LEERLING_LERAAR_RATIO", "center_lon", "center_lat", wealth_6, wealth_14
]
for col in number_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Rijen zonder jaar zijn niet bruikbaar
df = df.dropna(subset=["JAAR"]).reset_index(drop=True)

# ---------------------------------------------------------
# 2. Berekeningen (dezelfde logica als in het notebook)
# ---------------------------------------------------------
# Totaal aantal leerlingen per rij (deel niet door 0)
total_students = df[advice_cols].sum(axis=1)
total_students = total_students.where(total_students > 0)

# Percentage leerlingen per schooladvies (10 kolommen)
percentages10 = df[advice_cols].div(total_students, axis=0) * 100

# Percentage leerlingen per adviesgroep (3 kolommen)
percentages = pd.DataFrame(index=df.index)
percentages["Lager advies"] = df[lower].sum(axis=1).div(total_students) * 100
percentages["Middelbaar advies"] = df[middle].sum(axis=1).div(total_students) * 100
percentages["Hoger advies"] = df[higher].sum(axis=1).div(total_students) * 100

# Afwijking t.o.v. het gemiddelde van scholen in een vergelijkbare welvaartsgroep
bracket = df[wealth_14]
benchmark = percentages.groupby(bracket)[advice_groups].mean()

deviation = percentages[advice_groups].copy()
for group in advice_groups:
    deviation[group] = percentages[group] - bracket.map(benchmark[group])

# ---------------------------------------------------------
# 3. Zijbalk: jaarfilter (gebruikt door alle grafieken behalve de kaart)
# ---------------------------------------------------------
st.sidebar.header("Filters")

min_year = int(df["JAAR"].min())
max_year = int(df["JAAR"].max())

if min_year < max_year:
    year_range = st.sidebar.slider(
        "Jaren", min_value=min_year, max_value=max_year, value=(min_year, max_year)
    )
else:
    year_range = (min_year, max_year)

# True voor de rijen binnen de gekozen jaren
in_range = df["JAAR"].between(year_range[0], year_range[1])

st.sidebar.write("Geselecteerde rijen:", int(in_range.sum()))
st.sidebar.caption("De kaart heeft een eigen jaarkeuze in het tabblad 'Kaart'.")

if in_range.sum() == 0:
    st.warning("Geen data voor de gekozen jaren.")
    st.stop()

# ---------------------------------------------------------
# 4. Tabbladen
# ---------------------------------------------------------
tab_hoofd, tab1, tab_cor, tab_extra, tab2, tab3, tab4, tab_bron, tab_end = st.tabs([
    "Hoofdvraag",
    "Welvaart en advies",
    "Correlatie",
    "Afwijkers",
    "Leerling-leraarratio",
    "Provincie en schooltype",
    "Kaart",
    "Dataverantwoording",
    "Conclusie",
    
])

# ---------------------------------------------------------
# Tab hoofd
# ---------------------------------------------------------
with tab_hoofd:
    st.header("Hoofdvraag")
    st.subheader("Verschilt het schooladvies tussen buurten met hetzelfde inkomen?")

    st.write(
        "In deze app onderzoeken we in hoeverre het schooladvies samenhangt met het inkomen in de omgeving van een school"
        "in de omgeving van een school."
    )

    st.subheader("Deelvraag 1: Hoeveel verschilt het schooladvies tussen scholen met een vergelijkbare inkomensomgeving?")

    st.write(
        "Ook bij scholen in buurten met een vergelijkbaar inkomen verschilt het schooladvies. "
        "Het inkomen in de omgeving speelt dus een rol, maar is niet de enige factor die "
        "samenhangt met het schooladvies."
    )

    st.subheader("Deelvraag 2: Welke andere kenmerken hangen samen met deze verschillen?")

    st.write(
        "Naast inkomen zijn ook andere kenmerken onderzocht, zoals financiële welvaart, "
        "vermogen, provincie, onderwijsrichting en de leerling-leraarratio."
    )

# =========================================================
# TABBLAD 1: advies naar buurtwelvaart
# =========================================================
with tab1:
    data = df[in_range]
    pct10 = percentages10[in_range]
    pct3 = percentages[in_range]

    # Verdeel de scholen in 10 even grote groepen op basis van buurtwelvaart
    if data[wealth_14].nunique() < 2:
        st.warning("Te weinig verschillende welvaartswaarden om groepen te maken.")
    else:
        groups = pd.qcut(data[wealth_14], q=10, duplicates="drop")

        # ----- Grafiek 1: alle 10 adviescategorieën -----
        st.subheader("Verdeling van het schooladvies naar buurtscore")
        st.write(
            "Scholen zijn verdeeld in 10 even grote groepen op basis van het gemiddelde huishoudelijk vermogen in de buurt. Elke lijn toont het gemiddelde percentage leerlingen dat een bepaald schooladvies kreeg."
        )

        summary = pct10.groupby(groups, observed=True).mean()
        summary[wealth_14] = data.groupby(groups, observed=True)[wealth_14].mean()

        fig, ax = plt.subplots(figsize=(12, 8))
        summary.plot(
            ax=ax,
            x=wealth_14,
            y=advice_cols,
            marker="o",
            colormap="tab10",
        )
        ax.set_xlabel("Gemiddelde percentielgroep van de buurt")
        ax.set_ylabel("Gemiddeld percentage leerlingen (%)")
        ax.set_title("Verdeling van het schooladvies naar buurtscore")
        ax.legend(title="Schooladvies", bbox_to_anchor=(1, 1), loc="upper left")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        # ----- Grafiek 2: 3 adviesgroepen -----
        st.subheader("Adviesgroepen naar buurtwelvaart")
        st.write(
            "Dezelfde grafiek, maar de tien adviescategorieën zijn samengevoegd "
            "tot drie groepen: lager, middelbaar en hoger advies."
        )

        summary3 = pct3.groupby(groups, observed=True).mean()
        summary3["score"] = data.groupby(groups, observed=True)[wealth_14].mean()

        fig, ax = plt.subplots(figsize=(13, 6))
        summary3.plot(
            ax=ax,
            x="score",
            y=["Lager advies", "Middelbaar advies", "Hoger advies"],
            marker="o",
            color=["tab:orange", "tab:pink", "tab:cyan"],
        )
        ax.set_xlabel("Huishoudelijk vermogen in de buurt (percentielgroep)")
        ax.set_ylabel("Gemiddeld percentage leerlingen (%)")
        ax.set_title("Adviesgroepen naar buurtwelvaart")
        ax.legend(
            labels=[
                r"$\bf{Laag:}$" + "\n(PRO\nVMBO-B\nVMBO-B/K\nVMBO-K)",
                r"$\bf{Midden:}$" + "\n(VMBO-K/GT\nVMBO-GT\nVMBO-GT/HAVO\nHAVO)",
                r"$\bf{Hoog:}$" + "\n(HAVO/VWO\nVWO)",
            ],
            title="Adviesniveau",
            loc="upper left",
            bbox_to_anchor=(1, 1),
            frameon=False,
            labelspacing=1.5,
        )
        ax.grid(alpha=0.25)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    # ----- Grafiek 3: heatmap -----
    st.subheader("Heatmap: schooladvies naar buurtwelvaartsscore")
    st.write(
        "Buurten zijn gegroepeerd op hun score voor financiële welvaart. "
        "Elke cel toont de gemiddelde waarde voor scholen in die welvaartsgroep. "
    )

    bins = np.arange(30, 81, 5)
    wealth_group = pd.cut(data[wealth_6], bins=bins, right=False)

    # LET OP: dit middelt de aantallen leerlingen per school, zoals in het notebook.
    # Wil je percentages tonen, vervang dan data[advice_cols] door pct10.
    heatmap_data = pct10.groupby(
        wealth_group, observed=True
    ).mean().T

    if heatmap_data.empty:
        st.warning("Geen data beschikbaar voor de heatmap.")
    else:
        fig, ax = plt.subplots(figsize=(13, 7))
        sns.heatmap(
            heatmap_data,
            cmap="YlGnBu",
            annot=True,
            fmt=".1f",
            linewidths=0.5,
            cbar_kws={"label": "Gemiddeld percentage op schoolniveau (%)"},
            ax=ax,
        )
        ax.set(
            xlabel="Welvaartsscore huishoudens in de buurt",
            ylabel="Schooladvies",
            title="Verdeling van het schooladvies naar buurtwelvaart",
        )
        ax.tick_params(axis="both", rotation=0)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

# =========================================================
# TABBLAD 2: leerling-leraarratio
# =========================================================
with tab2:
    st.subheader("Afwijking in advies vs. leerling-leraarratio")
    st.write(
        "Elke stip staat voor een basisschool. De grafieken laten zien of scholen meer of minder leerlingen met een lager of hoger advies hebben dan je op basis van de welvaart in hun buurt zou verwachten. De nullijn geeft aan dat het advies overeenkomt met het gemiddelde van vergelijkbare scholen. De zwarte lijn laat de algemene trend zien. Gegevens over de leerling-leraarratio zijn beschikbaar vanaf 2021."
    )

    max_ratio = st.slider("Maximaal aantal leerlingen per leraar", 10, 70, 70)

    df1 = deviation.copy()
    df1[["LEERLING_LERAAR_RATIO", "SOORT_PO", "JAAR"]] = df[
        ["LEERLING_LERAAR_RATIO", "SOORT_PO", "JAAR"]
    ]

    df1 = df1[
        (df1["SOORT_PO"] == "Bo")
        & (df1["JAAR"] >= 2021)
        & in_range
        & df1["LEERLING_LERAAR_RATIO"].between(0, max_ratio)
    ].dropna(subset=["Lager advies", "Hoger advies", "LEERLING_LERAAR_RATIO"])

    if len(df1) < 2:
        st.warning("Te weinig data voor deze instellingen. Kies jaren vanaf 2021.")
    else:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        x = df1["LEERLING_LERAAR_RATIO"]

        for ax, col in zip(axes, ["Lager advies", "Hoger advies"]):
            y = df1[col]
            ax.scatter(x, y, alpha=0.2, s=12)

            # Trendlijn (alleen mogelijk met minstens 2 verschillende x-waarden)
            if x.nunique() > 1:
                m, b = np.polyfit(x, y, 1)
                ax.plot([0, max_ratio], m * np.array([0, max_ratio]) + b, color="black")

            ax.axhline(0, color="gray", linestyle="--")
            ax.set(
                xlim=(0, max_ratio),
                xlabel="Leerlingen per leraar",
                ylabel="Afwijking (procentpunten)",
                title=col,
            )
            ax.grid(alpha=0.2)

        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        st.write("Waarnemingen:", len(df1))

# =========================================================
# TABBLAD 3: provincie en denominatie
# =========================================================
with tab3:
    # ----- Grafiek: per provincie -----
    st.subheader("Afwijking per provincie")
    st.write(
        "De boxplots laten zien hoe het schooladvies per provincie afwijkt van wat je op basis van de buurtwelvaart zou verwachten. De gestippelde nullijn geeft aan wanneer het advies overeenkomt met het gemiddelde van vergelijkbare scholen."
    )

    df2 = deviation.copy()
    df2[["PROVINCIE", "SOORT_PO", "JAAR"]] = df[["PROVINCIE", "SOORT_PO", "JAAR"]]

    df2 = df2[(df2["SOORT_PO"] == "Bo") & in_range].dropna(
        subset=["Lager advies", "Hoger advies", "PROVINCIE"]
    )

    if len(df2) == 0:
        st.warning("Geen data voor de gekozen jaren.")
    else:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        provinces = sorted(df2["PROVINCIE"].unique())

        for ax, col in zip(axes, ["Lager advies", "Hoger advies"]):
            box_data = [df2.loc[df2["PROVINCIE"] == p, col] for p in provinces]

            ax.boxplot(box_data, showfliers=False)
            ax.axhline(0, color="gray", linestyle="--")
            ax.set_xticks(range(1, len(provinces) + 1))
            ax.set_xticklabels(provinces, rotation=45, ha="right")
            ax.set_ylabel("Afwijking (procentpunten)")
            ax.set_title(col)
            ax.grid(axis="y", alpha=0.2)

        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        st.write("Totaal aantal waarnemingen:", len(df2))

    # ----- Grafiek: per denominatie -----
    st.subheader("Afwijking per schooltype")
    st.write(
        "Dezelfde boxplots, nu uitgesplitst naar "
        "Schooltypen met een kleine hoeveelheid aan waarnemingen geven minder betrouwbare "
        "resultaten. Gebruik de schuifregelaar om het minimale aantal waarnemingen in te stellen."
    )

    min_obs = st.slider("Minimaal aantal waarnemingen per denominatie", 0, 500, 60, step=10)

    df3 = deviation.copy()
    df3[["DENOMINATIE_VESTIGING", "SOORT_PO", "JAAR"]] = df[
        ["DENOMINATIE_VESTIGING", "SOORT_PO", "JAAR"]
    ]

    df3 = df3[(df3["SOORT_PO"] == "Bo") & in_range].dropna(
        subset=["Lager advies", "Hoger advies", "DENOMINATIE_VESTIGING"]
    )

    # Houd denominaties met genoeg waarnemingen
    counts = df3["DENOMINATIE_VESTIGING"].value_counts()
    df3 = df3[df3["DENOMINATIE_VESTIGING"].isin(counts[counts >= min_obs].index)]

    if len(df3) == 0:
        st.warning("Geen denominaties met zoveel waarnemingen. Zet de schuifregelaar lager.")
    else:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        denominations = sorted(df3["DENOMINATIE_VESTIGING"].unique())

        for ax, col in zip(axes, ["Lager advies", "Hoger advies"]):
            box_data = [df3.loc[df3["DENOMINATIE_VESTIGING"] == d, col] for d in denominations]

            ax.boxplot(box_data, showfliers=False)
            ax.axhline(0, color="gray", linestyle="--")
            ax.set_xticks(range(1, len(denominations) + 1))
            ax.set_xticklabels(denominations, rotation=45, ha="right")
            ax.set_ylabel("Afwijking (procentpunten)")
            ax.set_title(col)
            ax.grid(axis="y", alpha=0.2)

        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        st.write("Totaal aantal waarnemingen:", len(df3))

        with st.expander("Waarnemingen per denominatie"):
            st.write(df3["DENOMINATIE_VESTIGING"].value_counts().sort_index())

# =========================================================
# TABBLAD 4: kaart
# =========================================================

with tab4:
    import folium
    from streamlit_folium import st_folium
    from branca.colormap import LinearColormap
    
    
    st.subheader("Schoollocaties gekleurd naar advies")
    st.write(
        "Elke stip is een school. De kleur toont het percentage leerlingen dat het "
        "gekozen advies kreeg. Kies een jaar en een adviescategorie."
    )

    years = sorted(df["JAAR"].astype(int).unique())

    col1, col2 = st.columns(2)

    with col1:
        year = st.selectbox("Jaar", years, index=len(years) - 1)

    with col2:
        adviesgroep = st.selectbox(
            "Adviescategorie", advice_groups, index=2
        )

    # Selecteer het jaar en voeg de adviespercentages toe
    kaart_data = df[df["JAAR"].astype(int) == year].copy()
    kaart_data[advice_groups] = percentages.loc[
        kaart_data.index, advice_groups
    ]

    # Verwijder scholen zonder locatie of zonder waarde
    kaart_data = kaart_data.dropna(
        subset=["center_lon", "center_lat", adviesgroep]
    )

    # Verwijder eventuele ongeldige coördinaten en percentages
    kaart_data = kaart_data[
        kaart_data["center_lon"].between(-180, 180)
        & kaart_data["center_lat"].between(-90, 90)
    ].copy()

    kaart_data[adviesgroep] = kaart_data[adviesgroep].astype(float)
    kaart_data = kaart_data[
        np.isfinite(kaart_data[adviesgroep])
    ]

    if len(kaart_data) == 0:
        st.warning("Geen scholen om te tonen voor deze selectie.")
    else:
        # Centreer de kaart op Nederland
        m = folium.Map(
            location=[52.2, 5.3],
            zoom_start=7,
            tiles=None,
            control_scale=True,
        )
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri — Sources: Esri, HERE, Garmin, USGS, and others",
            name="Light Gray",
            control=False,
        ).add_to(m)
        # Behoud dezelfde geel-oranje-rode kleurenschaal
        min_value = float(kaart_data[adviesgroep].min())
        max_value = float(kaart_data[adviesgroep].max())

        # Voorkom problemen als alle scholen dezelfde waarde hebben
        if min_value == max_value:
            max_value = min_value + 1

        colormap = LinearColormap(
            colors=[
                "#ffffd9",
                "#edf8b1",
                "#c7e9b4",
                "#7fcdbb",
                "#41b6c4",
                "#2c7fb8",
                "#253494",
            ]
          ,
            vmin=min_value,
            vmax=max_value,
            caption=f"{adviesgroep} (%)",
        )
        colormap.add_to(m)


        # Add a marker for each school
        for _, school in kaart_data.iterrows():
            waarde = float(school[adviesgroep])

            folium.CircleMarker(
                location=[
                    float(school["center_lat"]),
                    float(school["center_lon"]),
                ],
                radius=3,
                color=colormap(waarde),
                fill=True,
                fill_color=colormap(waarde),
                fill_opacity=0.5,
                opacity=0.5,
                weight=1,
                tooltip=f"{waarde:.1f}%",
            ).add_to(m)

        # Render the map with minimal interaction data returned to Streamlit
        st_folium(
            m,
            use_container_width=True,
            height=700,
            key=f"schoolkaart_{year}_{adviesgroep}",
            returned_objects=[],
        )


        st.write("Getoonde scholen:", len(kaart_data))
# =========================================================
# TABBLAD: DATAVERANTWOORDING
# =========================================================
with tab_bron:
    st.header("Dataverantwoording")

    # ----- Herkomst van de data -----
    st.subheader("Waar komt de data vandaan?")
    st.markdown(
        """
**1. DUO: Schooladviezen (niet-afgeschermde versie).** Per vestiging en per jaar het aantal
leerlingen per schooladvies (PRO tot en met VWO), schooljaren 2019-2020 tot en met 2024-2025.

**2. CBS: Sociaal-economische status; scores per wijk en buurt, regio-indeling 2025.** De
gemiddelde percentielgroep van de huishoudens in een wijk of buurt voor financiële welvaart,
inkomen en vermogen (hoger is welvarender), vanaf 2019.

**3. CBS: Wijk- en buurtkaart 2026.** Het middelpunt (lengte- en breedtegraad) van elke buurt.
Hiermee zijn buurten ruimtelijk aan scholen gekoppeld. De scores van het CBS gebruiken de
regio-indeling van 2025 en de kaart die van 2026, dus buurten die niet op de kaart van 2026
staan zijn weggelaten.

**4. Leerling-leraarratio** per instelling (BRIN) per jaar, 2021 tot en met 2025.
Schoollocaties zijn bepaald met het postcodegebied (6 cijfers) van de vestiging.
"""
    )

    st.markdown("**Waarom de niet-afgeschermde schooladviezen?**")
    st.write(
        "DUO schermt in de standaardversie kleine aantallen af: waarden kleiner dan 5 (dus 1 "
        "tot en met 4 leerlingen) worden niet getoond. Bij kleine scholen verdwijnt daardoor een "
        "groot deel van de adviezen en kloppen totalen en percentages niet meer. Daarom is de "
        "niet-afgeschermde versie aangevraagd."
    )

    # ----- Verwerking -----
    st.subheader("Hoe zijn de bronnen gekoppeld?")
    st.markdown(
        """
1. De adviezen van 2019 tot en met 2024 zijn onder elkaar gezet. Het totaal is het aantal
   adviezen min 'advies niet mogelijk'.
2. Elke schoolvestiging kreeg een locatie op basis van de zes cijfers van de postcode.
   Vestigingen zonder locatie zijn verwijderd.
3. Elke buurt is gekoppeld aan de **dichtstbijzijnde schoollocatie**. Per schoollocatie en per
   jaar is het gemiddelde van de buurtscores berekend.
4. Voor 773 schoollocaties waaraan geen enkele buurt was gekoppeld, is het gemiddelde genomen
   van de buurten binnen 1 km (4.037 rijen).
5. Rijen zonder buurtscore (1.830) zijn verwijderd. Er blijven 36.938 rijen over.
6. De leerling-leraarratio is gekoppeld op basis van instellingscode en jaar.
"""
    )

    # ----- Koppeling van de leerling-leraarratio -----
    st.subheader("Koppeling van de leerling-leraarratio")
    st.markdown(
        """
De schooladviezen zijn beschikbaar per vestiging, terwijl de leerling-leraarratio
per instelling wordt geregistreerd. Eén instelling kan dus meerdere vestigingen hebben.

Dit vormde geen probleem voor de koppeling van de schoollocaties, omdat deze aanvankelijk
op basis van de postcode van de vestiging zijn bepaald. De koppeling van de
leerling-leraarratio is vervolgens uitgevoerd op basis van de instellingscode en het jaar.
Daarbij is gebruikgemaakt van een `many_to_one`-validatie. Hiermee controleert pandas
of de combinatie van instellingscode en jaar in de tabel met leerling-leraarratio's uniek is.
Zo wordt voorkomen dat dubbele rijen in die tabel de adviesgegevens onbedoeld vermenigvuldigen.

Alle vestigingen van dezelfde instelling krijgen hierdoor dezelfde leerling-leraarratio.
De ratio geeft dus geen afzonderlijk beeld van iedere vestiging.
"""
    )

    # ----- Gebruik van AI -----
    st.subheader("Gebruik van AI")
    st.write(
        "Tijdens dit project zijn AI-hulpmiddelen van Anthropic (Claude) en OpenAI (ChatGPT) "
        "gebruikt ter ondersteuning. Ze zijn ingezet bij het ontwikkelen en verbeteren van de "
        "Streamlit-app, waaronder het schrijven en aanpassen van code, de indeling van de app, "
        "het formuleren van Nederlandse teksten en het bedenken en verbeteren van visualisaties. "
        "De AI-hulpmiddelen dienden als ondersteuning bij het programmeer- en schrijfproces. "
        "De gebruikte data en cijfers zijn afkomstig uit de genoemde databronnen van DUO en CBS. "
        "De keuzes voor de analyse, de interpretatie van de resultaten en de uiteindelijke "
        "verwerking zijn door de projectmakers gemaakt en gecontroleerd."
    )
    
# =========================================================
# extra
# =========================================================   
with tab_extra:
    # Bereken het gemiddelde adviespercentage per vermogensscore
    percentages["bracket"] = df[
        "buurt_avg_GemiddeldePercentielgroep_14"
    ]

    advice_groups = [
        "Lager advies",
        "Middelbaar advies",
        "Hoger advies"
]

    benchmark = percentages.groupby("bracket")[advice_groups].mean()

    # Bereken de afwijking ten opzichte van het gemiddelde
    # van scholen binnen dezelfde vermogensgroep
    deviation = percentages[advice_groups].copy()

    for group in advice_groups:
        deviation[group] = (
            percentages[group]
            - percentages["bracket"].map(benchmark[group])
        )

    # Voeg schoolinformatie toe vanuit df
    afwijkingen = deviation.copy()

    afwijkingen["School"] = df.loc[
        afwijkingen.index, "INSTELLINGSNAAM_VESTIGING"
    ]

    afwijkingen["Soort onderwijs"] = df.loc[
        afwijkingen.index, "SOORT_PO"
    ]

    afwijkingen["Vermogensscore buurt"] = percentages.loc[
        afwijkingen.index, "bracket"
    ]

    afwijkingen["Leerling-leraarratio"] = df.loc[
        afwijkingen.index, "LEERLING_LERAAR_RATIO"
    ]

    # =========================================================
    # WEERGAVE IN STREAMLIT
    # =========================================================

    st.subheader("Scholen die sterk afwijken van de verwachting")

    st.write(
        "Sommige scholen geven vaker een bepaald schooladvies dan je op basis van "
        "de vermogensscore van hun omgeving zou verwachten. Hieronder staan de scholen "
        "met de grootste afwijkingen. De afwijking is weergegeven in procentpunten "
        "ten opzichte van het gemiddelde van scholen binnen dezelfde vermogensgroep."
    )

    # Kies adviescategorie
    advieskeuze = st.selectbox(
        "Adviescategorie",
        ["Lager advies", "Hoger advies"],
        key="extreme_advies"
    )

    adviesnaam = {
        "Lager advies": "lager advies",
        "Hoger advies": "hoger advies"
    }[advieskeuze]

    # Kies onderwijstype
    onderwijstype = st.radio(
        "Type onderwijs",
        ["Alle scholen", "Reguliere basisscholen", "Speciaal onderwijs"],
        horizontal=True,
        key="extreme_onderwijs"
    )

    # Kies minimale afwijking
    drempel = st.slider(
        "Minimale afwijking (procentpunt)",
        min_value=20,
        max_value=80,
        value=60,
        step=5,
        key="extreme_drempel"
    )

    # Filter op minimale afwijking
    resultaat = afwijkingen[
        afwijkingen[advieskeuze].abs() >= drempel
    ].copy()

    # Filter op onderwijstype
    if onderwijstype == "Reguliere basisscholen":
        resultaat = resultaat[resultaat["Soort onderwijs"] == "Bo"]

    elif onderwijstype == "Speciaal onderwijs":
        resultaat = resultaat[resultaat["Soort onderwijs"] != "Bo"]

    # Sorteer op grootste absolute afwijking
    resultaat["Afwijking (procentpunt)"] = resultaat[advieskeuze]

    resultaat = resultaat.loc[
        resultaat["Afwijking (procentpunt)"].abs().sort_values(
            ascending=False
        ).index
    ]

    # =========================================================
    # TOON DE SCHOLEN ALS LIJST
    # =========================================================

    if resultaat.empty:
        st.info("Geen scholen gevonden met deze selectie.")

    else:
        st.write(f"**{len(resultaat)} scholen gevonden**")

        for _, school in resultaat.iterrows():

            afwijking = school["Afwijking (procentpunt)"]

            if afwijking > 0:
                beschrijving = f"meer {adviesnaam}"
            else:
                beschrijving = f"minder {adviesnaam}"

            st.markdown(
                f"**{school['School']}**  \n"
                f"{abs(afwijking):.1f} procentpunt {beschrijving} "
                f"dan verwacht."
            )

            st.caption(
                f"Vermogensscore buurt: {school['Vermogensscore buurt']} · "
                f"Type onderwijs: {school['Soort onderwijs']} · "
                f"Leerling-leraarratio: {school['Leerling-leraarratio']}"
            )

            st.divider()
    
with tab_end:
    st.subheader("Beantwoording van de hoofdvraag")

    st.markdown(
        """
        **Ja, het schooladvies verschilt tussen scholen met een vergelijkbare inkomensomgeving.**
        De analyses laten zien dat ook tussen scholen in vergelijkbare buurten verschillen bestaan.

        De correlatieanalyse laat zien dat de vermogensscore slechts zwak samenhangt met het schooladvies:
        - Lager advies: -0,24
        - Middelbaar advies: 0,07
        - Hoger advies: 0,21

        Dit betekent dat een hogere vermogensscore enigszins samenhangt met minder lage en meer hoge adviezen,
        maar dat dit verband beperkt is.

        Ook andere kenmerken, zoals provincie, onderwijsrichting en leerling-leraarratio,
        zijn onderzocht. Vooral bij onderwijsrichting zijn verschillen zichtbaar, terwijl
        de verschillen tussen provincies klein zijn en de leerling-leraarratio nauwelijks
        een duidelijk verband laat zien.

        ### Wat kunnen we niet concluderen?

        De analyses tonen samenhang, maar bewijzen geen oorzaak-gevolgverband.
        We kunnen niet vaststellen waardoor de verschillen tussen scholen precies ontstaan.
        Factoren zoals de samenstelling van leerlingen, thuissituatie en schoolkeuze van ouders
        zijn niet meegenomen.

        **Conclusie:** de buurt hangt enigszins samen met het schooladvies, maar verklaart
        niet alle verschillen tussen scholen. Andere factoren spelen waarschijnlijk ook een rol.
        """

    )
with tab_cor:
    st.subheader("Correlatiematrix")

    # Variabelen selecteren
    correlatie_data = pd.DataFrame({
        "Vermogensscore buurt": df[
            "buurt_avg_GemiddeldePercentielgroep_14"
        ],
        "Lager advies": percentages["Lager advies"],
        "Middelbaar advies": percentages["Middelbaar advies"],
        "Hoger advies": percentages["Hoger advies"]
    })

    # Correlaties berekenen
    correlatie = correlatie_data.corr()

    st.subheader("Samenhang tussen vermogen en schooladvies")

    correlaties = correlatie["Vermogensscore buurt"].drop(
        "Vermogensscore buurt"
    )

    fig, ax = plt.subplots(figsize=(8, 3.5))

    correlaties.sort_values().plot(
        kind="barh",
        ax=ax,
        color=["tab:orange", "tab:pink", "tab:cyan"]
    )

    ax.set_xlim(-1, 1)
    ax.set_xlabel("Correlatie")
    ax.set_ylabel("")
    ax.set_title("Samenhang met de vermogensscore van de buurt")
    ax.axvline(0, color="black", linewidth=0.8)

    for i, waarde in enumerate(correlaties.sort_values()):
        ax.text(
            waarde + (0.03 if waarde >= 0 else -0.03),
            i,
            f"{waarde:.2f}",
            va="center",
            ha="left" if waarde >= 0 else "right"
        )

    plt.tight_layout()
    st.pyplot(fig)
    st.write(
        "De vermogensscore hangt zwak negatief samen met het percentage "
        "lagere adviezen (-0,24). Voor middelbare adviezen is er vrijwel "
        "geen lineair verband (0,07). Voor hogere adviezen is er een zwak "
        "positief verband (0,21). De vermogensscore hangt dus maar beperkt "
        "samen met de verdeling van schooladviezen."
    )
    