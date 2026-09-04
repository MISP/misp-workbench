from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.auth import auth
from app.repositories import analyst_data as analyst_data_repository
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


WRITE_OPENSEARCH_PATCH = "app.repositories.analyst_data.get_opensearch_client"


class TestAnalystDataWrites(ApiTester):
    """
    Writes go through the real repository against the live index, so the parent
    resolution and the event_uuid denormalisation are actually exercised.
    """

    # ── POST /analyst-data/notes ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    def test_create_note_on_event(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        response = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "A note added from the UI",
                "language": "en",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED
        created = response.json()

        assert created["analyst_type"] == "Note"
        assert created["note"] == "A note added from the UI"
        assert created["object_uuid"] == str(event_1.uuid)
        # denormalised so the event scoped read finds it
        assert created["event_uuid"] == str(event_1.uuid)
        assert created["deleted"] is False
        # authorship comes from the token, never the request body
        assert created["authors"] is not None

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    def test_create_note_on_attribute_inherits_event_uuid(
        self, client: TestClient, auth_token: auth.Token, event_1, attribute_1
    ):
        response = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(attribute_1.uuid),
                "object_type": "Attribute",
                "note": "Attribute level note",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED
        created = response.json()

        assert created["object_type"] == "Attribute"
        # resolved from the attribute, so the event read returns it too
        assert created["event_uuid"] == str(event_1.uuid)

    @pytest.mark.parametrize("scopes", [["analyst_data:create", "analyst_data:read"]])
    def test_create_reply_inherits_event_from_parent_note(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        parent = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "Parent note",
            },
            headers={"Authorization": "Bearer " + auth_token},
        ).json()

        reply = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": parent["uuid"],
                "object_type": "Note",
                "note": "A reply",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert reply.status_code == status.HTTP_201_CREATED
        assert reply.json()["object_type"] == "Note"
        assert reply.json()["event_uuid"] == str(event_1.uuid)

        # and it comes back nested under its parent
        threads = client.get(
            f"/analyst-data/events/{event_1.uuid}",
            headers={"Authorization": "Bearer " + auth_token},
        ).json()
        parent_thread = next(n for n in threads["notes"] if n["uuid"] == parent["uuid"])
        assert [n["uuid"] for n in parent_thread["notes"]] == [reply.json()["uuid"]]

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    def test_create_note_on_missing_parent_is_404(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": "00000000-0000-0000-0000-000000000000",
                "object_type": "Event",
                "note": "Orphan",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    def test_create_note_rejects_empty_text(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        response = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("scopes", [[]])
    def test_create_note_unauthorized(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        response = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "nope",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── POST /analyst-data/opinions ───────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    def test_create_opinion(self, client: TestClient, auth_token: auth.Token, event_1):
        response = client.post(
            "/analyst-data/opinions",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "opinion": 75,
                "comment": "Broadly agree",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["opinion"] == 75
        assert response.json()["analyst_type"] == "Opinion"

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    @pytest.mark.parametrize("opinion", [-1, 101])
    def test_create_opinion_rejects_out_of_range(
        self, client: TestClient, auth_token: auth.Token, event_1, opinion
    ):
        response = client.post(
            "/analyst-data/opinions",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "opinion": opinion,
                "comment": "out of range",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ── POST /analyst-data/relationships ──────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:create"]])
    def test_create_relationship(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        response = client.post(
            "/analyst-data/relationships",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "related_object_uuid": "988ce14e-0802-4aa3-92ca-8ca1104e0b38",
                "related_object_type": "Event",
                "relationship_type": "related-to",
            },
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["relationship_type"] == "related-to"
        assert response.json()["analyst_type"] == "Relationship"

    # ── PUT /analyst-data/{uuid} ──────────────────────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:create", "analyst_data:update"]])
    def test_update_note(self, client: TestClient, auth_token: auth.Token, event_1):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "before",
                "language": "en",
            },
            headers=headers,
        ).json()

        response = client.put(
            f"/analyst-data/{created['uuid']}",
            json={"note": "after"},
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        updated = response.json()
        assert updated["note"] == "after"
        # a partial update must not blank the fields it omits
        assert updated["language"] == "en"
        assert updated["modified"] != created["modified"]

    @pytest.mark.parametrize("scopes", [["analyst_data:create", "analyst_data:update"]])
    def test_update_rejects_a_field_from_another_type(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "a note",
            },
            headers=headers,
        ).json()

        # opinion belongs to an Opinion, not a Note
        response = client.put(
            f"/analyst-data/{created['uuid']}",
            json={"opinion": 50},
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("scopes", [["analyst_data:update"]])
    def test_update_unknown_uuid_is_404(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.put(
            "/analyst-data/00000000-0000-0000-0000-000000000000",
            json={"note": "nope"},
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ── DELETE /analyst-data/{uuid} ───────────────────────────────────────────

    @pytest.mark.parametrize(
        "scopes",
        [["analyst_data:create", "analyst_data:delete", "analyst_data:read"]],
    )
    def test_delete_note_also_deletes_its_replies(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        parent = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "parent",
            },
            headers=headers,
        ).json()
        reply = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": parent["uuid"],
                "object_type": "Note",
                "note": "reply",
            },
            headers=headers,
        ).json()

        response = client.delete(f"/analyst-data/{parent['uuid']}", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # both are gone from the threaded read, not just the parent
        remaining = client.get(
            f"/analyst-data/events/{event_1.uuid}", headers=headers
        ).json()
        surviving = {n["uuid"] for n in remaining["notes"]}
        assert parent["uuid"] not in surviving
        assert reply["uuid"] not in surviving

    @pytest.mark.parametrize("scopes", [["analyst_data:delete"]])
    def test_delete_unknown_uuid_is_404(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.delete(
            "/analyst-data/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ── GET /analyst-data/events/{event_uuid}/counts ──────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:create", "analyst_data:read"]])
    def test_counts_are_keyed_by_object_and_include_replies(
        self, client: TestClient, auth_token: auth.Token, event_1, attribute_1
    ):
        headers = {"Authorization": "Bearer " + auth_token}

        # The OpenSearch cleanup runs at class teardown, not between tests, so
        # earlier tests in this class have already left analyst data on this
        # event. Assert on the delta rather than on absolute totals.
        before = client.get(
            f"/analyst-data/events/{event_1.uuid}/counts", headers=headers
        ).json()

        parent = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "event note",
            },
            headers=headers,
        ).json()
        client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": parent["uuid"],
                "object_type": "Note",
                "note": "a reply",
            },
            headers=headers,
        )
        client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(attribute_1.uuid),
                "object_type": "Attribute",
                "note": "attribute note",
            },
            headers=headers,
        )

        response = client.get(
            f"/analyst-data/events/{event_1.uuid}/counts", headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        after = response.json()

        # the note and its reply both land on the event's total, so a long
        # thread does not badge as "1"
        assert after[str(event_1.uuid)] - before.get(str(event_1.uuid), 0) == 2
        # the attribute is keyed separately, which is what badges its row
        assert after[str(attribute_1.uuid)] - before.get(str(attribute_1.uuid), 0) == 1
        # a reply is counted inside its thread rather than getting its own key
        assert parent["uuid"] not in after

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_counts_unknown_event_is_404(
        self, client: TestClient, auth_token: auth.Token
    ):
        response = client.get(
            "/analyst-data/events/00000000-0000-0000-0000-000000000000/counts",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("scopes", [[]])
    def test_counts_unauthorized(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        response = client.get(
            f"/analyst-data/events/{event_1.uuid}/counts",
            headers={"Authorization": "Bearer " + auth_token},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ── GET /analyst-data/relationship-types ──────────────────────────────────

    @pytest.mark.parametrize("scopes", [["analyst_data:read"]])
    def test_get_relationship_types(self, client: TestClient, auth_token: auth.Token):
        response = client.get(
            "/analyst-data/relationship-types",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == status.HTTP_200_OK
        types = response.json()
        assert len(types) > 0
        assert {"name", "description"} <= set(types[0])


FOREIGN_ORG_UUID = "99999999-9999-4999-8999-999999999999"


def _reassign_org(analyst_uuid, org_uuid):
    """
    Move a document to another organisation, straight in the index.

    Creating a second organisation with its own user and token would be a lot
    of fixture for what the ownership check actually reads: the org uuid on
    the document.
    """
    from app.repositories.sync import ANALYST_DATA_INDEX
    from app.services.opensearch import get_opensearch_client

    client = get_opensearch_client()
    document = client.get(index=ANALYST_DATA_INDEX, id=analyst_uuid)["_source"]
    document["org_uuid"] = org_uuid
    document["orgc_uuid"] = org_uuid
    client.index(index=ANALYST_DATA_INDEX, id=analyst_uuid, body=document, refresh=True)


def _is_deleted(analyst_uuid):
    from app.repositories.sync import ANALYST_DATA_INDEX
    from app.services.opensearch import get_opensearch_client

    client = get_opensearch_client()
    return client.get(index=ANALYST_DATA_INDEX, id=analyst_uuid)["_source"]["deleted"]


class TestAnalystDataOwnership(ApiTester):
    """
    Analyst data is attributed content, so only the creating organisation may
    change it -- which also stops analyst data pulled from a remote server
    being rewritten locally.
    """

    @pytest.mark.parametrize("scopes", [["analyst_data:create", "analyst_data:update"]])
    def test_update_another_orgs_analyst_data_is_403(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "owned elsewhere",
            },
            headers=headers,
        ).json()

        _reassign_org(created["uuid"], FOREIGN_ORG_UUID)

        response = client.put(
            f"/analyst-data/{created['uuid']}",
            json={"note": "rewritten"},
            headers=headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("scopes", [["analyst_data:create", "analyst_data:delete"]])
    def test_delete_another_orgs_analyst_data_is_403(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        created = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "owned elsewhere",
            },
            headers=headers,
        ).json()

        _reassign_org(created["uuid"], FOREIGN_ORG_UUID)

        response = client.delete(f"/analyst-data/{created['uuid']}", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert _is_deleted(created["uuid"]) is False

    @pytest.mark.parametrize(
        "scopes",
        [["analyst_data:create", "analyst_data:delete", "analyst_data:read"]],
    )
    def test_delete_keeps_another_orgs_reply(
        self, client: TestClient, auth_token: auth.Token, event_1
    ):
        headers = {"Authorization": "Bearer " + auth_token}
        parent = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": str(event_1.uuid),
                "object_type": "Event",
                "note": "my note",
            },
            headers=headers,
        ).json()
        mine = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": parent["uuid"],
                "object_type": "Note",
                "note": "my reply",
            },
            headers=headers,
        ).json()
        theirs = client.post(
            "/analyst-data/notes",
            json={
                "object_uuid": parent["uuid"],
                "object_type": "Note",
                "note": "their reply",
            },
            headers=headers,
        ).json()

        _reassign_org(theirs["uuid"], FOREIGN_ORG_UUID)

        response = client.delete(f"/analyst-data/{parent['uuid']}", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # the thread goes, but another org's reply is not collateral damage
        assert _is_deleted(parent["uuid"]) is True
        assert _is_deleted(mine["uuid"]) is True
        assert _is_deleted(theirs["uuid"]) is False


class TestCanModify:
    """Unit coverage for the ownership rule itself."""

    def _user(self, org_uuid, scopes, email="analyst@local"):
        return SimpleNamespace(
            email=email,
            organisation=SimpleNamespace(uuid=org_uuid) if org_uuid else None,
            role=SimpleNamespace(scopes=scopes),
        )

    def test_admin_may_modify_anything(self):
        document = {"orgc_uuid": FOREIGN_ORG_UUID, "authors": "someone@else"}
        user = self._user("11111111-1111-4111-8111-111111111111", ["*"])

        assert analyst_data_repository.can_modify(document, user) is True

    def test_same_org_may_modify(self):
        org = "11111111-1111-4111-8111-111111111111"
        document = {"orgc_uuid": org, "authors": "someone@else"}
        user = self._user(org, ["analyst_data:update"])

        assert analyst_data_repository.can_modify(document, user) is True

    def test_other_org_may_not_modify(self):
        document = {"orgc_uuid": FOREIGN_ORG_UUID, "authors": "someone@else"}
        user = self._user(
            "11111111-1111-4111-8111-111111111111", ["analyst_data:update"]
        )

        assert analyst_data_repository.can_modify(document, user) is False

    def test_org_falls_back_to_org_uuid(self):
        org = "11111111-1111-4111-8111-111111111111"
        document = {"orgc_uuid": None, "org_uuid": org}
        user = self._user(org, ["analyst_data:update"])

        assert analyst_data_repository.can_modify(document, user) is True

    def test_without_an_org_the_author_may_modify(self):
        document = {"authors": "analyst@local"}
        user = self._user(
            "11111111-1111-4111-8111-111111111111", ["analyst_data:update"]
        )

        assert analyst_data_repository.can_modify(document, user) is True

    def test_without_an_org_a_non_author_may_not(self):
        document = {"authors": "someone@else"}
        user = self._user(
            "11111111-1111-4111-8111-111111111111", ["analyst_data:update"]
        )

        assert analyst_data_repository.can_modify(document, user) is False

    def test_unattributed_data_is_not_modifiable(self):
        # no org, no author: fail closed rather than open to everyone
        user = self._user(
            "11111111-1111-4111-8111-111111111111", ["analyst_data:update"]
        )

        assert analyst_data_repository.can_modify({}, user) is False
