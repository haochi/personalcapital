# Personal Capital

Python library for accessing Personal Capital data

# Installation

## With Pip

`pip install personalcapital`

## With Source Code

You can get the source code by cloning it from Github:

`git clone https://github.com/haochi/personalcapital.git`

or get the tarball:

`curl -OJL https://github.com/haochi/personalcapital/tarball/master`

then either include the library into your code, or install it with:

`python setup.py install`

# Usage

You need to first create an instance.

```python
pc = PersonalCapital()
```

Then you will need to authenticate the account by logging in:

```python
pc.login(email, password)
```

`login` may throw a `RequireTwoFactorException`, if two factor is enabled on your account and the current session is not yet associated with the account.
In this case, you will need to pick a way to complete the two factor authenticate by calling

```python
pc.two_factor_challenge(mode)
```

`mode` can either be `TwoFactorVerificationModeEnum.SMS` or `TwoFactorVerificationModeEnum.EMAIL`.  
Then you need to finish the two factor challenge by verifying the code and continue the login process.

```python
pc.two_factor_authenticate(mode, raw_input('code'))
pc.authenticate_password(password)
```

Once authenticated, you can start fetching data from the Personal Capital API.

```python
accounts_response = pc.fetch('/newaccount/getAccounts')
```

The above request will load your accounts data, and with that response you can get your net worth.

```python
print('Networth', accounts_response.json()['spData']['networth'])
```

To avoid two factor authentication every time you run the script, you can use `get_session()` to store your session somewhere and `set_session(session)` to re-use the session.

Here's the entire thing.

```python
from personalcapital import PersonalCapital, RequireTwoFactorException, TwoFactorVerificationModeEnum

pc = PersonalCapital()

email, password = "email@domain.tld", "password"

try:
    pc.login(email, password)
except RequireTwoFactorException:
    pc.two_factor_challenge(TwoFactorVerificationModeEnum.SMS)
    pc.two_factor_authenticate(TwoFactorVerificationModeEnum.SMS, raw_input('code: '))
    pc.authenticate_password(password)

accounts_response = pc.fetch('/newaccount/getAccounts')
accounts = accounts_response.json()['spData']

print('Networth: {0}'.format(accounts['networth']))
```

# Example

See `main.py` for an example script.

To run it, simply run `python main.py`.

Or set the environment email and password so you don't need to enter it every time.

```bash
PEW_PASSWORD="password" PEW_EMAIL="email" python main.py 
```

# Personal Capital API

Please inspect the network requests to see what requests are possible. The `main.py` example includes two such calls.
