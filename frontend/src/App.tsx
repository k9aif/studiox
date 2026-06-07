import { useEffect } from 'react';
import { useStore } from './store';
import { Studio } from './components/Studio';
import { SetupScreen } from './components/SetupScreen';
import { SplashScreen } from './components/SplashScreen';

function App() {
  const { screen, setScreen } = useStore();

  useEffect(() => {
    if (sessionStorage.getItem('k9x_authed') === '1' && screen === 'splash') {
      setScreen('studio');
    }
  }, []);

  if (screen === 'splash') return <SplashScreen />;
  if (screen === 'studio') return <Studio />;
  return <SetupScreen />;
}

export default App;
