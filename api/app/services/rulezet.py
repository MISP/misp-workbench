import requests

RulezetClient = requests.Session()


def lookup(vuln_id: str) -> dict:

    detection_data = RulezetClient.get(
        f"https://rulezet.org/api/rule/public/search_rules_by_cve?cve_ids={vuln_id.lower()}"
    ).json()

    if detection_data is None:
        return {"error": "Vulnerability not found"}

    if (
        "results" in detection_data
    ):
        return detection_data["results"]

    return []
