"""Import the installed wheel and exercise auth, aliases, unions and nullability."""
import importlib
import pkgutil

import sully_openapi_smoke as sdk

for module in pkgutil.walk_packages(sdk.__path__, sdk.__name__ + '.'):
    importlib.import_module(module.name)

config = sdk.Configuration(api_key={'apiKeyAuth': 'example-key', 'accountIdAuth': 'example-account'})
settings = config.auth_settings()
assert settings['apiKeyAuth']['value'] == 'example-key'
assert settings['accountIdAuth']['value'] == 'example-account'
assert settings['apiKeyAuth']['key'] == 'X-API-Key'
assert settings['accountIdAuth']['key'] == 'X-Account-Id'
payload = sdk.CreateNoteV2Payload.from_dict({'transcript': 'Example', 'noteType': {'type': 'soap'}})
assert 'context' not in payload.to_dict()
template = {'id': 'example', 'title': 'Example', 'sections': [], 'globalPrompt': 'legacy', 'global_prompt': 'preferred'}
assert sdk.NoteTemplate.from_dict(template).to_dict() == template
completion = {'id': 'chatcmpl-example', 'object': 'chat.completion', 'created': 1, 'model': 'example', 'choices': [{'index': 0, 'finish_reason': 'stop', 'logprobs': None, 'message': {'role': 'assistant', 'content': 'Example', 'refusal': None}}]}
assert sdk.ChatCompletion.from_dict(completion).usage is None
chunk = {'id': 'chatcmpl-example', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'example', 'choices': [], 'usage': None}
assert sdk.ChatCompletionChunk.from_dict(chunk).usage is None
content = [{'type': 'text', 'text': 'Example'}]
assert sdk.ApiClient().sanitize_for_serialization(sdk.ChatCompletionMessageParam.from_dict({'role': 'user', 'content': content}))['content'] == content
print('Python installed-wheel smoke passed')
