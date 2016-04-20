import os, json, requests, collections, time, sys
import xml.etree.ElementTree as ET

access_token = collections.namedtuple('token_props', ['json', 'expires_epoch'])

_cs = None
def _get_client_secret():
    global _cs
    if _cs is None:
        client_secret_file = os.path.expanduser('~/.azure/myapp.secret')
        if not os.path.isfile(client_secret_file):
            raise Exception('''
    You have to configure credentials before this script will work properly.
    Define an application for your account in the Microsoft Azure Marketplace.
    Then look up the application's "Client secret" and store its value in
    %s.
    
    (It's highly recommended that you restrict access to this file, such that
    it cannot be read, written, or deleted except by your account.)
    ''' % client_secret_file)
        with open(client_secret_file, 'r') as f:
            _cs = f.read().strip()
    return _cs


def get_root_inner_text(xml_bytes):
    e = ET.XML(xml_bytes, parser=ET.XMLParser(encoding="UTF-8"))
    return e.text

class microsoft_translator:
    '''
    Transparently manages an access to the Microsoft Translator web service,
    including both language detection and translation.
    
    Requires a password in an external data file, plus some simple account
    setup as documented at http://j.mp/23IIweW. The token for credentials is
    automatically renewed each time it nears its 10 minute expiration.
    '''
    def __init__(self, should_trace=True):
        self._access_token = None
        self.should_trace = should_trace
        
    def trace(self, msg):
        if self.should_trace:
            print(msg)
            
    def _request_new_access_token(self):
        resp_time = time.time()
        params = {
            'client_id': 'webpulse',
            'client_secret': _get_client_secret(),
            'scope': 'http://api.microsofttranslator.com',
            'grant_type': 'client_credentials',
        }
        uri = 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13'
        self.trace('POST %s' % uri)
        resp = requests.post(uri, data=params)
        x = json.loads(resp.text)
        self._access_token = access_token(x, resp_time + 570)
        
    def _get_access_token(self):
        if self._access_token is None or (self._access_token.expires_epoch < time.time() - 30):
            self._request_new_access_token()
        return self._access_token
    
    def _get_credential(self):
        tok = self._get_access_token()
        return 'Bearer %s' % tok.json['access_token']
    
    def detect_lang(self, text):
        uri = 'http://api.microsofttranslator.com/v2/Http.svc/Detect'
        self.trace('GET %s' % uri)
        resp = requests.get(uri,
                     params={'text': text},
                     headers={'Authorization': self._get_credential()})
        return get_root_inner_text(resp.content)
    
    def translate(self, text, source_lang_code, target_lang_code):
        uri = 'http://api.microsofttranslator.com/v2/Http.svc/Translate'
        self.trace('GET %s' % uri)
        resp = requests.get(uri,
                    params={'from': source_lang_code,
                            'to': target_lang_code,
                            'text': text},
                    headers={'Authorization': self._get_credential()})
        return get_root_inner_text(resp.content)
    
if __name__ == '__main__':
    # Make sure we have credentials configured properly.
    _get_client_secret()
    mt = microsoft_translator()
    try:
        while True:
            sys.stdout.write('Enter some English text (CTRL+C to quit): ')
            src_txt = raw_input()
            tgt_txt = mt.translate(src_txt, 'en', 'es')
            print(tgt_txt)
    except KeyboardInterrupt:
        sys.stdout.write('\n')
