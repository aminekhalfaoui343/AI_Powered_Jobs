from scrapers.france_travail import FranceTravailScraper


BFF_PAYLOAD = {
    "numeroOffre": "Offre n° 214JPDD",
    "intituleOffre": "Platform Engineer Junior (H/F/N) - CDI - Paris (H/F)",
    "descriptif": "Votre mission : Au sein de l'équipe R&PD, la team Platform Engineering conçoit les infrastructures.",
    "lieuTravail": "PARIS (75)",
    "syntheseContrat": "CDI - Contrat travail",
    "salaire": "Annuel de 42000.0 Euros à 47000.0 Euros",
    "experienceProfil": {"experience": "Débutant accepté"},
    "listeCompetence": [
        {"libelleCompetence": "Configurer et optimiser des systèmes DevOps"},
        {"libelleCompetence": "Collaborer avec une équipe projet"},
    ],
    "listeFormation": [{"libelleFormation": "Bac+5 Cloud Computing"}],
    "etablissement": {"libelleEnseigne": "EKIMETRICS FRANCE"},
    "dateDerniereModification": "06 octobre 2026",
}


def test_offer_id_from_detail_url():
    scraper = FranceTravailScraper()
    assert scraper.offer_id_from_url("https://candidat.francetravail.fr/offres/recherche/detail/214JPDD") == "214JPDD"
    assert scraper.offer_id_from_url("https://candidat.francetravail.fr/offres/recherche") is None


def test_scrape_uses_bff_json_not_related_offers_html(monkeypatch):
    requested = {}

    def fake_fetch_json(url):
        requested["url"] = url
        return BFF_PAYLOAD

    def fail_html(_url):
        raise AssertionError("France Travail detail scrape must not parse the HTML shell")

    monkeypatch.setattr("scrapers.france_travail.fetch_json", fake_fetch_json)
    monkeypatch.setattr("utils.http.fetch_html", fail_html)

    raw = FranceTravailScraper().scrape("https://candidat.francetravail.fr/offres/recherche/detail/214JPDD")

    assert requested["url"] == "https://candidat.francetravail.fr/api-descriptifoffre/offre/214JPDD"
    assert raw.title.startswith("Platform Engineer Junior")
    assert raw.company == "EKIMETRICS FRANCE"
    assert raw.location == "PARIS (75)"
    assert "R&PD" in raw.raw_text
    assert "D'autres offres" not in raw.raw_text
    assert raw.metadata["structured"] is True
    assert "Configurer et optimiser des systèmes DevOps" in raw.metadata["skills"]


def test_scrape_rejects_incomplete_bff_payload(monkeypatch):
    monkeypatch.setattr("scrapers.france_travail.fetch_json", lambda url: {"intituleOffre": "Only a title"})

    try:
        FranceTravailScraper().scrape("https://candidat.francetravail.fr/offres/recherche/detail/214JPDD")
    except ValueError as exc:
        assert "title or description" in str(exc)
    else:
        raise AssertionError("Expected incomplete BFF payloads to fail fast")
