# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import os
from ..module import (
    load_config,
    load_llm_config,
    get_prometheus_url
)

def load_gpt_config(cache_seed: int | None = 42):
    secret = load_llm_config('secret.yaml')

    backend = secret['backend']
    assert backend in ['OpenAI', 'AzureOpenAI', 'Other'], f"Invalid backend"

    llm_config = secret[backend]
    llm_config['cache_seed'] = cache_seed
    llm_config['max_retries'] = 5
    llm_config['timeout'] = 60
    return llm_config

def load_reasoning_config(cache_seed: int | None = 42):
    secret = load_llm_config('secret_reasoning.yaml')

    backend = secret['backend']
    assert backend in ['OpenAI', 'AzureOpenAI', 'Other'], f"Invalid backend"

    llm_config = secret[backend]
    llm_config['cache_seed'] = cache_seed
    return llm_config

def load_service_maintainer_config(filename: str = 'service_maintainers.yaml'):
    maintainer_config = load_config(filename)
    maintainer_config['prometheus_url'] = get_prometheus_url()
    return maintainer_config  
    

AWAITING_FLAG = '<AWAITING FOR RESPONSE>'
TERMINATE_FLAG = 'TERMINATE'
TERMINATE = lambda x: x.get("content", "").find("TERMINATE") != -1