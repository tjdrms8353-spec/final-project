/** @license SPDX-License-Identifier: Apache-2.0 */
import { useCallback, useEffect, useState } from 'react';
import { PlatformProvider } from './context/PlatformContext';
import { AuthModal } from './components/AuthModal';
import { ValidationToasts } from './components/ValidationToasts';
import AppShell from './app/AppShell';
import AuthScreen from './app/AuthScreen';
import { Loading } from './app/ui';
import { WorkspaceProvider } from './app/workspace';
import { bi, biToken } from './services/biApi';

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(biToken.get()));
  useEffect(() => {
    if (!biToken.get()) return;
    bi('/auth/me').then(setUser).catch(() => biToken.clear()).finally(() => setChecking(false));
  }, []);
  const logout = useCallback(() => { biToken.clear(); setUser(null); }, []);

  if (checking) return <div className="flex min-h-screen items-center justify-center"><Loading label="세션 확인 중..." /></div>;
  if (!user) return <AuthScreen onLogin={setUser} />;
  return <PlatformProvider>
    <WorkspaceProvider key={user.id} user={user} onLogout={logout}><AppShell /></WorkspaceProvider>
    <AuthModal /><ValidationToasts />
  </PlatformProvider>;
}
