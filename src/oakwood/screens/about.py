"""About screen showing logo, version, and project URL."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from .. import __version__

LOGO = """\
                                            █▄
             ▄▄                             ██
 ▄███▄ ▄▀▀█▄ ██ ▄█▀▀█▄ █▄ ██▀▄███▄ ▄███▄ ▄████
 ██ ██ ▄█▀██ ████   ██▄██▄██ ██ ██ ██ ██ ██ ██
▄▀███▀▄▀█▄██▄██ ▀█▄  ▀██▀██▀▄▀███▀▄▀███▀▄█▀███"""

PROJECT_URL = "https://oakwood.flpm.dev"


class AboutScreen(Screen):
    """Modal about dialog with logo, version, and project URL."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Display the logo, version, URL, and config path."""
        yield Static(
            f"[#d4a04a]{LOGO}[/#d4a04a]\n\n"
            f"v. {__version__}    YOUR PERSONAL LIBRARY CATALOGUE\n\n"
            f"[#8a7e6a]{PROJECT_URL}[/#8a7e6a]\n\n"
            f"Configuration file: ~/.oakwood/oakwood-settings.json",
            id="about-panel",
        )
        yield Footer()

    def action_go_back(self) -> None:
        """Return to the main screen."""
        self.app.pop_screen()
