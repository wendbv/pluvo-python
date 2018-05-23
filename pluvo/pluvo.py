import itertools
import requests
import math


DEFAULT_API_URL = 'https://api.pluvo.co/rest/'
DEFAULT_PAGE_SIZE = 20


class PluvoException(Exception):
    pass


class PluvoAPIException(PluvoException):
    """Raised when the API gives an error."""

    def __init__(self, message, status_code, response_body):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super(PluvoAPIException, self).__init__(
            'HTTP status {} - {}'.format(status_code, message))


class PluvoMisconfigured(PluvoException):
    """Raised when the API is not correctly configured."""


class PluvoResultSet(object):
    """Returned for list API calls

    This object can be indexed, sliced, and iterated over like a regular
    sequence. Result pages will be fetched as needed from Pluvo.

    Page size can be set when instantiating the `Pluvo` object using
    `page_size`, otherwise the `DEFAULT_PAGE_SIZE` is used.
    """

    def __init__(self, pluvo, endpoint, params=None, method='GET'):
        self.pluvo = pluvo
        self.method = method
        self.endpoint = endpoint
        self.params = params if params is not None else {}

        self._count = None
        self.pages = {}

    def _get_page(self, index):
        if index not in self.pages:
            params = dict(self.params, offset=index * self.pluvo.page_size,
                          limit=self.pluvo.page_size)
            if self.method == 'POST':
                resp = self.pluvo._request('POST', self.endpoint, data=params)
            else:
                resp = self.pluvo._request('GET', self.endpoint, params=params)
            self.pages[index] = resp['data']
            if self._count is None:
                self._count = resp['count']
        return self.pages[index]

    def _get_page_key_offset(self, key):
        """transform a key into a page key and offset in to the page"""
        return key // self.pluvo.page_size, key % self.pluvo.page_size

    def __getitem__(self, key):
        def canonicalize(key):
            """transform negative keys to regular ones"""
            if key < 0:
                key = len(self) + key
            return key

        if isinstance(key, slice):
            start = canonicalize(
                key.start if key.start is not None else 0)
            stop = canonicalize(
                key.stop if key.stop is not None else len(self))

            if start > stop:
                return []

            start_key, start_offset = self._get_page_key_offset(start)
            stop_key, stop_offset = self._get_page_key_offset(stop)

            if start_key == stop_key:
                # slice is contained within a single page
                return self._get_page(start_key)[start_offset:stop_offset]
            else:
                result = self._get_page(start_key)[start_offset:]
                for k in range(start_key + 1, stop_key):
                    result.extend(self._get_page(k))
                if stop_offset > 0:
                    result.extend(self._get_page(stop_key)[:stop_offset])
                return result
        else:
            if key >= len(self):
                raise IndexError("PluvoResultSet index out of range")
            key, offset = self._get_page_key_offset(canonicalize(key))
            return self._get_page(key)[offset]

    def __len__(self):
        if self._count is None:
            # TODO
            # there is an optimization opportunity here: sometimes
            # when we call len() we already have some good guess which page
            # we're going to need. If we access resultset[40], for example, the
            # code does a bounds check which leads us to request the 0th page
            # (which we'll definitely don't need). I don't expect this to occur
            # frequently though. slices require no bound checks, and how often
            # would you need a specific item from the middle of the set?
            self._get_page(0)
        return self._count

    def __iter__(self):
        num_pages = int(math.ceil(len(self) / float(self.pluvo.page_size)))
        page_iters = (iter(self._get_page(key)) for key in range(0, num_pages))
        return itertools.chain(*page_iters)


class Pluvo:
    """Interface to the Pluvo API

    Set authentication data using `client_id` and `client_secret` or
    `token`.
    The API url can be set using `api_url`, default is the Pluvo API
    production url.
    Page sizes for the list API calls can be set using `page_size`."""

    def __init__(self, client_id=None, client_secret=None, token=None,
                 api_url=None, page_size=None):
        if not any([client_id, client_secret, token]):
            raise PluvoMisconfigured(
                'You need to set either client_id and client_secret, or '
                'provide a token.')
        if (client_id and not client_secret) \
                or (client_secret and not client_id):
            raise PluvoMisconfigured(
                'You need to set both client_id and client_secret.')
        if client_id and token:
            raise PluvoMisconfigured(
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

    def _request(self, method, endpoint, data=None, params=None):
        headers = self._set_auth_headers()
        params = self._set_auth_params(params)
        url = self.api_url + endpoint

        r = requests.request(
            method, url, params=params, json=data, headers=headers)
        try:
            data = r.json()
        except ValueError:
            if r.status_code == 500:
                msg = ('Server returned a 500 error. This is likely a bug. '
                       'Contact us at https://github.com/wendbv/pluvo-python/')
            else:
                msg = ('The server did not return a valid JSON response '
                       '(response status code: {}). If you have a custom '
                       '`api_url`, ensure that it is correct '
                       '(e.g. https://api.pluvo.co/rest/).'
                       .format(r.status_code))
            raise PluvoException(msg)

        if r.status_code < 200 or r.status_code > 299:
            if 'error' in data:
                raise PluvoAPIException(data['error'], r.status_code, data)
            else:
                msg = ('Server returned a non 20x status code, but the '
                       'returned JSON contains no error message. This is '
                       'likely a bug. Contact us at '
                       'https://github.com/wendbv/pluvo-python/'
                       '\n\nreturned JSON: '
                       '{}'.format(repr(data)))
                raise PluvoException(msg)
        return data

    def _get_multiple(self, endpoint, params=None, method='GET'):
        return PluvoResultSet(
            pluvo=self, endpoint=endpoint, params=params, method=method)

    def get_course(self, course_id):
        return self._request('GET', 'course/{}/'.format(course_id))

    def get_lti_info(self, course_id):
        return self._request('GET', 'course/{}/lti'.format(course_id))

    def get_courses(self, offset=None, limit=None, title=None,
                    description=None, published_from=None, published_to=None,
                    student_id=None, creator_id=None, creation_date_from=None,
                    creation_date_to=None, order_by=None, id_list=None,
                    include_version_numbers=False):
        params = {
            'offset': offset, 'limit': limit, 'title': title,
            'description': description, 'published_from': published_from,
            'published_to': published_to, 'student_id': student_id,
            'creator_id': creator_id, 'creation_date_from': creation_date_from,
            'creation_date_to': creation_date_to, 'order_by': order_by,
            'id': id_list, 'include_version_numbers': include_version_numbers
        }
        return self._get_multiple('course/', params=params)

    def set_course(self, course):
        if 'id' in course:
            return self._request('PUT', 'course/{}/'.format(course['id']),
                                 course)
        else:
            return self._request('POST', 'course/', course)

    def delete_course(self, course_id):
        return self._request('DELETE', 'course/{}/'.format(course_id))

    def archive_student_course_version(self, course_id, student_id):
        url = 'course/{}/user/{}/'.format(course_id, student_id)
        return self._request('PUT', url, {'action': 'archive'})

    def set_organisation(self, organisation):
        if 'id' in organisation:
            return self._request(
                'PUT', 'organisation/{}/'.format(organisation['id']),
                organisation)
        else:
            return self._request('POST', 'organisation/', organisation)

    def get_s3_upload_token(self, filename, media_type):
        return self._request(
            'GET',
            'media/s3_upload_token/',
            params={'filename': filename, 'media_type': media_type})

    def get_token(self, token_type, user_id, course_id, trainer_id=''):
        """Get a token for a user to access a course.

        `token_type` can be `student`, `manager`, or `trainer`."""
        params = {'user_id': user_id, 'course_id': course_id}
        if token_type == 'trainer':
            params['trainer_id'] = trainer_id
        url = 'user/token/{}/'.format(token_type)
        return self._request('GET', url, params=params)

    def get_user(self, user_id):
        return self._request('GET', 'user/{}/'.format(user_id))

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
            return self._request('PUT', 'user/{}/'.format(user['id']), user)
        else:
            return self._request('POST', 'user/', user)

    def get_progress_report(self, student_ids=None, course_ids=None,
                            order_by=None, offset=None, limit=None):
        params = {
            'student_id': student_ids,
            'course_id': course_ids,
            'order_by': order_by,
            'offset': offset,
            'limit': limit
        }
        return self._get_multiple(
            'progress/reports/', params=params, method='GET')

    def get_course_report(self, course_id, student_id, filename=None):
        params = {'filename': filename} if filename else {}
        url = 'report/course/{}/user/{}/'.format(course_id, student_id)
        return self._request('GET', url, params=params)

    def get_version(self):
        """Get the Pluvo API version."""
        return self._request('GET', 'version/')
