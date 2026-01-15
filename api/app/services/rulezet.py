import requests

RulezetClient = requests.Session()


def lookup(vuln_id: str) -> dict:

    vuln_id = vuln_id.upper()
    detection_data = RulezetClient.get(
        f"https://rulezet.org/api/rule/public/search_rules_by_cve?cve_ids={vuln_id.lower()}"
    ).json()

    if detection_data is None:
        return {"error": "Vulnerability not found"}

    if (
        detection_data["rules"] != {}
        and detection_data["rules"][vuln_id.lower()] is not None
    ):
        return detection_data["rules"][vuln_id.lower()]

    return []
