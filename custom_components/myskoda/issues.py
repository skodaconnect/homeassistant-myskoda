"""Issues for the MySkoda HomeAssistant integration."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


def _get_issue_id(issue_type: str, entry_id: str) -> str:
    return f"{issue_type}_{entry_id}"


@callback
def async_create_tnc_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create issue for new terms and conditions."""
    ir.async_create_issue(
        hass=hass,
        domain=DOMAIN,
        issue_id=_get_issue_id("new_tandc", entry_id),
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        learn_more_url="https://skodaid.vwgroup.io/landing-page",
        translation_key="new_tandc",
        data={"entry_id": entry_id},
    )


@callback
def async_delete_tnc_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Remove issue for new terms and conditions."""
    ir.async_delete_issue(
        hass=hass, domain=DOMAIN, issue_id=_get_issue_id("new_tandc", entry_id)
    )


@callback
def async_create_spin_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create issue for incorrect S-PIN."""
    ir.async_create_issue(
        hass=hass,
        domain=DOMAIN,
        issue_id=_get_issue_id("spin_error", entry_id),
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="spin_error",
        data={"entry_id": entry_id},
    )


@callback
def async_delete_spin_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Remove issue for incorrect S-PIN."""
    ir.async_delete_issue(
        hass=hass, domain=DOMAIN, issue_id=_get_issue_id("spin_error", entry_id)
    )
