from security_words import looks_like_shell
from intrinsic_valuation import classify_security


def test_aerospace_and_shell_plc_are_not_shells():
    for name, industry in [("GE Aerospace", "Aerospace & Defense"), ("The Boeing Company", "Aerospace & Defense"),
                           ("Howmet Aerospace Inc.", "Aerospace & Defense"), ("Shell plc", "Oil & Gas Integrated"),
                           ("SpaceX Holdings", "Aerospace & Defense")]:
        assert not looks_like_shell(name, industry), name


def test_real_shells_still_match():
    assert looks_like_shell("Churchill Capital Corp VII", "Shell Companies")
    assert looks_like_shell("Some Acquisition Corp", "Blank Check")
    assert looks_like_shell("XYZ SPAC Inc", "")


def test_classifier_keeps_aerospace_as_operating_company():
    info = {"quoteType": "EQUITY", "longName": "Lockheed Martin Corporation", "sector": "Industrials", "industry": "Aerospace & Defense"}
    assert classify_security("LMT", info, True) != "SPAC_OR_SHELL"
    shell = {"quoteType": "EQUITY", "longName": "Churchill Capital Corp VII", "sector": "Financial Services", "industry": "Shell Companies"}
    assert classify_security("CVII", shell, True) == "SPAC_OR_SHELL"
