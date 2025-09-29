from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def openai_model(messages, model_name: str = "gpt-4o-mini", temperature: float = 0.2):
    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature
    )
    return resp.choices[0].message.content


def openai_model_stream(messages, model_name: str = "gpt-4o-mini", temperature: float = 0.2):
    stream = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
        temperature=temperature,
    )
    for part in stream:
        delta = part.choices[0].delta
        if delta and delta.content:
            yield delta.content
