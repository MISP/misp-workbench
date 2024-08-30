feed_new_event_manifest = {
    "988ce14e-0802-4aa3-92ca-8ca1104e0b38": {
        "Orgc": {"name": "CIRCL", "uuid": "22bdfb84-98d9-468c-aba4-986e63ffea62"},
        "Tag": [
            {
                "colour": "#004646",
                "local": False,
                "name": "type:OSINT",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:white",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:clear",
                "relationship_type": "",
            },
        ],
        "info": "Test Feed Event",
        "date": "2024-08-27",
        "analysis": 0,
        "threat_level_id": 3,
        "timestamp": 1724753268,
    }
}


feed_new_event = {
    "Event": {
        "analysis": "0",
        "date": "2024-08-27",
        "extends_uuid": "",
        "info": "Test Feed Event",
        "publish_timestamp": "1724758165",
        "published": True,
        "threat_level_id": "3",
        "timestamp": "1724753268",
        "uuid": "988ce14e-0802-4aa3-92ca-8ca1104e0b38",
        "Orgc": {"name": "CIRCL", "uuid": "22bdfb84-98d9-468c-aba4-986e63ffea62"},
        "Tag": [
            {
                "colour": "#004646",
                "local": False,
                "name": "type:OSINT",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:white",
                "relationship_type": "",
            },
            {
                "colour": "#ffffff",
                "local": False,
                "name": "tlp:clear",
                "relationship_type": "",
            },
        ],
        "Attribute": [
            {
                "category": "Payload delivery",
                "comment": "Original RAR file",
                "deleted": False,
                "disable_correlation": False,
                "timestamp": "1724749019",
                "to_ids": True,
                "type": "sha1",
                "uuid": "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                "value": "7edc546f741eff3e13590a62ce2856bb39d8f71d",
                "Tag": [
                    {
                        "colour": "#004646",
                        "local": False,
                        "name": "tlp:red",
                        "relationship_type": "",
                    },
                ],
            }
        ],
        "Object": [
            {
                "comment": "Malicious account posting malicious links (compromise?)",
                "deleted": False,
                "description": "GitHub user",
                "meta-category": "misc",
                "name": "github-user",
                "template_uuid": "4329b5e6-8e6a-4b55-8fd1-9033782017d4",
                "template_version": "3",
                "timestamp": "1724749149",
                "uuid": "df23d3be-1179-4824-ac03-471f0bc6d92d",
                "ObjectReference": [
                    {
                        "comment": "",
                        "object_uuid": "df23d3be-1179-4824-ac03-471f0bc6d92d",
                        "referenced_uuid": "317e63e6-b95d-4dd1-b4fd-de2f64f33fd8",
                        "relationship_type": "mentions",
                        "timestamp": "1724749149",
                        "uuid": "d7e57f39-4dd5-4b87-b040-75561fa8289e",
                    }
                ],
                "Attribute": [
                    {
                        "category": "Social network",
                        "comment": "",
                        "deleted": False,
                        "disable_correlation": False,
                        "object_relation": "username",
                        "timestamp": "1724748475",
                        "to_ids": False,
                        "type": "github-username",
                        "uuid": "8be7a04d-c10b-4ef6-854f-2072e67f6cd5",
                        "value": "Foobar12345",
                    }
                ],
            },
        ],
    }
}

feed_update_event_manifest = {
    "ba4b11b6-dcce-4315-8fd0-67b69160ea76": {
        "Orgc": {
            "name": "test organisation",
            "uuid": "816e8f93-f169-49c1-bf15-efe2ab3211c8",
        },
        "Tag": [
            {
                "colour": "#004646",
                "local": False,
                "name": "EVENT_FEED_ADDED_TAG",
                "relationship_type": "",
            }
        ],
        "info": "Updated by Feed fetch",
        "date": "2024-08-27",
        "analysis": 0,
        "threat_level_id": 3,
        "timestamp": 1577836801,
    }
}

feed_update_event = {
    "Event": {
        "analysis": "0",
        "date": "2024-08-27",
        "extends_uuid": "",
        "info": "Updated by Feed fetch",
        "publish_timestamp": "1577836801",
        "published": True,
        "threat_level_id": "3",
        "timestamp": "1577836801",
        "uuid": "ba4b11b6-dcce-4315-8fd0-67b69160ea76",
        "Orgc": {
            "name": "test organisation",
            "uuid": "816e8f93-f169-49c1-bf15-efe2ab3211c8",
        },
        "Tag": [
            {
                "colour": "#004646",
                "local": False,
                "name": "EVENT_FEED_ADDED_TAG",
                "relationship_type": "",
            }
        ],
        "Attribute": [
            {
                "category": "Payload delivery",
                "comment": "Original RAR file",
                "deleted": False,
                "disable_correlation": False,
                "timestamp": "1577836801",
                "to_ids": True,
                "type": "sha1",
                "uuid": "7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0",
                "value": "7edc546f741eff3e13590a62ce2856bb39d8f71d",
                "Tag": [
                    {
                        "colour": "#004646",
                        "local": False,
                        "name": "ATTRIBUTE_EVENT_FEED_ADDED_TAG",
                        "relationship_type": "",
                    },
                ],
            }
        ],
        "Object": [
            {
                "comment": "Object comment updated by Feed fetch",
                "deleted": False,
                "description": "GitHub user",
                "meta-category": "misc",
                "name": "github-user",
                "template_uuid": "4329b5e6-8e6a-4b55-8fd1-9033782017d4",
                "template_version": "3",
                "timestamp": "1577836801",
                "uuid": "90e06ef6-26f8-40dd-9fb7-75897445e2a0",
                "ObjectReference": [
                    {
                        "comment": "",
                        "object_uuid": "90e06ef6-26f8-40dd-9fb7-75897445e2a0",
                        "referenced_uuid": "7f2fd15d-3c63-47ba-8a39-2c4b0b3314b0",
                        "relationship_type": "mentions",
                        "timestamp": "1577836801",
                        "uuid": "4d4c12b9-e514-496e-a8a6-06d5c6815b97",
                    }
                ],
                "Attribute": [
                    {
                        "category": "Social network",
                        "comment": "",
                        "deleted": False,
                        "disable_correlation": False,
                        "object_relation": "username",
                        "timestamp": "1577836801",
                        "to_ids": False,
                        "type": "github-username",
                        "uuid": "011aca4f-eaf0-4a06-8133-b69f3806cbe8",
                        "value": "Foobar12345",
                        "Tag": [
                            {
                                "colour": "#004646",
                                "local": False,
                                "name": "OBJECT_ATTRIBUTE_EVENT_FEED_ADDED_TAG",
                                "relationship_type": "",
                            },
                        ],
                    }
                ],
            },
        ],
    }
}
