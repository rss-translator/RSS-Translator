"""The overview page of the app."""

import reflex as rx
from .. import styles
from ..templates import template
from ..views.stats_cards import stats_cards
from ..views.charts import (
    users_chart,
    revenue_chart,
    orders_chart,
    area_toggle,
    pie_chart,
    timeframe_select,
    StatsState,
)
from ..views.adquisition_view import adquisition
from ..components.notification import notification
from ..components.card import card
from .profile import ProfileState
import datetime


def _time_data() -> rx.Component:
    return rx.hstack(
        rx.tooltip(
            rx.icon("info", size=20),
            content=f"{(datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%b %d, %Y')} - {datetime.datetime.now().strftime('%b %d, %Y')}",
        ),
        rx.text("Last 30 days", size="4", weight="medium"),
        align="center",
        spacing="2",
        display=["none", "none", "flex"],
    )


def tab_content_header() -> rx.Component:
    return rx.hstack(
        _time_data(),
        area_toggle(),
        align="center",
        width="100%",
        spacing="4",
    )


@template(route="/", title="Overview", on_load=StatsState.randomize_data)
def index() -> rx.Component:
    """The overview page.

    Returns:
        The UI for the overview page.
    """
    return rx.vstack(
        rx.heading(f"Welcome, {ProfileState.profile.name}", size="5"),
        rx.flex(
            rx.input(
                rx.input.slot(rx.icon("search"), padding_left="0"),
                placeholder="Search here...",
                size="3",
                width="100%",
                max_width="450px",
                radius="large",
                style=styles.ghost_input_style,
            ),
            rx.flex(
                notification("bell", "cyan", 12),
                notification("message-square-text", "plum", 6),
                spacing="4",
                width="100%",
                wrap="nowrap",
                justify="end",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        stats_cards(),
        card(
            rx.hstack(
                tab_content_header(),
                rx.segmented_control.root(
                    rx.segmented_control.item("Users", value="users"),
                    rx.segmented_control.item("Revenue", value="revenue"),
                    rx.segmented_control.item("Orders", value="orders"),
                    margin_bottom="1.5em",
                    default_value="users",
                    on_change=StatsState.set_selected_tab,
                ),
                width="100%",
                justify="between",
            ),
            rx.match(
                StatsState.selected_tab,
                ("users", users_chart()),
                ("revenue", revenue_chart()),
                ("orders", orders_chart()),
            ),
        ),
        rx.grid(
            card(
                rx.hstack(
                    rx.hstack(
                        rx.icon("user-round-search", size=20),
                        rx.text("Visitors Analytics", size="4", weight="medium"),
                        align="center",
                        spacing="2",
                    ),
                    timeframe_select(),
                    align="center",
                    width="100%",
                    justify="between",
                ),
                pie_chart(),
            ),
            card(
                rx.hstack(
                    rx.icon("globe", size=20),
                    rx.text("Acquisition Overview", size="4", weight="medium"),
                    align="center",
                    spacing="2",
                    margin_bottom="2.5em",
                ),
                rx.vstack(
                    adquisition(),
                ),
            ),
            gap="1rem",
            grid_template_columns=[
                "1fr",
                "repeat(1, 1fr)",
                "repeat(2, 1fr)",
                "repeat(2, 1fr)",
                "repeat(2, 1fr)",
            ],
            width="100%",
        ),
        spacing="8",
        width="100%",
    )
