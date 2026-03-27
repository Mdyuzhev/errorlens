"""Tests for OpenAPI spec parser."""

import pytest
from app.generators.spec_parser import OpenAPISpecParser, ParsedSpec


SIMPLE_OPENAPI_30 = """
openapi: "3.0.0"
info:
  title: Pet Store
  version: "1.0.0"
servers:
  - url: https://api.petstore.io/v1
paths:
  /pets:
    get:
      operationId: listPets
      summary: List all pets
      tags:
        - pets
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            maximum: 100
      responses:
        "200":
          description: A list of pets
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: integer
                    name:
                      type: string
                  required:
                    - id
                    - name
    post:
      operationId: createPet
      summary: Create a pet
      tags:
        - pets
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
              properties:
                name:
                  type: string
                  minLength: 1
                  maxLength: 100
                tag:
                  type: string
      responses:
        "201":
          description: Created
"""

SWAGGER_20 = """
{
  "swagger": "2.0",
  "info": {"title": "Legacy API", "version": "1.0"},
  "host": "api.legacy.com",
  "basePath": "/v1",
  "schemes": ["https"],
  "paths": {
    "/users": {
      "post": {
        "operationId": "createUser",
        "parameters": [
          {
            "in": "body",
            "name": "body",
            "required": true,
            "schema": {
              "type": "object",
              "required": ["email"],
              "properties": {
                "email": {"type": "string", "format": "email"},
                "name": {"type": "string"}
              }
            }
          }
        ],
        "responses": {
          "201": {
            "description": "Created",
            "schema": {"type": "object", "properties": {"id": {"type": "integer"}}}
          }
        }
      }
    }
  }
}
"""

REF_OPENAPI = """
openapi: "3.0.0"
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      operationId: getUser
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        "200":
          description: A user
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      required:
        - id
        - email
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        profile:
          $ref: "#/components/schemas/Profile"
    Profile:
      type: object
      properties:
        bio:
          type: string
        avatar_url:
          type: string
          format: uri
"""


class TestOpenAPIParser:
    def test_parse_openapi30_basic(self):
        parser = OpenAPISpecParser(SIMPLE_OPENAPI_30)
        result = parser.parse()
        assert isinstance(result, ParsedSpec)
        assert result.title == "Pet Store"
        assert result.base_url == "https://api.petstore.io/v1"
        assert len(result.endpoints) == 2

    def test_parse_openapi30_get_endpoint(self):
        parser = OpenAPISpecParser(SIMPLE_OPENAPI_30)
        result = parser.parse()
        get_ep = next(e for e in result.endpoints if e.method == "GET")
        assert get_ep.path == "/pets"
        assert get_ep.operation_id == "listPets"
        assert len(get_ep.query_params) == 1
        assert get_ep.query_params[0].name == "limit"
        assert get_ep.has_response_schema is True
        assert len(get_ep.response_fields) > 0

    def test_parse_openapi30_post_endpoint(self):
        parser = OpenAPISpecParser(SIMPLE_OPENAPI_30)
        result = parser.parse()
        post_ep = next(e for e in result.endpoints if e.method == "POST")
        assert post_ep.request_body_required is True
        assert len(post_ep.request_body_schema) > 0
        name_field = next(f for f in post_ep.request_body_schema if f.name == "name")
        assert name_field.min_length == 1
        assert name_field.max_length == 100
        assert name_field.required is True

    def test_parse_swagger20(self):
        parser = OpenAPISpecParser(SWAGGER_20)
        result = parser.parse()
        assert result.title == "Legacy API"
        assert result.base_url == "https://api.legacy.com/v1"
        assert len(result.endpoints) == 1
        ep = result.endpoints[0]
        assert ep.method == "POST"
        assert len(ep.request_body_schema) > 0
        email_field = next(f for f in ep.request_body_schema if f.name == "email")
        assert email_field.required is True
        assert email_field.format == "email"

    def test_ref_resolution(self):
        parser = OpenAPISpecParser(REF_OPENAPI)
        result = parser.parse()
        ep = result.endpoints[0]
        assert ep.has_response_schema is True
        assert len(ep.response_fields) > 0
        field_names = [f.name for f in ep.response_fields]
        assert "id" in field_names
        assert "email" in field_names
        # Nested $ref Profile should also be resolved
        assert "bio" in field_names or any("profile" in f.path for f in ep.response_fields)

    def test_path_params(self):
        parser = OpenAPISpecParser(REF_OPENAPI)
        result = parser.parse()
        ep = result.endpoints[0]
        assert len(ep.path_params) == 1
        assert ep.path_params[0].name == "id"
        assert ep.path_params[0].schema.format == "uuid"

    def test_invalid_spec_raises(self):
        with pytest.raises(ValueError):
            OpenAPISpecParser("not valid at all {{{")

    def test_dict_input(self):
        spec_dict = {"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}
        parser = OpenAPISpecParser(spec_dict)
        result = parser.parse()
        assert result.title == "T"
        assert len(result.endpoints) == 0
