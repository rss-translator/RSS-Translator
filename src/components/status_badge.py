import reflex as rx


def _badge(status: str):
    badge_mapping = {
        "Completed": ("check", "Completed", "green"),
        "Pending": ("loader", "Pending", "yellow"),
        "Canceled": ("ban", "Canceled", "red"),
    }
    icon, text, color_scheme = badge_mapping.get(
        status, ("loader", "Pending", "yellow")
    )
    return rx.badge(
        rx.icon(icon, size=16),
        text,
        color_scheme=color_scheme,
        radius="large",
        variant="surface",
        size="2",
    )


def status_badge(status: str):
    return rx.match(
        status,
        ("Completed", _badge("Completed")),
        ("Pending", _badge("Pending")),
        ("Canceled", _badge("Canceled")),
        _badge("Pending"),
    )
