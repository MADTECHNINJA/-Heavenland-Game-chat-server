
class JWTDecodeError(Exception):
    """
    raised if the decoding of JWT was not successful
    """


class UnauthorizedError(Exception):
    """
    raised if the request is unauthorized
    """


class HeavenlandAPIUnavailable(Exception):
    """
    raise if there was a connection or timeout error on request to heavenland API
    """


class HeavenlandAPIError(Exception):
    """
    raise if there was an status error of 4xx on the API response from heavenland API
    """
    status_code = 400
    status_description = 'error'
    error_message = 'bad request'

    def __init__(self, statusCode: int = 400, statusDescription: str = 'error', errorMessage: str = 'bad request'):
        self.status_code = statusCode
        self.status_description = statusDescription
        self.error_message = errorMessage
