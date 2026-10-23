import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { printTable } = vi.hoisted(() => ({
  printTable: vi.fn(),
}));

vi.mock('../src/output.js', () => ({
  output: {
    writeln: vi.fn(),
    printTable,
    bold: (value: string) => value,
    dim: (value: string) => value,
    success: (value: string) => value,
    warning: (value: string) => value,
    printList: vi.fn(),
  },
}));

import { providersCommand } from '../src/commands/providers.js';

describe('providers list Google Gemini environment keys', () => {
  const originalCwd = process.cwd();
  const originalGoogleKey = process.env.GOOGLE_API_KEY;
  const originalGeminiKey = process.env.GEMINI_API_KEY;

  beforeEach(() => {
    printTable.mockClear();
  });

  afterEach(() => {
    process.chdir(originalCwd);
    if (originalGoogleKey === undefined) delete process.env.GOOGLE_API_KEY;
    else process.env.GOOGLE_API_KEY = originalGoogleKey;
    if (originalGeminiKey === undefined) delete process.env.GEMINI_API_KEY;
    else process.env.GEMINI_API_KEY = originalGeminiKey;
  });

  async function listProviders() {
    const list = providersCommand.subcommands!.find(command => command.name === 'list')!;
    await list.action!({ flags: { type: 'all', active: false } } as never);
    return printTable.mock.calls.at(-1)?.[0]?.data as Array<{ provider: string; status: string }>;
  }

  it('recognizes GEMINI_API_KEY when GOOGLE_API_KEY is absent', async () => {
    delete process.env.GOOGLE_API_KEY;
    process.env.GEMINI_API_KEY = 'gemini-test';

    const rows = await listProviders();

    expect(rows.find(row => row.provider === 'Google')?.status).toBe('Configured (env)');
  });

  it('prefers GOOGLE_API_KEY when both environment keys are present', async () => {
    process.env.GOOGLE_API_KEY = 'google-test';
    process.env.GEMINI_API_KEY = 'gemini-test';

    const rows = await listProviders();

    expect(rows.find(row => row.provider === 'Google')?.status).toBe('Configured (env)');
  });
});
