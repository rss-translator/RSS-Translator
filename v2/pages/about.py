"""The about page."""

from .. import styles
from ..templates import template

import reflex as rx


@template(route="/about", title="About")
def about() -> rx.Component:
    """The about page.

    Returns:
        The UI for the about page.
    """
    with open("README.md", encoding="utf-8") as readme:
        content = readme.read()
    return rx.markdown(content, component_map=styles.markdown_style)
