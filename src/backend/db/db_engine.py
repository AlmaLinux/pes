# coding=utf-8
import os

from sqlalchemy import create_engine
from sqlalchemy.pool import SingletonThreadPool

POSTGRES_CONNECTION_PATH = f'postgresql+psycopg2://' \
                           f'{os.environ.get("POSTGRES_USER")}:' \
                           f'{os.environ.get("POSTGRES_PASSWORD")}@' \
                           f'{os.environ.get("POSTGRES_HOST")}/' \
                           f'{os.environ.get("POSTGRES_DB")}'


class Engine:
    __instance = None

    @classmethod
    def get_instance(cls):
        if not cls.__instance:
            cls.__instance = create_engine(
                POSTGRES_CONNECTION_PATH,
                pool_size=20,
            )
        return cls.__instance
