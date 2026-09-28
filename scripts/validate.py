"""Validate the canonical document and generator-facing invariants."""
from pathlib import Path
import re
import sys

import yaml
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parents[1]
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace'}


class ContractLoader(yaml.SafeLoader):
    """Keep YAML timestamps as JSON strings and reject duplicate mapping keys."""

    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(k, deep=deep) for k, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError(f'Duplicate YAML key at line {node.start_mark.line + 1}')
        return super().construct_mapping(node, deep=deep)


ContractLoader.yaml_implicit_resolvers = {
    key: [entry for entry in entries if entry[0] != 'tag:yaml.org,2002:timestamp']
    for key, entries in ContractLoader.yaml_implicit_resolvers.items()
}


def load_contract(path=ROOT / 'openapi.yaml'):
    return yaml.load(Path(path).read_text(), Loader=ContractLoader)


def walk(value):
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            if key not in {'example', 'examples'}:
                yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate_contract(document):
    validate(document)
    assert document['openapi'].startswith('3.1.')
    assert document['security'] == [{'apiKeyAuth': [], 'accountIdAuth': []}]
    schemes = document['components']['securitySchemes']
    for name, header in [('apiKeyAuth', 'x-api-key'), ('accountIdAuth', 'x-account-id')]:
        assert schemes[name]['type'] == 'apiKey' and schemes[name]['in'] == 'header'
        assert schemes[name]['name'].lower() == header
    ids = set()
    for path, item in document['paths'].items():
        for method, operation in item.items():
            if method not in METHODS:
                continue
            operation_id = operation.get('operationId', '')
            assert re.fullmatch('[a-z][A-Za-z0-9]*', operation_id), (path, operation_id)
            assert operation_id not in ids, f'Duplicate operationId: {operation_id}'
            ids.add(operation_id)
            security = operation.get('security', document['security'])
            expected = [{'apiKeyAuth': [], 'accountIdAuth': []}]
            if path.startswith('/openai/'):
                expected += [{'compatCompositeBearerAuth': []}, {'compatBearerAuth': [], 'accountIdAuth': []}]
            assert security == expected, f'Unexpected authentication for {path}'
            for media in operation.get('requestBody', {}).get('content', {}).values():
                assert '$ref' in media['schema'], f'Unnamed request model: {path}'
    for node in walk(document):
        assert 'nullable' not in node, 'OpenAPI 3.0 nullable keyword is not supported'
        if '$ref' in node:
            reference = node['$ref']
            assert reference.startswith('#/'), f'External reference: {reference}'
            target = document
            for part in reference[2:].split('/'):
                target = target[part.replace('~1', '/').replace('~0', '~')]
    return len(ids)


if __name__ == '__main__':
    document = load_contract(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'openapi.yaml')
    print(f'Valid OpenAPI 3.1: {validate_contract(document)} unique operations')
