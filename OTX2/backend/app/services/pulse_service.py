from typing import Any

from app.services.otx_client import OTXClient


def normalize_pulse(pulse: dict[str, Any]) -> dict[str, Any]:
    targeted_countries = (
        pulse.get("targeted_countries")
        or pulse.get("targeted_country")
        or pulse.get("countries")
        or pulse.get("country")
        or []
    )
    if isinstance(targeted_countries, str):
        targeted_countries = [targeted_countries]

    adversary = (
        pulse.get("adversary")
        or pulse.get("adversaries")
        or pulse.get("threat_actor")
        or pulse.get("actor")
    )
    if isinstance(adversary, list):
        adversary = ", ".join(str(item) for item in adversary if item)

    return {
        "id": pulse.get("id"),
        "name": pulse.get("name"),
        "description": pulse.get("description"),
        "author_name": pulse.get("author_name") or pulse.get("author", {}).get("username"),
        "created": pulse.get("created"),
        "modified": pulse.get("modified"),
        "tags": pulse.get("tags", []),
        "TLP": pulse.get("TLP"),
        "attack_ids": pulse.get("attack_ids", []),
        "malware_families": pulse.get("malware_families", []),
        "references": pulse.get("references", []),
        "adversary": adversary,
        "targeted_countries": targeted_countries,
        "indicator_count": pulse.get("indicator_count", len(pulse.get("indicators", []))),
    }


class PulseService:
    def __init__(self, otx_client: OTXClient) -> None:
        self.otx_client = otx_client

    def search(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        result = self.otx_client.search_pulses(query=query, max_results=limit)
        return [normalize_pulse(item) for item in result.get("results", [])]

    def get_details(self, pulse_id: str) -> dict[str, Any]:
        return normalize_pulse(self.otx_client.get_pulse_details(pulse_id))

    def get_indicators(self, pulse_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        return self.otx_client.get_pulse_indicators(pulse_id, limit=limit)
