"""Helpers for the check functions of the example circuits."""


def approx(value, expected, rel=0.01, absol=1e-9, what=""):
    """Assert |value-expected| <= max(rel*|expected|, absol)."""
    tol = max(rel * abs(expected), absol)
    if abs(value - expected) > tol:
        raise AssertionError("%s = %.6g, expected %.6g (tol %.3g)" %
                             (what or "value", value, expected, tol))
    return value
