from smsframework.exc import *


class VianettProviderError(ProviderError):
    """ All Vianett errors """
    code = None

    def __init__(self, code, message=''):
        self.code = code
        super(VianettProviderError, self).__init__(
            '#{}: {}'.format(self.code, message)
        )
