import { useRef, useState } from 'react';
import type { Analysis, Context, Filters, Sample, Session, View } from '../types';
import { api } from '../services/api';

export function useWorkspace() {
  const [view, setView] = useState<View>('home');
  const [session, setSession] = useState<Session | null>(null);
  const [sheet, setSheet] = useState('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [version, setVersion] = useState<'original' | 'cleaned'>('original');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  // Close the gap before disabled controls render; reject late cleaning callbacks
  // from a worksheet that has since been replaced or changed.
  const pending = useRef(false);
  const contextEpoch = useRef(0);
  const renderedEpoch = contextEpoch.current;
  const context: Context = { sheet, filters, version };
  const reportError = (reason: unknown) => setError(reason instanceof Error ? reason.message : 'Something went wrong. Please try again.');

  function begin() {
    if (pending.current) return false;
    pending.current = true;
    setBusy(true);
    setError('');
    return true;
  }
  function finish() { pending.current = false; setBusy(false); }

  async function receiveFile(file: File) {
    const previous = session;
    const next = await api.upload(file);
    contextEpoch.current += 1;
    setSession(next);
    setAnalysis(null);
    setSheet('');
    setVersion('original');
    setFilters({});
    setMessage('File uploaded. Choose a worksheet to preview your data.');
    if (previous) void api.delete(previous).catch(() => undefined);
  }

  async function upload(file: File) {
    if (!begin()) return;
    setView('upload');
    setMessage('');
    try { await receiveFile(file); }
    catch (reason) { reportError(reason); }
    finally { finish(); }
  }

  async function sample(selected: Sample) {
    if (!begin()) return;
    setView('upload');
    setMessage('');
    try { await receiveFile(await api.sampleFile(selected)); }
    catch (reason) { reportError(reason); }
    finally { finish(); }
  }

  function chooseSheet(next: string) {
    if (pending.current || !session?.sheets.includes(next)) return;
    contextEpoch.current += 1;
    setSheet(next);
    setAnalysis(null);
    setFilters({});
    setVersion('original');
    setView('preview');
    setError('');
    setMessage('');
  }

  async function navigate(next: View) {
    if (pending.current) return;
    setError('');
    if (['dashboard', 'explore', 'quality'].includes(next)) {
      if (!session || !sheet) { setView('upload'); return; }
      if (!analysis) {
        if (!begin()) return;
        try { setAnalysis(await api.analyze(session, context)); setView(next); }
        catch (reason) { reportError(reason); }
        finally { finish(); }
        return;
      }
    }
    setView(next);
  }

  async function applyFilters(next: Filters) {
    if (!session || !begin()) return;
    try {
      const result = await api.filter(session, { ...context, filters: next });
      setAnalysis(result);
      setFilters(next);
    } catch (reason) { reportError(reason); throw reason; }
    finally { finish(); }
  }

  async function changeVersion(next: 'original' | 'cleaned') {
    if (!session || renderedEpoch !== contextEpoch.current) throw new Error('The selected dataset changed. Reopen data quality to continue.');
    if (!begin()) throw new Error('Another operation is in progress. Please try again when it finishes.');
    try {
      const result = await api.analyze(session, { ...context, version: next });
      if (renderedEpoch !== contextEpoch.current) throw new Error('The selected dataset changed. Reopen data quality to continue.');
      setAnalysis(result);
      setVersion(next);
      setMessage(next === 'cleaned' ? 'Cleaned data is active. Your dashboard and exports use this version.' : 'Original data is active.');
    } finally { finish(); }
  }

  async function deleteSession() {
    if (!session || !begin()) return;
    try {
      await api.delete(session);
      contextEpoch.current += 1;
      setSession(null);
      setAnalysis(null);
      setSheet('');
      setFilters({});
      setVersion('original');
      setView('upload');
      setMessage('Session deleted. Its temporary data has been removed.');
    } catch (reason) { reportError(reason); }
    finally { finish(); }
  }

  return { view, session, sheet, analysis, filters, version, context, busy, error, message, setError, setMessage, upload, sample, chooseSheet, navigate, applyFilters, changeVersion, deleteSession };
}
