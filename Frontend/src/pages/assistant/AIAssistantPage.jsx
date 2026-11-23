import React, { useState, useEffect } from 'react';
import Navbar from '../../components/common/Navbar';
import { Send, Bot } from 'lucide-react';
import { assistantService } from '../../services';

export default function AIAssistantPage() {
  const [messages, setMessages] = useState([
    {
      sender: 'assistant',
      time: '09:45',
      text: 'Good morning. I can help you explore incidents, workforce hours and activity across your plant. What would you like to know?'
    },
    {
      sender: 'user',
      time: '09:46',
      text: 'How many helmet violations today?'
    },
    {
      sender: 'assistant',
      time: '09:46',
      text: 'There have been 4 helmet violations today. The latest was detected at 09:42 in Zone B · Press Line (INC-2041).',
      source: 'Source: incident register · Current shift'
    }
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [quickPrompts, setQuickPrompts] = useState([]);

  useEffect(() => {
    let isMounted = true;
    assistantService.getQuickPrompts().then(prompts => {
      if (isMounted) setQuickPrompts(prompts || []);
    });
    return () => { isMounted = false; };
  }, []);

  const handleSend = async (textToSend) => {
    const query = textToSend || inputQuery;
    if (!query.trim()) return;

    const userMsg = {
      sender: 'user',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: query
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');

    try {
      const response = await assistantService.sendQuery(query, messages);
      const assistantMsg = {
        sender: 'assistant',
        time: response.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: response.reply,
        source: response.source
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      const fallbackMsg = {
        sender: 'assistant',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: "I couldn't process that query right now. Please try again or rephrase.",
        source: "Source: Operix Vision Engine"
      };
      setMessages(prev => [...prev, fallbackMsg]);
    }
  };

  return (
    <>
      <Navbar
        title="AI Assistant"
        subtitle="Ask questions in natural language about your plant data"
      />

      <div className="page-container">
        <div className="operix-card" style={{ display: 'flex', flexDirection: 'column', minHeight: '680px' }}>
          {/* Card Header */}
          <div className="card-header-flex" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bot size={20} color="var(--primary)" />
              <h3 className="card-title">Operix AI</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', color: '#10B981', fontWeight: 600 }}>
              <span className="badge-dot" style={{ backgroundColor: '#10B981' }} />
              <span>Connected to Plant 1 data</span>
            </div>
          </div>

          {/* Time separator */}
          <div style={{ textAlign: 'center', margin: '1rem 0', fontSize: '11px', color: 'var(--text-light)', fontWeight: 700, letterSpacing: '0.08em' }}>
            TODAY · 09:45
          </div>

          {/* Messages Stream */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.25rem', overflowY: 'auto', paddingRight: '6px' }}>
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`chat-bubble ${m.sender}`}
              >
                <div>{m.text}</div>
                {m.source && (
                  <div style={{ fontSize: '11px', opacity: 0.7, marginTop: '8px' }}>
                    {m.source}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Bottom Area: Suggestions & Input */}
          <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
              Explore your operations
            </span>

            {/* Quick Prompt Chips */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
              {quickPrompts.map((p, idx) => (
                <button
                  key={idx}
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleSend(p)}
                  style={{ borderRadius: '9999px', fontSize: '12.5px' }}
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Input Box */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              style={{ display: 'flex', gap: '10px' }}
            >
              <input
                type="text"
                className="form-control"
                placeholder="Ask about incidents, hours or zones"
                value={inputQuery}
                onChange={e => setInputQuery(e.target.value)}
              />
              <button type="submit" className="btn btn-primary" style={{ padding: '0.65rem 1.75rem' }}>
                Ask
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
