from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.tests.api_tester import ApiTester
from fastapi import status
from fastapi.testclient import TestClient

OPENSEARCH_PATCH = "app.repositories.analyst_data.get_opensearch_client"

EVENT_UUID = "572503da-c87f-4520-a9bc-8de08b9c92e5"
ATTRIBUTE_UUID = "e437b43c-8b13-4599-9ccf-f31c61007dd2"
NOTE_UUID = "a1b11111-1111-4111-8111-111111111111"
REPLY_UUID = "a1b22222-2222-4222-8222-222222222222"
NESTED_OPINION_UUID = "a1b33333-3333-4333-8333-333333333333"
OPINION_UUID = "a1b44444-4444-4444-8444-444444444444"
RELATIONSHIP_UUID = "a1b55555-5555-4555-8555-555555555555"
ATTRIBUTE_NOTE_UUID = "a1b66666-6666-4666-8666-666666666666"


def _document(uuid, analyst_type, object_uuid, object_type, event_uuid, **extra):
    document = {
        "uuid": uuid,
        "analyst_type": analyst_type,
        "object_uuid": object_uuid,
        "object_type": object_type,
        "event_uuid": event_uuid,
        "authors": "analyst@remote.test",
        "created": "2022-06-09T10:00:00",
        "modified": "2022-06-09T10:00:00",
        "distribution": 1,
        "deleted": False,
    }
    document.update(extra)
    return document


def event_documents(event_uuid):
    """
    One event note carrying a reply and an opinion, plus an event level opinion
    and relationship, and a note on one of the event's attributes.
    """
    return [
        _document(
            NOTE_UUID, "Note", event_uuid, "Event", event_uuid, note="Event level note"
        ),
        _document(
            REPLY_UUID, "Note", NOTE_UUID, "Note", event_uuid, note="Reply to the note"
        ),
        _document(
            NESTED_OPINION_UUID,
            "Opinion",
            NOTE_UUID,
            "Note",
            event_uuid,
            opinion=90,
            comment="Opinion on the note",
        ),
        _document(
            OPINION_UUID,
            "Opinion",
            event_uuid,
            "Event",
            event_uuid,
            opinion=75,
            comment="Event level opinion",
        ),
        _document(
            RELATIONSHIP_UUID,
            "Relationship",
            event_uuid,
            "Event",
            event_uuid,
            related_object_uuid="988ce14e-0802-4aa3-92ca-8ca1104e0b38",
            related_object_type="Event",
            relationship_type="related-to",
        ),
        _document(
            ATTRIBUTE_NOTE_UUID,
            "Note",
            ATTRIBUTE_UUID,
            "Attribute",
            event_uuid,
            note="Attribute level note",
        ),
    ]


def make_opensearch_mock(documents):
    """
    Return the documents whose object_uuid matches the query, so the thread
    assembly in the repository is exercised rather than stubbed out.
    """

    def search(index, body):
        query = body["query"]["bool"]["must"][0]
        term = query.get("term", {}).get("object_uuid")
        terms = query.get("terms", {}).get("object_uuid")
        event = query.get("term", {}).get("event_uuid")

        if event is not None:
            matched = [d for d in documents if d["event_uuid"] == event]
        elif term is not None:
            matched = [d for d in documents if d["object_uuid"] == term]
        else:
            matched = [d for d in documents if d["object_uuid"] in (terms or [])]

        return {"hits": {"hits": [{"_source": d} for d in matched]}}

    return MagicMock(search=MagicMock(side_effect=search))


class TestAnalystDataResource(ApiTester):
    # ── GET /analyst-data/events/{event_uuid} ─────────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_get_event_analyst_data(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        documents = event_documents(str(event_1.uuid))
        with patch(OPENSEARCH_PATCH, return_value=make_opensearch_mock(documents)):
            response = client.get(
                f"/analyst-data/events/{event_1.uuid}",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # only the event level analyst data is at the top of the response
        assert [n["uuid"] for n in data["notes"]] == [NOTE_UUID]
        assert [o["uuid"] for o in data["opinions"]] == [OPINION_UUID]
        assert [r["uuid"] for r in data["relationships"]] == [RELATIONSHIP_UUID]

        # the reply and the opinion on the note come back nested under it
        event_note = data["notes"][0]
        assert [n["uuid"] for n in event_note["notes"]] == [REPLY_UUID]
        assert [o["uuid"] for o in event_note["opinions"]] == [NESTED_OPINION_UUID]
        assert event_note["data"]["note"] == "Event level note"

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_get_event_analyst_data_unknown_event(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/analyst-data/events/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_event_analyst_data_unauthorized(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        response = client.get(
            f"/analyst-data/events/{event_1.uuid}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /analyst-data/events/{event_uuid}/all ─────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_get_all_event_analyst_data_is_flat(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        documents = event_documents(str(event_1.uuid))
        with patch(OPENSEARCH_PATCH, return_value=make_opensearch_mock(documents)):
            response = client.get(
                f"/analyst-data/events/{event_1.uuid}/all",
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # every document for the event, attribute level ones included
        assert len(data) == len(documents)
        assert ATTRIBUTE_NOTE_UUID in {d["uuid"] for d in data}

    # ── GET /analyst-data/objects/{object_uuid} ───────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_get_object_analyst_data(self, client: TestClient, auth_token: auth.Token):
        with patch(
            OPENSEARCH_PATCH,
            return_value=make_opensearch_mock(event_documents(EVENT_UUID)),
        ):
            response = client.get(
                f"/analyst-data/objects/{ATTRIBUTE_UUID}",
                params={"object_type": "Attribute"},
                headers={"Authorization": "Bearer " + auth_token},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert [n["uuid"] for n in data["notes"]] == [ATTRIBUTE_NOTE_UUID]
        assert data["opinions"] == []
        assert data["relationships"] == []

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_get_object_analyst_data_rejects_unknown_object_type(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            f"/analyst-data/objects/{ATTRIBUTE_UUID}",
            params={"object_type": "NotAThing"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [[]])
    def test_get_object_analyst_data_unauthorized(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            f"/analyst-data/objects/{ATTRIBUTE_UUID}",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
