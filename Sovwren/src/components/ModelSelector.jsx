import { ChevronDown } from 'lucide-react';
import { useState } from 'react';

const MODELS = [
    { id: 'gemini', name: 'Gemini Pro', provider: 'Google' },
    { id: 'claude', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
    { id: 'gpt4', name: 'GPT-4o', provider: 'OpenAI' },
];

export default function ModelSelector({ currentModel, onModelChange }) {
    const [isOpen, setIsOpen] = useState(false);

    const selectedModel = MODELS.find(m => m.id === currentModel) || MODELS[0];

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors text-sm font-medium text-gray-200"
            >
                <span>{selectedModel.name}</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute top-full left-0 mt-2 w-56 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-xl overflow-hidden z-50 backdrop-blur-xl">
                    {MODELS.map((model) => (
                        <button
                            key={model.id}
                            onClick={() => {
                                onModelChange(model.id);
                                setIsOpen(false);
                            }}
                            className="w-full text-left px-4 py-3 hover:bg-white/5 transition-colors flex flex-col gap-0.5"
                        >
                            <span className="text-sm font-medium text-gray-200">{model.name}</span>
                            <span className="text-xs text-gray-500">{model.provider}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
