# coding=utf-8
from collections import defaultdict

import wtforms.validators as validators
from db.data_models import ActionType
from db.utils import get_releases_list
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    BooleanField,
    FileField,
    SelectField,
    IntegerField,
    Field,
)
from wtforms.widgets import TextArea


class BulkUpload(FlaskForm):
    uploaded_file = FileField(
        'Init JSON PES file',
        validators=[
            validators.DataRequired(),
        ],
    )


class Dump(FlaskForm):
    source_release = SelectField(
        'Source OS',
        validators=[
            validators.DataRequired(),
        ],
        choices=['CentOS', 'OL']
    )
    target_release = SelectField(
        'Target OS',
        validators=[
            validators.DataRequired(),
        ],
        choices=get_releases_list()
    )


def release_version_validator(form, field: Field):
    print(1)
    if field.data == '' and field.name in (
        'source_major_version',
        'source_minor_version',
    ) and (form.source_release.data or form.source_generic.data):
        field.errors.append(
            'You should set version of source release if it is not empty'
        )
        raise validators.StopValidation()
    if field.data == '' and field.name in (
        'target_major_version',
        'target_minor_version',
    ) and (form.target_release.data or form.target_release.data):
        field.errors.append(
            'You should set version of target release if it is not empty'
        )
        raise validators.StopValidation()


def generic_release_validator(form, field: Field):
    generic_release_dict = defaultdict(lambda: True, **{
        'source_generic': not form.source_release.data,
        'target_generic': not form.target_release.data,
    })
    if field.data == '' and generic_release_dict[field.name]:
        field.errors.append(
            'You should select release name if checkbox "generic" is not set'
        )
        raise validators.StopValidation()


def package_set_validator(form, field: Field):
    package_set_data = field.data
    error_rows = []
    for i, pkg_data in enumerate(package_set_data.split()):
        if len(pkg_data.split(',')) != 4:
            error_rows += [str(i + 1)]
    if error_rows:
        error_rows = ', '.join(error_rows)
        field.errors.append(
            f'Error in rows "{error_rows}". You should write package data in '
            'format "name,repository,module_name,module_stream", '
            'there are name or stream of module can be empty strings'
        )
        raise validators.StopValidation()


class AddAction(FlaskForm):
    action = SelectField(
        'Action type',
        validators=[
            validators.DataRequired()
        ],
        choices=ActionType.get_type_list(),
    )
    source_generic = BooleanField(
        'source is generic',
        default=True,
    )
    source_release = SelectField(
        'Source OS',
        validators=[
            generic_release_validator,
        ],
        choices=[
            '',
            'CentOS',
            'OL',
        ]
    )
    source_major_version = IntegerField(
        'Source major version',
        validators=[
            validators.Optional(),
            release_version_validator,
        ]
    )
    source_minor_version = IntegerField(
        'Source minor version',
        validators=[
            validators.Optional(),
            release_version_validator,
        ]
    )
    target_generic = BooleanField(
        'target is generic',
        validators=[
            generic_release_validator,
        ],
        default=True,
    )
    target_release = SelectField(
        'Target OS',
        validators=[
            validators.Optional(),
        ],
        choices=[''] + get_releases_list()
    )
    target_major_version = IntegerField(
        'Target major version',
        validators=[
            validators.Optional(),
            release_version_validator,
        ]
    )
    target_minor_version = IntegerField(
        'Target minor version',
        validators=[
            validators.Optional(),
            release_version_validator,
        ]
    )
    arches = StringField(
        'Architectures',
        validators=[
            validators.DataRequired(),
        ]
    )
    in_package_set = StringField(
        'In package set',
        validators=[
            validators.Optional(),
            package_set_validator,
        ],
        widget=TextArea(),
    )
    out_package_set = StringField(
        'Out package set',
        validators=[
            validators.Optional(),
            package_set_validator,
        ],
        widget=TextArea(),
    )
