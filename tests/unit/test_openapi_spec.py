import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_openapi_spec_generate

def test_func_openapi_spec_generate_basic():
    # Mock route
    route = MagicMock()
    route.path = "/public/test"
    route.methods = ["GET"]
    
    # Mock endpoint with source code for inspection
    def fake_endpoint(request):
        """Docstring test"""
        return {"status": 1}
    
    route.endpoint = fake_endpoint
    app_routes = [route]
    
    app_state = MagicMock()
    app_state.config_regex = {}
    
    spec = func_openapi_spec_generate(
        app_routes=app_routes,
        config_api_roles_auth=["/my/"],
        app_state=app_state
    )
    
    assert spec["openapi"] == "3.0.0"
    assert "/public/test" in spec["paths"]
    assert "get" in spec["paths"]["/public/test"]
    assert spec["paths"]["/public/test"]["get"]["tags"] == ["public"]

def test_func_openapi_spec_generate_with_params():
    route = MagicMock()
    route.path = "/public/item/{id}"
    route.methods = ["POST"]
    
    # Need an endpoint that calls func_request_param_read in its source
    def item_create(request):
        # The generator parses this source code!
        # It looks for the string 'func_request_param_read'
        params = func_request_param_read(request=request, mode="body", config=[("name", "str", 1, None, None)])
        return {"id": 1}
    
    route.endpoint = item_create
    app_routes = [route]
    
    app_state = MagicMock()
    app_state.config_regex = {"name": [".*", "Any name"]}
    
    source_code = """
def item_create(request):
    params = func_request_param_read(request=request, mode="body", config=[("name", "str", 1, None, None)])
    return {"id": 1}
"""
    with patch("inspect.getsource", return_value=source_code):
        spec = func_openapi_spec_generate(
            app_routes=app_routes,
            config_api_roles_auth=[],
            app_state=app_state
        )
    
    path_item = spec["paths"]["/public/item/{id}"]["post"]
    # Check path param
    assert any(p["name"] == "id" and p["in"] == "path" for p in path_item["parameters"])
    # Check body param (parsed from source)
    assert "requestBody" in path_item
    content = path_item["requestBody"]["content"]["application/json"]
    assert "name" in content["schema"]["properties"]
    assert content["schema"]["properties"]["name"]["type"] == "string"
    assert "name" in content["schema"]["required"]
