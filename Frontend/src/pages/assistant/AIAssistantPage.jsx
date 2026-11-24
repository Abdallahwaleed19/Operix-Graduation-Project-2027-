import React, { useState, useEffect } from 'react';
import Navbar from '../../components/common/Navbar';
import { Send, Bot, Trash2, ShieldCheck, CheckCircle2, ArrowRight, BookOpen, AlertCircle } from 'lucide-react';
import { assistantService } from '../../services';

export default function AIAssistantPage() {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([
    {
      sender: 'assistant',
      time: '09:45',
      text: 'Good morning. I am your Operix Industrial Safety & Vision Assistant. Ask me anything about real-time plant telemetry, PPE compliance, incidents, and safety protocols in English or Arabic.',
      citations: [],
      proposedActions: []
    }
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [quickPrompts, setQuickPrompts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionExecuting, setActionExecuting] = useState(null);
  const [actionFeedback, setActionFeedback] = useState(null);

  useEffect(() => {
    let isMounted = true;
    assistantService.getQuickPrompts().then(prompts => {
      if (isMounted) setQuickPrompts(prompts || []);
    });
    return () => { isMounted = false; };
  }, []);

  const handleSend = async (textToSend) => {
    const query = textToSend || inputQuery;
    if (!query.trim() || isLoading) return;

    const userMsg = {
      sender: 'user',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: query
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const response = await assistantService.sendQuery(query, messages, conversationId);
      if (response.conversationId) {
        setConversationId(response.conversationId);
      }

      const assistantMsg = {
        sender: 'assistant',
        time: response.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: response.reply,
        source: response.source,
        citations: response.citations || [],
        proposedActions: response.proposedActions || []
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const fallbackMsg = {
        sender: 'assistant',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: err.message || "I couldn't process that query right now. Please check backend connection.",
        source: "Source: Operix Vision Engine (Error)"
      };
      setMessages(prev => [...prev, fallbackMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearConversation = async () => {
    if (conversationId) {
      try {
        await assistantService.clearConversation(conversationId);
      } catch (err) {
        console.warn('Clear conversation error:', err.message);
      }
    }
    setConversationId(null);
    setMessages([
      {
        sender: 'assistant',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: 'Conversation history cleared. Ready for a new safety inquiry.',
        citations: [],
        proposedActions: []
      }
    ]);
  };

  const handleExecuteAction = async (action) => {
    setActionExecuting(action.action_id);
    setActionFeedback(null);
    try {
      const result = await assistantService.executeAction({
        actionId: action.action_id,
        actionType: action.action_type,
        parameters: action.parameters,
        confirmedBy: 'Supervisor'
      });
      setActionFeedback({
        type: 'success',
        message: result.message || `Action '${action.action_type}' executed successfully. Audit: ${result.audit_reference || 'N/A'}`
      });
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err.message || 'Action execution failed due to permissions or validation error.'
      });
    } finally {
      setActionExecuting(null);
      setTimeout(() => setActionFeedback(null), 5000);
    }
  };

  return (
    <>
      <Navbar
        title="AI Assistant"
        subtitle="Bilingual RAG industrial safety advisor & action agent"
        rightActions={
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleClearConversation}
            title="Clear conversation history on server"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Trash2 size={14} />
            <span>Clear chat</span>
          </button>
        }
      />

      <div className="page-container">
        {actionFeedback && (
          <div style={{
            marginBottom: '1rem',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: actionFeedback.type === 'success' ? 'var(--success-bg)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${actionFeedback.type === 'success' ? 'var(--success-border)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: actionFeedback.type === 'success' ? 'var(--success-text)' : '#EF4444'
          }}>
            {actionFeedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <span>{actionFeedback.message}</span>
          </div>
        )}

        <div className="operix-card" style={{ display: 'flex', flexDirection: 'column', minHeight: '680px' }}>
          {/* Card Header */}
          <div className="card-header-flex" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bot size={20} color="var(--primary)" />
              <h3 className="card-title">Operix RAG Engine</h3>
              {conversationId && (
                <span className="status-pill neutral font-mono" style={{ fontSize: '11px', padding: '2px 8px' }}>
                  {conversationId}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', color: '#10B981', fontWeight: 600 }}>
              <span className="badge-dot" style={{ backgroundColor: '#10B981' }} />
              <span>Plant 1 Telemetry Active</span>
            </div>
          </div>

          {/* Time separator */}
          <div style={{ textAlign: 'center', margin: '1rem 0', fontSize: '11px', color: 'var(--text-light)', fontWeight: 700, letterSpacing: '0.08em' }}>
            TODAY · LIVE SESSION
          </div>

          {/* Messages Stream */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1.25rem', overflowY: 'auto', paddingRight: '6px' }}>
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`chat-bubble ${m.sender}`}
                style={{ maxWidth: '85%' }}
              >
                <div style={{ lineHeight: 1.55 }}>{m.text}</div>

                {/* Citations Badges */}
                {m.citations && m.citations.length > 0 && (
                  <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.15)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, opacity: 0.85, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <BookOpen size={12} />
                      <span>Verified Sources & Evidence:</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {m.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          title={c.snippet || c.source_title}
                          style={{
                            fontSize: '11px',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            backgroundColor: 'rgba(0, 0, 0, 0.2)',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <span>{c.source_title || c.source_id}</span>
                          {c.similarity_score && (
                            <span style={{ opacity: 0.7, fontSize: '10px' }}>
                              ({Math.round(c.similarity_score * 100)}%)
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Proposed Remediation Actions */}
                {m.proposedActions && m.proposedActions.length > 0 && (
                  <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.15)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, opacity: 0.85, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <ShieldCheck size={12} />
                      <span>Suggested Remediation Action:</span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {m.proposedActions.map((a, aIdx) => (
                        <button
                          key={aIdx}
                          disabled={actionExecuting === a.action_id}
                          onClick={() => handleExecuteAction(a)}
                          className="btn btn-sm"
                          style={{
                            backgroundColor: 'var(--primary)',
                            color: '#FFFFFF',
                            fontSize: '11.5px',
                            fontWeight: 600,
                            padding: '4px 10px',
                            borderRadius: '6px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            cursor: 'pointer'
                          }}
                        >
                          <span>{actionExecuting === a.action_id ? 'Executing...' : (a.title || `Execute: ${a.action_type}`)}</span>
                          <ArrowRight size={12} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {m.source && !m.citations?.length && (
                  <div style={{ fontSize: '11px', opacity: 0.7, marginTop: '8px' }}>
                    {m.source}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="chat-bubble assistant" style={{ maxWidth: '60%', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge-dot pulse" style={{ backgroundColor: 'var(--primary)' }} />
                <span style={{ fontSize: '13px' }}>Querying Operix Safety RAG models...</span>
              </div>
            )}
          </div>

          {/* Bottom Area: Suggestions & Input */}
          <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
              Explore safety telemetry & protocols:
            </span>

            {/* Quick Prompt Chips */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
              {quickPrompts.map((p, idx) => (
                <button
                  key={idx}
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleSend(p)}
                  disabled={isLoading}
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
                placeholder="Ask in Arabic or English (e.g., 'What are the PPE rules?' or 'ما هي مخالفات الخوذة اليوم؟')"
                value={inputQuery}
                disabled={isLoading}
                onChange={e => setInputQuery(e.target.value)}
              />
              <button
                type="submit"
                disabled={isLoading || !inputQuery.trim()}
                className="btn btn-primary"
                style={{ padding: '0.65rem 1.75rem', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Send size={15} />
                <span>{isLoading ? 'Sending...' : 'Ask'}</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
