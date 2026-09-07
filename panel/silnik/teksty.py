"""Generator tekstów analitycznych bez AI (Etap 4, krok 8/9) — reguły
dopasowane do wzorca z realnego raportu (Raport_Torun_Orange_v3), nie
model językowy. Każda funkcja zwraca jeden akapit `teksty.*`, budowany
wyłącznie z `obliczenia` (Etap 1) + podstawowych metadanych punktu.

Zakres świadomie ograniczony do JEDNEGO punktu na raz — referencyjny
raport czasem porównuje punkty między sobą ("w przeciwieństwie do
Punktu 1..."), ale to wymagałoby kontekstu całego projektu na etapie
generowania tekstu pojedynczego punktu; pominięte, nie ma tego w
żadnym z 7 pól.
"""
from __future__ import annotations

import re


def _liczba(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


def _procent(p: float) -> str:
    return f"{p:.1f}".replace(".", ",") + "%"


# --- 1. Lokalizacja ---------------------------------------------------------

def tekst_lokalizacja(nazwa: str, miejscowosc: str, wloty: list[dict], geometria_regularna: bool) -> str:
    ulice = []
    for w in wloty:
        opis = (w.get("opis") or "").strip()
        nazwa_ulicy = re.sub(r"\s*\(od [a-ząćęłńóśźż]+\)\s*$", "", opis).strip()
        if nazwa_ulicy and nazwa_ulicy not in ulice:
            ulice.append(nazwa_ulicy)

    if ulice:
        opis_ulic = " i ".join(ulice) if len(ulice) <= 2 else ", ".join(ulice[:-1]) + " i " + ulice[-1]
        zdanie_ulic = f"na skrzyżowaniu ulic {opis_ulic}"
    else:
        zdanie_ulic = "w lokalizacji opisanej w karcie skrzyżowania"

    n = len(wloty)
    kierunki = ", ".join(w.get("id", "") for w in wloty if w.get("id"))
    if geometria_regularna:
        zdanie_wlotow = f"Skrzyżowanie ma {n} wloty ({kierunki})."
    else:
        zdanie_wlotow = f"Skrzyżowanie ma {n} wloty (geometria nietypowa: {kierunki})."

    return (
        # "w miejscowości X" zamiast "w X" — deklinacja nazw miast (Toruń -> Toruniu,
        # Warszawa -> Warszawie...) jest niedeterministyczna bez słownika odmian, ta
        # konstrukcja zostaje poprawna niezależnie od podanej nazwy.
        f"Punkt pomiarowy zlokalizowany jest w miejscowości {miejscowosc}, {zdanie_ulic}. {zdanie_wlotow} "
        "Pomiary wykonano w pełnym cyklu dobowym metodą rejestracji wideo z automatyczną "
        "klasyfikacją i weryfikacją manualną."
    )


# --- 2. Organizacja ruchu (diagramy przepływów) -----------------------------

def tekst_organizacja_ruchu(relacje_sdr: list[dict], sdr: int) -> str:
    if not relacje_sdr or not sdr:
        return "Brak danych o relacjach ruchu dla tego punktu."

    wloty_uzyte = sorted({r["wlot"] for r in relacje_sdr})
    manewry_uzyte = [m for m in ["Prawo", "Wprost", "Lewo", "Zawracający"]
                      if m in {r["manewr"] for r in relacje_sdr}]
    manewry_tekst = {"Prawo": "w prawo", "Wprost": "wprost", "Lewo": "w lewo", "Zawracający": "zawracający"}
    zdanie_wstep = (
        f"Relacje ruchu opisano poprzez wloty kierunkowe {', '.join(wloty_uzyte)} "
        f"oraz manewry: {', '.join(manewry_tekst[m] for m in manewry_uzyte)}."
    )

    udzial_wprost = sum(r["udzial"] for r in relacje_sdr if r["manewr"] == "Wprost")
    udzial_zawracanie = sum(r["udzial"] for r in relacje_sdr if r["manewr"] == "Zawracający")

    if udzial_wprost >= 50:
        zdanie_glowne = (
            f"W badanym punkcie dominują potoki na wprost ({_procent(udzial_wprost)} SDR łącznie), "
            "co wskazuje na korytarzowy charakter pracy skrzyżowania. Ruch skrętny pełni rolę uzupełniającą"
        )
        zdanie_glowne += (
            ", a manewry zawracania występują incydentalnie." if udzial_zawracanie < 1
            else f" (zawracanie: {_procent(udzial_zawracanie)})."
        )
    else:
        top = max(relacje_sdr, key=lambda r: r["udzial"])
        zdanie_glowne = (
            f"Dominującą pojedynczą relacją jest {top['opis'].lower()} ({_procent(top['udzial'])} SDR), "
            "co wskazuje na istotną rolę tego skrzyżowania w rozprowadzaniu ruchu do układu lokalnego, "
            "a nie wyłącznie tranzytowego przejazdu na wprost."
        )

    return (
        f"{zdanie_wstep} {zdanie_glowne} Poniższe diagramy przepływów prezentują rozkład relacji "
        "ruchowych dla SDR (całodobowo) oraz dla dwóch stałych okien szczytowych - porannego "
        "(7:00-8:00) i popołudniowego (15:00-16:00) - tych samych dla wszystkich punktów "
        "pomiarowych projektu, co zapewnia porównywalność między punktami."
    )


# --- 3. Ruch według kierunków i relacji -------------------------------------

def tekst_ruch_wg_kierunkow(relacje_sdr: list[dict]) -> str:
    if not relacje_sdr:
        return "Brak danych o relacjach ruchu dla tego punktu."

    posortowane = sorted(relacje_sdr, key=lambda r: -r["udzial"])
    top = posortowane[:2] if len(posortowane) > 1 and posortowane[1]["udzial"] >= posortowane[0]["udzial"] / 3 else posortowane[:1]
    suma_top = sum(r["udzial"] for r in top)

    opisy_top = " oraz ".join(f"{r['opis'].lower()} ({_liczba(r['sdr'])} poj./dobę, {_procent(r['udzial'])} SDR)" for r in top)
    zdanie_koncentracji = (
        "bardzo silną koncentrację" if suma_top >= 60
        else "umiarkowaną koncentrację" if suma_top >= 35
        else "rozproszony rozkład"
    )
    liczebnik = "relacjach" if len(top) > 1 else "relacji"
    zdanie_glowne = f"Analiza kierunkowa wskazuje na {zdanie_koncentracji} ruchu w {len(top)} {liczebnik}: {opisy_top}."
    if len(top) > 1:
        zdanie_glowne += f" Łącznie te relacje generują ok. {_procent(suma_top)} całego SDR."

    godziny = {r["godzinaSzczytu"] for r in top}
    if len(godziny) > 1:
        opisy_szczytow = ", ".join(f"{r['opis']}: {r['godzinaSzczytu']}" for r in top)
        zdanie_szczytow = (
            f" Godziny szczytu relacji dominujących różnią się ({opisy_szczytow}), "
            "co jest typowym obrazem porannego i popołudniowego wahadła dojazdowego."
        )
    else:
        zdanie_szczytow = f" Relacje dominujące osiągają szczyt o tej samej porze ({godziny.pop()})."

    udzial_zawracanie = sum(r["udzial"] for r in relacje_sdr if r["manewr"] == "Zawracający")
    zdanie_zawracanie = f" Manewry zawracania mają znikomy udział ({_procent(udzial_zawracanie)})." if 0 < udzial_zawracanie < 1 else ""

    return zdanie_glowne + zdanie_szczytow + zdanie_zawracanie


# --- 4. Ruch pojazdów ciężkich -----------------------------------------------

def tekst_ruch_ciezkich(relacje_ciezkie: list[dict], upc: list[dict], ruch_ciezki_suma: int, sdr: int) -> str:
    if not relacje_ciezkie or not sdr:
        return "Brak danych o ruchu pojazdów ciężkich dla tego punktu."

    udzial_ogolny = round(ruch_ciezki_suma / sdr * 100, 1) if sdr else 0.0
    zdanie_wstep = (
        f"Udział pojazdów ciężkich w ruchu ogółem wynosi {_procent(udzial_ogolny)} "
        f"({_liczba(ruch_ciezki_suma)} poj./dobę)."
    )

    if not upc or all(u["upc"] == 0 for u in upc):
        return f"{zdanie_wstep} Ruch ciężki jest rozłożony równomiernie pomiędzy relacjami, bez wyraźnej koncentracji."

    top_upc = max(upc, key=lambda u: u["upc"])
    if top_upc["upc"] >= 15:
        ocena = "co wyraźnie wyróżnia tę relację na tle pozostałych i może wskazywać na jej funkcję tranzytową/towarową"
    elif top_upc["upc"] >= 5:
        ocena = "co jest wartością zauważalną, choć niewyróżniającą się drastycznie na tle pozostałych relacji"
    else:
        ocena = "co oznacza brak istotnej koncentracji ruchu ciężkiego w pojedynczej relacji"

    return (
        f"{zdanie_wstep} Najwyższy udział pojazdów ciężkich w relacji odnotowano dla "
        f"{top_upc['opis'].lower()} ({_procent(top_upc['upc'])} ruchu tej relacji), {ocena}."
    )


# --- 5. Pory doby ------------------------------------------------------------

def tekst_pory_doby(pory_doby: dict) -> str:
    dzien_suma, dzien_udzial = pory_doby["dzien"]
    noc_suma, noc_udzial = pory_doby["noc"]
    return (
        f"Ruch zmotoryzowany w porze dziennej (06:00-22:00) stanowi {_procent(dzien_udzial)} SDR "
        f"({_liczba(dzien_suma)} poj.), natomiast w porze nocnej (22:00-06:00) - {_procent(noc_udzial)} SDR "
        f"({_liczba(noc_suma)} poj.). Podział na dwie pory (dzień/noc) ujednolica prezentację między "
        "punktami i jest spójny z konwencją przyjętą w metodologii raportu."
    )


# --- 6. Struktura rodzajowa ---------------------------------------------------

def _udzial_kategorii(struktura: list[dict], nazwy: list[str]) -> float:
    return sum(w["udzialCale"] for w in struktura if w["kategoria"] in nazwy)


def tekst_struktura_rodzajowa(struktura: list[dict]) -> str:
    if not struktura:
        return "Brak danych o strukturze rodzajowej ruchu dla tego punktu."

    slownik = {w["kategoria"]: w for w in struktura}
    osobowe = slownik.get("Osobowe", {}).get("udzialCale", 0.0)

    dostawcze = slownik.get("Dostawcze", {}).get("udzialCale", 0.0)
    ciezarowe = slownik.get("Ciężarowe", {}).get("udzialCale", 0.0)
    naczepy = slownik.get("Ciężarowe z naczepami", {}).get("udzialCale", 0.0)
    gospodarczy = dostawcze + ciezarowe + naczepy
    if gospodarczy >= 8:
        zdanie_gospodarczy = (
            f"Ruch gospodarczy jest znaczący - pojazdy dostawcze ({_procent(dostawcze)}) oraz ciężkie "
            f"- ciężarowe z naczepami ({_procent(naczepy)}) i ciężarowe ({_procent(ciezarowe)}) - "
            f"łącznie ok. {_procent(gospodarczy)}."
        )
    elif gospodarczy >= 3:
        zdanie_gospodarczy = (
            f"Ruch gospodarczy jest widoczny - pojazdy dostawcze i ciężkie stanowią łącznie ok. "
            f"{_procent(gospodarczy)}."
        )
    else:
        zdanie_gospodarczy = f"Ruch gospodarczy (dostawcze i ciężkie łącznie) jest marginalny ({_procent(gospodarczy)})."

    autobusy = slownik.get("Autobusy", {}).get("udzialCale", 0.0)
    mikrobusy = slownik.get("Mikrobusy", {}).get("udzialCale", 0.0)
    zdanie_publiczny = (
        f"Środki transportu publicznego mają {'zauważalny' if autobusy + mikrobusy >= 2 else 'niewielki'} "
        f"udział (autobusy {_procent(autobusy)}, mikrobusy {_procent(mikrobusy)})."
    )

    rowery = slownik.get("Rowery", {}).get("udzialCale", 0.0)
    piesi = slownik.get("Piesi", {}).get("udzialCale", 0.0)
    niezmot = rowery + piesi
    if niezmot >= 10:
        zdanie_niezmot = (
            f"Na uwagę zasługuje wysoki udział ruchu nie zmotoryzowanego - rowery ({_procent(rowery)}) "
            f"i piesi ({_procent(piesi)}) - co wskazuje na istotną rolę tego skrzyżowania w lokalnej "
            "sieci pieszo-rowerowej."
        )
    elif niezmot >= 3:
        zdanie_niezmot = f"Ruch nie zmotoryzowany jest widoczny, choć umiarkowany (rowery {_procent(rowery)}, piesi {_procent(piesi)})."
    else:
        zdanie_niezmot = f"Ruch nie zmotoryzowany jest obecny, choć udziałowo mały (rowery {_procent(rowery)}, piesi {_procent(piesi)})."

    return (
        f"Struktura rodzajowa ruchu jest zdominowana przez pojazdy osobowe ({_procent(osobowe)}). "
        f"{zdanie_gospodarczy} {zdanie_publiczny} {zdanie_niezmot}"
    )


# --- 7. Komentarz analityczny (synteza) --------------------------------------

def tekst_komentarz_analityczny(
    sdr: int, szczyt_dobowy: dict, relacje_sdr: list[dict],
    struktura: list[dict], przypisy_jakosci: list[dict],
) -> str:
    if not relacje_sdr or not sdr:
        return "Brak wystarczających danych do sformułowania komentarza analitycznego."

    top = max(relacje_sdr, key=lambda r: r["udzial"])
    udzial_wprost = sum(r["udzial"] for r in relacje_sdr if r["manewr"] == "Wprost")
    if udzial_wprost >= 50:
        zdanie_charakter = (
            f"Punkt charakteryzuje się dominacją ruchu na wprost ({_procent(udzial_wprost)} SDR łącznie), "
            "co wskazuje na korytarzowy charakter skrzyżowania."
        )
    else:
        zdanie_charakter = (
            f"Punkt charakteryzuje się rozproszonym rozkładem relacji - dominującą pojedynczą relacją jest "
            f"{top['opis'].lower()} ({_procent(top['udzial'])} SDR), co wskazuje na funkcję rozprowadzającą "
            "ruch do układu lokalnego, a nie wyłącznie tranzytową."
        )

    zdanie_szczyt = f"Szczyt dobowy przypada na {szczyt_dobowy['godzina']} ({_liczba(szczyt_dobowy['wartosc'])} poj./h)."

    slownik = {w["kategoria"]: w for w in struktura}
    osobowe = slownik.get("Osobowe", {}).get("udzialCale", 0.0)
    ciezki = (slownik.get("Ciężarowe", {}).get("udzialCale", 0.0)
              + slownik.get("Ciężarowe z naczepami", {}).get("udzialCale", 0.0)
              + slownik.get("Dostawcze", {}).get("udzialCale", 0.0))
    zdanie_struktura = (
        f"Struktura rodzajowa ({_procent(osobowe)} osobowe, ok. {_procent(ciezki)} ruch gospodarczy łącznie) "
        f"jest {'typowa dla miejskiego ciągu o funkcji dojazdowo-tranzytowej' if osobowe >= 70 else 'zróżnicowana, z zauważalnym udziałem kategorii pozaosobowych'}."
    )

    if przypisy_jakosci:
        zdanie_jakosc = (
            f"Zidentyfikowano {len(przypisy_jakosci)} "
            f"{'zastrzeżenie' if len(przypisy_jakosci) == 1 else 'zastrzeżenia'} jakościowe dotyczące danych "
            "źródłowych, opisane w przypisach przy odpowiednich tabelach."
        )
    else:
        zdanie_jakosc = "Dane są wewnętrznie spójne, sumy kategorii zgadzają się z SDR. Brak istotnych zastrzeżeń jakościowych."

    return f"{zdanie_charakter} {zdanie_szczyt} {zdanie_struktura} {zdanie_jakosc}"


# --- Wejście dla CLI (server.js) ---------------------------------------------

def generuj_wszystkie_teksty(punkt: dict) -> dict:
    o = punkt["obliczenia"]
    return {
        "lokalizacja": tekst_lokalizacja(punkt["nazwa"], punkt["miejscowosc"], punkt["wloty"], punkt["geometriaRegularna"]),
        "organizacjaRuchu": tekst_organizacja_ruchu(o["relacjeSDR"], o["sdr"]),
        "ruchWgKierunkow": tekst_ruch_wg_kierunkow(o["relacjeSDR"]),
        "ruchPojazdowCiezkich": tekst_ruch_ciezkich(o["relacjeCiezkie"], o["upc"], o["ruchCiezkiSuma"], o["sdr"]),
        "poryDoby": tekst_pory_doby(o["poryDoby"]),
        "strukturaRodzajowa": tekst_struktura_rodzajowa(o["strukturaRodzajowa"]),
        "komentarzAnalityczny": tekst_komentarz_analityczny(
            o["sdr"], o["szczytDobowy"], o["relacjeSDR"], o["strukturaRodzajowa"],
            punkt.get("przypisyJakosciDanych") or [],
        ),
    }
