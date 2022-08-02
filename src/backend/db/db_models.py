# coding=utf-8
from __future__ import annotations

import json

from flask import g
from sqlalchemy_pagination import (
    paginate,
    Page,
)
from api.exceptions import DBRecordNotFound
from db.data_models import (
    ActionType,
    ActionData,
    PackageData,
    PackageType,
    ModuleStreamData,
    ReleaseData,
    UserData,
    GitHubOrgData,
    ActionHistoryData,
    DataClassesJSONEncoder,
    TIME_FORMAT_STRING,
    GroupActionsData,
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
    DateTime,
    func,
)
from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    relationship,
    Session,
    backref,
)

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

groups_actions = Table(
    'groups_actions',
    Base.metadata,
    Column(
        'action_id', Integer, ForeignKey(
            'actions.id',
            ondelete='CASCADE',
        ),
    ),
    Column(
        'group_id', Integer, ForeignKey(
            'groups.id',
            ondelete='CASCADE',
        ),
    ),
)


class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    github_org_id = Column(
        Integer,
        ForeignKey(
            'github_orgs.id',
            ondelete='CASCADE',
        ),
        nullable=False,
    )
    github_org = relationship(
        'GitHubOrg',
        foreign_keys=[github_org_id],
        passive_deletes=True,
        backref='groups_actions',
    )
    actions = relationship(
        'Action',
        secondary=groups_actions,
        passive_deletes=True,
        backref=backref('groups'),
    )

    @staticmethod
    def search_by_github_orgs(
            session: Session,
            github_orgs: list[GitHubOrgData],
            page_size: int = None,
            page: int = None,
    ):
        query = session.query(Group)
        if github_orgs is not None:
            query = query.filter(
                Group.github_org.has(
                    GitHubOrg.name.in_(
                        github_org.name for github_org in github_orgs
                    )
                )
            )
        if page is None or page_size is None:
            return query.all()
        else:
            return paginate(query, page=page, page_size=page_size)

    @staticmethod
    def search_by_dataclass(
            session: Session,
            group_actions_data: GroupActionsData,
            only_one: bool,
    ) -> list[Group] | Group:
        query = session.query(Group).filter_by(
            **group_actions_data.to_dict(),
        )
        if group_actions_data.github_org is not None:
            org = GitHubOrg.search_by_dataclass(
                session=session,
                github_org_data=group_actions_data.github_org,
                only_one=True,
            )
        else:
            org = None
        query = query.filter_by(
            github_org=org,
        )
        if only_one:
            return query.one_or_none()
        else:
            return query.all()

    def to_dataclass(self) -> GroupActionsData:
        return GroupActionsData(
            id=self.id,
            name=self.name,
            description=self.description,
            github_org=self.github_org.to_dataclass(),
            actions_ids=[action.id for action in self.actions],
        )

    @staticmethod
    def create_from_dataclass(
            session: Session,
            group_actions_data: GroupActionsData,
    ) -> Group:
        query = session.query(Group).filter_by(
            **group_actions_data.to_dict(),
        )
        org = GitHubOrg.create_from_dataclass(
            session=session,
            github_org_data=group_actions_data.github_org,
        )
        query = query.filter_by(
            github_org=org,
        )
        action_group = query.one_or_none()
        if action_group is None:
            action_group = Group(
                **group_actions_data.to_dict(),
            )

            action_group.github_org = org
            action_group.github_org_id = org.id
            if group_actions_data.actions_ids is not None:
                actions = session.query(Action).filter(
                    Action.id.in_(group_actions_data.actions_ids)
                ).all()
            action_group.actions = actions
            session.add(action_group)
            session.flush()
        return action_group

    @staticmethod
    def update_from_dataclass(
            session: Session,
            group_actions_data: GroupActionsData,
    ):
        group_actions = session.query(Group).get(group_actions_data.id)
        org = GitHubOrg.create_from_dataclass(
            session=session,
            github_org_data=group_actions_data.github_org,
        )
        actions = session.query(Action).filter(
            Action.id.in_(group_actions_data.actions_ids)
        ).all()
        group_actions.actions = actions
        group_actions.github_org = org
        group_actions.github_org_id = org.id
        for key, value in group_actions_data.to_dict().items():
            setattr(group_actions, key, value)
        session.flush()

    @staticmethod
    def delete_by_dataclass(
            session: Session,
            group_actions_data: GroupActionsData,
    ):
        session.query(Group).filter_by(
            **group_actions_data.to_dict(force_included=['id']),
        ).delete()


class GitHubOrg(Base):
    __tablename__ = 'github_orgs'

    id = Column(Integer, primary_key=True)
    github_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)

    @staticmethod
    def search_by_dataclass(
            session: Session,
            github_org_data: GitHubOrgData,
            only_one: bool,
    ) -> list[GitHubOrg] | GitHubOrg | None:
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
            github_id=self.github_id,
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
    ) -> list[User] | User | Page:
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
            return paginate(query, page=page, page_size=page_size)

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
    timestamp = Column(DateTime, nullable=False, onupdate=func.now())

    @staticmethod
    def search_by_dataclass(
            session: Session,
            action_history_data: ActionHistoryData,
            only_one: bool,
            page_size: int = None,
            page: int = None,
    ) -> list[ActionHistory] | ActionHistory | Page:
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
    ) -> list[ActionHistory] | Page:
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
    ) -> list[ActionHistoryData] | Page:
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
            timestamp=self.timestamp.strftime(TIME_FORMAT_STRING),
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
    ) -> ModuleStream | None:
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
    ) -> list[ModuleStream] | None:
        if module_stream_data.is_empty:
            return
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
    ) -> Release | None:
        if release_data.is_empty:
            return
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
    ) -> list[Release] | None:
        if release_data.is_empty:
            return
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
    ) -> list[Package] | None:
        if package_data.is_empty:
            return
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
    description = Column(String, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_approved = Column(Boolean, nullable=False, default=False)
    github_org = Column(String, nullable=True)
    github_org_id = Column(Integer, ForeignKey(
        'github_orgs.id',
        ondelete='CASCADE',
    ))
    github_org_rel = relationship(
        'GitHubOrg',
        foreign_keys=[github_org_id],
        passive_deletes=True,
        backref='actions',
    )
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
            description=self.description,
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
            github_org=self.github_org_rel.to_dataclass() if
            self.github_org_rel else None,
            groups=[group.to_dataclass() for group in self.groups],
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
        github_org = GitHubOrg.create_from_dataclass(
            session=session,
            github_org_data=action_data.github_org,
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
        action.github_org_rel = github_org
        action.version += 1
        session.flush()
        session.refresh(action)
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
        github_org = GitHubOrg.create_from_dataclass(
            session=session,
            github_org_data=action_data.github_org,
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
                github_org_rel=github_org,
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
            group_id: int = None,
    ) -> list[Action] | Page | Action | None:
        if action_data.is_empty:
            return
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
        github_org = GitHubOrg.search_by_dataclass(
            session=session,
            github_org_data=action_data.github_org,
            only_one=False,
        )
        action_query = session.query(Action).filter_by(
            **action_data.to_dict(force_included=['id'])
        )
        if github_org is not None:
            action_query = action_query.filter(
                Action.github_org_rel.has(GitHubOrg.id.in_(
                    gho.id for gho in github_org
                ))
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
        if group_id is not None:
            action_query = action_query.filter(
                Action.groups.any(
                    Group.id.in_([group_id])
                )
            )
        if page_size is None or page is None:
            if only_one:
                result = action_query.one_or_none()
            else:
                result = action_query.all()
        else:
            result = paginate(action_query, page=page, page_size=page_size)
        return result
