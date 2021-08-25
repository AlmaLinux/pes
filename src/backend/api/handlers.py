# coding=utf-8
import datetime
import json
from typing import (
    List,
    Optional,
)

from api.exceptions import BadRequestFormatExceptioin
from common.forms import AddAction
from db.data_models import ActionData, ActionType, GENERIC_OS_NAME
from db.utils import session_scope
from db.db_models import Action, User
from flask_github import GitHub
from common.sentry import (
    get_logger,
)
from api.utils import create_flask_client, is_our_member
from flask import request, url_for, Request, session, g

logger = get_logger(__name__)


def before_request_handler():
    g.user_data = None
    if 'user_id' in session:
        with session_scope() as db_session:
            db_user = db_session.query(User).get(
                session['user_id'],
            )  # type: User
            if db_user is not None:
                g.user_data = db_user.to_dataclass()
            else:
                session.pop('user_id')


def authorized_handler(access_token: str, github: GitHub):
    with session_scope() as db_session:
        db_user = db_session.query(User).filter_by(
            github_access_token=access_token
        ).first()
        if db_user is None:
            db_user = User(access_token)
            db_session.add(db_user)

        db_user.github_access_token = access_token

        # Not necessary to get these details here
        # but it helps humans to identify users easily.
        g.user_data = db_user.to_dataclass()
        github_user = github.get('/user')
        db_user.github_id = github_user['id']
        db_user.github_login = github_user['login']
        if github_user['organizations_url']:
            orgs = [
                org['login'] for org in
                github.get(github_user['organizations_url'])
            ]
            db_user.github_orgs = ','.join(orgs)
        db_session.flush()
        g.user_data = db_user.to_dataclass()

        session.update({
            'user_id': db_user.id,
            'is_our_member': is_our_member(github=github)
        })


def push_action(action_data: ActionData) -> None:
    with session_scope() as db_session:
        Action.create_from_dataclass(
            action_data=action_data,
            session=db_session,
        )
        db_session.flush()


def get_actions(
        action_data: ActionData = ActionData(is_approved=True),
) -> Optional[List[ActionData]]:
    with session_scope() as db_session:
        return [action.to_dataclass() for action in Action.search_by_dataclass(
            action_data=action_data,
            session=db_session,
        )]


def remove_action(action_data: ActionData) -> None:
    with session_scope() as db_session:
        Action.delete_action(action_data=action_data, session=db_session)
        db_session.flush()


def modify_action(action_data: ActionData) -> None:
    with session_scope() as db_session:
        Action.update_from_dataclass(
            action_data=action_data,
            session=db_session,
        )
        db_session.flush()


def dump_pes_json(source_release: str, target_release: str):

    legal_notice_value = 'AlmaLinux Foundation, Oracle and Others 2021 ©'

    def filter_action_by_releases(
            action: ActionData,
    ) -> bool:
        if (action.source_release is None or action.source_release.os_name in (
            GENERIC_OS_NAME,
            source_release,
        )) and (action.target_release is None or action.target_release.os_name in (
            GENERIC_OS_NAME,
            target_release,
        )):
            return True
        return False

    actions = get_actions()
    result = {
        'legal_notice': legal_notice_value,
        'timestamp': datetime.datetime.strftime(
            datetime.datetime.now(),
            # YearMonthDayHoursMinutesZ
            '%Y%m%d%H%MZ',
        ),
        'packageinfo': [
            action.dump(
                source_release=source_release,
                target_release=target_release,
            ) for action in actions if
            filter_action_by_releases(action) and action.is_approved
        ],
    }

    return result


def bulk_upload_handler(json_dict: dict) -> None:
    if 'packageinfo' not in json_dict:
        raise BadRequestFormatExceptioin('The JSON has no field "packageinfo"')
    actions = json_dict['packageinfo']
    for i, action in enumerate(actions):
        action['action'] = ActionType.get_name(action['action'])
        action.pop('id', None)
        for root_key in (
            'initial_release',
            'release',
            'in_packageset',
            'out_packageset',
        ):
            for unnecessary_key in (
                'modified',
                'tag',
                'z_stream',
                'set_id',
            ):
                (action.get(root_key) or {}).pop(unnecessary_key, None)
        logger.info('Uploaded action "%s" from "%s"', i, len(actions))
        create_flask_client().put(
            url_for('actions'),
            data=json.dumps(action),
            headers=list(request.headers),
            content_type='application/json',
        )


def dump_handler(source_release: str, target_release: str) -> Request:
    return create_flask_client().get(
        url_for('dump'),
        data=json.dumps({
            'source_release': source_release,
            'target_release': target_release,
        }),
        headers=list(request.headers),
        content_type='application/json',
    )


def add_action_handler(add_action_form: AddAction) -> None:
    json_dict = {
        'action': add_action_form.action.data,
        'in_packageset': None,
        'out_packageset': None,
        'initial_release': None,
        'release': None,
        'architectures': [
            arch.strip() for arch in add_action_form.arches.data.split(',')
        ],
    }
    if add_action_form.source_generic.data:
        json_dict['initial_release'] = {}
        json_dict['initial_release']['os_name'] = GENERIC_OS_NAME
        json_dict['initial_release']['major_version'] = add_action_form. \
            source_major_version.data
        json_dict['initial_release']['minor_version'] = add_action_form. \
            source_minor_version.data
    elif add_action_form.source_release != '':
        json_dict['initial_release'] = {}
        json_dict['initial_release']['os_name'] = add_action_form. \
            source_release.data
        json_dict['initial_release']['major_version'] = add_action_form. \
            source_major_version.data
        json_dict['initial_release']['minor_version'] = add_action_form. \
            source_minor_version.data
    if add_action_form.target_generic.data:
        json_dict['release'] = {}
        json_dict['release']['os_name'] = GENERIC_OS_NAME
        json_dict['release']['major_version'] = add_action_form. \
            target_major_version.data
        json_dict['release']['minor_version'] = add_action_form. \
            target_minor_version.data
    elif add_action_form.target_release != '':
        json_dict['release'] = {}
        json_dict['release']['os_name'] = add_action_form. \
            source_release.data
        json_dict['release']['major_version'] = add_action_form. \
            target_major_version.data
        json_dict['release']['minor_version'] = add_action_form. \
            target_minor_version.data
    if add_action_form.in_package_set.data:
        json_dict['in_packageset'] = {
            'package': [],
        }
    if add_action_form.out_package_set.data:
        json_dict['out_packageset'] = {
            'package': [],
        }
    for pkg_data in add_action_form.in_package_set.data.split():
        name, repo, module_name, module_stream = [
            el.strip() for el in pkg_data.split(',')
        ]
        if not module_name or not module_stream:
            module_data = None
        else:
            module_data = {
                'name': module_name,
                'stream': module_stream,
            }
        json_dict['in_packageset']['package'].append({
            'name': name,
            'repository': repo,
            'module_stream': module_data,
        })
    for pkg_data in add_action_form.out_package_set.data.split():
        name, repo, module_name, module_stream = [
            el.strip() for el in pkg_data.split(',')
        ]
        if not module_name or not module_stream:
            module_data = None
        else:
            module_data = {
                'name': module_name,
                'stream': module_stream,
            }
        json_dict['out_packageset']['package'].append({
            'name': name,
            'repository': repo,
            'module_stream': module_data,
        })
    create_flask_client().put(
        url_for('actions'),
        data=json.dumps(json_dict),
        headers=list(request.headers),
        content_type='application/json',
    )
