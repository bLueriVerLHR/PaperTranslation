"""Tests for the MathML recovery in :mod:`tools.web`.

The web extractor does not parse LaTeX: it walks the SVG a MathJax renderer already
produced and rebuilds the MathML tree from it. Two structural traps in that walk used to
wreck almost every recovered equation on the page:

* a ``TeXAtom`` grouping atom was emitted as ``mi``, so its children ended up inside a
  token element and the browser laid them out one per line;
* an anonymous ``<g>`` layout group was skipped, which dropped a radical's radicand and a
  ``menclose``'s struck term.

Both are covered here with hand-built fragments shaped exactly like the renderer's.
"""

from __future__ import annotations

from tools import web


def _container(inner: str) -> web.Element:
    """Wrap a ``math`` group in the site's container markup, as the fetcher sees it."""
    html = (
        '<mjx-container class="MathJax" jax="SVG"><svg>'
        f'<g data-mml-node="math">{inner}</g></svg></mjx-container>'
    )
    return web.parse(html).find_all("mjx-container")[0]


def _use(codepoint: str) -> str:
    """One glyph reference, as the SVG carries it."""
    return f'<use data-c="{codepoint}">'


def _token(name: str, codepoints: list[str]) -> str:
    """A token element holding the given glyphs."""
    return f'<g data-mml-node="{name}">' + "".join(_use(c) for c in codepoints) + "</g>"


def _text(codepoints: list[str]) -> str:
    """A ``text`` run, which the renderer uses for written-out operators."""
    return '<g data-mml-node="text">' + "".join(_use(c) for c in codepoints) + "</g>"


_OPEN = _token("mo", ["28"])
_CLOSE = _token("mo", ["29"])
_ITALIC_J = _token("mi", ["1D457"])
_BOLD_K = _token("mi", ["1D40A"])
_HEAD = _token("mtext", [f"{ord(c):X}" for c in "head"])


def test_grouping_atom_becomes_a_row_not_a_token() -> None:
    """A ``TeXAtom`` is the renderer's ``mrow``; emitting it as ``mi`` stacks its children."""
    inner = '<g data-mml-node="TeXAtom">' + _OPEN + _ITALIC_J + _CLOSE + "</g>"
    assert web.container_to_mathml(_container(inner)) == (
        '<math><mrow><mo>(</mo><mi mathvariant="italic">j</mi><mo>)</mo></mrow></math>'
    )


def test_superscript_over_a_grouping_atom_stays_inline() -> None:
    """The idiom in the Flash Attention text: ``K`` raised to a parenthesised ``(j)``."""
    inner = (
        '<g data-mml-node="msup">'
        + _BOLD_K
        + '<g data-mml-node="TeXAtom">'
        + _OPEN
        + _ITALIC_J
        + _CLOSE
        + "</g></g>"
    )
    assert web.container_to_mathml(_container(inner)) == (
        '<math><msup><mi mathvariant="bold">K</mi>'
        '<mrow><mo>(</mo><mi mathvariant="italic">j</mi><mo>)</mo></mrow>'
        "</msup></math>"
    )


def test_radical_keeps_the_radicand_from_the_anonymous_group() -> None:
    """A radical's radicand sits beside the sign inside a group carrying no node name."""
    inner = (
        '<g data-mml-node="msqrt"><g>'
        '<g data-mml-node="msub">'
        + _token("mi", ["1D451"])
        + _HEAD
        + "</g></g>"
        + _token("mo", ["221A"])
        + "<rect/></g>"
    )
    assert web.container_to_mathml(_container(inner)) == (
        '<math><msqrt><msub><mi mathvariant="italic">d</mi>'
        "<mtext>head</mtext></msub></msqrt></math>"
    )


def test_radical_does_not_keep_a_duplicate_sign() -> None:
    """MathML draws the sign itself, so the renderer's glyph must not be copied in."""
    inner = '<g data-mml-node="msqrt"><g>' + "</g>" + _token("mo", ["221A"]) + "</g>"
    emitted = web.container_to_mathml(_container(inner))
    assert "\u221a" not in emitted
    assert emitted == "<math><msqrt/></math>"


def test_menclose_keeps_the_struck_term() -> None:
    """An emptied ``menclose`` renders as nothing at all, losing the cancelled term."""
    inner = (
        '<g data-mml-node="menclose"><g><g data-mml-node="msup">'
        + _BOLD_K
        + '<g data-mml-node="TeXAtom">'
        + _OPEN
        + _ITALIC_J
        + _CLOSE
        + "</g></g></g>"
        '<line x1="0" y1="0" x2="10" y2="10" stroke-width="67"/></g>'
    )
    assert web.container_to_mathml(_container(inner)) == (
        '<math><menclose notation="updiagonalstrike"><msup><mi mathvariant="bold">K</mi>'
        '<mrow><mo>(</mo><mi mathvariant="italic">j</mi><mo>)</mo></mrow>'
        "</msup></menclose></math>"
    )


def test_strike_direction_follows_the_drawn_line() -> None:
    """The renderer strokes the line instead of writing ``notation``, so read it off."""
    rising = '<line x1="0" y1="0" x2="10" y2="10"/>'
    falling = '<line x1="0" y1="10" x2="10" y2="0"/>'
    for drawn, expected in ((rising, "updiagonalstrike"), (falling, "downdiagonalstrike")):
        inner = f'<g data-mml-node="menclose">{_BOLD_K}<g>{drawn}</g></g>'
        assert web.container_to_mathml(_container(inner)) == (
            f'<math><menclose notation="{expected}"><mi mathvariant="bold">K</mi></menclose></math>'
        )


def test_a_menclose_that_was_not_struck_is_left_unadorned() -> None:
    """A box or circle is not a cancellation; inventing a strike would be a claim."""
    inner = f'<g data-mml-node="menclose">{_BOLD_K}<rect width="10" height="10"/></g>'
    assert web.container_to_mathml(_container(inner)) == (
        '<math><menclose><mi mathvariant="bold">K</mi></menclose></math>'
    )


def test_multiple_text_runs_collapse_into_the_operator() -> None:
    """``:=`` arrives as two text runs in one ``mo``; as elements they would stack."""
    inner = '<g data-mml-node="mo">' + _text(["3A"]) + _text(["3D"]) + "</g>"
    assert web.container_to_mathml(_container(inner)) == "<math><mo>:=</mo></math>"


def test_ordinary_token_keeps_its_own_text() -> None:
    """The token path must stay intact: a plain ``mi`` is text, not a container."""
    assert web.container_to_mathml(_container(_BOLD_K + _OPEN)) == (
        '<math><mi mathvariant="bold">K</mi><mo>(</mo></math>'
    )


def test_container_without_math_root_emits_nothing() -> None:
    """A container holding no ``math`` group is "nothing to emit", not an error."""
    node = web.parse("<mjx-container><svg><g></g></svg></mjx-container>")
    assert web.container_to_mathml(node.find_all("mjx-container")[0]) == ""
