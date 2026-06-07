import { useState } from 'react';
import { useStore } from '../store';
import type { LlmSessionConfig } from '../store';

export function SetupPanel() {
  const { llmConfig, setLlmConfig, addLog, setLlmActive, setAvailableModels } = useStore();

  // Restore last used LLM config from localStorage
  const getSavedConfig = (): LlmSessionConfig => {
    try {
      const saved = localStorage.getItem('k9x_llm');
      if (saved) {
        const parsed = JSON.parse(saved);
        return { provider: parsed.provider ?? 'ollama', endpoint: parsed.endpoint ?? '', model: parsed.model ?? '', api_key: '' };
      }
    } catch { /* ignore */ }
    return { provider: 'ollama', endpoint: 'http://localhost:11434', model: '', api_key: '' };
  };

  const defaultForm = llmConfig ?? getSavedConfig();
  if (defaultForm.provider === 'ollama' && !defaultForm.endpoint) {
    defaultForm.endpoint = 'http://localhost:11434';
  }
  // Restore llmConfig from localStorage if not already set
  if (!llmConfig) {
    const saved = getSavedConfig();
    if (saved.model) setLlmConfig(saved);
  }
  const [form, setForm] = useState<LlmSessionConfig>(defaultForm);
  const [testing, setTesting]         = useState(false);
  const [connected, setConnected]     = useState(false);
  const [testErr, setTestErr]         = useState('');
  const [models, setModels]           = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  const set = (key: keyof LlmSessionConfig, val: string) => {
    const next = { ...form, [key]: val };
    setForm(next);
    if (key === 'model' && val) setLlmConfig(next);
    setConnected(false); setTestErr('');
  };

  const loadModelsFor = async (cfg: LlmSessionConfig) => {
    setLoadingModels(true);
    try {
      const res = await fetch('/api/llm/models', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      });
      if (res.ok) {
        const data = await res.json();
        setModels(data.models ?? []); setAvailableModels(data.models ?? []);
        if (data.models?.length) addLog(`✓ ${data.models.length} models available`);
      }
    } catch { /* silent */ } finally { setLoadingModels(false); }
  };

  const handleTest = async () => {
    setTesting(true); setTestErr(''); setConnected(false); setModels([]);
    addLog(`Testing LLM connection (${form.provider})…`);
    setLlmActive(true);
    try {
      const res = await fetch('/api/llm/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) throw new Error(data.detail ?? 'Connection failed');
      setConnected(true);
      setLlmConfig(form);
      localStorage.setItem('k9x_llm', JSON.stringify({ provider: form.provider, endpoint: form.endpoint, model: form.model }));
      addLog(`✓ LLM connected — ${data.detail ?? 'OK'}`);
      await loadModelsFor(form);
    } catch (err: any) {
      setTestErr(err.message ?? 'Connection failed');
      addLog(`✕ LLM connection failed: ${err.message}`, 'error');
    } finally { setTesting(false); setLlmActive(false); }
  };

  const handleClear = () => {
    const empty: LlmSessionConfig = { provider: 'ollama', endpoint: '', model: '', api_key: '' };
    setForm(empty); setLlmConfig(null);
    setConnected(false); setTestErr(''); setModels([]);
  };

  return (
    <div style={{ maxWidth: 520, padding: '4px 0' }}>
      <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>LLM Configuration</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 24 }}>
        Configure your LLM for AI-powered architecture generation. Optional — the studio works without one using rule-based defaults.
      </div>

      {/* .env upload */}
      <div style={{ marginBottom: 20 }}>
        <label className="intake-bpmn-btn" style={{ width: '100%', justifyContent: 'center' }}>
          <span>⬆ Upload .env — auto-fills config</span>
          <input type="file" accept=".env,.txt" style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0]; e.target.value = '';
              if (!file) return;
              const reader = new FileReader();
              reader.onload = (ev) => {
                const text = ev.target?.result as string ?? '';
                const p: Record<string, string> = {};
                text.split('\n').forEach((line) => {
                  const clean = line.trim();
                  if (!clean || clean.startsWith('#')) return;
                  const idx = clean.indexOf('=');
                  if (idx < 0) return;
                  p[clean.slice(0, idx).trim()] = clean.slice(idx + 1).trim();
                });
                const next: LlmSessionConfig = {
                  provider: p['LLM_PROVIDER'] ?? form.provider,
                  endpoint: p['LLM_ENDPOINT'] ?? form.endpoint,
                  model:    p['LLM_MODEL']    ?? form.model,
                  api_key:  p['LLM_API_KEY']  ?? form.api_key,
                };
                setForm(next); setConnected(false); setModels([]);
              };
              reader.readAsText(file);
            }}
          />
        </label>
      </div>

      <div className="intake-row-2" style={{ marginBottom: 14 }}>
        <div className="intake-field">
          <label className="intake-label">Provider</label>
          <select className="intake-input" value={form.provider}
            onChange={(e) => {
              const p = e.target.value;
              setForm((f) => ({
                ...f, provider: p,
                endpoint: p === 'ollama' ? (f.endpoint || 'http://localhost:11434')
                         : p === 'watsonx' ? (f.endpoint || 'https://us-south.ml.cloud.ibm.com/ml/v1')
                         : f.endpoint,
              }));
              setConnected(false); setModels([]);
            }}>
            <option value="ollama">Ollama</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="watsonx">IBM watsonx.ai</option>
            <option value="openai">OpenAI / Custom</option>
          </select>
        </div>
        <div className="intake-field">
          <label className="intake-label">
            Model {loadingModels && <span style={{ color: '#64748b' }}>⟳</span>}
          </label>
          {models.length > 0 ? (
            <select className="intake-input" value={form.model}
              onChange={(e) => set('model', e.target.value)}>
              <option value="">— select model —</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          ) : (
            <input className="intake-input" placeholder="granite3.3:2b"
              value={form.model} onChange={(e) => set('model', e.target.value)} />
          )}
        </div>
      </div>

      <div className="intake-field" style={{ marginBottom: 14 }}>
        <label className="intake-label">Endpoint</label>
        <input className="intake-input" placeholder="http://localhost:11434"
          value={form.endpoint}
          onChange={(e) => set('endpoint', e.target.value)}
          onBlur={async (e) => {
            if (form.provider !== 'ollama') return;
            const ep = e.target.value.trim(); if (!ep) return;
            const cfg = { ...form, endpoint: ep };
            setLoadingModels(true);
            try {
              const res = await fetch('/api/llm/models', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg),
              });
              if (res.ok) {
                const data = await res.json();
                setModels(data.models ?? []); setAvailableModels(data.models ?? []);
                if (data.models?.length) { setConnected(true); setLlmConfig(cfg); addLog(`✓ Ollama connected — ${data.models.length} models`); }
              }
            } catch { /* silent */ } finally { setLoadingModels(false); }
          }}
        />
      </div>

      <div className="intake-field" style={{ marginBottom: 24 }}>
        <label className="intake-label">API Key</label>
        <input className="intake-input" type="password"
          placeholder={form.provider === 'watsonx' ? 'IBM Cloud IAM API key' : form.provider === 'anthropic' ? 'sk-ant-...' : 'leave blank for local LLM'}
          value={form.api_key} onChange={(e) => set('api_key', e.target.value)} />
        {form.provider === 'watsonx' && (
          <div style={{ fontSize: 10, color: '#64748b', marginTop: 4 }}>
            IBM Cloud IAM API key — also add <code style={{ fontSize: 10 }}>?project_id=YOUR_PROJECT_ID</code> to the endpoint URL
          </div>
        )}
      </div>

      {!connected ? (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button className="intake-btn-flow" style={{ padding: '8px 24px' }}
            onClick={handleTest} disabled={testing || !form.provider}>
            {testing ? '⟳ Testing…' : '⚡ Test Connection'}
          </button>
          {testErr && <span style={{ fontSize: 12, color: '#f87171' }}>✕ {testErr}</span>}
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ fontSize: 13, color: '#10b981', fontWeight: 500 }}>✓ Connected</div>
          <button className="intake-btn-generate" style={{ padding: '4px 12px', fontSize: 11 }}
            onClick={handleClear}>Clear</button>
        </div>
      )}

      <div style={{ marginTop: 16, fontSize: 11, color: '#475569' }}>
        ⚠ LLM config is session-only — clears on page refresh
      </div>
    </div>
  );
}
