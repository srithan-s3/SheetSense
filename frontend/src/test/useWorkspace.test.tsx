import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useWorkspace } from '../hooks/useWorkspace';
import { api } from '../services/api';
import type { Analysis, Session } from '../types';

vi.mock('../services/api', () => ({ api: { upload: vi.fn(), delete: vi.fn(), analyze: vi.fn(), filter: vi.fn() } }));
const session: Session = { session_id: 'example', token: 'local-test-token', filename: 'example.xlsx', sheets: ['First', 'Second'], expires_at: '2026-10-13T12:00:00Z' };
const analysis = { filename: session.filename, sheet: 'First', version: 'original', rows: 10, total_rows: 10, column_count: 1, columns: [], kpis: [], charts: [], insights: [], filters: [], notes: [], analyzed_at: '', quality: { missing_cells: 0, missing_percent: 0, duplicate_rows: 0, issues: [] } } satisfies Analysis;
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.upload).mockResolvedValue(session);
  vi.mocked(api.delete).mockResolvedValue({ deleted: true });
  vi.mocked(api.analyze).mockResolvedValue(analysis);
});
afterEach(cleanup);

async function workspaceWithAnalysis() {
  const hook = renderHook(() => useWorkspace());
  await act(() => hook.result.current.upload(new File(['sample'], 'example.xlsx')));
  act(() => hook.result.current.chooseSheet('First'));
  await act(() => hook.result.current.navigate('dashboard'));
  return hook;
}

describe('workspace request consistency', () => {
  it('rejects a late cleaning callback after selecting another worksheet', async () => {
    const { result } = await workspaceWithAnalysis();
    const lateCleaningCallback = result.current.changeVersion;
    const calls = vi.mocked(api.analyze).mock.calls.length;
    act(() => result.current.chooseSheet('Second'));
    await expect(lateCleaningCallback('cleaned')).rejects.toThrow('dataset changed');
    expect(result.current.sheet).toBe('Second');
    expect(result.current.analysis).toBeNull();
    expect(api.analyze).toHaveBeenCalledTimes(calls);
  });

  it('locks navigation until a version change finishes', async () => {
    const { result } = await workspaceWithAnalysis();
    let resolve!: (value: Analysis) => void;
    vi.mocked(api.analyze).mockImplementationOnce(() => new Promise(done => { resolve = done; }));
    let request!: Promise<void>;
    act(() => { request = result.current.changeVersion('cleaned'); });
    expect(result.current.busy).toBe(true);
    await act(() => result.current.navigate('upload'));
    expect(result.current.view).toBe('dashboard');
    await act(async () => { resolve({ ...analysis, version: 'cleaned', rows: 8 }); await request; });
    expect(result.current.busy).toBe(false);
    expect(result.current.version).toBe('cleaned');
    expect(result.current.analysis?.rows).toBe(8);
  });

  it('keeps the previous filters and results when a filter request fails', async () => {
    const { result } = await workspaceWithAnalysis();
    vi.mocked(api.filter).mockRejectedValueOnce(new Error('Invalid range'));
    await act(async () => {
      await expect(result.current.applyFilters({ Amount: { min: 9, max: 1 } })).rejects.toThrow('Invalid range');
    });
    expect(result.current.filters).toEqual({});
    expect(result.current.analysis?.rows).toBe(10);
    expect(result.current.error).toBe('Invalid range');
    expect(result.current.busy).toBe(false);
  });
});
