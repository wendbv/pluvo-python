import copy
import json
import requests


DEFAULT_API_URL = 'https://api.pluvo.co/api/'
DEFAULT_PAGE_SIZE = 20


class PluvoException(Exception):
    pass


class PluvoRequestException(PluvoException):

    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super(PluvoRequestException, self).__init__(
            'HTTP status {} - {}'.format(status_code, message))


class PluvoGenerator:
    def __init__(self, pluvo, endpoint, params=None):
        self.pluvo = pluvo
        self.endpoint = endpoint
        self.params = params if params is not None else {}
        self.initial_limit = self.params.get('limit')
        self.initial_offset = self.params.get('offset')
        self.length = 0

        result = self._get_next_page()

        self.items = result['data']

    def _get_next_page(self, initial=True):
        if initial and (self.initial_limit is None
                        or self.initial_limit > self.pluvo.page_size):
            self.params['limit'] = self.pluvo.page_size
        if initial and self.initial_offset is None:
            self.params['offset'] = 0

        params = copy.copy(self.params)
        result = self.pluvo._get(self.endpoint, params=params)
        if not self.length:
            if self.initial_limit is None \
                    or self.initial_limit > result['count']:
                self.length = result['count']
                if self.initial_offset is not None:
                    self.length -= self.initial_offset
            else:
                self.length = self.initial_limit

        next_page_size = min(
            self.params['limit'],
            (self.length - self.params['offset'] - self.params['limit']))
        self.params['offset'] += self.params['limit']
        self.params['limit'] = next_page_size
        return result

    def __len__(self):
        return self.length

    def __iter__(self):
        i = 0
        while True:
            for item in self.items:
                yield item
                i += 1
                if i >= self.length:
                    return
            self.items = self._get_next_page(initial=False)['data']
            if not self.items:
                return


class Pluvo:

    def __init__(self, client_id=None, client_secret=None, token=None,
                 api_url=None, page_size=None):
        if (client_id and not client_secret) \
                or (client_secret and not client_id):
            raise PluvoException(
                'You need to set both client_id and client_secret.')
        if client_id and token:
            raise PluvoException(
                'You can not use both client and token authentication '
                'simultaneously.')

        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token

        if api_url is not None:
            self.api_url = api_url
        else:
            self.api_url = DEFAULT_API_URL

        if page_size is not None:
            self.page_size = page_size
        else:
            self.page_size = DEFAULT_PAGE_SIZE

    def _set_auth_headers(self, headers=None):
        if headers is None:
            headers = {}

        if self.client_id:
            headers['client_id'] = self.client_id
            headers['client_secret'] = self.client_secret

        return headers

    def _set_auth_params(self, params=None):
        if params is None:
            params = {}

        if self.token:
            params['token'] = self.token

        return params

    def _get(self, endpoint, params=None):
        headers = self._set_auth_headers()
        params = self._set_auth_params(params)

        url = '{}{}'.format(self.api_url, endpoint)
        r = requests.get(url, params=params, headers=headers)
        data = r.json()

        if r.status_code != 200:
            raise PluvoRequestException(data['message'], r.status_code)

        return data

    def _get_multiple(self, endpoint, params=None):
        return PluvoGenerator(pluvo=self, endpoint=endpoint, params=params)

    def _put(self, endpoint, data, params=None):
        headers = self._set_auth_headers()
        params = self._set_auth_params(params)

        url = '{}{}'.format(self.api_url, endpoint)
        data = json.dumps(data)
        r = requests.put(url, params=params, headers=headers, data=data)
        data = r.json()

        if r.status_code != 200:
            raise PluvoRequestException(data['message'], r.status_code)

        return data

    def _post(self, endpoint, data, params=None):
        headers = self._set_auth_headers()
        params = self._set_auth_params(params)

        url = '{}{}'.format(self.api_url, endpoint)
        data = json.dumps(data)
        r = requests.post(url, params=params, headers=headers, data=data)
        data = r.json()

        if r.status_code != 200:
            raise PluvoRequestException(data['message'], r.status_code)

        return data

    def set_course(self, course):
        if 'id' in course:
            return self._put('course/{}/'.format(course['id']), course)
        else:
            return self._post('course/', course)

    def get_courses(self, offset=None, limit=None, title=None,
                    description=None, published_from=None, published_to=None,
                    student_id=None, creator_id=None, creation_date_from=None,
                    creation_date_to=None):
        """Get a list of courses."""
        params = {
            'offset': offset, 'limit': limit, 'title': title,
            'description': description, 'published_from': published_from,
            'published_to': published_to, 'student_id': student_id,
            'creator_id': creator_id, 'creation_date_from': creation_date_from,
            'creation_date_to': creation_date_to
        }
        return self._get_multiple('course/', params=params)

    def get_user(self, user_id):
        """Get a specific user."""
        return self._get('user/{}/'.format(user_id))

    def get_version(self):
        """Get the Pluvo API version."""
        return self._get('version/')
