from flask import jsonify


class ApiError(Exception):
    status_code = 500
    additional_dict = {}

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())

        rv.update(self.additional_dict)

        rv['error'] = self.message

        return rv

    def add_additional_dict(self, d):
        self.additional_dict.update(d)