import pickle
import requests
import re

csrf_regexp = re.compile(r"window.csrf ='([a-f0-9-]+)'")
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
base_url = 'https://home.personalcapital.com'
ident_endpoint = base_url + '/page/login/goHome'
api_endpoint = base_url + '/api'

SP_HEADER_KEY = "spHeader"
SUCCESS_KEY = "success"
CSRF_KEY = "csrf"
AUTH_LEVEL_KEY = "authLevel"
ERRORS_KEY = "errors"

def getSpHeaderValue(result, valueKey):
    if (SP_HEADER_KEY in result) and (valueKey in result[SP_HEADER_KEY]):
        return result[SP_HEADER_KEY][valueKey]
    return None

def getErrorValue(result):
    try:
        return getSpHeaderValue(result, ERRORS_KEY)[0]['message']
    except (ValueError, IndexError):
        return None

class AuthLevelEnum(object):
    USER_REMEMBERED = "USER_REMEMBERED"

class TwoFactorVerificationModeEnum(object):
    SMS = 0
    # PHONE = 1
    EMAIL = 2

class RequireTwoFactorException(Exception):
    pass

class LoginFailedException(Exception):
    pass

class PersonalCapital(object):
    def __init__(self):
        self.__session = requests.Session()
        self.__session.headers.update({'user-agent': user_agent})
        self.__csrf = ""

    def login(self, username, password):
        initial_csrf = self.__get_csrf_from_home_page(ident_endpoint)
        if initial_csrf is None:
          LoginFailedException("Unable to extract initial CSRF token")
        csrf, auth_level = self.__identify_user(username, initial_csrf)
        if csrf is None or auth_level is None:
          LoginFailedException("Unable to extract CSRF token and user auth level")

        if csrf and auth_level:
            self.__csrf = csrf
            if auth_level != AuthLevelEnum.USER_REMEMBERED:
                raise RequireTwoFactorException()
            result = self.__authenticate_password(password).json()
            if getSpHeaderValue(result, SUCCESS_KEY) == False:
                raise LoginFailedException(getErrorValue(result))
        else:
            raise LoginFailedException()

    def authenticate_password(self, password):
        return self.__authenticate_password(password)

    def two_factor_authenticate(self, mode, code):
        if mode == TwoFactorVerificationModeEnum.SMS:
            return self.__authenticate_sms(code)
        elif mode == TwoFactorVerificationModeEnum.EMAIL:
            return self.__authenticate_email(code)

    def two_factor_challenge(self, mode):
        if mode == TwoFactorVerificationModeEnum.SMS:
            return self.__challenge_sms()
        elif mode == TwoFactorVerificationModeEnum.EMAIL:
            return self.__challenge_email()

    def fetch(self, endpoint, data = None):
        """
        for getting data after logged in
        """
        payload = {
            "lastServerChangeId": "-1",
            "csrf": self.__csrf,
            "apiClient": "WEB"
        }
        if data is not None:
            payload.update(data)

        return self.post(endpoint, payload)

    def post(self, endpoint, data):
        response = self.__session.post(api_endpoint + endpoint, data)
        return response

    def get_session(self):
        """
        return cookies as a dictionary
        """
        return requests.utils.dict_from_cookiejar(self.__session.cookies)

    def set_session(self, cookies):
        """
        sets the cookies (should be a dictionary)
        """
        self.__session.cookies = requests.utils.cookiejar_from_dict(cookies)

    def save_session(self, filename):
      session_data = {
          "csrf": self.__csrf,
          "cookies": self.__session.cookies._cookies, 
      }
      with open(filename, 'wb') as fh:
        pickle.dump(session_data, fh) 
        
    def load_session(self, filename):
      with open(filename, 'rb') as fh:
        data = pickle.load(fh) 
        jar = requests.cookies.RequestsCookieJar() 
        jar._cookies = data["cookies"]
        self.__session.cookies = jar
        self.__csrf = data["csrf"]

    # private methods
    def __get_csrf_from_home_page(self, url):
        r = self.__session.get(url)
        found_csrf = csrf_regexp.search(r.text)

        if found_csrf:
            return found_csrf.group(1)
        return None

    def __identify_user(self, username, csrf):
        """
        Returns reusable CSRF code and the auth level as a 2-tuple
        """
        data = {
            "username": username,
            "csrf": csrf,
            "apiClient": "WEB",
            "bindDevice": "false",
            "skipLinkAccount": "false",
            "redirectTo": "",
            "skipFirstUse": "",
            "referrerId": "",
        }

        r = self.post("/login/identifyUser", data)

        if r.status_code == requests.codes.ok:
            result = r.json()
            new_csrf = getSpHeaderValue(result, CSRF_KEY)
            auth_level = getSpHeaderValue(result, AUTH_LEVEL_KEY)
            return (new_csrf, auth_level)

        return (None, None)

    def __generate_challenge_payload(self, challenge_type):
        return {
            "challengeReason": "DEVICE_AUTH",
            "challengeMethod": "OP",
            "challengeType": challenge_type,
            "apiClient": "WEB",
            "bindDevice": "false",
            "csrf": self.__csrf
        }

    def __generate_authentication_payload(self, code):
        return {
            "challengeReason": "DEVICE_AUTH",
            "challengeMethod": "OP",
            "apiClient": "WEB",
            "bindDevice": "false",
            "code": code,
            "csrf": self.__csrf
        }

    def __challenge_email(self):
        data = self.__generate_challenge_payload("challengeEmail")
        return self.post("/credential/challengeEmail", data)

    def __authenticate_email(self, code):
        data = self.__generate_authentication_payload(code)
        return self.post("/credential/authenticateEmailByCode", data)

    def __challenge_sms(self):
        data = self.__generate_challenge_payload("challengeSMS")
        return self.post("/credential/challengeSms", data)

    def __authenticate_sms(self, code):
        data = self.__generate_authentication_payload(code)
        return self.post("/credential/authenticateSms", data)

    def __authenticate_password(self, passwd):
        data = {
            "bindDevice": "true",
            "deviceName": "Personal Capital Python API",
            "redirectTo": "",
            "skipFirstUse": "",
            "skipLinkAccount": "false",
            "referrerId": "",
            "passwd": passwd,
            "apiClient": "WEB",
            "csrf": self.__csrf
        }
        return self.post("/credential/authenticatePassword", data)
        