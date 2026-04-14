import { useState } from 'react';

type LoginPageProps = {
  onSubmit: (loginId: string, password: string) => Promise<void>;
  loading: boolean;
  error: string | null;
};

export function LoginPage({ onSubmit, loading, error }: LoginPageProps) {
  const [loginId, setLoginId] = useState('admin');
  const [password, setPassword] = useState('');

  return (
    <div className="login-layout">
      <section className="login-hero">
        <p className="eyebrow">Separated Admin Surface</p>
        <h1>Operate users, backups, and catalog data without touching the app shell.</h1>
        <p className="hero-copy">
          This console is reserved for privileged operators. User auth and admin auth are
          intentionally isolated.
        </p>
      </section>

      <section className="login-card">
        <form
          className="login-form"
          onSubmit={async (event) => {
            event.preventDefault();
            await onSubmit(loginId, password);
          }}
        >
          <div className="login-card-header">
            <p className="eyebrow">Admin Sign In</p>
            <h2>Deokive Control Room</h2>
          </div>

          <label>
            <span>ID</span>
            <input
              autoComplete="username"
              value={loginId}
              onChange={(event) => setLoginId(event.target.value)}
              type="text"
              placeholder="admin"
            />
          </label>

          <label>
            <span>Password</span>
            <input
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              placeholder="Enter your password"
            />
          </label>

          {error ? <p className="error-banner">{error}</p> : null}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </div>
  );
}
