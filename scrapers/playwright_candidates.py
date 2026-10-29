# Websites identified as Playwright candidates (JavaScript-heavy)
#
# These sites often render job listings or detail pages client-side.
# requests + BeautifulSoup may return empty shells or search pages only.
#
# - HelloWork (hellowork.com) — heavy client-side rendering
# - JobTeaser (jobteaser.com) — authentication + SPA
# - Welcome to the Jungle (welcometothejungle.com) — SPA
# - Stage.fr — returned 403 in testing (anti-bot)
# - Studyrama — many URLs are hash/SPA routes (#emploi/...)
# - Monster, Indeed-style aggregators — often bot protection
#
# Strategy: keep requests scrapers for server-rendered pages (France Travail),
# add Playwright scrapers later for dynamic sites without mixing concerns.

PLAYWRIGHT_CANDIDATES = [
    "hellowork.com",
    "jobteaser.com",
    "welcometothejungle.com",
    "stage.fr",
    "studyrama.com",
    "monster.fr",
    "cadremploi.fr",
    "moovijob.com",
]
