from cloudgpt_aoai import get_chat_completion, encode_image

test_message = "What is the content in the image?"

test_chat_message = [
    {
        "role": "user",
        # multi-modality input in message
        "content": [
            {
                "type": "text",
                "text": test_message
            }
        ]
    }
]

response = get_chat_completion(
    engine="gpt-4o-20240513",
    messages=test_chat_message,
)

print(response.choices[0].message)