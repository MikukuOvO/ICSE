import os
import asyncio

from autogen_core.models import UserMessage
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_core.models import ModelFamily

# Create the token provider
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "api://feb7b661-cac7-44a8-8dc1-163b63c23df2/.default")

az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="o1-mini-20240912",
    model="o1-mini-2024-09-12",
    api_version="2024-06-01",
    azure_endpoint="https://cloudgpt-openai.azure-api.net/",
    azure_ad_token_provider=token_provider,  # Optional if you choose key-based authentication.
    # model_info=custom_model_info, 
)

async def main():
    result = await az_model_client .create([UserMessage(content="What is the capital of France?", source="user")])
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
