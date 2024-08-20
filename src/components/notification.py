import reflex as rx
from dashboard import styles
from reflex.components.radix.themes.base import (
    LiteralAccentColor,
)


def notification(icon: str, color: LiteralAccentColor, count: int) -> rx.Component:
    return rx.box(
        rx.icon_button(
            rx.icon(icon),
            padding="0.5rem",
            radius="full",
            variant="soft",
            color_scheme=color,
            size="3",
        ),
        rx.badge(
            rx.text(count, size="1"),
            radius="full",
            variant="solid",
            color_scheme=color,
            style=styles.notification_badge_style,
        ),
        position="relative",
    )
