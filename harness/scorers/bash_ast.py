"""Small shared entry point for the pinned Tree-sitter Bash parser."""

from __future__ import annotations


class BashParseError(ValueError):
    """A fixed parser failure reason, without source text or parser output."""


def parse_bash(source: str | bytes):
    """Return a valid Bash root node; import parser wheels only when called.

    Consumers can walk Tree-sitter fields and children directly. Syntax recovery
    is never accepted as a successful parse.
    """
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_bash
    except ImportError:
        raise BashParseError("parser_unavailable") from None
    root = Parser(Language(tree_sitter_bash.language())).parse(
        source.encode("utf-8") if isinstance(source, str) else source).root_node
    if root.has_error:
        raise BashParseError("invalid_bash")
    return root
