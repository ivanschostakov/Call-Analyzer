import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const currentDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(currentDir, '..');
const workspaceDir = resolve(frontendDir, '..');
const backendDir = resolve(workspaceDir, 'backend');
const outputPath = resolve(frontendDir, 'openapi.json');
const pythonPath = resolve(backendDir, '.venv', 'bin', 'python');

const script = `
import json
from src.app.main import app
print(json.dumps(app.openapi(), ensure_ascii=False))
`.trim();

const result = spawnSync(pythonPath, ['-c', script], {
  cwd: backendDir,
  encoding: 'utf-8',
});

if (result.status !== 0) {
  process.stderr.write(result.stderr || 'Failed to export OpenAPI schema.\\n');
  process.exit(result.status ?? 1);
}

mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, result.stdout, 'utf-8');
process.stdout.write(`OpenAPI schema exported to ${outputPath}\n`);
