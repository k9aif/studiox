// Shared by LandingPage's "Get Started" and App.tsx's direct-visit-to-
// /studiox handler — the same demo/demo auto-login (Ravi: "Get Started
// directly goes to login automatically as demo/demo") needs to run from
// both places now that /studiox is a bookmarkable URL, not just something
// reached by clicking through the landing page.
export async function autoLogin(clientId: string): Promise<boolean> {
  try {
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-K9X-Client-Id': clientId },
      body: JSON.stringify({ username: 'demo', password: 'demo' }),
    });
    if (resp.ok) {
      sessionStorage.setItem('k9x_authed', '1');
      return true;
    }
  } catch {
    // fall through
  }
  return false;
}
