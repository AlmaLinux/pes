# coding=utf-8
from __future__ import annotations

import json
from typing import List, Optional, Union

from flask import g
from sqlalchemy_pagination import paginate, Page
from api.exceptions import DBRecordNotFound
from db.data_models import (
    ActionType,
    ActionData,
    PackageData,
    PackageType,
    ModuleStreamData,
    ReleaseData,
    UserData, GitHubOrgData, ActionHistoryData, DataClassesJSONEncoder,
)
from sqlalchemy import (
    Column,
    String,
    Integer,
    Table,
    ForeignKey,
    Boolean,
    Enum,
    null,
)
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship, Session

from common.sentry import (
    get_logger,
)

logger = get_logger(__name__)

Base = declarative_base()


users_github_orgs = Table(
    'users_github_orgs',
    Base.metadata,
    Column(
        'user_id', Integer, ForeignKey(
            'users.id',
            ondelete='CASCADE',
        ),
    ),
    Column(
        'github_org_id', Integer, ForeignKey(
            'github_orgs.id',
            ondelete='CASCADE',
        )
    ),
)


class GitHubOrg(Base):
    __tablename__ = 'github_orgs'
    id = Column(Integer, primary_key=True)
    name = Column(String)

    @staticmethod
    def search_by_dataclass(
            session: Session,
            github_org_data: GitHubOrgData,
            only_one: bool,
    ) -> Optional[Union[List[GitHubOrg], GitHubOrg]]:
        if github_org_data is None:
            return
        query = session.query(GitHubOrg).filter_by(
            **github_org_data.to_dict(),
        )
        if only_one:
            return query.one_or_none()
        else:
            return query.all()

    def to_dataclass(self) -> GitHubOrgData:
        return GitHubOrgData(
            name=self.name,
        )

    @staticmethod
    def create_from_dataclass(
            session: Session,
            github_org_data: GitHubOrgData,
    ) -> GitHubOrg:
        github_org = session.query(GitHubOrg).filter_by(
            **github_org_data.to_dict(),
        ).one_or_none()
        if github_org is None:
            github_org = GitHubOrg(
                **github_org_data.to_dict(),
            )
            session.add(github_org)
            session.flush()
        return github_org


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    github_access_token = Column(String)
    github_id = Column(Integer)
    github_login = Column(String)
    github_orgs = relationship(
        'GitHubOrg',
        secondary=users_github_orgs,
        passive_deletes=True,
        backref='users',
    )

    @staticmethod
    def search_by_dataclass(
            session: Session,
            user_data: UserData,
            only_one: bool,
            page_size: int = None,
            page: int = None,
    ) -> Union[List[User], User]:
        orgs = []
        if user_data.github_orgs is not None:
            orgs = [
                GitHubOrg.search_by_dataclass(
                    session=session,
                    github_org_data=org,
                    only_one=True,
                ) for org in user_data.github_orgs
            ]
        query = session.query(User).filter_by(
            **user_data.to_dict(),
        )
        if orgs:
            query = query.filter(
                User.github_orgs.any(
                    GitHubOrg.id.in_(
                        org.id for org in orgs
                    )
                ),
            )
        if page_size is None or page is None:
            if only_one:
                return query.one_or_none()
            else:
                return query.all()
        else:
            result = paginate(query, page=page, page_size=page_size)
        return result

    @staticmethod
    def create_from_dataclass(
            session: Session,
            user_data: UserData,
    ) -> User:
        user = session.query(User).filter_by(
            **user_data.to_dict(),
        ).one_or_none()
        github_orgs = [
            GitHubOrg.create_from_dataclass(
                session=session,
                github_org_data=github_org_data,
            ) for github_org_data in user_data.github_orgs
        ]
        if user is None:
            user = User(
                **user_data.to_dict()
            )
            user.github_orgs = github_orgs
            session.add(user)
        user.github_access_token = user_data.github_access_token
        session.flush()
        return user

    def to_dataclass(self) -> UserData:
        return UserData(
            github_access_token=self.github_access_token,
            github_id=self.github_id,
            github_login=self.github_login,
            github_orgs=[
                github_org.to_dataclass() for github_org in self.github_orgs
            ],
        )


class ActionHistory(Base):
    __tablename__ = 'actions_history'

    id = Column(Integer, primary_key=True)
    action_before = Column(String, nullable=True)
    action_after = Column(String, nullable=True)
    history_type = Column(String, nullable=False)
    username = Column(String, nullable=False)
    action_id = Column(Integer, nullable=False)

    @staticmethod
    def search_by_dataclass(
            session: Session,
            action_history_data: ActionHistoryData,
            only_one: bool,
            page_size: int = None,
            page: int = None,
    ) -> Union[List[ActionHistory], ActionHistory]:
        query = session.query(ActionHistory).filter_by(
            **action_history_data.to_dict(),
        )
        if page_size is None or page is None:
            if only_one:
                return query.one_or_none()
            else:
                return query.all()
        else:
            result = paginate(query, page=page, page_size=page_size)
        return result

    @staticmethod
    def get_history_by_action_id(
            session: Session,
            action_id: int,
            page_size: int = None,
            page: int = None,
    ) -> List[ActionHistory]:
        query = session.query(ActionHistory).filter_by(action_id=action_id)
        if page_size is None or page is None:
            return query.all()
        else:
            return paginate(query, page=page, page_size=page_size)

    @staticmethod
    def get_history_by_username(
            session: Session,
            username: str,
            page_size: int = None,
            page: int = None,
    ) -> List[ActionHistoryData]:
        query = session.query(ActionHistory).filter_by(username=username)
        if page_size is None or page is None:
            return query.all()
        else:
            return paginate(query, page=page, page_size=page_size)

    @staticmethod
    def create_from_dataclass(
            session: Session,
            action_history_data: ActionHistoryData,
    ) -> ActionHistory:
        action_history = ActionHistory(
            **action_history_data.to_dict(),
        )
        session.add(action_history)
        session.flush()
        return action_history

    def to_dataclass(self) -> ActionHistoryData:
        return ActionHistoryData(
            action_before=self.action_before,
            action_after=self.action_after,
            history_type=self.history_type,
            username=self.username,
            action_id=self.action_id,
        )


class ModuleStream(Base):
    __tablename__ = 'modules_streams'

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    stream = Column(String, nullable=False)

    def to_dataclass(self) -> ModuleStreamData:
        return ModuleStreamData(
            name=self.name,
            stream=self.stream,
        )

    @staticmethod
    def create_from_dataclass(
            module_stream_data: ModuleStreamData,
            session: Session,
    ) -> Optional[ModuleStream]:
        if module_stream_data.is_empty:
            return
        module_stream = session.query(ModuleStream).filter_by(
            **module_stream_data.to_dict(),
        ).one_or_none()
        if module_stream is None:
            module_stream = ModuleStream(
                **module_stream_data.to_dict(),
            )
            session.add(module_stream)
        return module_stream

    @staticmethod
    def search_by_dataclass(
            module_stream_data: ModuleStreamData,
            session: Session,
    ) -> Optional[List[ModuleStream]]:
        if module_stream_data.is_empty:
            return None
        return session.query(ModuleStream).filter_by(
            **module_stream_data.to_dict()
        ).all()


class Release(Base):
    __tablename__ = 'releases'

    id = Column(Integer, nullable=False, primary_key=True)
    os_name = Column(String, nullable=False)
    major_version = Column(Integer, nullable=False)
    minor_version = Column(Integer, nullable=False)

    def to_dataclass(self) -> ReleaseData:
        return ReleaseData(
            os_name=self.os_name,
            major_version=self.major_version,
            minor_version=self.minor_version,
        )

    @staticmethod
    def create_from_dataclass(
            release_data: ReleaseData,
            session: Session,
    ) -> Optional[Release]:
        if release_data.is_empty:
            return None
        release = session.query(Release).filter_by(
            **release_data.to_dict(),
        ).one_or_none()
        if release is None:
            release = Release(
                **release_data.to_dict(),
            )
            session.add(release)
        return release

    @staticmethod
    def search_by_dataclass(
            release_data: ReleaseData,
            session: Session,
    ) -> Optional[List[Release]]:
        if release_data.is_empty:
            return None
        return session.query(Release).filter_by(
            **release_data.to_dict()
        ).all()


actions_packages_out = Table(
    'actions_packages_out',
    Base.metadata,
    Column(
        'action_id', Integer, ForeignKey(
            'actions.id',
            ondelete='CASCADE',
        ),
    ),
    Column(
        'package_id', Integer, ForeignKey(
            'packages.id',
            ondelete='CASCADE',
        )
    ),
)


actions_packages_in = Table(
    'actions_packages_in',
    Base.metadata,
    Column(
        'action_id', Integer, ForeignKey(
            'actions.id',
            ondelete='CASCADE',
        ),
    ),
    Column(
        'package_id', Integer, ForeignKey(
            'packages.id',
            ondelete='CASCADE',
        )
    ),
)


class Package(Base):
    __tablename__ = 'packages'

    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    repository = Column(String, nullable=False)
    type = Column(Enum(PackageType), nullable=False)
    module_stream_id = Column(Integer, ForeignKey(
        'modules_streams.id',
        ondelete='CASCADE',
    ))
    module_stream = relationship(
        'ModuleStream',
        foreign_keys=[module_stream_id],
        passive_deletes=True,
        backref='packages',
    )

    def to_dataclass(self) -> PackageData:
        return PackageData(
            id=self.id,
            name=self.name,
            repository=self.repository,
            type=self.type.value,
            module_stream=self.module_stream.to_dataclass() if
            self.module_stream else None,
        )

    @staticmethod
    def create_from_dataclass(
            package_data: PackageData,
            session: Session,
    ) -> Package:
        module_stream = ModuleStream.create_from_dataclass(
            module_stream_data=package_data.module_stream,
            session=session,
        )
        package = session.query(Package).filter_by(
            **package_data.to_dict(),
        ).filter(
            module_stream == module_stream or null(),
        ).one_or_none()
        if package is None:
            package = Package(
                **package_data.to_dict(),
            )
            if module_stream is not None:
                package.module_stream = module_stream
            session.add(package)
        session.flush()
        session.refresh(package)
        return package

    @staticmethod
    def search_by_dataclass(
            package_data: PackageData,
            session: Session,
    ) -> Optional[List[Package]]:
        if package_data.is_empty:
            return None
        module_stream_data = package_data.module_stream
        module_stream = ModuleStream.search_by_dataclass(
            module_stream_data=module_stream_data,
            session=session,
        )
        package_query = session.query(Package).filter_by(
            **package_data.to_dict()
        )
        if module_stream is not None:
            package_query = package_query.filter(
                module_stream == module_stream,
            )
        return package_query.all()


class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, nullable=False, primary_key=True)
    version = Column(Integer, nullable=False, default=1)
    is_approved = Column(Boolean, nullable=False, default=False)
    github_org = Column(String, nullable=True)
    source_release_id = Column(Integer, ForeignKey(
        'releases.id',
        ondelete='CASCADE',
    ))
    source_release = relationship(
        'Release',
        foreign_keys=[source_release_id],
        passive_deletes=True,
        backref='actions_source',
    )
    target_release_id = Column(Integer, ForeignKey(
        'releases.id',
        ondelete='CASCADE',
    ))
    target_release = relationship(
        'Release',
        foreign_keys=[target_release_id],
        passive_deletes=True,
        backref='actions_target',
    )
    action = Column(Enum(ActionType), nullable=False)
    in_package_set = relationship(
        'Package',
        secondary=actions_packages_in,
        passive_deletes=True,
        backref='actions_in',
    )
    out_package_set = relationship(
        'Package',
        secondary=actions_packages_out,
        passive_deletes=True,
        backref='actions_out',
    )
    arches = Column(String, nullable=False)

    @staticmethod
    def delete_action(
            action_data: ActionData,
            session: Session,
    ) -> None:
        action_before = session.query(Action).get(
            action_data.id
        )  # type: Action
        user_data = g.user_data
        ActionHistory.create_from_dataclass(
            session=session,
            action_history_data=ActionHistoryData(
                action_before=json.dumps(
                    action_before.to_dataclass(),
                    cls=DataClassesJSONEncoder,
                    indent=4,
                    sort_keys=True,
                ),
                history_type='delete',
                username=user_data.github_login,
                action_id=action_before.id,
            ),
        )
        session.query(Action).filter(
            Action.id == action_data.id,
        ).delete(synchronize_session='fetch')
        session.query(Release).filter(
            ~Release.actions_target.any(),
            ~Release.actions_source.any(),
        ).delete(synchronize_session='fetch')
        session.query(Package).filter(
            ~Package.actions_in.any(),
            ~Package.actions_out.any(),
        ).delete(synchronize_session='fetch')
        session.query(ModuleStream).filter(
            ~ModuleStream.packages.any(),
        ).delete(synchronize_session='fetch')

    def to_dataclass(self) -> ActionData:
        return ActionData(
            id=self.id,
            version=self.version,
            source_release=self.source_release.to_dataclass() if
            self.source_release else None,
            target_release=self.target_release.to_dataclass() if
            self.target_release else None,
            action=self.action.value,
            in_package_set=[package.to_dataclass() for package
                            in self.in_package_set],
            out_package_set=[package.to_dataclass() for package
                             in self.out_package_set],
            arches=self.arches.split(','),
            is_approved=self.is_approved,
            github_org=self.github_org if
            self.github_org else None
        )

    @staticmethod
    def update_from_dataclass(
            action_data: ActionData,
            session: Session,
    ) -> None:
        in_package_set = [Package.create_from_dataclass(
            package_data=in_package,
            session=session,
        ) for in_package in action_data.in_package_set]
        out_package_set = [Package.create_from_dataclass(
            package_data=out_package,
            session=session,
        ) for out_package in action_data.out_package_set]
        source_release = Release.create_from_dataclass(
            release_data=action_data.source_release,
            session=session,
        )
        target_release = Release.create_from_dataclass(
            release_data=action_data.target_release,
            session=session,
        )
        action = session.query(Action).get(action_data.id)
        action_before = action.to_dataclass()
        if action is None:
            raise DBRecordNotFound(
                'Action by ID "%s" is not found',
                action_data.id,
            )
        for key, value in action_data.to_dict().items():
            setattr(action, key, value)
        action.source_release = source_release
        action.target_release = target_release
        action.in_package_set = in_package_set
        action.out_package_set = out_package_set
        action.version += 1
        session.query(Release).filter(
            ~Release.actions_target.any(),
            ~Release.actions_source.any(),
        ).delete(synchronize_session='fetch')
        session.query(Package).filter(
            ~Package.actions_in.any(),
            ~Package.actions_out.any(),
        ).delete(synchronize_session='fetch')
        session.query(ModuleStream).filter(
            ~ModuleStream.packages.any(),
        ).delete(synchronize_session='fetch')
        session.flush()
        session.refresh(action)
        user_data = g.user_data  # type: User
        ActionHistory.create_from_dataclass(
            session=session,
            action_history_data=ActionHistoryData(
                action_before=json.dumps(
                    action_before,
                    cls=DataClassesJSONEncoder,
                    indent=4,
                    sort_keys=True,
                ),
                action_after=json.dumps(
                    action.to_dataclass(),
                    cls=DataClassesJSONEncoder,
                    indent=4,
                    sort_keys=True,
                ),
                history_type='modify',
                username=user_data.github_login,
                action_id=action.id,
            ),
        )

    @staticmethod
    def create_from_dataclass(
            action_data: ActionData,
            session: Session,
    ) -> Action:
        in_package_set = [Package.create_from_dataclass(
            package_data=in_package,
            session=session,
        ) for in_package in action_data.in_package_set]
        out_package_set = [Package.create_from_dataclass(
            package_data=out_package,
            session=session,
        ) for out_package in action_data.out_package_set]
        source_release = Release.create_from_dataclass(
            release_data=action_data.source_release,
            session=session,
        )
        target_release = Release.create_from_dataclass(
            release_data=action_data.target_release,
            session=session,
        )
        actions = Action.search_by_dataclass(action_data=action_data,
                                             session=session)
        actions = [
            action for action in actions if
            len(action.in_package_set) == len(in_package_set) and
            len(action.out_package_set) == len(out_package_set)
        ]
        if len(actions) > 1:
            raise MultipleResultsFound()
        elif not len(actions):
            action = None
        else:
            action = actions[0]
        if action is None:
            action = Action(
                **action_data.to_dict(),
                source_release=source_release,
                target_release=target_release,
                in_package_set=in_package_set,
                out_package_set=out_package_set,
            )
            session.add(action)
            session.flush()
            session.refresh(action)
            user_data = g.user_data  # type: User
            ActionHistory.create_from_dataclass(
                session=session,
                action_history_data=ActionHistoryData(
                    action_after=json.dumps(
                        action.to_dataclass(),
                        cls=DataClassesJSONEncoder,
                        indent=4,
                        sort_keys=True,
                    ),
                    history_type='create',
                    username=user_data.github_login,
                    action_id=action.id,
                ),
            )
        return action

    @staticmethod
    def search_by_dataclass(
            action_data: ActionData,
            session: Session,
            only_one: bool = False,
            page_size: int = None,
            page: int = None,
    ) -> Optional[Union[List[Action], Page, Action]]:
        if action_data.is_empty:
            return None
        in_package_set = []
        for in_package in action_data.in_package_set:
            in_package_set.extend(Package.search_by_dataclass(
                package_data=in_package,
                session=session,
            ))
        out_package_set = []
        for out_package in action_data.out_package_set:
            out_package_set.extend(Package.search_by_dataclass(
                package_data=out_package,
                session=session,
            ))
        source_release = Release.search_by_dataclass(
            release_data=action_data.source_release,
            session=session,
        )
        target_release = Release.search_by_dataclass(
            release_data=action_data.target_release,
            session=session,
        )
        action_query = session.query(Action).filter_by(
            **action_data.to_dict(force_included=['id'])
        )
        if source_release is not None:
            action_query = action_query.filter(
                Action.source_release.has(
                    Release.id.in_(
                        rls.id for rls in source_release
                    )
                ),
            )
        if target_release is not None:
            action_query = action_query.filter(
                Action.target_release.has(
                    Release.id.in_(
                        rls.id for rls in target_release
                    )
                ),
            )
        if in_package_set:
            action_query = action_query.filter(
                Action.in_package_set.any(
                    Package.id.in_(
                        pkg.id for pkg in in_package_set
                    )
                ),
            )
        if out_package_set:
            action_query = action_query.filter(
                Action.out_package_set.any(
                    Package.id.in_(
                        pkg.id for pkg in out_package_set
                    )
                ),
            )
        if page_size is None or page is None:
            if only_one:
                result = action_query.one_or_none()
            else:
                result = action_query.all()
        else:
            result = paginate(action_query, page=page, page_size=page_size)
        return result
