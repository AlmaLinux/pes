# coding=utf-8
import datetime
import json
from itertools import zip_longest
from typing import (
    List,
    Optional, Union, Tuple, Dict,
)

from sqlalchemy_pagination import Page, paginate

from api.exceptions import BadRequestFormatExceptioin
from common.forms import AddAction
from db.data_models import ActionData, ActionType, GENERIC_OS_NAME, UserData, \
    GitHubOrgData, ActionHistoryData, GLOBAL_ORGANIZATION
from db.utils import session_scope
from db.db_models import Action, User, GitHubOrg, ActionHistory, Package
from flask_github import GitHub
from common.sentry import (
    get_logger,
)
from api.utils import create_flask_client, is_our_member, raise_for_status
from flask import request, url_for, session, g
from werkzeug.test import TestResponse

logger = get_logger(__name__)


PAGE_SIZE = 20


def before_request_handler():
    g.user_data = None
    if 'user_id' in session:
        with session_scope() as db_session:
            db_user = db_session.query(User).filter_by(
                id=session['user_id'],
            ).one_or_none()  # type: User
            if db_user is not None:
                g.user_data = db_user.to_dataclass()
            else:
                session.pop('user_id')


def authorized_handler(access_token: str, github: GitHub):
    with session_scope() as db_session:
        g.user_data = UserData(
            github_access_token=access_token,
        )
        github_user = github.get('/user')
        user_data = UserData(
            github_access_token=access_token,
            github_id=github_user['id'],
            github_login=github_user['login'],
        )
        github_orgs_data = [
            GitHubOrgData(name=org['organization']['login']) for org in
            github.get('/user/memberships/orgs')
            if org['state'] == 'active'
        ]
        db_user = User.search_by_dataclass(
            session=db_session,
            user_data=user_data,
            only_one=True,
        )
        if db_user is None:
            db_user = User.create_from_dataclass(
                session=db_session,
                user_data=user_data,
            )

        g.user_data = db_user.to_dataclass()
        github_orgs = [
            GitHubOrg.search_by_dataclass(
                session=db_session,
                github_org_data=org_data,
                only_one=True,
            ) for org_data in github_orgs_data
        ]
        db_user.github_orgs = github_orgs
        db_session.flush()
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


def get_actions(
        action_data: ActionData = ActionData(is_approved=True),
) -> Optional[Union[List[ActionData], Page]]:
    with session_scope() as db_session:
        return [action.to_dataclass() for action in
                Action.search_by_dataclass(
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


def dump_pes_json(
        source_release: str,
        target_release: str,
        organization: str,
):

    legal_notice_value = 'Copyright (c) 2021 Oracle, AlmaLinux OS Foundation'

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

    if organization == GLOBAL_ORGANIZATION:
        action_data = ActionData(is_approved=True)
    else:
        action_data = ActionData(is_approved=True, github_org=organization)
    actions = get_actions(action_data=action_data)
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
            filter_action_by_releases(action)
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
        result = create_flask_client().put(
            url_for('actions'),
            data=json.dumps(action),
            headers=list(request.headers),
            content_type='application/json',
        )
        raise_for_status(result)


def dump_handler(
        source_release: str,
        target_release: str,
        organization: str,
) -> TestResponse:
    result = create_flask_client().get(
        url_for('dump'),
        data=json.dumps({
            'source_release': source_release,
            'target_release': target_release,
            'org': organization,
        }),
        headers=list(request.headers),
        content_type='application/json',
    )
    raise_for_status(result)
    return result


def add_or_edit_action_handler(add_action_form: AddAction, is_new: bool) -> None:
    json_dict = {
        'action': add_action_form.action.data,
        'org': add_action_form.org.data,
        'in_packageset': None,
        'out_packageset': None,
        'initial_release': None,
        'release': None,
        'architectures': [
            arch.strip() for arch in add_action_form.arches.data.split(',')
        ],
    }
    if not is_new:
        json_dict['id'] = int(add_action_form.id.data)
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
            target_release.data
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
            'modulestream': module_data,
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
            'modulestream': module_data,
        })
    flask_client = create_flask_client()
    if is_new:
        http_method = flask_client.put
    else:
        http_method = flask_client.post
    response = http_method(
        url_for('actions'),
        data=json.dumps(json_dict),
        headers=list(request.headers),
        content_type='application/json',
    )
    raise_for_status(response)


def get_actions_handler(
        page: int,
        page_size: int = PAGE_SIZE,
) -> Tuple[List[ActionData], Page]:
    with session_scope() as db_session:
        pagination = Action.search_by_dataclass(
            action_data=ActionData(is_approved=None),
            session=db_session,
            page=page,
            page_size=page_size,
        )
        actions = [action.to_dataclass() for action in pagination.items]
    for action in actions:
        setattr(action, 'packages', list(zip_longest(
            action.in_package_set,
            action.out_package_set,
        )))
    return actions, pagination


def search_actions_handler(
        params: dict,
        page: int,
        page_size: int = PAGE_SIZE,
) -> Tuple[List[ActionData], Page]:
    with session_scope() as db_session:
        package_name = params.get('package')
        packages = db_session.query(Package).filter(
            Package.name.like(f'%{package_name}%')
        ).all()
        query_actions_1 = db_session.query(Action).filter(
            Action.in_package_set.any(
                Package.id.in_(
                    pkg.id for pkg in packages
                )
            )
        )
        query_actions_2 = db_session.query(Action).filter(
            Action.out_package_set.any(
                Package.id.in_(
                    pkg.id for pkg in packages
                )
            )
        )
        total_query = query_actions_1.union(query_actions_2)
        pagination = paginate(total_query, page=page, page_size=page_size)
        actions = [action.to_dataclass() for action in pagination.items]
    for action in actions:
        setattr(action, 'packages', list(zip_longest(
            action.in_package_set,
            action.out_package_set,
        )))
    return actions, pagination


def get_action_handler(action_id: int) -> Optional[ActionData]:
    with session_scope() as db_session:
        actions = Action.search_by_dataclass(
            action_data=ActionData(id=action_id, is_approved=None),
            session=db_session,
        )
        if actions:
            action = actions[0].to_dataclass()
        else:
            return
    setattr(action, 'packages', list(zip_longest(
        action.in_package_set,
        action.out_package_set,
    )))
    return action


def approve_pull_request(data: dict[str, int]):
    with session_scope() as db_session:
        actions = Action.search_by_dataclass(
            action_data=ActionData(id=data['id'], is_approved=None),
            session=db_session,
        )
        action = actions[0]
        action.is_approved = True
        db_session.flush()


def get_users_handler(
        page: int,
        page_size: int = PAGE_SIZE,
) -> Tuple[List[ActionData], Page]:
    with session_scope() as db_session:
        user_data = g.user_data  # type: UserData
        pagination = User.search_by_dataclass(
            session=db_session,
            user_data=UserData(
                github_orgs=None if session.get('is_our_member', False)
                else user_data.github_orgs,
            ),
            only_one=False,
            page_size=page_size,
            page=page,
        )
        users = [user.to_dataclass() for user in pagination.items]
        return users, pagination


def get_history_handler(
        page: int,
        action_history_data: ActionHistoryData = ActionHistoryData(),
        action_id: int = None,
        username: str = None,
        page_size: int = PAGE_SIZE,
) -> Tuple[List[ActionHistoryData], Page]:
    with session_scope() as db_session:
        if action_id is not None:
            pagination = ActionHistory.get_history_by_action_id(
                session=db_session,
                action_id=action_id,
                page_size=page_size,
                page=page,
            )
        elif username is not None:
            pagination = ActionHistory.get_history_by_username(
                session=db_session,
                username=username,
                page_size=page_size,
                page=page,
            )
        else:
            pagination = ActionHistory.search_by_dataclass(
                session=db_session,
                action_history_data=action_history_data,
                only_one=False,
                page_size=page_size,
                page=page,
            )
        actions_history = [
            action_history.to_dataclass() for action_history
            in pagination.items
        ]
        return actions_history, pagination
