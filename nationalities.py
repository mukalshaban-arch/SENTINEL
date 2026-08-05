"""
SENTINEL - nationalities.py
Maps free-text nationality/demonym values (as stored in poi.nationality,
e.g. "Nigerian", "Brazilian") to their country name (e.g. "Nigeria",
"Brazil") for display and aggregation in the Country Profiles module.

Lookup is case-insensitive. Values not found in the table are returned
title-cased and unchanged, so free-text entries that are already a country
name (or an unrecognised demonym) still work rather than erroring out.
"""

DEMONYM_TO_COUNTRY = {
    "afghan": "Afghanistan", "albanian": "Albania", "algerian": "Algeria",
    "american": "United States", "andorran": "Andorra", "angolan": "Angola",
    "argentine": "Argentina", "argentinian": "Argentina", "armenian": "Armenia",
    "australian": "Australia", "austrian": "Austria", "azerbaijani": "Azerbaijan",
    "bahamian": "Bahamas", "bahraini": "Bahrain", "bangladeshi": "Bangladesh",
    "barbadian": "Barbados", "belarusian": "Belarus", "belgian": "Belgium",
    "belizean": "Belize", "beninese": "Benin", "bhutanese": "Bhutan",
    "bolivian": "Bolivia", "bosnian": "Bosnia and Herzegovina", "botswanan": "Botswana",
    "brazilian": "Brazil", "british": "United Kingdom", "bruneian": "Brunei",
    "bulgarian": "Bulgaria", "burkinabe": "Burkina Faso", "burmese": "Myanmar",
    "burundian": "Burundi", "cambodian": "Cambodia", "cameroonian": "Cameroon",
    "canadian": "Canada", "cape verdean": "Cabo Verde", "central african": "Central African Republic",
    "chadian": "Chad", "chilean": "Chile", "chinese": "China",
    "colombian": "Colombia", "comoran": "Comoros", "congolese": "Democratic Republic of the Congo",
    "costa rican": "Costa Rica", "croatian": "Croatia", "cuban": "Cuba",
    "cypriot": "Cyprus", "czech": "Czech Republic", "danish": "Denmark",
    "djiboutian": "Djibouti", "dominican": "Dominican Republic", "dutch": "Netherlands",
    "ecuadorian": "Ecuador", "egyptian": "Egypt", "emirati": "United Arab Emirates",
    "equatorial guinean": "Equatorial Guinea", "eritrean": "Eritrea", "estonian": "Estonia",
    "ethiopian": "Ethiopia", "fijian": "Fiji", "filipino": "Philippines",
    "finnish": "Finland", "french": "France", "gabonese": "Gabon",
    "gambian": "Gambia", "georgian": "Georgia", "german": "Germany",
    "ghanaian": "Ghana", "greek": "Greece", "grenadian": "Grenada",
    "guatemalan": "Guatemala", "guinean": "Guinea", "guyanese": "Guyana",
    "haitian": "Haiti", "honduran": "Honduras", "hungarian": "Hungary",
    "icelandic": "Iceland", "indian": "India", "indonesian": "Indonesia",
    "iranian": "Iran", "iraqi": "Iraq", "irish": "Ireland",
    "israeli": "Israel", "italian": "Italy", "ivorian": "Ivory Coast",
    "jamaican": "Jamaica", "japanese": "Japan", "jordanian": "Jordan",
    "kazakh": "Kazakhstan", "kenyan": "Kenya", "kittitian": "Saint Kitts and Nevis",
    "kuwaiti": "Kuwait", "kyrgyz": "Kyrgyzstan", "lao": "Laos",
    "latvian": "Latvia", "lebanese": "Lebanon", "liberian": "Liberia",
    "libyan": "Libya", "liechtensteiner": "Liechtenstein", "lithuanian": "Lithuania",
    "luxembourgish": "Luxembourg", "macedonian": "North Macedonia", "malagasy": "Madagascar",
    "malawian": "Malawi", "malaysian": "Malaysia", "maldivian": "Maldives",
    "malian": "Mali", "maltese": "Malta", "mauritanian": "Mauritania",
    "mauritian": "Mauritius", "mexican": "Mexico", "moldovan": "Moldova",
    "monegasque": "Monaco", "mongolian": "Mongolia", "montenegrin": "Montenegro",
    "moroccan": "Morocco", "mozambican": "Mozambique", "namibian": "Namibia",
    "nepalese": "Nepal", "nepali": "Nepal", "nicaraguan": "Nicaragua",
    "nigerien": "Niger", "nigerian": "Nigeria", "north korean": "North Korea",
    "norwegian": "Norway", "omani": "Oman", "pakistani": "Pakistan",
    "palestinian": "Palestine", "panamanian": "Panama", "papua new guinean": "Papua New Guinea",
    "paraguayan": "Paraguay", "peruvian": "Peru", "polish": "Poland",
    "portuguese": "Portugal", "qatari": "Qatar", "romanian": "Romania",
    "russian": "Russia", "rwandan": "Rwanda", "salvadoran": "El Salvador",
    "samoan": "Samoa", "saudi": "Saudi Arabia", "senegalese": "Senegal",
    "serbian": "Serbia", "seychellois": "Seychelles", "sierra leonean": "Sierra Leone",
    "singaporean": "Singapore", "slovak": "Slovakia", "slovenian": "Slovenia",
    "somali": "Somalia", "south african": "South Africa", "south korean": "South Korea",
    "south sudanese": "South Sudan", "spanish": "Spain", "sri lankan": "Sri Lanka",
    "sudanese": "Sudan", "surinamese": "Suriname", "swazi": "Eswatini",
    "swedish": "Sweden", "swiss": "Switzerland", "syrian": "Syria",
    "taiwanese": "Taiwan", "tajik": "Tajikistan", "tanzanian": "Tanzania",
    "thai": "Thailand", "togolese": "Togo", "tongan": "Tonga",
    "trinidadian": "Trinidad and Tobago", "tunisian": "Tunisia", "turkish": "Turkey",
    "turkmen": "Turkmenistan", "ugandan": "Uganda", "ukrainian": "Ukraine",
    "uruguayan": "Uruguay", "uzbek": "Uzbekistan", "venezuelan": "Venezuela",
    "vietnamese": "Vietnam", "yemeni": "Yemen", "zambian": "Zambia",
    "zimbabwean": "Zimbabwe",
}


def country_for_nationality(nationality: str) -> str:
    """Best-effort demonym -> country name. Falls back to the input, title-cased."""
    key = (nationality or "").strip().lower()
    if key in DEMONYM_TO_COUNTRY:
        return DEMONYM_TO_COUNTRY[key]
    return (nationality or "").strip().title()


# All real country names this module recognises (the demonym table's values).
# Used to cross-check a candidate before it's ever surfaced as a "country" —
# e.g. in Country Profiles — so an unrecognised word (a typo, a stray NLP
# extraction, an unrelated nationality string) never gets shown as if it were
# a real country.
KNOWN_COUNTRIES = set(DEMONYM_TO_COUNTRY.values())

# Case-insensitive lookup back to the canonical casing. NOT built with
# str.title() matching — Python's .title() capitalises every word including
# connectors ("of", "the", "and"), turning "Democratic Republic of the Congo"
# into "Democratic Republic Of The Congo", which then fails to match the
# canonically-cased entry above. Compare lowercased instead.
_COUNTRY_BY_LOWER = {c.lower(): c for c in KNOWN_COUNTRIES}


def canonical_country_name(name: str) -> str | None:
    """Case-insensitive match against KNOWN_COUNTRIES. Returns the
    canonically-cased country name, or None if not recognised."""
    return _COUNTRY_BY_LOWER.get((name or "").strip().lower())


def resolve_known_country(nationality: str) -> str | None:
    """Like country_for_nationality(), but returns None instead of guessing
    when the input isn't a recognised demonym AND isn't already a real
    country name verbatim (e.g. someone entered "Nigeria" directly instead
    of "Nigerian"). Use this wherever a value must be a *validated* country
    — e.g. before it's added as a Country Profiles card."""
    key = (nationality or "").strip().lower()
    if key in DEMONYM_TO_COUNTRY:
        return DEMONYM_TO_COUNTRY[key]
    return canonical_country_name(nationality)


def nationalities_for_country(country: str, known_nationalities: list[str]) -> list[str]:
    """Given a country name and the distinct nationality values present in the DB,
    return the subset of those nationality values that map to that country."""
    target = (country or "").strip().lower()
    return [n for n in known_nationalities if country_for_nationality(n).lower() == target]
