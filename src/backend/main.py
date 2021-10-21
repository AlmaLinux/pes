# coding=utf-8
import json
from typing import Union, Dict

from requests import RequestException
from webargs import fields
from webargs.flaskparser import use_args

from api.exceptions import (
    BaseCustomException,
    BadRequestFormatExceptioin, CustomHTTPError,
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
    add_or_edit_action_handler, before_request_handler, get_actions_handler,
    get_action_handler, approve_pull_request, get_users_handler,
    get_history_handler, search_actions_handler,
    add_or_edit_group_of_actions_handler, get_groups_of_actions_handler,
    get_group_of_actions_handler,
)
from api.utils import (
    success_result,
    error_result,
    jsonify_response,
    validate_json,
    membership_requires,
    login_requires,
    create_flask_application,
    clear_sessions_fields_before_logout, get_user_organizations,
)
from common.forms import (
    BulkUpload,
    Dump,
    AddAction, AddGroupActions,
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


GET_ACTIONS_ARGS = {
    'package': fields.String()
}


def _prepare_data_dict() -> Dict[str, Union[str, bool]]:
    data = {
        'logged': bool(g.user_data),
        'username': g.user_data.github_login if g.user_data else None,
        'is_our_member': session.get('is_our_member', False),
        'url_args': {},
    }
    return data


@app.before_request
def before_request():
    before_request_handler()


@github.access_token_getter
def token_getter():
    user_data = g.user_data
    if user_data is not None:
        return user_data.github_access_token


@app.route('/github-callback')
@github.authorized_handler
def authorized(access_token):
    next_url = session.pop('next_url', None) or url_for('index')
    if access_token is None:
        return redirect(next_url)
    authorized_handler(access_token=access_token, github=github)
    return redirect(next_url)


@app.route(
    '/login',
    methods=('GET',),
)
def login():
    if session.get('github_id', None) is None:
        session.update({
            'next_url': request.referrer,
        })
        return github.authorize(
            scope='user:email read:org',
        )
    else:
        return 'Already logged in'


@app.route('/logout', methods=('GET',))
@clear_sessions_fields_before_logout
def logout():
    return redirect(url_for('index'))


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
    dump_form.org.choices = get_user_organizations()
    data = {
        'main_title': 'Dump JSON',
        'form': dump_form,
    }
    data.update(_prepare_data_dict())
    if dump_form.validate_on_submit():
        req = dump_handler(
            source_release=dump_form.source_release.data,
            target_release=dump_form.target_release.data,
            organization=dump_form.org.data,
        )
        return jsonify_response(
            result=req.json,
            status_code=HTTP_200_OK,
        )
    return render_template('dump.html', **data)


@app.route(
    '/view_action/<int:action_id>',
    methods=('GET',),
)
def view_action(action_id: int):
    data = {
        'action': get_action_handler(action_id),
    }
    data.update(**_prepare_data_dict())
    return render_template('view_action.html', **data)


@app.route(
    '/add_action',
    methods=('GET', 'POST',),
)
@login_requires
def add_action():
    add_action_form = AddAction()
    add_action_form.org.choices = get_user_organizations(add_specific=True)
    data = {
        'main_title': 'Add an action',
        'form': add_action_form,
        'is_added': False,
        'saving_button_name': 'Add action',
    }
    data.update(_prepare_data_dict())
    if add_action_form.validate_on_submit():
        add_or_edit_action_handler(
            add_action_form=add_action_form,
            is_new=True,
        )
        data['is_added'] = True
    return render_template('add_action.html', **data)


@app.route(
    '/add_group',
    methods=('GET', 'POST',),
)
@login_requires
def add_group():
    add_group_form = AddGroupActions()
    add_group_form.org.choices = get_user_organizations(
        add_specific=False,
        only_self=True,
    )
    data = {
        'main_title': 'Add an group of actions',
        'form': add_group_form,
        'is_added': False,
        'saving_button_name': 'Add group of actions',
    }
    data.update(_prepare_data_dict())
    if add_group_form.validate_on_submit():
        add_or_edit_group_of_actions_handler(
            add_group_form=add_group_form,
            is_new=True,
        )
        data['is_added'] = True
    return render_template('add_group_of_actions.html', **data)


@app.route(
    '/edit_action/<int:action_id>',
    methods=('GET', 'POST',),
)
@login_requires
def edit_action(action_id: int):
    edit_action_form = AddAction()
    edit_action_form.org.choices = get_user_organizations(add_specific=False)
    action = get_action_handler(action_id)
    if request.method == 'GET':
        edit_action_form.load_from_dataclass(action=action)
    data = {
        'main_title': 'Edit an action',
        'form': edit_action_form,
        'is_added': False,
        'saving_button_name': 'Save action' if action.is_approved
        else 'Approve & save action',
    }
    data.update(_prepare_data_dict())
    if edit_action_form.validate_on_submit():
        add_or_edit_action_handler(
            add_action_form=edit_action_form,
            is_new=False,
        )
        data['is_added'] = True
        data['action'] = get_action_handler(action_id)
        del data['main_title']
        return redirect(url_for('view_action', action_id=action_id))
    return render_template('add_action.html', **data)


@app.route(
    '/edit_group/<int:group_id>',
    methods=('GET', 'POST',),
)
@login_requires
def edit_group(group_id: int):
    edit_group_of_actions_form = AddGroupActions()
    edit_group_of_actions_form.org.choices = get_user_organizations(
        add_specific=False,
        only_self=True,
    )
    group = get_group_of_actions_handler(group_id)
    if request.method == 'GET':
        edit_group_of_actions_form.load_from_dataclass(group)
    data = {
        'main_title': 'Edit an group of actions',
        'form': edit_group_of_actions_form,
        'is_added': False,
        'saving_button_name': 'Save group of actions',
    }
    data.update(_prepare_data_dict())
    if edit_group_of_actions_form.validate_on_submit():
        add_or_edit_group_of_actions_handler(
            add_group_form=edit_group_of_actions_form,
            is_new=False,
        )
        data['is_added'] = True
        data['group'] = get_group_of_actions_handler(group_id)
        del data['main_title']
        return redirect(url_for('get_group_of_actions'))
    return render_template('add_group_of_actions.html', **data)


@app.route('/users', methods=('GET',))
@app.route('/users/<int:page>', methods=('GET',))
@login_requires
def get_users(page: int = 1):
    list_users, pagination = get_users_handler(page=page)
    setattr(pagination, 'page', page)
    data = {
        'main_title': 'List of registered users',
        'users': list_users,
        'pagination': pagination,
    }
    data.update(_prepare_data_dict())

    return render_template('users.html', **data)


@app.route('/group_of_actions', methods=('GET',))
@app.route('/group_of_actions/<int:page>', methods=('GET',))
@login_requires
def get_group_of_actions(page: int = 1):
    list_groups_of_actions, pagination = get_groups_of_actions_handler(
        page=page
    )
    setattr(pagination, 'page', page)
    data = {
        'main_title': 'List of groups of actions',
        'groups': list_groups_of_actions,
        'pagination': pagination,
    }
    data.update(_prepare_data_dict())

    return render_template('group_of_actions.html', **data)


@app.route('/history', methods=('GET',))
@app.route('/history/<int:page>', methods=('GET',))
@app.route('/history_by_action/<int:action_id>', methods=('GET',))
@app.route('/history_by_action/<int:action_id>/<int:page>', methods=('GET',))
@app.route('/history_by_user/<string:username>', methods=('GET',))
@app.route('/history_by_user/<string:username>/<int:page>', methods=('GET',))
@login_requires
def get_history(page: int = 1, action_id: int = None, username: str = None):
    list_actions_history, pagination = get_history_handler(
        page=page,
        action_id=action_id,
        username=username,
    )
    setattr(pagination, 'page', page)
    if action_id is not None:
        main_title = f'History of action #{action_id}'
    elif username is not None:
        main_title = f'History of changes made by user {username}'
    else:
        main_title = 'Actions history'
    data = {
        'main_title': main_title,
        'actions_history': list_actions_history,
        'pagination': pagination,
        'action_id': action_id,
    }
    data.update(_prepare_data_dict())

    return render_template('history.html', **data)


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


@app.route('/actions', methods=('GET',))
@app.route('/actions/<int:page>', methods=('GET',))
@use_args(GET_ACTIONS_ARGS, location='query')
def get_list_actions(url_args, page: int = 1):

    data = {
        'main_title': 'List of actions',
        'search_value': url_args.get('package', ''),
    }
    data.update(_prepare_data_dict())
    data['url_args'] = url_args
    if url_args:
        list_actions, pagination = search_actions_handler(
            params=url_args,
            page=page,
        )
    else:
        list_actions, pagination = get_actions_handler(page=page)
    data.update({
        'actions': list_actions,
        'pagination': pagination,
    })
    setattr(pagination, 'page', page)

    return render_template('actions.html', **data)


@app.route(
    '/api/pull_requests',
    methods=('POST', 'GET'),
)
@success_result
@error_result
@validate_json
@membership_requires
def pull_requests():
    data = request.json
    if request.method == 'POST':
        return approve_pull_request(data)


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
        organization=data['org'],
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


@app.errorhandler(CustomHTTPError)
def handle_internal_server_error(error: CustomHTTPError) -> Response:
    logger.exception(error)
    return jsonify_response(
        result={
            'reason': error.reason,
            'url': error.url,
        },
        status_code=error.status_code,
    )


if __name__ == '__main__':
    app.run(
        debug=True,
        host='0.0.0.0',
        port=8080,
    )
