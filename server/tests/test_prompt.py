from app.lesson.prompt import CHILDREN, system_prompt, template_catalogue
from app.lesson.safe_expr import FUNCTIONS
from app.lesson.templates import TEMPLATES


def test_catalogue_lists_every_template_with_its_parameters() -> None:
    catalogue = template_catalogue()
    assert set(CHILDREN) == set(TEMPLATES)
    for name in TEMPLATES:
        assert f"| {name} |" in catalogue
    assert "n (default 8)" in catalogue
    assert "sign (default +) (+ / -)" in catalogue
    assert "name (optional)" in catalogue


def test_prompt_is_complete_and_static() -> None:
    prompt = system_prompt()
    assert "{template_catalogue}" not in prompt
    assert "| axes_plot |" in prompt
    for function in FUNCTIONS:
        assert function in prompt
    # Prompt caching needs >= 512 tokens; any change must keep the text static (no dates).
    assert len(prompt) > 4 * 512


def test_prompt_carries_the_audit_safeguards() -> None:
    prompt = system_prompt()
    for phrase in (
        "p = 2 q a",
        "full precision",
        "complete swings",
        "not to scale",
        "use `lam` for lambda",
        "not allowed: abs, Min, Max",
    ):
        assert phrase in prompt, phrase
