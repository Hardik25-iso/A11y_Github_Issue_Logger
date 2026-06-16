from backend.app.services.scanner import _criterion, normalize_violations


def test_normalize_violations_maps_axe_output():
    issues = normalize_violations(
        [
            {
                "id": "button-name",
                "impact": "serious",
                "help": "Buttons must have discernible text",
                "helpUrl": "https://dequeuniversity.com/rules/axe/button-name",
                "description": "Ensures buttons have accessible names",
                "tags": ["wcag412", "cat.name-role-value"],
                "nodes": [
                    {
                        "target": ["header", "button.search"],
                        "html": '<button class="search"></button>',
                    },
                    {
                        "target": ["footer", "button.search"],
                        "html": '<button class="search"></button>',
                    },
                ],
            }
        ]
    )
    assert len(issues) == 1
    assert issues[0].severity == "High"
    assert issues[0].wcag_criterion == "4.1.2"
    assert issues[0].occurrences == 2
    assert issues[0].selector == "header button.search"


def test_normalize_violations_handles_sparse_output():
    issue = normalize_violations([{"id": "custom"}])[0]
    assert issue.title == "Accessibility violation"
    assert issue.severity == "Low"
    assert issue.occurrences == 1


def test_normalize_violations_handles_iframe_nested_target():
    """axe-core encodes iframe elements as nested lists in target — must not crash."""
    issues = normalize_violations(
        [
            {
                "id": "button-name",
                "impact": "serious",
                "help": "Buttons must have discernible text",
                "tags": ["wcag412"],
                "nodes": [
                    {
                        "target": [["iframe#modal", "#submit-btn"]],
                        "html": "<button></button>",
                    }
                ],
            }
        ]
    )
    assert len(issues) == 1
    assert "iframe#modal" in issues[0].selector
    assert "#submit-btn" in issues[0].selector


def test_normalize_violations_truncates_long_html():
    long_html = "<div " + "x" * 400 + "></div>"
    issues = normalize_violations(
        [{"id": "html-has-lang", "impact": "serious", "tags": ["wcag311"], "nodes": [{"target": [], "html": long_html}]}]
    )
    assert len(issues[0].element) <= 300


def test_criterion_three_digit():
    assert _criterion(["wcag412"]) == "4.1.2"
    assert _criterion(["wcag111"]) == "1.1.1"
    assert _criterion(["wcag244"]) == "2.4.4"


def test_criterion_four_digit_wcag22():
    """WCAG 2.2 added criteria 2.4.10–2.4.13; tags are 8 chars like wcag2410."""
    assert _criterion(["wcag2410"]) == "2.4.10"
    assert _criterion(["wcag2411"]) == "2.4.11"
    assert _criterion(["wcag2412"]) == "2.4.12"
    assert _criterion(["wcag2413"]) == "2.4.13"


def test_criterion_falls_back_for_unrecognised_tags():
    assert _criterion(["cat.text-alternatives", "best-practice"]) == "4.1.2"
    assert _criterion([]) == "4.1.2"


def test_normalize_violations_empty_nodes():
    issues = normalize_violations(
        [{"id": "color-contrast", "impact": "serious", "tags": ["wcag143"], "nodes": []}]
    )
    assert issues[0].element == ""
    assert issues[0].selector == ""
    assert issues[0].occurrences == 1
