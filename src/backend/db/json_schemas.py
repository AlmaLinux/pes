# coding=utf-8
from collections import defaultdict

from common.forms import TARGET_RELEASES
from db.utils import get_major_version_list

put_action = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "present",
                "removed",
                "deprecated",
                "replaced",
                "split",
                "merged",
                "moved",
                "renamed"
            ]
        },
        "org": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
                "github_id": {
                    "type": "integer",
                },
            },
        },
        "description": {
            "type": "string",
        },
        "in_packageset": {
            "type": "object",
            "properties": {
                "package": {
                    "type": "array",
                    "items": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "repository": {
                                    "type": "string"
                                },
                                "modulestream": {
                                    "type": [
                                        "null",
                                        "object"
                                    ],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "stream": {
                                            "type": "string"
                                        }
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "repository",
                            ]
                        }
                    ]
                }
            },
            "required": [
                "package"
            ]
        },
        "out_packageset": {
            "type": [
                "object",
                "null"
            ],
            "properties": {
                "package": {
                    "type": "array",
                    "items": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "repository": {
                                    "type": "string"
                                },
                                "modulestream": {
                                    "type": [
                                        "null",
                                        "object"
                                    ],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "stream": {
                                            "type": "string"
                                        }
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "repository",
                            ]
                        }
                    ]
                }
            },
            "required": [
                "package"
            ]
        },
        "initial_release": {
            "type": ["object", "null"],
            "properties": {
                "os_name": {
                    "type": "string"
                },
                "major_version": {
                    "type": "integer"
                },
                "minor_version": {
                    "type": "integer"
                }
            },
            "required": [
                "os_name",
                "major_version",
                "minor_version"
            ]
        },
        "release": {
            "type": "object",
            "properties": {
                "os_name": {
                    "type": "string"
                },
                "major_version": {
                    "type": "integer"
                },
                "minor_version": {
                    "type": "integer"
                }
            },
            "required": [
                "os_name",
                "major_version",
                "minor_version"
            ]
        },
        "architectures": {
            "type": "array",
            "items": [
                {
                    "type": "string"
                }
            ]
        }
    },
    "required": [
        "action",
        "in_packageset",
        "out_packageset",
        "release",
        "architectures"
    ]
}

get_actions = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "id": {
            "type": "integer",
        },
        "org": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
                "github_id": {
                    "type": "integer",
                },
            },
        },
        "description": {
            "type": "string",
        },
        "action": {
            "type": "string",
            "enum": [
                "present",
                "removed",
                "deprecated",
                "replaced",
                "split",
                "merged",
                "moved",
                "renamed"
            ]
        },
        "in_packageset": {
            "type": "object",
            "properties": {
                "package": {
                    "type": "array",
                    "items": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "repository": {
                                    "type": "string"
                                },
                                "modulestream": {
                                    "type": [
                                        "null",
                                        "object"
                                    ],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "stream": {
                                            "type": "string"
                                        }
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "repository",
                                "modulestream"
                            ]
                        }
                    ]
                }
            },
            "required": [
                "package"
            ]
        },
        "out_packageset": {
            "type": [
                "object",
                "null"
            ],
            "properties": {
                "package": {
                    "type": "array",
                    "items": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "repository": {
                                    "type": "string"
                                },
                                "modulestream": {
                                    "type": [
                                        "null",
                                        "object"
                                    ],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "stream": {
                                            "type": "string"
                                        }
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "repository",
                                "modulestream"
                            ]
                        }
                    ]
                }
            },
            "required": [
                "package"
            ]
        },
        "initial_release": {
            "type": "object",
            "properties": {
                "os_name": {
                    "type": "string"
                },
                "major_version": {
                    "type": "integer"
                },
                "minor_version": {
                    "type": "integer"
                }
            },
            "required": [
                "os_name",
                "major_version",
                "minor_version"
            ]
        },
        "release": {
            "type": "object",
            "properties": {
                "os_name": {
                    "type": "string"
                },
                "major_version": {
                    "type": "integer"
                },
                "minor_version": {
                    "type": "integer"
                }
            },
            "required": [
                "os_name",
                "major_version",
                "minor_version"
            ]
        },
        "architectures": {
            "type": "array",
            "items": [
                {
                    "type": "string"
                }
            ]
        }
    }
}

delete_action = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "id": {
            "type": "integer"
        }
    },
    "required": [
        "id"
    ]
}

post_action = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "id": {
            "type": "integer",
        },
        "description": {
            "type": "string",
        },
        "action": {
            "type": "string",
            "enum": [
                "present",
                "removed",
                "deprecated",
                "replaced",
                "split",
                "merged",
                "moved",
                "renamed"
            ]
        },
        "org": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                },
                "github_id": {
                    "type": "integer",
                },
            },
        },
        "in_packageset": {
            "type": "object",
            "properties": {
                "package": {
                    "type": "array",
                    "items": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "repository": {
                                    "type": "string"
                                },
                                "modulestream": {
                                    "type": [
                                        "null",
                                        "object"
                                    ],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "stream": {
                                            "type": "string"
                                        }
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "repository",
                                "modulestream"
                            ]
                        }
                    ]
                }
            },
            "required": [
                "package"
            ]
        },
        "out_packageset": {
            "type": [
                "object",
                "null"
            ],
            "properties": {
                "package": {
                    "type": "array",
                    "items": [
                        {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string"
                                },
                                "repository": {
                                    "type": "string"
                                },
                                "modulestream": {
                                    "type": [
                                        "null",
                                        "object"
                                    ],
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        },
                                        "stream": {
                                            "type": "string"
                                        }
                                    }
                                }
                            },
                            "required": [
                                "name",
                                "repository",
                                "modulestream"
                            ]
                        }
                    ]
                }
            },
            "required": [
                "package"
            ]
        },
        "initial_release": {
            "type": ["object", "null"],
            "properties": {
                "os_name": {
                    "type": "string"
                },
                "major_version": {
                    "type": "integer"
                },
                "minor_version": {
                    "type": "integer"
                }
            },
        },
        "release": {
            "type": "object",
            "properties": {
                "os_name": {
                    "type": "string"
                },
                "major_version": {
                    "type": "integer"
                },
                "minor_version": {
                    "type": "integer"
                }
            },
            "required": [
                "os_name",
                "major_version",
                "minor_version"
            ]
        },
        "architectures": {
            "type": "array",
            "items": [
                {
                    "type": "string"
                }
            ]
        }
    },
    "required": [
        "id",
        "action",
        "in_packageset",
        "out_packageset",
        "release",
        "architectures"
    ]
}

post_pull_request = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "id": {
            "type": "integer"
        }
    },
    "required": [
        "id",
    ]
}

get_dump = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$ref": "#/definitions/Welcome4",
    "definitions": {
        "Welcome4": {
            "type": "object",
            "properties": {
                "oses": {
                    "type": "object",
                    "patternProperties": {
                        "^[0-9]$": {
                            "$ref": "#/definitions/OsNames"
                        }
                    },
                    "propertyNames": {
                        "$ref": "#/definitions/Version"
                    },
                    "additionalProperties": False
                },
                "orgs": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "groups": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "only_approved": {
                    "type": "boolean",
                },
            },
            "required": [
                "oses",
            ]
        },
        "Version": {
            "type": "string",
            "enum": [str(i) for i in get_major_version_list()]
        },
        "OsNames": {
            "type": "string",
            "enum": TARGET_RELEASES,
        },
    }
}

delete_group = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "id": {
            "type": "integer"
        }
    },
    "required": [
        "id"
    ]
}


json_schema_mapping = defaultdict(dict, {
    '/api/actions': {
        'PUT': put_action,
        'GET': get_actions,
        'POST': post_action,
        'DELETE': delete_action,
    },
    '/api/pull_requests': {
        'GET': None,
        'POST': post_pull_request,
    },
    '/api/dump': {
        'GET': get_dump,
    },
    '/api/groups': {
        'DELETE': delete_group,
    },
})
