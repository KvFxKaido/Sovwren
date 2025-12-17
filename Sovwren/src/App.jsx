import { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import ModelSelector from './components/ModelSelector';
import SettingsModal from './components/SettingsModal';
import { Settings } from 'lucide-react';

function App() {
  const [currentModel, setCurrentModel] = useState('gemini');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [apiKeys, setApiKeys] = useState({});

  useEffect(() => {
    const savedKeys = localStorage.getItem('mythos_api_keys');
    if (savedKeys) {
      setApiKeys(JSON.parse(savedKeys));
    }
  }, [isSettingsOpen]); // Reload keys when settings close

  return (
    <div className="flex flex-col h-screen bg-[#0f0f0f] text-gray-100 font-sans selection:bg-purple-500/30">
      {/* Header */}
      <header className="h-14 border-b border-white/5 bg-[#1a1a1a]/50 backdrop-blur-xl flex items-center justify-between px-4 shrink-0 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <span className="font-bold text-white text-lg">M</span>
            </div>
            <span className="font-bold text-white text-lg tracking-tight">
              MythOS
            </span>
          </div>
          <div className="h-6 w-px bg-white/10 mx-2" />
          <ModelSelector currentModel={currentModel} onModelChange={setCurrentModel} />
        </div>

        <button
          onClick={() => setIsSettingsOpen(true)}
          className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
        >
          <Settings size={20} />
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden relative">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-900/20 via-[#0f0f0f] to-[#0f0f0f] pointer-events-none" />
        <ChatInterface currentModel={currentModel} apiKeys={apiKeys} />
      </main>

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
}

export default App;
