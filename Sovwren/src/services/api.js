export const sendMessage = async (modelId, messages, apiKeys) => {
    const lastMessage = messages[messages.length - 1].content;

    switch (modelId) {
        case 'gemini':
            return callGemini(lastMessage, apiKeys.gemini);
        case 'claude':
            return callClaude(messages, apiKeys.claude);
        case 'gpt4':
            return callOpenAI(messages, apiKeys.openai);
        default:
            throw new Error('Unknown model');
    }
};

const callGemini = async (prompt, apiKey) => {
    if (!apiKey) throw new Error('Gemini API key is missing');

    const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${apiKey}`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{ parts: [{ text: prompt }] }],
            }),
        }
    );

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to fetch from Gemini');
    }

    const data = await response.json();
    return data.candidates[0].content.parts[0].text;
};

const callClaude = async (messages, apiKey) => {
    if (!apiKey) throw new Error('Claude API key is missing');

    // Note: This will likely fail due to CORS in a browser environment without a proxy.
    // We are implementing it for completeness or if the user has a CORS-disabled browser/proxy.
    const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
            'dangerously-allow-browser': 'true' // Attempt to bypass client-side check if SDK was used, but for fetch headers it's just a header.
        },
        body: JSON.stringify({
            model: 'claude-3-5-sonnet-20240620',
            max_tokens: 1024,
            messages: messages.map(m => ({ role: m.role, content: m.content })).filter(m => m.role !== 'system'), // Claude handles system separately usually, but for simple chat...
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to fetch from Claude');
    }

    const data = await response.json();
    return data.content[0].text;
};

const callOpenAI = async (messages, apiKey) => {
    if (!apiKey) throw new Error('OpenAI API key is missing');

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            model: 'gpt-4o',
            messages: messages.map(m => ({ role: m.role, content: m.content })),
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Failed to fetch from OpenAI');
    }

    const data = await response.json();
    return data.choices[0].message.content;
};
