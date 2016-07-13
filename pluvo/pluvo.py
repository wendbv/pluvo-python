import copy
import json
import requests


DEFAULT_API_URL = 'https://api.pluvo.co/api/'
DEFAULT_PAGE_SIZE = 20


class PluvoException(Exception):
    pass


class PluvoAPIException(PluvoException):
    """Raised when the API gives an error."""

    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super(PluvoAPIException, self).__init__(
            'HTTP status {} - {}'.format(status_code, message))


class PluvoGenerator:
    """Returned for list API calls

    Immediatly gets the first page of a list API call. The length is set
    using the `count` result from the call, so is not nessecary to get
    all items to know the total count.

    Page size can be set when instantiating the `Pluvo` object using
    `page_size`, otherwise the `DEFAULT_PAGE_SIZE` is used.

    Items are yielded using a generator. When the items from the first page
    request are all yielded, the next page is retrieved."""

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
            raise PluvoAPIException(data['message'], r.status_code)

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
            raise PluvoAPIException(data['message'], r.status_code)

        return data

    def _post(self, endpoint, data, params=None):
        headers = self._set_auth_headers()
        params = self._set_auth_params(params)

        url = '{}{}'.format(self.api_url, endpoint)
        data = json.dumps(data)
        r = requests.post(url, params=params, headers=headers, data=data)
        data = r.json()

        if r.status_code != 200:
            raise PluvoAPIException(data['message'], r.status_code)

        return data

    def get_course(self, course_id):
        return self._get('course/{}/'.format(course_id))

    def get_courses(self, offset=None, limit=None, title=None,
                    description=None, published_from=None, published_to=None,
                    student_id=None, creator_id=None, creation_date_from=None,
                    creation_date_to=None):
        params = {
            'offset': offset, 'limit': limit, 'title': title,
            'description': description, 'published_from': published_from,
            'published_to': published_to, 'student_id': student_id,
            'creator_id': creator_id, 'creation_date_from': creation_date_from,
            'creation_date_to': creation_date_to
        }
        return self._get_multiple('course/', params=params)

    def set_course(self, course):
        if 'id' in course:
            return self._put('course/{}/'.format(course['id']), course)
        else:
            return self._post('course/', course)

    def set_organisation(self, organisation):
        if 'id' in organisation:
            return self._put(
                'organisation/{}/'.format(organisation['id']), organisation)
        else:
            return self._post('organisation/', organisation)

    def get_s3_upload_token(self, filename, media_type):
        return self._get(
            'media/s3_upload_token/',
            params={'filename': filename, 'media_type': media_type})

    def get_token(self, user_id, course_id, token_type):
        """Get a token for an user to access a course.

        `token_type` can be `student` or `manager`."""
        return self._get('user/{}/course/{}/token/{}/'.format(
            user_id, course_id, token_type))

    def get_user(self, user_id):
        return self._get('user/{}/'.format(user_id))

    def get_users(self, offset=None, limit=None, name=None,
                  creation_date_from=None, creation_date_to=None,
                  created_course_id=None, following_course_id=None):
        params = {
            'offset': offset, 'limit': limit, 'name': name,
            'creation_date_from': creation_date_from,
            'creation_date_to': creation_date_to,
            'created_course_id': created_course_id,
            'following_course_id': following_course_id
        }
        return self._get_multiple('user/', params=params)

    def set_user(self, user):
        if 'id' in user:
            return self._put('user/{}/'.format(user['id']), user)
        else:
            return self._post('user/', user)

    def get_version(self):
        """Get the Pluvo API version."""
        return self._get('version/')
