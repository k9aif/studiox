import { useState } from 'react';
import { useStore } from '../store';
import logo from '../assets/k9aif-logo.png';

const DEMO_USER = 'demo';
const DEMO_PASS = 'demo';

export function SplashScreen() {
  const { setScreen } = useStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = () => {
    if (!username.trim() || !password.trim()) {
      setError('Enter username and password');
      return;
    }
    setLoading(true);
    setError('');
    setTimeout(() => {
      if (username.trim() === DEMO_USER && password.trim() === DEMO_PASS) {
        sessionStorage.setItem('k9x_authed', '1');
        setScreen('studio');
      } else {
        setError('Invalid credentials');
        setLoading(false);
      }
    }, 600);
  };

  return (
    <div className="splash-screen">
      <div className="splash-card">
        <img src={logo} alt="K9-AIF Logo" className="splash-logo" />
        <div className="splash-ecosystem">K9X Ecosystem</div>
        <div className="splash-title">Studio</div>
        <div className="splash-tagline">Architecture-First AI Builder</div>

        <div className="splash-form">
          <input
            className="splash-input"
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => { setUsername(e.target.value); setError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
            autoFocus
          />
          <input
            className="splash-input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(''); }}
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
          />
          {error && <div className="splash-error">{error}</div>}
          <div className="splash-demo-hint">demo / demo</div>
          <button
            className="splash-btn-login"
            onClick={handleLogin}
            disabled={loading}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
          <button className="splash-btn-register" disabled>
            Register
          </button>
        </div>

        <div className="splash-footer">
          K9-AIF Framework · <a href="https://k9x.ai" target="_blank" rel="noopener noreferrer">k9x.ai</a>
        </div>
      </div>
    </div>
  );
}
