// Smoke-test the compiled package without calling a live service.
const assert = require('node:assert/strict');
const path = require('node:path');
const sdk = require(path.resolve(process.argv[2]));
(async () => {
  const requests = [];
  const config = new sdk.Configuration({
    basePath: 'https://example.invalid',
    apiKey: name => ({ 'X-API-Key': 'example-key', 'X-Account-Id': 'example-account' })[name],
    fetchApi: async (url, init) => {
      requests.push({ url, ...init });
      const data = url.endsWith('/v2/notes')
        ? { status: 'ok', data: { noteId: 'note_example' }, date: '2026-09-28T00:00:00Z' }
        : { data: { id: 'tr_example', status: 'pending', created_at: '2026-09-28T00:00:00Z', updated_at: '2026-09-28T00:00:00Z' } };
      return new Response(JSON.stringify(data), { status: url.endsWith('/v2/notes') ? 200 : 201, headers: { 'Content-Type': 'application/json' } });
    },
  });
  const result = await new sdk.NotesV2Api(config).createNoteV2({ createNoteV2Payload: { transcript: 'Example', noteType: { type: 'soap' } } });
  assert.equal(result.data.noteId, 'note_example');
  assert.equal(requests[0].headers['X-API-Key'], 'example-key');
  assert.equal(requests[0].headers['X-Account-Id'], 'example-account');
  assert.equal(Object.hasOwn(JSON.parse(requests[0].body), 'context'), false);
  await new sdk.V2TranscriptionsApi(config).createV2Transcription({ audio: new Blob(['audio-example'], { type: 'audio/wav' }), dictation: false });
  const form = requests[1].body;
  assert(form instanceof FormData);
  assert.equal(form.get('audio').type, 'audio/wav');
  assert.equal(await form.get('audio').text(), 'audio-example');
  assert.equal(form.get('dictation'), 'false');
  assert.equal(requests[1].headers['X-Account-Id'], 'example-account');
  const template = { id: 'example', title: 'Example', sections: [], globalPrompt: 'legacy', global_prompt: 'preferred' };
  assert.deepEqual(sdk.NoteTemplateToJSON(template), template);
  const content = [{ type: 'text', text: 'Example' }, { type: 'image_url', image_url: { url: 'data:image/png;base64,YQ==' } }];
  assert.deepEqual(JSON.parse(JSON.stringify(sdk.ChatCompletionMessageParamToJSON({ role: 'user', content }))).content, content);
  console.log('TypeScript wire smoke passed');
})().catch(error => { console.error(error); process.exit(1); });
