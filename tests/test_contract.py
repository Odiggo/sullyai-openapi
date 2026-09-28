"""Wire fixtures derived from api-server validators, mappers and HTTP handlers."""
import copy
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from scripts.validate import load_contract, validate_contract


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_contract()
        cls.registry = Registry().with_resource(
            'urn:sully:openapi', Resource.from_contents(cls.doc, default_specification=DRAFT202012)
        )

    def accepts(self, name, value, valid=True):
        validator = Draft202012Validator(
            {'$ref': f'urn:sully:openapi#/components/schemas/{name}'}, registry=self.registry
        )
        errors = list(validator.iter_errors(value))
        self.assertEqual(not errors, valid, f'{name}: {[e.message for e in errors]}')

    def test_document_and_auth(self):
        self.assertGreaterEqual(validate_contract(self.doc), 23)
        broken = copy.deepcopy(self.doc)
        broken['security'] = [{'apiKeyAuth': []}, {'accountIdAuth': []}]
        with self.assertRaises(AssertionError):
            validate_contract(broken)

    def test_null_only_fields_and_content_parts(self):
        for name, field in [('ChatCompletionChoice', 'logprobs'), ('ChatCompletionMessage', 'refusal')]:
            schema = self.doc['components']['schemas'][name]['properties'][field]
            validator = Draft202012Validator(schema)
            self.assertTrue(validator.is_valid(None))
            self.assertFalse(validator.is_valid('unsupported'))
        self.accepts('ChatCompletionContentPart', {'type': 'text', 'text': 'Example'})
        self.accepts('ChatCompletionContentPart', {'type': 'text'}, False)
        self.accepts('ChatCompletionContentPart', {'type': 'image_url'}, False)
        self.accepts('V2LanguageCode', 'no')
        self.accepts('V2LanguageCode', False, False)

    def test_notes_null_is_not_omission(self):
        for name in ('CreateNotePayload', 'CreateNoteV2Payload'):
            minimal = {'transcript': 'Example encounter', 'noteType': {'type': 'soap'}}
            self.accepts(name, minimal)
            self.accepts(name, {**minimal, 'patientInfo': None})
            for field in ('context', 'instructions', 'previousNote', 'medicationList', 'date', 'language'):
                self.accepts(name, {**minimal, field: None}, False)
            self.accepts(name, {'transcript': 'Example encounter', 'noteType': {}}, False)
        self.accepts('SoapNote', {'past_medical_history': [{'ended': None}]})

    def test_v2_template_and_demographics(self):
        request = {'transcript': 'Example encounter', 'noteType': {'type': 'note_template'}}
        self.accepts('CreateNoteV2Payload', request, False)
        self.accepts('CreateNoteV2Payload', {**request, 'noteType': {**request['noteType'], 'template': 'bad'}}, False)
        template = {'id': 'template_example', 'title': 'Example', 'global_prompt': 'Use provided facts', 'sections': [
            {'id': 'h1', 'type': 'heading', 'properties': {'level': 1, 'text': 'Assessment'}, 'children': [
                {'id': 't1', 'type': 'text', 'prompt': 'Summarize findings', 'properties': {}}
            ]},
            {'id': 'l1', 'type': 'list', 'prompt': 'List next steps', 'properties': {'list_type': 'bullet'}}
        ]}
        self.accepts('NoteTemplate', template)
        self.accepts('CreateNoteV2Payload', {**request, 'noteType': {**request['noteType'], 'template': template}, 'patientInfo': {'gender': 'self-described'}})
        broken = copy.deepcopy(template)
        broken['sections'][0]['properties'].pop('text')
        self.accepts('NoteTemplate', broken, False)

    def test_v3_strict_input(self):
        self.accepts('CreateNoteV3Payload', {'transcript': 'Example encounter'})
        self.accepts('CreateNoteV3Payload', {'transcript': '   '}, False)
        template = {'sections': [{'title': 'Summary', 'instructions': ''}]}
        self.accepts('CreateNoteV3Payload', {'transcript': 'Example', 'template': template})
        self.accepts('CreateNoteV3Payload', {'transcript': 'Example', 'templateId': 'x', 'template': template}, False)
        for extra in ({'unknown': True}, {'clinicalContext': None}, {'clinicalContext': {'patient': {'age': 151}}}):
            self.accepts('CreateNoteV3Payload', {'transcript': 'Example', **extra}, False)

    def test_note_success_and_error_envelopes(self):
        self.accepts('CreateNoteV2Response', {'status': 'ok', 'data': {'noteId': 'note_example'}, 'date': '2026-09-28T00:00:00Z'})
        self.accepts('GetNoteV2Response', {'status': 'ok', 'data': {'status': 'STATUS_PROCESSING', 'payload': {}, 'timestamp': {'start': 1}, 'created_at': '2026-09-28T00:00:00Z', 'updated_at': '2026-09-28T00:00:00Z'}, 'date': '2026-09-28T00:00:00Z'})
        for error in ({'message': 'Invalid API key'}, {'status': 'error', 'data': {'message': 'Note not found'}, 'date': '2026-09-28T00:00:00Z'}):
            self.accepts('NoteV2Error', error)
        self.accepts('NoteV2Error', {}, False)
        self.accepts('CreateNoteV3Response', {'requestId': 'req_example', 'note': 'Example note'})
        self.accepts('NoteV3Error', {'code': 'generation_timeout', 'message': 'Note generation timed out.', 'requestId': 'req_example'})

    def test_chat_request_and_structured_output(self):
        minimal = {'messages': [{'role': 'user', 'content': 'Example'}]}
        self.accepts('ChatCompletionCreateParams', minimal)
        self.accepts('ChatCompletionCreateParams', {'messages': []}, False)
        self.accepts('ChatCompletionCreateParams', {**minimal, 'model': None}, False)
        self.accepts('ChatCompletionCreateParams', {**minimal, 'reasoning_effort': None})
        self.accepts('ChatCompletionCreateParams', {**minimal, 'reasoning_effort': 'unsupported'}, False)
        self.accepts('ChatCompletionCreateParams', {**minimal, 'response_format': {'type': 'json_schema', 'json_schema': {'name': 'example', 'schema': {'type': 'object'}}}})

    def test_usage_omission_and_sse_null(self):
        completion = {'id': 'chatcmpl-example', 'object': 'chat.completion', 'created': 1, 'model': 'sully-clinical-1', 'choices': [{'index': 0, 'finish_reason': 'stop', 'logprobs': None, 'message': {'role': 'assistant', 'content': 'Example', 'refusal': None}}]}
        self.accepts('ChatCompletion', completion)
        self.accepts('ChatCompletion', {**completion, 'usage': None}, False)
        usage = {'prompt_tokens': 2, 'completion_tokens': 1, 'total_tokens': 3, 'prompt_tokens_details': {'cached_tokens': 0}}
        self.accepts('ChatCompletion', {**completion, 'usage': usage})
        chunk = {'id': 'chatcmpl-example', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'sully-clinical-1', 'choices': []}
        self.accepts('ChatCompletionChunk', {**chunk, 'usage': None})
        self.accepts('ChatCompletionChunk', {**chunk, 'usage': usage})
        self.accepts('ChatCompletionChunk', {**chunk, 'choices': [{'index': 0, 'delta': {'content': 'Example'}, 'finish_reason': None}]})

    def test_openai_errors_include_billing_codes(self):
        for code in ('insufficient_funds', 'billing_provider_unavailable', 'billing_conflict', 'invalid_api_key'):
            self.accepts('OpenAIErrorResponse', {'error': {'code': code, 'message': 'Example error', 'type': 'invalid_request_error', 'param': None}})
        self.accepts('OpenAIErrorResponse', {'error': {'code': 'invalid_value', 'message': 'Example', 'type': 'invalid_request_error'}}, False)

    def test_uploads_and_tokens(self):
        for name in ('CreateAudioTranscriptionPayload', 'CreateV2TranscriptionPayload'):
            self.accepts(name, {}, False)
            self.accepts(name, {'audio': 'binary-file'})
        self.accepts('CreateV2TranscriptionPayload', {'audio': 'binary-file', 'dictation': False})
        self.accepts('CreateAudioTranscriptionJsonPayload', {'audio': 'YWJj', 'filename': 'example.wav', 'encoding': 'base64'})
        self.accepts('CreateAudioTranscriptionJsonPayload', {'audio': 'YWJj'}, False)
        self.accepts('CreateAudioTranscriptionResponse', {'status': 'ok', 'date': '2026-09-28T00:00:00Z', 'data': {'transcriptionId': 'tr_example', 'message': 'Accepted', 'status': 'STATUS_PROCESSING'}})
        self.accepts('CreateStreamingTranscriptionTokenPayload', {})
        self.accepts('CreateStreamingTranscriptionTokenResponse', {'status': 'ok', 'date': '2026-09-28T00:00:00Z', 'data': {'token': 'example'}})
        self.accepts('CreateStreamingTranscriptionTokenResponse', {'token': 'example'}, False)
        upload = self.doc['paths']['/v2/audio/transcriptions']['post']
        self.assertIn('400', upload['responses'])
        self.assertIn('audio/wav', upload['requestBody']['content']['multipart/form-data']['encoding']['audio']['contentType'])
        delete = self.doc['paths']['/v2/audio/transcriptions/{id}']['delete']
        self.assertNotIn('content', delete['responses']['204'])


if __name__ == '__main__':
    unittest.main()
