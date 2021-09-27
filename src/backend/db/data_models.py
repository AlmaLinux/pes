# coding=utf-8
from __future__ import annotations

from copy import deepcopy

import flask
import enum
from dataclasses import (
    dataclass,
    field,
    is_dataclass,
    asdict, fields,
)
from typing import List, Optional

GENERIC_OS_NAME = 'generic'


ReposMapping = {
    'CentOS': {
        'el8-baseos': 'centos8-baseos',
        'el8-appstream': 'centos8-appstream',
        'el8-powertools': 'centos8-powertools',
        'el8-ha': 'centos8-ha',
        'el8-extras': 'centos8-extras',
    },
    'AlmaLinux': {
        'el8-baseos': 'almalinux8-baseos',
        'el8-appstream': 'almalinux8-appstream',
        'el8-powertools': 'almalinux8-powertools',
        'el8-ha': 'almalinux8-ha',
        'el8-extras': 'almalinux8-extras',
    },
    'Rocky': {
        'el8-baseos': 'rocky8-baseos',
        'el8-appstream': 'rocky8-appstream',
        'el8-powertools': 'rocky8-powertools',
        'el8-ha': 'rocky8-ha',
        'el8-extras': 'rocky8-extras',
    },
    'OL': {
        'el8-baseos': 'ol8-baseos',
        'el8-appstream': 'ol8-appstream',
        'el8-powertools': 'ol8-crb',
        'el8-ha': 'ol8-addons',
        'el8-extras': 'ol8-baseos',
    },
}


def change_repos_and_releases_by_mapping(
        action: ActionData,
        target_release: str,
        source_release: str,
) -> None:
    for in_package in action.in_package_set:
        in_pkg_repo = in_package.repository
        if source_release in ReposMapping and \
                in_pkg_repo in ReposMapping[source_release]:
            in_package.repository = ReposMapping[source_release][in_pkg_repo]
    if action.source_release is not None and \
            action.source_release.os_name == GENERIC_OS_NAME:
        action.source_release.os_name = source_release
    for out_package in action.out_package_set:
        out_pkg_repo = out_package.repository
        if target_release in ReposMapping and \
                out_pkg_repo in ReposMapping[target_release]:
            out_package.repository = ReposMapping[target_release][out_pkg_repo]
    if action.target_release is not None and \
            action.target_release.os_name == GENERIC_OS_NAME:
        action.target_release.os_name = target_release


class DataClassesJSONEncoder(flask.json.JSONEncoder):
    """
    Custom JSON encoder for data classes
    """

    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


class PackageType(enum.Enum):
    in_package = 'in'
    out_package = 'out'


class ActionType(enum.Enum):
    present = 'present'
    removed = 'removed'
    deprecated = 'deprecated'
    replaced = 'replaced'
    split = 'split'
    merged = 'merged'
    moved = 'moved'
    renamed = 'renamed'

    @staticmethod
    def get_type_list():
        return [value.value for value in ActionType]

    @staticmethod
    def get_index(name: ActionType):
        return {value.value: i for i, value in enumerate(ActionType)}[name]

    @staticmethod
    def get_name(index: int):
        return {i: value.value for i, value in enumerate(ActionType)}[index]


@dataclass
class BaseData:

    __skip_fields__ = ()
    __convertors__ = {}

    def to_dict(self, force_included: list[str] = tuple()) -> dict:
        result = dict()
        for f in fields(self):
            value_convertor = self.__convertors__.get(f.name)
            value = getattr(self, f.name)
            if value is None or value == []:
                continue
            if value_convertor is not None:
                value = value_convertor(getattr(self, f.name))
            if is_dataclass(value):
                continue
            if f.name in self.__skip_fields__ and f.name not in force_included:
                continue
            result[f.name] = value
        return result

    @property
    def is_empty(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if value is not None:
                return False
        return True


@dataclass
class GitHubOrgData(BaseData):
    name: str = None


@dataclass
class UserData(BaseData):

    __skip_fields__ = (
        'github_orgs',
    )

    github_access_token: str = None
    github_id: int = None
    github_login: str = None
    github_orgs: List[GitHubOrgData] = field(default_factory=list)


@dataclass
class ModuleStreamData(BaseData):
    name: str = None
    stream: str = None

    @staticmethod
    def create_from_json(json_data: dict) -> ModuleStreamData:
        return ModuleStreamData(
            name=json_data.get('name'),
            stream=json_data.get('stream'),
        )


@dataclass
class ReleaseData(BaseData):
    os_name: str = None
    major_version: int = None
    minor_version: int = None

    @staticmethod
    def create_from_json(json_data: dict) -> ReleaseData:
        return ReleaseData(
            os_name=json_data.get('os_name'),
            major_version=json_data.get('major_version'),
            minor_version=json_data.get('minor_version'),
        )


@dataclass
class PackageData(BaseData):

    __skip_fields__ = (
        'id',
    )

    id: int = None
    name: str = None
    repository: str = None
    type: PackageType = None
    module_stream: ModuleStreamData = field(default_factory=ModuleStreamData)

    @staticmethod
    def create_from_json(
            json_data: dict,
            package_type: PackageType,
    ) -> PackageData:
        module_stream = json_data.get('modulestream') or {}
        return PackageData(
            name=json_data.get('name'),
            repository=json_data.get('repository'),
            type=package_type,
            module_stream=ModuleStreamData.create_from_json(module_stream),
        )

    def dump(self) -> dict:
        result = asdict(self)
        del result['type']
        return result


@dataclass
class ActionData(BaseData):

    __skip_fields__ = (
        'id',
        'in_package_set',
        'out_package_set',
    )
    __convertors__ = {
        'arches': lambda i: ','.join(i),
    }

    id: int = None
    version: int = None
    is_approved: Optional[bool] = False
    source_release: ReleaseData = field(default_factory=ReleaseData)
    target_release: ReleaseData = field(default_factory=ReleaseData)
    action: ActionType = None
    in_package_set: List[PackageData] = field(default_factory=list)
    out_package_set: List[PackageData] = field(default_factory=list)
    arches: List[str] = field(default_factory=list)

    @staticmethod
    def create_from_json(json_data: dict) -> ActionData:
        in_package_set = json_data.get('in_packageset') or {}
        out_package_set = json_data.get('out_packageset') or {}
        source_release = json_data.get('initial_release') or {}
        target_release = json_data.get('release') or {}
        return ActionData(
            id=json_data.get('id'),
            source_release=ReleaseData.create_from_json(source_release),
            target_release=ReleaseData.create_from_json(target_release),
            action=json_data.get('action'),
            in_package_set=[PackageData.create_from_json(
                json_data=package,
                package_type=PackageType.in_package,
            ) for package in in_package_set.get('package', [])],
            out_package_set=[PackageData.create_from_json(
                json_data=package,
                package_type=PackageType.out_package,
            ) for package in out_package_set.get('package', [])],
            arches=json_data.get('architectures'),
        )

    def dump(self, source_release: str, target_release: str) -> dict:
        if self.action == ActionType.present:
            change_repos_and_releases_by_mapping(action=self,
                                                 target_release=source_release,
                                                 source_release=target_release)
        else:
            change_repos_and_releases_by_mapping(action=self,
                                                 target_release=target_release,
                                                 source_release=source_release)
        result = asdict(self)
        result['in_packageset'] = {
            'package': list(),
            'set_id': 0,
        }
        result['out_packageset'] = {
            'package': list(),
            'set_id': 0,
        }
        result['action'] = ActionType.get_index(result['action'])
        result['initial_release'] = deepcopy(result['source_release'])
        result['release'] = deepcopy(result['target_release'])
        del result['source_release']
        del result['target_release']
        for in_package in result['in_package_set']:
            result['in_packageset']['package'].append(in_package)
            result['in_packageset']['set_id'] += in_package['id']
            del in_package['type']
            del in_package['id']
        for out_package in result['out_package_set']:
            result['out_packageset']['package'].append(out_package)
            result['out_packageset']['set_id'] += out_package['id']
            del out_package['type']
            del out_package['id']
        del result['in_package_set']
        del result['out_package_set']
        return result
