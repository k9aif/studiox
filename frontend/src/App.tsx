import { useEffect } from 'react';
import { useStore } from './store';
import { Studio } from './components/Studio';
import { SetupScreen } from './components/SetupScreen';
import { SplashScreen } from './components/SplashScreen';
import { LandingPage } from './components/LandingPage';
import { autoLogin } from './lib/autoLogin';

const STUDIO_PATHS = ['/studio', '/studiox'];

function App() {
  const { screen, setScreen, clientId } = useStore();

  // URL -> screen, on first load and on browser back/forward. "/studio" is a
  // bookmarkable, shareable link into the app: a cold visit signs in as the
  // demo user the same way "Get Started" does (the login screen appears only
  // if that fails). "/studiox" is accepted for links from the retired
  // studiox.k9x.ai instance. setScreen() keeps the URL in sync afterwards.
  useEffect(() => {
    const syncFromPath = () => {
      if (!STUDIO_PATHS.includes(window.location.pathname)) {
        setScreen('landing');
        return;
      }
      if (sessionStorage.getItem('k9x_authed') === '1') {
        setScreen('studio');
        return;
      }
      autoLogin(clientId).then((ok) => setScreen(ok ? 'studio' : 'splash'));
    };

    syncFromPath();
    window.addEventListener('popstate', syncFromPath);
    return () => window.removeEventListener('popstate', syncFromPath);
  }, []);

  if (screen === 'landing') return <LandingPage />;
  if (screen === 'splash') return <SplashScreen />;
  if (screen === 'studio') return <Studio />;
  return <SetupScreen />;
}

export default App;
