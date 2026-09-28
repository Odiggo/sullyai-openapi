"""Generate and build disposable clients from the canonical OpenAPI 3.1 file."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = '7.25.0'
JAR_SHA256 = '41ce4f6b07f196676439d710759fa1ced7a08066d06ff1bf314681470289efae'


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def smoke(language, jar):
    workspace = ROOT / '.sdk-smoke'
    workspace.mkdir(exist_ok=True)
    if not jar:
        jar = workspace / f'openapi-generator-{VERSION}.jar'
        if not jar.exists():
            urllib.request.urlretrieve(f'https://repo.maven.apache.org/maven2/org/openapitools/openapi-generator-cli/{VERSION}/openapi-generator-cli-{VERSION}.jar', jar)
    jar = Path(jar).resolve()
    assert hashlib.sha256(jar.read_bytes()).hexdigest() == JAR_SHA256, 'Unexpected generator JAR checksum'
    generator = 'typescript-fetch' if language == 'typescript' else 'python'
    with tempfile.TemporaryDirectory(prefix=language + '-', dir=workspace) as temp:
        destination = Path(temp)
        command = [os.environ.get('JAVA_BIN', 'java'), '-jar', str(jar), 'generate', '-i', str(ROOT / 'openapi.yaml'), '-g', generator, '-c', str(ROOT / 'generator' / f'{generator}.json'), '-o', str(destination / 'client'), '--global-property', 'apiTests=false,modelTests=false']
        if language == 'python':
            command += ['--name-mappings', 'globalPrompt=global_prompt_legacy,hideIfEmpty=hide_if_empty_legacy,emptyPlaceholder=empty_placeholder_legacy']
        with (workspace / f'{language}-generation.log').open('w') as log:
            run(*command, stdout=log, stderr=subprocess.STDOUT)
        client = destination / 'client'
        if language == 'typescript':
            run('npm', 'install', '--ignore-scripts', '--no-audit', '--no-fund', '--save-exact', 'typescript@5.9.3', cwd=client)
            run('npm', 'run', 'build', cwd=client)
            run('node', ROOT / 'tests/generated_typescript.cjs', client / 'dist')
        else:
            run(sys.executable, '-m', 'venv', destination / 'venv')
            python = destination / 'venv/bin/python'
            run(python, '-m', 'pip', 'wheel', '--no-deps', client, '-w', destination / 'wheels')
            wheel, = (destination / 'wheels').glob('*.whl')
            run(python, '-m', 'pip', 'install', '-c', ROOT / 'generator/python-requirements.txt', wheel)
            run(python, ROOT / 'tests/generated_python.py', cwd=destination)
    print(f'{language}: generation, build and wire smoke passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('language', choices=['typescript', 'python'])
    parser.add_argument('--jar', type=Path)
    args = parser.parse_args()
    smoke(args.language, args.jar)
