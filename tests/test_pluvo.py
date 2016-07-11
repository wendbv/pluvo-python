from mock import call
import pytest

import pluvo
from pluvo.pluvo import PluvoGenerator, DEFAULT_API_URL, DEFAULT_PAGE_SIZE


class Multiple:
    call_nr = 0

    def __init__(self, pages):
        self.pages = pages

    def results(self, *args, **kwargs):
        result = self.pages[self.call_nr]
        self.call_nr += 1
        return result


def test_pluvo_generator_one_page(mocker):
    pages = [
        {'count': 2, 'data': [1, 2]}
    ]

    _get_mock = mocker.MagicMock(side_effect=Multiple(pages).results)
    pluvo_mock = mocker.MagicMock(page_size=2, _get=_get_mock)

    retval = PluvoGenerator(pluvo_mock, 'endpoint')

    assert len(retval) == 2
    assert list(retval) == [1, 2]
    _get_mock.assert_has_calls([
        call('endpoint', params={'limit': 2, 'offset': 0})])


def test_pluvo_generator_two_pages(mocker):
    pages = [
        {'count': 4, 'data': [1, 2]},
        {'count': 4, 'data': [3, 4]}
    ]

    _get_mock = mocker.MagicMock(side_effect=Multiple(pages).results)
    pluvo_mock = mocker.MagicMock(page_size=2, _get=_get_mock)

    retval = PluvoGenerator(pluvo_mock, 'endpoint')

    assert len(retval) == 4
    assert list(retval) == [1, 2, 3, 4]
    _get_mock.assert_has_calls([
        call('endpoint', params={'limit': 2, 'offset': 0}),
        call('endpoint', params={'limit': 2, 'offset': 2})
    ])


def test_pluvo_generator_limit(mocker):
    pages = [
        {'count': 4, 'data': [1, 2]},
        {'count': 4, 'data': [3, 4]}
    ]

    _get_mock = mocker.MagicMock(side_effect=Multiple(pages).results)
    pluvo_mock = mocker.MagicMock(page_size=2, _get=_get_mock)

    retval = PluvoGenerator(pluvo_mock, 'endpoint', params={'limit': 3})

    assert len(retval) == 3
    assert list(retval) == [1, 2, 3]
    _get_mock.assert_has_calls([
        call('endpoint', params={'limit': 2, 'offset': 0}),
        call('endpoint', params={'limit': 1, 'offset': 2})
    ])


def test_pluvo_generator_offset(mocker):
    pages = [
        {'count': 4, 'data': [3, 4]}
    ]

    _get_mock = mocker.MagicMock(side_effect=Multiple(pages).results)
    pluvo_mock = mocker.MagicMock(page_size=2, _get=_get_mock)

    retval = PluvoGenerator(pluvo_mock, 'endpoint', params={'offset': 2})

    assert len(retval) == 2
    assert list(retval) == [3, 4]
    _get_mock.assert_has_calls([
        call('endpoint', params={'limit': 2, 'offset': 2})
    ])


def test_pluvo_generator_limit_and_offset(mocker):
    pages = [
        {'count': 1, 'data': [3]}
    ]

    _get_mock = mocker.MagicMock(side_effect=Multiple(pages).results)
    pluvo_mock = mocker.MagicMock(page_size=2, _get=_get_mock)

    retval = PluvoGenerator(pluvo_mock, 'endpoint',
                            params={'limit': 1, 'offset': 2})

    assert len(retval) == 1
    assert list(retval) == [3]
    _get_mock.assert_has_calls([
        call('endpoint', params={'limit': 1, 'offset': 2})
    ])


def test_pluvo_generator_retrieving_less_items(mocker):
    pages = [
        {'count': 3, 'data': [1, 2]},
        {'count': 3, 'data': []}
    ]

    _get_mock = mocker.MagicMock(side_effect=Multiple(pages).results)
    pluvo_mock = mocker.MagicMock(page_size=2, _get=_get_mock)

    retval = PluvoGenerator(pluvo_mock, 'endpoint')

    assert len(retval) == 3
    assert list(retval) == [1, 2]
    _get_mock.assert_has_calls([
        call('endpoint', params={'limit': 2, 'offset': 0}),
        call('endpoint', params={'limit': 1, 'offset': 2})
    ])


def test_pluvo_init():
    p = pluvo.Pluvo()

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token is None
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_client_credentials():
    p = pluvo.Pluvo(client_id='client_id', client_secret='client_secret')

    assert p.client_id == 'client_id'
    assert p.client_secret == 'client_secret'
    assert p.token is None
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_client_credentials_missing_one():
    with pytest.raises(pluvo.PluvoException):
        pluvo.Pluvo(client_id='client_id')

    with pytest.raises(pluvo.PluvoException):
        pluvo.Pluvo(client_secret='client_secret')


def test_pluvo_init_token():
    p = pluvo.Pluvo(token='token')

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token == 'token'
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_client_credentials_too_many():
    with pytest.raises(pluvo.PluvoException):
        pluvo.Pluvo(client_id='client_id', client_secret='client_secret',
                    token='token')


def test_pluvo_init_api_url():
    p = pluvo.Pluvo(api_url='api_url')

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token is None
    assert p.api_url == 'api_url'
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_pluvo_init_page_size():
    p = pluvo.Pluvo(page_size='page_size')

    assert p.client_id is None
    assert p.client_secret is None
    assert p.token is None
    assert p.api_url == DEFAULT_API_URL
    assert p.page_size == 'page_size'


def test_pluvo_get(mocker):
    p = pluvo.Pluvo()
    requests_get_mock = mocker.patch(
        'requests.get', return_value=mocker.MagicMock(status_code=200))

    retval = p._get('url')

    assert retval == requests_get_mock.return_value.json()
    requests_get_mock.assert_called_once_with(
        '{}url'.format(DEFAULT_API_URL), params={}, headers={})


def test_pluvo_get_with_client_credentials(mocker):
    p = pluvo.Pluvo(client_id='client_id', client_secret='client_secret')
    requests_get_mock = mocker.patch(
        'requests.get', return_value=mocker.MagicMock(status_code=200))

    retval = p._get('url')

    assert retval == requests_get_mock.return_value.json()
    requests_get_mock.assert_called_once_with(
        '{}url'.format(DEFAULT_API_URL), params={},
        headers={'client_id': 'client_id', 'client_secret': 'client_secret'})


def test_pluvo_get_with_token(mocker):
    p = pluvo.Pluvo(token='token')
    requests_get_mock = mocker.patch(
        'requests.get', return_value=mocker.MagicMock(status_code=200))

    retval = p._get('url')

    assert retval == requests_get_mock.return_value.json()
    requests_get_mock.assert_called_once_with(
        '{}url'.format(DEFAULT_API_URL), params={'token': 'token'},
        headers={})


def test_pluvo_get_with_params(mocker):
    p = pluvo.Pluvo()
    requests_get_mock = mocker.patch(
        'requests.get', return_value=mocker.MagicMock(status_code=200))

    retval = p._get('url', params={'param': 1})

    assert retval == requests_get_mock.return_value.json()
    requests_get_mock.assert_called_once_with(
        '{}url'.format(DEFAULT_API_URL), params={'param': 1},
        headers={})


def test_pluvo_get_with_params_and_token(mocker):
    p = pluvo.Pluvo(token='token')
    requests_get_mock = mocker.patch(
        'requests.get', return_value=mocker.MagicMock(status_code=200))

    retval = p._get('url', params={'param': 1})

    assert retval == requests_get_mock.return_value.json()
    requests_get_mock.assert_called_once_with(
        '{}url'.format(DEFAULT_API_URL),
        params={'param': 1, 'token': 'token'}, headers={})


def test_pluvo_get_request_error(mocker):
    p = pluvo.Pluvo()
    mocker.patch('requests.get', return_value=mocker.MagicMock(
            status_code=400, json=mocker.MagicMock(
                return_value={'message': 'error message'})))

    with pytest.raises(pluvo.PluvoRequestException) as exc_info:
        p._get('url')

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == 'error message'
    assert str(exc_info.value) == 'HTTP status 400 - error message'


def test_pluvo_get_multiple(mocker):
    p = pluvo.Pluvo()
    pluvo_generator_mock = mocker.patch('pluvo.pluvo.PluvoGenerator')

    p._get_multiple('endpoint', params='params')

    pluvo_generator_mock.assert_called_once_with(
        pluvo=p, endpoint='endpoint', params='params')


def test_pluvo_get_courses(mocker):
    p = pluvo.Pluvo()
    mocker.patch.object(p, '_get_multiple')

    retval = p.get_courses(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

    assert retval == p._get_multiple.return_value
    p._get_multiple.assert_called_once_with(
        'course/', params={
            'offset': 1, 'limit': 2, 'title': 3,
            'description': 4, 'published_from': 5,
            'published_to': 6, 'student_id': 7,
            'creator_id': 8, 'creation_date_from': 9,
            'creation_date_to': 10
        })


def test_pluvo_get_user(mocker):
    p = pluvo.Pluvo()
    mocker.patch.object(p, '_get')

    retval = p.get_user(1)

    assert retval == p._get.return_value
    p._get.assert_called_once_with('user/1/')


def test_pluvo_get_version(mocker):
    p = pluvo.Pluvo()
    mocker.patch.object(p, '_get')

    retval = p.get_version()

    assert retval == p._get.return_value
    p._get.assert_called_once_with('version/')
