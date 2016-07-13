# Pluvo Python

[![Build Status](http://img.shields.io/travis/wendbv/pluvo-python.svg)](https://travis-ci.org/wendbv/pluvo-python)
[![Coverage Status](http://img.shields.io/coveralls/wendbv/pluvo-python.svg)](https://coveralls.io/r/wendbv/pluvo-python)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](https://tldrlegal.com/license/mit-license)

Python library to access the Pluvo REST API.

## Authentication using client credentials

To access the methods that need authentication with client credentials, for
instance getting data for a specific user:

```python
from pluvo import Pluvo

pluvo = Pluvo(client_id='client_id', client_secret='client_secret')

user = pluvo.get_user(1)
```

## Authentication using token

To access methods that need a token to authenticate.

```python
from pluvo import Pluvo

pluvo = Pluvo(token='token')

user = pluvo.get_user(1)
```

## API list endpoints

Methods for API endpoints that return a list will return a `PluvoGenerator`
instance. The first page of the results is immediately retrieved. The length
of the instance will be the total number of items. The instance implements
an iterator, fetching more pages as nessecary.

See this example with a total of 50 courses in Pluvo.

```python
from pluvo import Pluvo

pluvo = Pluvo(client_id='client_id', client_secret='client_secret')

# Only the first 20 courses and the total number of courses are retrieved.
courses = pluvo.get_courses()

# No extra request is done.
len(courses)  # 50

# Two more pages are retrieved.
list(courses)  # [...]
```

### Altering page size

The default page size of 20 can be changed when instantiating the `Pluvo`
object.

```pluvo
from pluvo import Pluvo

pluvo = Pluvo(
    client_id='client_id', client_secret='client_secret', page_size=50)
```

## API errors

When an API error is encountered an `PluvoAPIException` is raised.

```python
from pluvo import Pluvo, PluvoAPIException

# Not authenticated.
pluvo = Pluvo()

try:
    pluvo.get_course(1)
except PluvoAPIException as e:
    e.message  # 'Missing token or client_id and client_secret missing in headers.'
    e.status_code  # 403
    str(e)  # 'HTTP status 403 - Missing token or client_id and client_secret missing in headers.'
```

## General errors

All errors thrown by the library that are not a result of an API error will be
`PluvoException` errors. This is also the base class for `PluvoAPIException`.
