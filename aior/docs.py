import json
import typing
from inspect import isclass
from typing import Optional, Any, Union, Set, Dict, Text, Type, Sequence, List, Tuple, cast

from aiohttp import web
from aiohttp.web_urldispatcher import View
from pydantic import BaseModel
from pydantic.schema import model_process_schema, get_flat_models_from_model, get_model_name_map

from aior.components import BaseHTTPHandler, NoContentResponse, BaseStatus, JSONResponse, OKStatus, BytesBody, \
    PlainBody, IntBody, FloatBody, BooleanBody
from aior.components.http_exceptions import AiorHTTPError
from aior.constants import REF_PREFIX, NoneType, DEFAULT_CONTENT_TYPE, NONE_RESPONSE, DEFAULT_JSON_HEADERS, JSON_TYPES
from aior.helpers import app_log
from aior.utils import add_space_in_front_of_capital_letter, get_generic_type_args, get_generic_origin_type, \
    get_json_type

if typing.TYPE_CHECKING:
    from aior.application import AiorApplication

SetIntStr = Set[Union[int, str]]
DictIntStrAny = Dict[Union[int, str], Any]


def get_swagger_ui_html(
        *,
        openapi_url: str,
        title: str,
        swagger_ui_js_url: str,
        swagger_ui_css_url: str,
        docs_favicon_url: str,
        oauth2_redirect_url: Optional[str] = None,
        init_oauth: Optional[dict] = None,
) -> Text:
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="{swagger_ui_css_url}">
    <link rel="shortcut icon" href="{docs_favicon_url}">
    <title>{title}</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="{swagger_ui_js_url}"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({{
        url: '{openapi_url}',
    """

    if oauth2_redirect_url:
        html += f"oauth2RedirectUrl: window.location.origin + '{oauth2_redirect_url}',"

    html += """
        dom_id: '#swagger-ui',
        presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
        deepLinking: true
    })"""

    if init_oauth:
        html += f"""
        ui.initOAuth({json.dumps(init_oauth)})
        """

    html += """
        </script>
        </body>
        </html>
        """

    return html


def get_redoc_html(
        *,
        openapi_url: str,
        title: str,
        redoc_js_url: str,
        redoc_favicon_url: str,
        with_google_fonts: bool = False,
) -> Text:
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>{title}</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """
    if with_google_fonts:
        html += """
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    """
    html += f"""
    <link rel="shortcut icon" href="{redoc_favicon_url}">
    <!--
    ReDoc doesn't change outer page styles
    -->
    <style>
      body {{
        margin: 0;
        padding: 0;
      }}
    </style>
    </head>
    <body>
    <redoc spec-url="{openapi_url}"></redoc>
    <script src="{redoc_js_url}"> </script>
    </body>
    </html>
    """
    return html


def get_swagger_ui_oauth2_redirect_html() -> Text:
    html = """
    <!DOCTYPE html>
    <html lang="en-US">
    <body onload="run()">
    </body>
    </html>
    <script>
        'use strict';
        function run () {
            var oauth2 = window.opener.swaggerUIRedirectOauth2;
            var sentState = oauth2.state;
            var redirectUrl = oauth2.redirectUrl;
            var isValid, qp, arr;

            if (/code|token|error/.tests(window.location.hash)) {
                qp = window.location.hash.substring(1);
            } else {
                qp = location.search.substring(1);
            }

            arr = qp.split("&")
            arr.forEach(function (v,i,_arr) { _arr[i] = '"' + v.replace('=', '":"') + '"';})
            qp = qp ? JSON.parse('{' + arr.join() + '}',
                    function (key, value) {
                        return key === "" ? value : decodeURIComponent(value)
                    }
            ) : {}

            isValid = qp.state === sentState

            if ((
            oauth2.auth.schema.get("flow") === "accessCode"||
            oauth2.auth.schema.get("flow") === "authorizationCode"
            ) && !oauth2.auth.code) {
                if (!isValid) {
                    oauth2.errCb({
                        authId: oauth2.auth.name,
                        source: "auth",
                        level: "warning",
                        message: "Authorization may be unsafe, passed state was changed in server Passed state wasn't returned from auth server"
                    });
                }

                if (qp.code) {
                    delete oauth2.state;
                    oauth2.auth.code = qp.code;
                    oauth2.callback({auth: oauth2.auth, redirectUrl: redirectUrl});
                } else {
                    let oauthErrorMsg
                    if (qp.error) {
                        oauthErrorMsg = "["+qp.error+"]: " +
                            (qp.error_description ? qp.error_description+ ". " : "no accessCode received from the server. ") +
                            (qp.error_uri ? "More info: "+qp.error_uri : "");
                    }

                    oauth2.errCb({
                        authId: oauth2.auth.name,
                        source: "auth",
                        level: "error",
                        message: oauthErrorMsg || "[Authorization failed]: no accessCode received from the server"
                    });
                }
            } else {
                oauth2.callback({auth: oauth2.auth, token: qp, isValid: isValid, redirectUrl: redirectUrl});
            }
            window.close();
        }
    </script>
        """
    return html


class DocsHandler(web.View):
    async def get(self):
        app = self.request.app  # type: AiorApplication
        body = get_swagger_ui_html(openapi_url=app.openapi_url,
                                   title=app.docs_title,
                                   swagger_ui_js_url=app.swagger_ui_js_url,
                                   swagger_ui_css_url=app.swagger_ui_css_url,
                                   docs_favicon_url=app.swagger_ui_favicon_url)
        return web.Response(text=body, content_type="text/html")


class RedocHandler(web.View):
    async def get(self):
        app = self.request.app  # type: AiorApplication
        body = get_redoc_html(openapi_url=app.openapi_url,
                              title=app.docs_title,
                              redoc_js_url=app.redoc_ui_js_url,
                              redoc_favicon_url=app.redoc_ui_favicon_url)
        return web.Response(text=body, content_type="text/html")


class OpenapiSchemaHandler(web.View):
    async def get(self):
        app = self.request.app  # type: AiorApplication
        body = json.dumps(app.openapi_schema)
        return web.Response(text=body)


def get_openapi(*,
                routes: Sequence[Tuple[str, Union[Type[BaseHTTPHandler], Type[View]], Dict[str, Dict]]],
                info: Dict[str, Any],
                openapi_version: str,
                ) -> Dict:
    output = {'openapi': openapi_version, 'info': info}
    components = {}  # type: Dict[str, Dict]
    paths = {}  # type:Dict[str, Dict]

    flat_models = get_flat_models_from_routes(routes)
    model_name_map = get_model_name_map(flat_models)

    definitions = get_model_definitions(
        flat_models=flat_models, model_name_map=model_name_map
    )
    if definitions:
        components["schemas"] = {k: definitions[k] for k in sorted(definitions)}
    if components:
        output["components"] = components

    for uri, handler, handler_hints in routes:
        path = {}
        for method, hints in handler_hints.items():
            path_operation = get_path_operation(uri=uri,
                                                handler=handler,
                                                method=method,
                                                hints=hints,
                                                model_name_map=model_name_map)
            if path_operation:
                path.update(path_operation)

        if path:
            paths.update({uri: path})

    output["paths"] = paths

    return output


def get_path_operation(*, uri: str,
                       handler: Type[BaseHTTPHandler],
                       method: str,
                       hints: Dict[str, Type],
                       model_name_map: Dict,
                       ) -> Dict:
    # TODO: get_openapi_security_definitions
    operation = get_openapi_operation_metadata(uri=uri, handler=handler, method=method)
    parameters = []  # type: List[Dict]
    request_body = None  # type: Optional[Dict]
    responses = {}  # type: Dict[str, Dict]

    response_definition = get_response_definition(model_name_map=model_name_map,
                                                  uri=uri,
                                                  method=method,
                                                  response_type=hints.pop("return", None))
    if response_definition:
        responses.update(response_definition)

    for name, (typ, clazz) in hints.items():
        if typ == "json_body":
            request_body = get_request_body(clazz, model_name_map)
        elif typ == "queries":
            parameters.append(get_query_params(name, clazz))
        elif typ == "query":
            parameters.append(get_query_param(name, clazz))
        elif typ == "path_args":
            parameters.append(get_query_params(name, clazz))
        elif typ == "path_arg":
            parameters.append(get_path_param(name, clazz))
        elif typ == "json_body":
            request_body = get_request_body(clazz, model_name_map)

    if parameters:
        operation["parameters"] = parameters

    if request_body:
        operation["requestBody"] = request_body

    if responses:
        operation["responses"] = responses

    return {method: operation}


def get_body_list_body_type(typ: List[Type]):
    args = get_generic_type_args(typ)
    assert len(args) == 1, f"{type(args)}: not supported body"
    arg = args[0]
    assert issubclass(arg, JSON_TYPES), f"{type(arg)}: not supported body"
    return arg


def get_response_definition(*,
                            response_type: Optional[Type[JSONResponse]],
                            uri: str,
                            method: str,
                            model_name_map: Dict,
                            ) -> Optional[Dict]:
    if response_type is None:
        return

    origin_type = get_generic_origin_type(response_type)
    if origin_type:
        if issubclass(origin_type, NoContentResponse):
            return get_no_content_response_definition(response_type)

        elif issubclass(origin_type, JSONResponse):
            return get_json_response_definition(response_type=response_type,
                                                uri=uri,
                                                method=method,
                                                model_name_map=model_name_map)


def get_no_content_response_definition(
        response_type: Type[NoContentResponse]
) -> Optional[Dict]:
    type_args = get_generic_type_args(response_type)
    if type_args:
        status = cast(BaseStatus, type_args[0])
        return {status.code: {"description": status.reason}}
    else:
        return NONE_RESPONSE


BODY_TYPES = (BaseModel, NoneType, PlainBody, BytesBody, IntBody, FloatBody, BooleanBody)
NUMBER_BODY_TYPES = (IntBody, FloatBody)


def get_json_response_definition(*,
                                 response_type: Type[JSONResponse],
                                 uri: str,
                                 method: str,
                                 model_name_map: Dict
                                 ) -> Optional[Dict]:
    type_args = get_generic_type_args(response_type)
    if not type_args:
        app_log.warning(f"response type {type(type_args)} in "
                        f"{method} method of {uri} has not type arguments")
        return

    resp_args = type_args[0]

    body_type = None
    success_status_type = OKStatus
    headers_type = DEFAULT_JSON_HEADERS
    errors = []
    body_is_list = False

    if isclass(resp_args):
        if issubclass(resp_args, BODY_TYPES):
            body_type = resp_args
        elif issubclass(resp_args, AiorHTTPError):
            errors.append(resp_args)
        else:
            app_log.warning(f"response type {type(resp_args)} in "
                            f"{method} method of {uri} is not supported")
            return
    else:
        origin_type = get_generic_origin_type(resp_args)
        if origin_type is list:
            body_type = get_body_list_body_type(resp_args)
        elif origin_type is Union:
            sub_args = get_generic_type_args(resp_args)
            for arg in sub_args:
                if isclass(arg):
                    if resp_args in BODY_TYPES:
                        body_type = arg
                    elif issubclass(arg, AiorHTTPError):
                        errors.append(arg)
                    else:
                        app_log.warning(f"response type {type(arg)} in "
                                        f"{method} method of {uri} is not supported")
                        return
                elif get_generic_origin_type(arg) is list:
                    body_is_list = True
                    body_type = get_body_list_body_type(arg)
                else:
                    app_log.warning(f"response type {type(arg)} in "
                                    f"{method} method of {uri} is not supported")
                    return
        else:
            app_log.warning(f"response type {type(origin_type)} in "
                            f"{method} method of {uri} is not supported")
            return

    if body_type is None:
        app_log.warning(f"response type in {method} method of {uri} is not defined")
        return

    if issubclass(body_type, BaseModel):
        schema = {"schema": {"$ref": f"{REF_PREFIX}{model_name_map[body_type]}"}}
    elif issubclass(body_type, (NoneType, BytesBody)):
        schema = {}
    elif issubclass(body_type, PlainBody):
        schema = {"type": "string"}
    elif issubclass(body_type, NUMBER_BODY_TYPES):
        schema = {"type": "number"}
    elif issubclass(body_type, BooleanBody):
        schema = {"type": "boolean"}
    else:
        app_log.warning(f"response body type {type(body_type)} in "
                        f"{method} method of {uri} is not supported")
        return

    content_type = headers_type.get("Content-Type", DEFAULT_CONTENT_TYPE)

    if schema:
        if body_is_list:
            schema = {"type": "array", "items": {schema}}
        content = {"content": {content_type: schema}}
    else:
        content = {}
    content.update({"description": success_status_type.reason})

    ret = {str(success_status_type.code): content}

    for e in errors:
        ret.update({str(e.status_code): {"description": e().reason}})

    return ret


def get_query_param(name, clazz):
    return {
        'in': 'query',
        'name': name,
        'schema': {'type': get_json_type(clazz)}
    }


def get_query_params(name, clazz: Type[BaseModel]):
    schema = clazz.schema()
    required = schema.pop("required", None)
    return {
        'in': 'query',
        'name': name,
        'required': required is not None and name in required,
        'schema': schema
    }


def get_path_param(name, clazz):
    return {
        'in': 'path',
        'name': name,
        'schema': {'type': get_json_type(clazz)}
    }


def get_path_params(name, clazz):
    # TODO: required value depends on path
    schema = clazz.schema()
    required = schema.pop("required", None)
    return {
        'in': 'path',
        'name': name,
        'required': required is not None and name in required,
        'schema': schema
    }


def get_request_body(clazz, model_name_map):
    schema_ref = f"{REF_PREFIX}{model_name_map[clazz]}"
    return {
        'content': {
            'application/json': {
                'schema': {'$ref': schema_ref}
            }
        },
        'required': True
    }


def get_flat_models_from_routes(routes: Sequence[Tuple[str, web.View]]
                                ) -> Set[Type[BaseModel]]:
    flat_models = set()
    for _, _, handler_hints in routes:
        for method, hints in handler_hints.items():
            for name, typ in hints.items():
                if isinstance(typ, tuple) and len(typ) == 2:
                    models = get_models_of_type(typ[1])
                else:
                    models = get_models_of_type(typ)
                if models:
                    for model in models:
                        flat_models |= get_flat_models_from_model(model, flat_models)

    return flat_models


def get_models_of_type(typ: Type) -> List[BaseModel]:
    ret = []

    if not isclass(typ):
        for arg in get_generic_type_args(typ):
            if not isclass(arg):
                ret.extend(get_models_of_type(arg))
            elif issubclass(arg, BaseModel):
                ret.append(arg)
    elif issubclass(typ, BaseModel):
        ret.append(typ)

    return ret


def get_model_definitions(
        *, flat_models: Set[Type[BaseModel]], model_name_map: Dict[Type[BaseModel], str]
) -> Dict[str, Any]:
    definitions: Dict[str, Dict] = {}
    for model in flat_models:
        m_schema, m_definitions, m_nested_models = model_process_schema(
            model, model_name_map=model_name_map, ref_prefix=REF_PREFIX
        )
        definitions.update(m_definitions)
        model_name = model_name_map[model]
        definitions[model_name] = m_schema
    return definitions


def get_openapi_operation_metadata(*, uri: str,
                                   handler: Type[BaseHTTPHandler],
                                   method: str,
                                   tags: str = None,
                                   summary: str = None,
                                   deprecated: str = None,
                                   operation_id: str = None,
                                   description: str = None,
                                   ) -> Dict:
    # TODO: enable deprecated, operation_id, summary
    operation: Dict[str, Any] = {}

    if tags:
        operation["tags"] = tags
    operation["summary"] = generate_operation_summary(handler=handler,
                                                      method=method,
                                                      summary=summary)

    if not description:
        doc_str = handler.__doc__
        if doc_str:
            description = doc_str.strip()
    if description:
        operation["description"] = description
    operation["operationId"] = generate_operation_id(uri=uri,
                                                     method=method,
                                                     operation_id=operation_id)

    if deprecated:
        operation["deprecated"] = deprecated

    return operation


def generate_operation_summary(*, handler: Type[BaseHTTPHandler],
                               method: str,
                               summary: str
                               ) -> str:
    if summary:
        return summary

    summary = handler.__name__
    if summary[-7:] == "Handler":
        summary = summary[:-7]

    return add_space_in_front_of_capital_letter(f"{method.capitalize()}{summary}")


def generate_operation_id(*, uri: str,
                          method: str,
                          operation_id: Optional[str]
                          ) -> str:
    if operation_id:
        return operation_id

    return f"{uri.lstrip('/').replace('/', '_').replace('{', '_').replace('}', '')}__{method}"
