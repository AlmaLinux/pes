# coding=utf-8
from __future__ import annotations

from typing import List, Optional, Union
from sqlalchemy_pagination import paginate, Page
from api.exceptions import DBRecordNotFound
from db.data_models import (
    ActionType,
    ActionData,
    PackageData,
    PackageType,
    ModuleStreamData,
    ReleaseData,
    UserData, GitHubOrgData,
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

    @staticmethod
    def create_from_dataclass(
            action_data: ActionData,
            session: Session,
    ):
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
        return action

    @staticmethod
    def search_by_dataclass(
            action_data: ActionData,
            session: Session,
            page_size: int = None,
            page: int = None,
    ) -> Optional[Union[List[Action], Page]]:
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
            result = action_query.all()
        else:
            result = paginate(action_query, page=page, page_size=page_size)
        return result


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
    def search_by_dataclass(session: Session, github_org_data: GitHubOrgData):
        return session.query(GitHubOrg).filter_by(
            **github_org_data.to_dict(),
        ).all()

    def to_dataclass(self) -> GitHubOrgData:
        return GitHubOrgData(
            name=self.name,
        )

    @staticmethod
    def create_from_dataclass(
            session: Session,
            github_org_data: GitHubOrgData,
    ):
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
    ):
        query = session.query(User).filter_by(
            **user_data.to_dict(),
        )
        if only_one:
            return query.one_or_none()
        else:
            return query.all()

    @staticmethod
    def create_from_dataclass(session: Session, user_data: UserData):
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
