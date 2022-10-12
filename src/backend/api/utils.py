# coding=utf-8
import os
from functools import wraps
from typing import Any

import jsonschema
from flask import (
    Response,
    jsonify,
    make_response,
    request, session, current_app, Flask,
)
from flask import g
from flask_api.status import (
    HTTP_200_OK,
    HTTP_403_FORBIDDEN,
)
from flask_bs4 import Bootstrap
from flask_github import GitHub, GitHubError
from werkzeug.exceptions import InternalServerError
from werkzeug.test import TestResponse

from api.exceptions import (
    BaseCustomException,
    BadRequestFormatExceptioin,
    CustomHTTPError,
)
from common.sentry import get_logger
from db.data_models import (
    GitHubOrgData,
    UserData,
    MAIN_ORGANIZATION,
    MAIN_ORGANIZATION_ID,
)
from db.db_models import GitHubOrg, Group
from db.json_schemas import json_schema_mapping
from db.utils import session_scope

logger = get_logger(__name__)


def jsonify_response(
        result: dict[str, Any],
        status_code: int,
) -> Response:
    return make_response(
        jsonify(result),
        status_code,
    )


def textify_response(
        content: str,
        status_code: int,
) -> Response:
    response = make_response(
        content,
        status_code,
    )
    response.mimetype = 'text/plain'
    return response


def validate_json(f):
    """
    Decorator: wrap success result
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        json_schema = json_schema_mapping.get(
            request.url_rule.rule
        ).get(request.method)
        if json_schema is not None and not request.is_json:
            raise BadRequestFormatExceptioin(
                'Passed data is not JSON',
            )
        elif json_schema is not None:
            try:
                jsonschema.validate(
                    request.json,
                    json_schema,
                )
            except jsonschema.ValidationError as err:
                raise BadRequestFormatExceptioin(
                    'Passed data is not valid JSON, because "%s"',
                    err,
                )
        return f(*args, **kwargs)

    return decorated_function


def success_result(f):
    """
    Decorator: wrap success result
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)
        if isinstance(result, Response):
            return result
        return jsonify_response(
            result=result,
            status_code=HTTP_200_OK,
        )

    return decorated_function


def error_result(f):
    """
    Decorator: catch unknown exceptions and raise InternalServerError
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BaseCustomException:
            raise
        except Exception as err:
            raise InternalServerError(
                description=str(err),
                original_exception=err,
            )

    return decorated_function


def login_requires(f):
    """
    Decorator: Requires login through GH
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_is_forbidden = jsonify_response(
            result={
                'result': 'You should be logged through GitHub'
            },
            status_code=HTTP_403_FORBIDDEN,
        )
        if g.user_data is None:
            return access_is_forbidden
        return f(*args, **kwargs)

    return decorated_function


def is_our_member(github: GitHub) -> bool:
    if g.user_data is None:
        return False
    if g.user_data.github_orgs is None:
        return False
    if all(org.name != MAIN_ORGANIZATION for org in g.user_data.github_orgs):
        return False
    try:
        membership = github.get(
            '/orgs/AlmaLinux/teams/packagers/'
            f'memberships/{g.user_data.github_login}'
        )
        if membership.get('state', 'not_active') != 'active':
            return False
    except GitHubError:
        return False
    return True


def membership_requires(f):
    """
    Decorator: Requires membership of a specific GH team
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_is_forbidden = jsonify_response(
            result={
                'result': 'This action is required a spec.membership on GitHub'
            },
            status_code=HTTP_403_FORBIDDEN,
        )
        if session.get('is_our_member', False):
            return f(*args, **kwargs)
        else:
            return access_is_forbidden

    return decorated_function


def clear_sessions_fields_before_logout(f):
    """
    Decorator: Clear auth fields in a session object before logout
    """

    auth_fields = (
        'csrf_token',
        'github_id',
        'is_our_member',
    )

    @wraps(f)
    def decorated_function(*args, **kwargs):
        for auth_field in auth_fields:
            session.pop(auth_field, None)
        return f(*args, **kwargs)

    return decorated_function


def create_flask_client():
    app_client = current_app.test_client()
    for key, value in request.cookies.items():
        app_client.set_cookie('localhost', key, value)
    return app_client


def create_flask_application() -> Flask:
    app = Flask('pes')
    app.secret_key = os.environ['FLASK_SECRET_KEY']
    app.config['SESSION_TYPE'] = 'filesystem'
    Bootstrap(app)
    app.config['GITHUB_CLIENT_ID'] = os.environ['GITHUB_CLIENT_ID']
    app.config['GITHUB_CLIENT_SECRET'] = os.environ['GITHUB_CLIENT_SECRET']
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['template_folder'] = 'templates'

    return app


def raise_for_status(response: TestResponse):
    """
        Raise for status of a response from Flask client
    """

    http_error_msg = ''
    reason = response.data
    if isinstance(reason, bytes):
        # We attempt to decode utf-8 first because some servers
        # choose to localize their reason strings. If the string
        # isn't utf-8, we fall back to iso-8859-1 for all other
        # encodings. (See PR #3538)
        try:
            reason = reason.decode('utf-8')
        except UnicodeDecodeError:
            reason = reason.decode('iso-8859-1')
    else:
        reason = reason

    if 400 <= response.status_code < 500 or 500 <= response.status_code < 600:
        raise CustomHTTPError(
            reason=reason,
            url=response.request.base_url,
            status_code=response.status_code,
        )


def get_user_organizations(
        only_self: bool = False
) -> list[tuple[str, str]]:
    """
    Return list of GH orgs for a currently logged user
    :param only_self: return list of orgs to which a user belongs
    """
    user_data = g.user_data  # type: UserData
    user_orgs = [] if user_data is None else user_data.github_orgs

    def is_admin_org(only_self: bool, user_data: UserData):
        return not only_self and user_data.is_in_org(MAIN_ORGANIZATION)

    if is_admin_org(only_self, user_data):
        with session_scope() as db_session:
            orgs = [
                org.to_dataclass() for org in
                GitHubOrg.search_by_dataclass(
                    session=db_session,
                    github_org_data=GitHubOrgData(),
                    only_one=False,
                )
            ]
            orgs = [(str(org.github_id), org.name) for org in orgs]
    else:
        orgs = [(str(org.github_id), org.name) for org in user_orgs]
    if not only_self and (MAIN_ORGANIZATION_ID, MAIN_ORGANIZATION) not in orgs:
        orgs.append((MAIN_ORGANIZATION_ID, MAIN_ORGANIZATION))
    return orgs


def get_groups():
    with session_scope() as db_session:
        groups = [
            group.to_dataclass() for group in db_session.query(Group).all()
        ]
        return [(str(group.id), group.name) for group in groups]
