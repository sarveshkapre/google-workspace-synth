from __future__ import annotations

from typing import Any

from . import __version__


def openapi_spec() -> dict[str, Any]:
    """
    Hand-maintained OpenAPI spec for the local emulator API.

    Keep this intentionally small and correct; it's a dev UX feature, not a full compatibility
    layer.
    """
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Google Workspace Synth API",
            "version": __version__,
            "description": (
                "Local-first synthetic Google Workspace (Drive/Docs/Sheets) emulator.\n\n"
                "Auth note: if `GWSYNTH_API_KEY` is set, most endpoints require either "
                "`Authorization: Bearer <key>` or `X-API-Key: <key>`."
            ),
        },
        # If API key auth is enabled, clients should provide either X-API-Key
        # or Authorization: Bearer.
        # Public routes explicitly opt out per-operation below.
        "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/stats": {
                "get": {
                    "summary": "Counts of core resources",
                    "security": [],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/snapshot": {
                "get": {
                    "summary": "Export a DB snapshot",
                    "parameters": [
                        {
                            "name": "tables",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Comma-separated subset of tables.",
                        },
                        {
                            "name": "gzip",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "If truthy, stream a gzip-compressed JSON snapshot.",
                        },
                        {
                            "name": "stream",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "If truthy, stream compact JSON (no indentation).",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Snapshot document",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Snapshot"}
                                }
                            },
                        }
                        ,
                        "304": {"description": "Not modified (ETag match)"},
                    },
                },
                "post": {
                    "summary": "Import a DB snapshot",
                    "description": (
                        "Accepts JSON. For large snapshots, clients may send gzip-compressed JSON "
                        "with `Content-Encoding: gzip`."
                    ),
                    "parameters": [
                        {
                            "name": "mode",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "enum": ["replace", "replace_tables"]},
                        },
                        {
                            "name": "tables",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Comma-separated subset of tables to import.",
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Snapshot"}
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Imported"},
                        "400": {
                            "description": "Invalid snapshot",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                        "413": {
                            "description": "Request entity too large",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
            },
            "/users": {
                "get": {
                    "summary": "List users",
                    "parameters": [
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Users",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "oneOf": [
                                            {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/User"},
                                            },
                                            {"$ref": "#/components/schemas/UsersPage"},
                                        ]
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserIn"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "409": {
                            "description": "Duplicate email",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
            },
            "/users/{user_id}": {
                "get": {
                    "summary": "Get user",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "User",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "404": {
                            "description": "Not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                }
            },
            "/groups": {
                "get": {
                    "summary": "List groups",
                    "parameters": [
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Groups",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "oneOf": [
                                            {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/Group"},
                                            },
                                            {"$ref": "#/components/schemas/GroupsPage"},
                                        ]
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create group",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GroupIn"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Group"}
                                }
                            },
                        }
                    },
                },
            },
            "/groups/{group_id}": {
                "get": {
                    "summary": "Get group",
                    "parameters": [
                        {
                            "name": "group_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Group",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Group"}
                                }
                            },
                        },
                        "404": {
                            "description": "Not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                }
            },
            "/groups/{group_id}/members": {
                "get": {
                    "summary": "List group members",
                    "parameters": [
                        {
                            "name": "group_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Members",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "oneOf": [
                                            {"$ref": "#/components/schemas/GroupMembersList"},
                                            {"$ref": "#/components/schemas/GroupMembersPage"},
                                        ]
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "Not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
                "post": {
                    "summary": "Add group member (idempotent)",
                    "parameters": [
                        {
                            "name": "group_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GroupMemberIn"},
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Added"},
                        "404": {"description": "Not found"},
                    },
                },
            },
            "/groups/{group_id}/members/{user_id}": {
                "delete": {
                    "summary": "Remove group member",
                    "parameters": [
                        {
                            "name": "group_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {
                        "200": {"description": "Removed"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/items": {
                "get": {
                    "summary": "List items",
                    "parameters": [
                        {
                            "name": "parent_id",
                            "in": "query",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "owner_user_id",
                            "in": "query",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "item_type",
                            "in": "query",
                            "schema": {"type": "string", "enum": ["folder", "doc", "sheet"]},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Items",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ItemsList"}
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create item",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ItemIn"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Item"}
                                }
                            },
                        },
                        "400": {"description": "Validation error"},
                        "404": {"description": "Not found"},
                    },
                },
            },
            "/items/{item_id}": {
                "get": {
                    "summary": "Get item",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Item",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Item"}
                                }
                            },
                        },
                        "404": {
                            "description": "Not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                }
            },
            "/items/{item_id}/content": {
                "put": {
                    "summary": "Update item content (doc/sheet only)",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ItemContentUpdateIn"},
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Updated"},
                        "400": {"description": "Invalid"},
                    },
                }
            },
            "/items/{item_id}/permissions": {
                "get": {
                    "summary": "List permissions",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Permissions",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PermissionsList"}
                                }
                            },
                        },
                        "404": {"description": "Not found"},
                    },
                },
                "post": {
                    "summary": "Create permission",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PermissionIn"},
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "404": {"description": "Not found"},
                    },
                },
            },
            "/items/{item_id}/permissions/{permission_id}": {
                "delete": {
                    "summary": "Delete permission",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "permission_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {
                        "200": {"description": "Deleted"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/items/{item_id}/share-links": {
                "get": {
                    "summary": "List share links",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Share links",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ShareLinksList"}
                                }
                            },
                        },
                        "404": {"description": "Not found"},
                    },
                },
                "post": {
                    "summary": "Create share link",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ShareLinkIn"},
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "404": {"description": "Not found"},
                    },
                },
            },
            "/items/{item_id}/share-links/{link_id}": {
                "delete": {
                    "summary": "Delete share link",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "link_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {
                        "200": {"description": "Deleted"},
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/items/{item_id}/comments": {
                "get": {
                    "summary": "List comments",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Comments",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CommentsList"}
                                }
                            },
                        },
                        "404": {"description": "Not found"},
                    },
                },
                "post": {
                    "summary": "Create comment",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CommentIn"},
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "404": {"description": "Not found"},
                    },
                },
            },
            "/items/{item_id}/activity": {
                "get": {
                    "summary": "List item activity (descending by created_at)",
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                        {
                            "name": "before",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "An ISO timestamp to page backwards from.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Events",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ActivityList"}
                                }
                            },
                        },
                        "404": {"description": "Not found"},
                    },
                }
            },
            "/search": {
                "get": {
                    "summary": "Search items by name/content",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"$ref": "#/components/parameters/Limit"},
                        {"$ref": "#/components/parameters/Cursor"},
                    ],
                    "responses": {
                        "200": {
                            "description": "Items",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ItemsList"}
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "Provide the API key in the X-API-Key header.",
                },
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Provide the API key as an Authorization: Bearer token.",
                },
            },
            "parameters": {
                "Limit": {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "minimum": 1, "maximum": 200},
                },
                "Cursor": {
                    "name": "cursor",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                },
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                    "required": ["error"],
                },
                "UserIn": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "display_name": {"type": "string"},
                    },
                    "required": ["email", "display_name"],
                },
                "User": {
                    "allOf": [
                        {"$ref": "#/components/schemas/UserIn"},
                        {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "created_at": {"type": "string"},
                            },
                            "required": ["id", "created_at"],
                        },
                    ]
                },
                "UsersPage": {
                    "type": "object",
                    "properties": {
                        "users": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["users", "next_cursor"],
                },
                "GroupIn": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["name"],
                },
                "Group": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "created_at": {"type": "string"},
                    },
                    "required": ["id", "name", "description", "created_at"],
                },
                "GroupsPage": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Group"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["groups", "next_cursor"],
                },
                "GroupMemberIn": {
                    "type": "object",
                    "properties": {"user_id": {"type": "string"}},
                    "required": ["user_id"],
                },
                "GroupMember": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "group_id": {"type": "string"},
                        "user_id": {"type": "string"},
                        "email": {"type": "string"},
                        "display_name": {"type": "string"},
                        "created_at": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "group_id",
                        "user_id",
                        "email",
                        "display_name",
                        "created_at",
                    ],
                },
                "GroupMembersList": {
                    "type": "object",
                    "properties": {
                        "members": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/GroupMember"},
                        }
                    },
                    "required": ["members"],
                },
                "GroupMembersPage": {
                    "type": "object",
                    "properties": {
                        "members": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/GroupMember"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["members", "next_cursor"],
                },
                "ItemIn": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "item_type": {"type": "string", "enum": ["folder", "doc", "sheet"]},
                        "parent_id": {"type": "string", "nullable": True},
                        "owner_user_id": {"type": "string", "nullable": True},
                        "content_text": {"type": "string", "nullable": True},
                        "sheet_data": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "nullable": True,
                        },
                    },
                    "required": ["name", "item_type"],
                },
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "item_type": {"type": "string", "enum": ["folder", "doc", "sheet"]},
                        "parent_id": {"type": "string", "nullable": True},
                        "owner_user_id": {"type": "string", "nullable": True},
                        "content_text": {"type": "string", "nullable": True},
                        "sheet_data": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "nullable": True,
                        },
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"},
                    },
                    "required": ["id", "name", "item_type", "created_at", "updated_at"],
                },
                "ItemsList": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Item"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["items"],
                },
                "ItemContentUpdateIn": {
                    "type": "object",
                    "properties": {
                        "actor_user_id": {"type": "string", "nullable": True},
                        "content_text": {"type": "string", "nullable": True},
                        "sheet_data": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "nullable": True,
                        },
                    },
                },
                "PermissionIn": {
                    "type": "object",
                    "properties": {
                        "actor_user_id": {"type": "string", "nullable": True},
                        "principal_type": {"type": "string", "enum": ["user", "group", "anyone"]},
                        "principal_id": {"type": "string", "nullable": True},
                        "role": {"type": "string", "enum": ["owner", "editor", "viewer"]},
                    },
                    "required": ["principal_type", "role"],
                },
                "Permission": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "item_id": {"type": "string"},
                        "principal_type": {
                            "type": "string",
                            "enum": ["user", "group", "anyone"],
                        },
                        "principal_id": {"type": "string", "nullable": True},
                        "role": {"type": "string", "enum": ["owner", "editor", "viewer"]},
                        "created_at": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "item_id",
                        "principal_type",
                        "principal_id",
                        "role",
                        "created_at",
                    ],
                },
                "PermissionsList": {
                    "type": "object",
                    "properties": {
                        "permissions": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Permission"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["permissions"],
                },
                "ShareLinkIn": {
                    "type": "object",
                    "properties": {
                        "actor_user_id": {"type": "string", "nullable": True},
                        "role": {"type": "string", "enum": ["owner", "editor", "viewer"]},
                        "expires_at": {"type": "string", "nullable": True},
                    },
                    "required": ["role"],
                },
                "ShareLink": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "item_id": {"type": "string"},
                        "token": {"type": "string"},
                        "role": {"type": "string", "enum": ["owner", "editor", "viewer"]},
                        "expires_at": {"type": "string", "nullable": True},
                        "created_at": {"type": "string"},
                    },
                    "required": ["id", "item_id", "token", "role", "created_at"],
                },
                "ShareLinksList": {
                    "type": "object",
                    "properties": {
                        "share_links": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ShareLink"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["share_links"],
                },
                "CommentIn": {
                    "type": "object",
                    "properties": {
                        "author_user_id": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["author_user_id", "body"],
                },
                "Comment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "item_id": {"type": "string"},
                        "author_user_id": {"type": "string"},
                        "body": {"type": "string"},
                        "created_at": {"type": "string"},
                    },
                    "required": ["id", "item_id", "author_user_id", "body", "created_at"],
                },
                "CommentsList": {
                    "type": "object",
                    "properties": {
                        "comments": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Comment"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["comments"],
                },
                "ActivityEvent": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "item_id": {"type": "string"},
                        "event_type": {"type": "string"},
                        "actor_user_id": {"type": "string", "nullable": True},
                        "data": {"type": "object"},
                        "created_at": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "item_id",
                        "event_type",
                        "actor_user_id",
                        "data",
                        "created_at",
                    ],
                },
                "ActivityList": {
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ActivityEvent"},
                        },
                        "next_cursor": {"type": "string", "nullable": True},
                    },
                    "required": ["events", "next_cursor"],
                },
                "Snapshot": {
                    "type": "object",
                    "properties": {
                        "snapshot_version": {"type": "integer"},
                        "app_version": {"type": "string"},
                        "exported_at": {"type": "string"},
                        "exported_tables": {"type": "array", "items": {"type": "string"}},
                        "schema": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "tables": {
                            "type": "object",
                            "additionalProperties": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                    "required": ["snapshot_version", "tables"],
                },
            },
        },
    }
