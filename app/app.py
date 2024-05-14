"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config


class State(rx.State):
    """The app state."""

    stag_ticket: str = ""


def index() -> rx.Component:
    return rx.container(
        rx.heading("STAG výkazy V", size="9", padding="10px"),
        
    )


app = rx.App()
app.add_page(index)
