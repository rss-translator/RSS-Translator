"""The profile page."""

from ..templates import template
from ..components.profile_input import profile_input

import reflex as rx


class Profile(rx.Base):
    name: str = ""
    email: str = ""
    notifications: bool = True


class ProfileState(rx.State):
    profile: Profile = Profile(name="Admin", email="", notifications=True)

    def handle_submit(self, form_data: dict):
        self.profile = Profile(**form_data)
        return rx.toast.success(
            "Profile updated successfully", position="top-center"
        )

    def toggle_notifications(self):
        self.profile.notifications = not self.profile.notifications


@template(route="/profile", title="Profile")
def profile() -> rx.Component:
    """The profile page.

    Returns:
        The UI for the account page.
    """
    return rx.vstack(
        rx.flex(
            rx.vstack(
                rx.hstack(
                    rx.icon("square-user-round"),
                    rx.heading("Personal information", size="5"),
                    align="center",
                ),
                rx.text("Update your personal information.", size="3"),
                width="100%",
            ),
            rx.form.root(
                rx.vstack(
                    profile_input(
                        "Name",
                        "name",
                        "Admin",
                        "text",
                        "user",
                        ProfileState.profile.name,
                    ),
                    profile_input(
                        "Email",
                        "email",
                        "user@reflex.dev",
                        "email",
                        "mail",
                        ProfileState.profile.email,
                    ),
                    rx.button("Update", type="submit", width="100%"),
                    width="100%",
                    spacing="5",
                ),
                on_submit=ProfileState.handle_submit,
                reset_on_submit=True,
                width="100%",
                max_width="325px",
            ),
            width="100%",
            spacing="4",
            flex_direction=["column", "column", "row"],
        ),
        rx.divider(),
        rx.flex(
            rx.vstack(
                rx.hstack(
                    rx.icon("bell"),
                    rx.heading("Notifications", size="5"),
                    align="center",
                ),
                rx.text("Manage your notification settings.", size="3"),
            ),
            rx.checkbox(
                "Receive product updates",
                size="3",
                checked=ProfileState.profile.notifications,
                on_change=ProfileState.toggle_notifications(),
            ),
            width="100%",
            spacing="4",
            justify="between",
            flex_direction=["column", "column", "row"],
        ),
        spacing="6",
        width="100%",
        max_width="800px",
    )
