from mock import call, patch
import pytest

import pluvo
from pluvo import PluvoResultSet, DEFAULT_API_URL, DEFAULT_PAGE_SIZE


class Multiple:
    call_nr = 0

    def __init__(self, pages):
        self.pages = pages

    def results(self, *args, **kwargs):
        result = self.pages[self.call_nr]
        self.call_nr += 1
        return result


def test_pluvo_resultset_get_page(mocker):
    pages = [
        {'count': 4, 'data': [0, 1]},
        {'count': 4, 'data': [2, 3]}
    ]
    i = iter(pages)

    request_mock = mocker.MagicMock(
        side_effect=lambda *args, **kwargs: next(i))
    pluvo_mock = mocker.MagicMock(page_size=2, _request=request_mock)

    p = PluvoResultSet(pluvo_mock, 'endpoint')
    page0 = p._get_page(0)
    # make sure that fetching twice doesn't generate a new request
    page0_again = p._get_page(0)
    page1 = p._get_page(1)

    assert page0 == page0_again
    assert page0 == pages[0]['data']
    assert page1 == pages[1]['data']

    pluvo_mock._request.assert_has_calls([
        call('GET', 'endpoint', params={'limit': 2, 'offset': 0}),
        call('GET', 'endpoint', params={'limit': 2, 'offset': 2}),
    ])


def test_pluvo_resultset_post_page(mocker):
    pages = [
        {'count': 4, 'data': [0, 1]},
        {'count': 4, 'data': [2, 3]}
    ]
    i = iter(pages)

    request_mock = mocker.MagicMock(
        side_effect=lambda *args, **kwargs: next(i))
    pluvo_mock = mocker.MagicMock(page_size=2, _request=request_mock)

    p = PluvoResultSet(pluvo_mock, 'endpoint', method='POST')
    page0 = p._get_page(0)
    assert page0 == [0, 1]

    pluvo_mock._request_assert_has_calls([
        call('POST', 'endpoint', data={'limit': 2, 'offset': 0})
    ])


def test_pluvo_resultset_get_page_key_offset(mocker):
    pluvo_mock = mocker.MagicMock(page_size=2)
    p = PluvoResultSet(pluvo_mock, 'endpoint')

    assert p._get_page_key_offset(0) == (0, 0)
    assert p._get_page_key_offset(1) == (0, 1)
    assert p._get_page_key_offset(7) == (3, 1)


def test_pluvo_resultset_getitem(mocker):
    pages = [
        [0, 1],
        [2, 3],
        [4, 5],
        [6, 7],
    ]

    get_page_mock = mocker.MagicMock(side_effect=lambda x: pages[x])
    pluvo_mock = mocker.MagicMock(page_size=2)
    p = PluvoResultSet(pluvo_mock, 'endpoint')
    p._count = 8
    with patch.object(p, '_get_page', get_page_mock):
        assert p[:] == [0, 1, 2, 3, 4, 5, 6, 7]
        assert p[-1] == 7
        assert p[:1] == [0]
        assert p[-3:] == [5, 6, 7]
        assert p[:-3] == [0, 1, 2, 3, 4]
        assert p[8:1] == []
        assert p[0:1] == [0]
        assert p[3:7] == [3, 4, 5, 6]
        with pytest.raises(IndexError):
            p[8]


def test_pluvo_resultset_len(mocker):
    pages = [
        {'count': 4, 'data': [0, 1]},
        {'count': 4, 'data': [2, 3]}
    ]
    i = iter(pages)

    request_mocker = mocker.MagicMock(
        side_effect=lambda *args, **kwargs: next(i))
    pluvo_mock = mocker.MagicMock(page_size=2, _request=request_mocker)
    p = PluvoResultSet(pluvo_mock, 'endpoint')

    assert len(p) == 4
    assert len(p) == 4
    # assert that even though len is called twice, we do not make 2 requests
    assert pluvo_mock._request.call_count == 1


def test_pluvo_resultset_iter(mocker):
    pages = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7],
    ]

    get_page_mock = mocker.MagicMock(side_effect=lambda x: pages[x])
    pluvo_mock = mocker.MagicMock(page_size=2)
    p = PluvoResultSet(pluvo_mock, 'endpoint')
    p._count = 7
    with patch.object(p, '_get_page', get_page_mock):
        assert list(iter(p)) == [1, 2, 3, 4, 5, 6, 7]
        get_page_mock.assert_has_calls([
            call(0), call(1), call(2), call(3)
        ])


def test_pluvo_init_client_credentials():
    p = pluvo.Pluvo(client_id='client_id', client_secret='client_secret')

    assert p.client_id == 'client_id'
    assert p.client_secret == 'client_secret'
    assert p.token is None
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_client_credentials_missing_one():
    with pytest.raises(pluvo.PluvoMisconfigured):
        pluvo.Pluvo(client_id='client_id')

    with pytest.raises(pluvo.PluvoMisconfigured):
        pluvo.Pluvo(client_secret='client_secret')


def test_pluvo_init_token():
    p = pluvo.Pluvo(token='token')

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token == 'token'
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_client_credentials_too_many():
    with pytest.raises(pluvo.PluvoMisconfigured):
        pluvo.Pluvo(client_id='client_id', client_secret='client_secret',
                    token='token')


def test_pluvo_init_no_credentials():
    with pytest.raises(pluvo.PluvoMisconfigured):
        pluvo.Pluvo()

    with pytest.raises(pluvo.PluvoMisconfigured):
        pluvo.Pluvo(client_id='', client_secret='')

    with pytest.raises(pluvo.PluvoMisconfigured):
        pluvo.Pluvo(client_id=None, client_secret=None)


def test_pluvo_init_api_url():
    p = pluvo.Pluvo(token='token', api_url='api_url')

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token == 'token'
    assert p.api_url == 'api_url'
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_page_size():
    p = pluvo.Pluvo(token='token', page_size='page_size')

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token == 'token'
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == 'page_size'


def test_pluvo_set_auth_headers():
    p = pluvo.Pluvo(client_id='client_id', client_secret='client_secret')

    retval = p._set_auth_headers()

    assert retval == {'client_id': 'client_id',
                      'client_secret': 'client_secret'}

    retval = p._set_auth_headers(headers={'test': 1})

    assert retval == {'client_id': 'client_id',
                      'client_secret': 'client_secret', 'test': 1}


def test_pluvo_set_auth_params():
    p = pluvo.Pluvo(token='token')

    retval = p._set_auth_params()

    assert retval == {'token': 'token'}

    retval = p._set_auth_params(params={'test': 1})

    assert retval == {'token': 'token', 'test': 1}


def test_pluvo_get_with_client_credentials(mocker):
    p = pluvo.Pluvo(client_id='client_id', client_secret='client_secret')
    requests_mock = mocker.patch(
        'requests.request', return_value=mocker.MagicMock(status_code=200))

    retval = p._request('GET', 'url')

    assert retval == requests_mock.return_value.json()
    requests_mock.assert_called_once_with(
        'GET', '{}url'.format(DEFAULT_API_URL), params={}, json=None,
        headers={'client_id': 'client_id', 'client_secret': 'client_secret'})


def test_pluvo_get_with_token(mocker):
    p = pluvo.Pluvo(token='token')
    requests_mock = mocker.patch(
        'requests.request', return_value=mocker.MagicMock(status_code=200))

    retval = p._request('GET', 'url')

    assert retval == requests_mock.return_value.json()
    requests_mock.assert_called_once_with(
        'GET', '{}url'.format(DEFAULT_API_URL), params={'token': 'token'},
        json=None, headers={})


def test_pluvo_get_with_params_and_token(mocker):
    p = pluvo.Pluvo(token='token')
    requests_mock = mocker.patch(
        'requests.request', return_value=mocker.MagicMock(status_code=200))

    retval = p._request('GET', 'url', params={'param': 1})

    assert retval == requests_mock.return_value.json()
    requests_mock.assert_called_once_with(
        'GET', '{}url'.format(DEFAULT_API_URL),
        json=None, params={'param': 1, 'token': 'token'}, headers={})


def test_pluvo_get_request_error(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch('requests.request', return_value=mocker.MagicMock(
        status_code=400, json=mocker.MagicMock(
            return_value={'error': 'error message'})))

    with pytest.raises(pluvo.PluvoAPIException) as exc_info:
        p._request('GET', 'url')

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == 'error message'
    assert str(exc_info.value) == 'HTTP status 400 - error message'


def test_pluvo_request_500_error(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch('requests.request', return_value=mocker.MagicMock(
        status_code=500, json=mocker.MagicMock(side_effect=ValueError())))

    with pytest.raises(pluvo.PluvoException):
        p._request('GET', 'url')


def test_pluvo_request_no_json_response(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch('requests.request', return_value=mocker.MagicMock(
        status_code=200, json=mocker.MagicMock(side_effect=ValueError())))

    with pytest.raises(pluvo.PluvoException):
        p._request('GET', 'url')


def test_pluvo_request_error_no_error_data(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch('requests.request', return_value=mocker.MagicMock(
        status_code=404, json=mocker.MagicMock(return_value={''})))

    with pytest.raises(pluvo.PluvoException):
        p._request('GET', 'url')


def test_pluvo_get_multiple(mocker):
    p = pluvo.Pluvo(token='token')
    pluvo_generator_mock = mocker.patch('pluvo.pluvo.PluvoResultSet')

    p._get_multiple('endpoint', params='params', method='POST')

    pluvo_generator_mock.assert_called_once_with(
        pluvo=p, endpoint='endpoint', params='params', method='POST')


def test_pluvo_put(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_set_auth_params')
    mocker.patch.object(p, '_set_auth_headers')
    requests_mock = mocker.patch(
        'requests.request', return_value=mocker.MagicMock(status_code=200))

    retval = p._request('PUT', 'endpoint', {'test': 1}, params='params')

    assert retval == requests_mock.return_value.json()
    p._set_auth_params.assert_called_once_with('params')
    p._set_auth_headers.assert_called_once_with()
    requests_mock.assert_called_once_with(
        'PUT', '{}endpoint'.format(DEFAULT_API_URL),
        params=p._set_auth_params.return_value,
        headers=p._set_auth_headers.return_value, json={"test": 1})


def test_pluvo_put_request_error(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch('requests.request', return_value=mocker.MagicMock(
        status_code=400, json=mocker.MagicMock(
            return_value={'error': 'error message'})))

    with pytest.raises(pluvo.PluvoAPIException) as exc_info:
        p._request('PUT', 'url', 'data')

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == 'error message'
    assert str(exc_info.value) == 'HTTP status 400 - error message'


def test_pluvo_post(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_set_auth_params')
    mocker.patch.object(p, '_set_auth_headers')
    requests_mock = mocker.patch(
        'requests.request', return_value=mocker.MagicMock(status_code=200))

    retval = p._request('POST', 'endpoint', {'test': 1}, params='params')

    assert retval == requests_mock.return_value.json()
    p._set_auth_params.assert_called_once_with('params')
    p._set_auth_headers.assert_called_once_with()
    requests_mock.assert_called_once_with(
        'POST', '{}endpoint'.format(DEFAULT_API_URL),
        params=p._set_auth_params.return_value,
        headers=p._set_auth_headers.return_value, json={"test": 1})


def test_pluvo_post_request_error(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch('requests.request', return_value=mocker.MagicMock(
        status_code=400, json=mocker.MagicMock(
            return_value={'error': 'error message'})))

    with pytest.raises(pluvo.PluvoAPIException) as exc_info:
        p._request('POST', 'url', 'data')

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == 'error message'
    assert str(exc_info.value) == 'HTTP status 400 - error message'


def test_pluvo_set_course_put(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.set_course({'id': 1})

    assert retval == p._request.return_value
    p._request.assert_called_once_with('PUT', 'course/1/', {'id': 1})


def test_delete_course(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.delete_course(1)

    assert retval == p._request.return_value
    p._request.assert_called_once_with('DELETE', 'course/1/')


def test_pluvo_set_course_post(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.set_course({'test': 1})

    assert retval == p._request.return_value
    p._request.assert_called_once_with('POST', 'course/', {'test': 1})


def test_pluvo_get_course(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_course(1)

    assert retval == p._request.return_value
    p._request.assert_called_once_with('GET', 'course/1/')


def test_pluvo_get_lti_info(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_lti_info(1)
    assert retval == p._request.return_value
    p._request.assert_called_once_with('GET', 'course/1/lti')


def test_pluvo_get_courses(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_get_multiple')

    retval = p.get_courses(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

    assert retval == p._get_multiple.return_value
    p._get_multiple.assert_called_once_with(
        'course/', params={
            'offset': 1, 'limit': 2, 'title': 3,
            'description': 4, 'published_from': 5,
            'published_to': 6, 'student_id': 7,
            'creator_id': 8, 'creation_date_from': 9,
            'creation_date_to': 10,
            'order_by': 11,
            'id': 12,
            'include_version_numbers': False,
        })


def test_pluvo_set_organisation_put(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.set_organisation({'id': 1})

    assert retval == p._request.return_value
    p._request.assert_called_once_with('PUT', 'organisation/1/', {'id': 1})


def test_pluvo_set_organisation_post(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.set_organisation({'test': 1})

    assert retval == p._request.return_value
    p._request.assert_called_once_with('POST', 'organisation/', {'test': 1})


def test_pluvo_get_s3_upload_token(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_s3_upload_token('filename.jpg', 'image/jpeg')

    assert retval == p._request.return_value
    p._request.assert_called_once_with(
        'GET', 'media/s3_upload_token/',
        params={'filename': 'filename.jpg', 'media_type': 'image/jpeg'})


def test_pluvo_get_token(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_token('student', 1, 2)

    assert retval == p._request.return_value
    p._request.assert_called_once_with('GET', 'user/token/student/',
                                       params={'user_id': 1, 'course_id': 2})


def test_pluvo_get_trainer_token(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_token('trainer', 1, 2, 3)

    assert retval == p._request.return_value
    p._request.assert_called_once_with('GET', 'user/token/trainer/', params={
        'user_id': 1, 'course_id': 2, 'trainer_id': 3})


def test_pluvo_get_user(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_user(1)

    assert retval == p._request.return_value
    p._request.assert_called_once_with('GET', 'user/1/')


def test_pluvo_get_users(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_get_multiple')

    retval = p.get_users(1, 2, 3, 4, 5, 6, 7)

    assert retval == p._get_multiple.return_value
    p._get_multiple.assert_called_once_with(
        'user/', params={
            'offset': 1, 'limit': 2, 'name': 3,
            'creation_date_from': 4, 'creation_date_to': 5,
            'created_course_id': 6, 'following_course_id': 7
        })


def test_pluvo_set_user_put(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.set_user({'id': 1})

    assert retval == p._request.return_value
    p._request.assert_called_once_with('PUT', 'user/1/', {'id': 1})


def test_pluvo_set_user_post(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.set_user({'test': 1})

    assert retval == p._request.return_value
    p._request.assert_called_once_with('POST', 'user/', {'test': 1})


def test_pluvo_get_progress_report(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_get_multiple')

    retval = p.get_progress_report([1, 2], [3, 4], ['-student_id'], 10, 0)
    assert retval == p._get_multiple.return_value
    p._get_multiple.assert_called_once_with('progress/reports/', params={
        'student_id': [1, 2],
        'course_id': [3, 4],
        'order_by': ['-student_id'],
        'offset': 10,
        'limit': 0,
    }, method='GET')


def test_pluvo_archive_student_course_version(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.archive_student_course_version(1, 2)
    assert retval == p._request.return_value
    p._request.assert_called_once_with(
        'PUT', 'course/1/user/2/', {'action': 'archive'})


def test_pluvo_get_course_report(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_course_report(1, 2)
    assert retval == p._request.return_value
    p._request.assert_called_once_with(
        'GET', 'report/course/1/user/2/', params={})


def test_pluvo_get_course_report_filename(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    filename = 'test.pdf'
    retval = p.get_course_report(1, 2, filename)
    assert retval == p._request.return_value
    p._request.assert_called_once_with(
        'GET', 'report/course/1/user/2/', params={'filename': filename})


def test_pluvo_get_version(mocker):
    p = pluvo.Pluvo(token='token')
    mocker.patch.object(p, '_request')

    retval = p.get_version()

    assert retval == p._request.return_value
    p._request.assert_called_once_with('GET', 'version/')
