# coding=utf-8

from flask_api.status import (
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)


class BaseCustomException(Exception):

    response_code = HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message, *args):
        Exception.__init__(self, message, *args)
        self.message = message
        self.args = args

    def __str__(self):
        return self.message % self.args


class BadRequestFormatExceptioin(BaseCustomException):
    response_code = HTTP_400_BAD_REQUEST


class DBRecordNotFound(BaseCustomException):
    response_code = HTTP_404_NOT_FOUND
