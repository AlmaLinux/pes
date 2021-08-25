# coding=utf-8
import json
from typing import Union, Dict

from api.exceptions import (
    BaseCustomException,
    BadRequestFormatExceptioin,
)
from api.handlers import (
    push_action,
    get_actions,
    dump_pes_json,
    remove_action,
    modify_action,
    bulk_upload_handler,
    dump_handler,
    authorized_handler,
    add_action_handler, before_request_handler,
)
from api.utils import (
    success_result,
    error_result,
    jsonify_response,
    validate_json,
    membership_requires,
    login_requires,
    create_flask_application,
    clear_sessions_fields_before_logout,
)
from common.forms import (
    BulkUpload,
    Dump,
    AddAction,
)
from common.sentry import (
    init_sentry_client,
    get_logger,
)
from db.data_models import ActionData
from flask import (
    request,
    Response,
    render_template,
    redirect,
    g,
    url_for,
    session,
)
from flask_api.status import HTTP_200_OK
from flask_github import GitHub
from werkzeug.exceptions import InternalServerError

app = create_flask_application()
init_sentry_client()
logger = get_logger(__name__)
github = GitHub(app)


def _prepare_data_dict() -> Dict[str, Union[str, bool]]:
    data = {
        'logged': bool(g.user_data),
        'username': g.user_data.github_login if g.user_data else None,
    }
    return data


@app.before_request
def before_request():
    before_request_handler()


@app.route('/')
def index():
    return render_template('index.html', **_prepare_data_dict())


@app.route(
    '/bulk_upload',
    methods=('GET', 'POST',),
)
@membership_requires
def bulk_upload():
    bulk_upload_form = BulkUpload()
    data = {
        'main_title': 'Bulk upload',
        'form': bulk_upload_form,
        'is_uploaded': False,
    }
    data.update(_prepare_data_dict())
    if bulk_upload_form.validate_on_submit():
        try:
            json_dict = json.load(bulk_upload_form.uploaded_file.data)
        except json.JSONDecodeError:
            raise BadRequestFormatExceptioin('The JSON file is incorrect')
        bulk_upload_handler(json_dict=json_dict)
        data['is_uploaded'] = True,
    return render_template('bulk_upload.html', **data)


@app.route(
    '/dump',
    methods=('GET', 'POST',),
)
def dump_json():
    dump_form = Dump()
    data = {
        'main_title': 'Dump JSON',
        'form': dump_form,
    }
    data.update(_prepare_data_dict())
    if dump_form.validate_on_submit():
        req = dump_handler(
            source_release=dump_form.source_release.data,
            target_release=dump_form.target_release.data,
        )
        return jsonify_response(
            result=req.json,
            status_code=HTTP_200_OK,
        )
    return render_template('dump.html', **data)


@app.route(
    '/add_action',
    methods=('GET', 'POST',),
)
@login_requires
def add_action():
    add_action_form = AddAction()
    data = {
        'main_title': 'Add an action',
        'form': add_action_form,
        'is_added': False,
    }
    data.update(_prepare_data_dict())
    if add_action_form.validate_on_submit():
        add_action_handler(add_action_form=add_action_form)
        data['is_added'] = True
    return render_template('add_action.html', **data)


@github.access_token_getter
def token_getter():
    user_data = g.user_data
    if user_data is not None:
        return user_data.github_access_token


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    next_url = request.args.get('next') or url_for('index')
    if access_token is None:
        return redirect(next_url)
    authorized_handler(access_token=access_token, github=github)
    return redirect(next_url)


@app.route(
    '/login',
    methods=('GET',),
)
def login():
    if session.get('user_id', None) is None:
        return github.authorize(scope='user:email read:org')
    else:
        return 'Already logged in'


@app.route(
    '/logout',
    methods=('GET',),
)
@clear_sessions_fields_before_logout
def logout():
    return redirect(url_for('index'))


@app.route(
    '/api/actions',
    methods=('GET', 'PUT', 'DELETE', 'POST'),
)
@success_result
@error_result
@validate_json
@login_requires
def actions():
    data = request.json
    _is_our_member = session.get('is_our_member', False)
    if request.method == 'PUT':
        action = ActionData.create_from_json(data)
        action.is_approved = _is_our_member
        return push_action(action)
    elif request.method == 'GET':
        action = ActionData.create_from_json(data)
        action.is_approved = _is_our_member
        return get_actions(action)
    elif request.method == 'POST':
        action = ActionData.create_from_json(data)
        action.is_approved = _is_our_member
        return modify_action(action)
    elif request.method == 'DELETE':
        action = ActionData.create_from_json(data)
        action.is_approved = _is_our_member
        return remove_action(action)


@app.route(
    '/api/dump',
    methods=('GET',),
)
@success_result
@error_result
@validate_json
def dump():
    data = request.json
    return dump_pes_json(
        source_release=data['source_release'],
        target_release=data['target_release'],
    )


@app.errorhandler(BaseCustomException)
def handle_jwt_exception(error: BaseCustomException) -> Response:
    logger.exception(error.message, *error.args)
    return jsonify_response(
        result={
            'message': str(error),
        },
        status_code=error.response_code,
    )


@app.errorhandler(InternalServerError)
def handle_internal_server_error(error: InternalServerError) -> Response:
    logger.exception(error)
    return jsonify_response(
        result={
            'message': 'Internal server error',
        },
        status_code=error.code,
    )


if __name__ == '__main__':
    app.run(
        debug=True,
        host='0.0.0.0',
        port=8080,
    )
