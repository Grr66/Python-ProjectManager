
class APIError(Exception):
    '''
    the base APIError which contains error(required), data(optional) and message(optional).
    '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    def __init__(self,field,message=''):
        super(APIValueError, self).__init__('value:invalid',field,message)

class APIResourceNotFoundError(APIError):

    """docstring for APIResourceNotFoundError"""

    def __init__(self,field,message=''):
        super(APIResourceNotFoundError, self).__init__(
            'value:notfound', field, message)