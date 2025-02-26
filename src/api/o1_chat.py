import argparse
from msal import PublicClientApplication
import json
import requests
import os
import time

class LLMClient:

    # 获取当前脚本所在的绝对路径
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    # 在脚本同级目录下保存 token 文件
    _TOKEN_CACHE_FILE = os.path.join(_SCRIPT_DIR, 'llm_token.json')

    _ENDPOINT = 'https://fe-26.qas.bing.net/sdf/'
    _SCOPES = ['https://substrate.office.com/llmapi/LLMAPI.dev']
    _API = 'chat/completions'

    def __init__(self, endpoint):
        self._app = PublicClientApplication(
            '68df66a4-cad9-4bfd-872b-c6ddde00d6b2',
            authority='https://login.microsoftonline.com/72f988bf-86f1-41af-91ab-2d7cd011db47',
            allow_broker=True
        )
        if endpoint is not None:
            LLMClient._ENDPOINT = endpoint
        LLMClient._ENDPOINT += self._API

    def send_request(self, model_name, request):
        # 获取 token
        token = self._get_token()
        # 填充请求头
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
            'X-ModelType': model_name
        }
        body = json.dumps(request).encode('utf-8')
        response = requests.post(LLMClient._ENDPOINT, data=body, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}. Response: {response.text}")
        return response.json()

    def _get_token(self):
        """
        从本地缓存读取或通过 DeviceCodeCredential 获取最新 token。
        """
        from azure.identity import DeviceCodeCredential

        # 如果本地有缓存的 token，且未过期，则直接使用
        if os.path.exists(self._TOKEN_CACHE_FILE):
            with open(self._TOKEN_CACHE_FILE, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            # 判断是否过期：expires_on 为 epoch 时间戳
            if token_data.get('expires_on') and token_data['expires_on'] > time.time():
                return token_data['token']

        # 如果没有缓存或已过期，则重新获取
        cred = DeviceCodeCredential(
            client_id='68df66a4-cad9-4bfd-872b-c6ddde00d6b2',
            tenant_id='72f988bf-86f1-41af-91ab-2d7cd011db47'
        )
        token_response = cred.get_token('https://substrate.office.com/llmapi/LLMAPI.dev')

        # 将 token 及过期时间保存到本地文件
        token_data = {
            'token': token_response.token,
            'expires_on': token_response.expires_on  # epoch 时间戳
        }
        with open(self._TOKEN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)

        return token_response.token

def get_o1_chat_completion(messages):
    llm_client = LLMClient(None)
    request_data = {
        "messages": [
            {"role": "user", "content": messages}
        ]
    }
    response = llm_client.send_request('dev-gpt-4o-11-20', request_data)
    return response["choices"][0]["message"]["content"]

if __name__ == '__main__':
    messages = "Hello, how are you?"
    response = get_o1_chat_completion(messages)
    print(response)
