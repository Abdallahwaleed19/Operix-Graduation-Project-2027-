import apiClient, { isMockEnabled } from './apiClient.js';
import { initialQuickPrompts } from '../data/mockData.js';

/**
 * Operix AI Safety Assistant & Action Service
 * Connects directly to FastAPI endpoints under `/api/v1/assistant`
 */
export const assistantService = {
  /**
   * Quick prompts for safety assistant suggestions
   */
  async getQuickPrompts() {
    return [...initialQuickPrompts];
  },

  /**
   * POST /api/v1/assistant/ask
   * Bilingual RAG Safety Q&A with citations and proposed remediation actions
   */
  async ask({ question, conversationId = null, language = 'auto' }) {
    if (isMockEnabled('assistant')) {
      let replyText = "Based on the Operix vision models, worker safety protocols require all personnel to wear certified helmets and high-visibility vests.";
      let citations = [
        {
          source_title: "General Plant Safety Standard",
          source_type: "safety_manual",
          source_id: "sop-plant-01",
          snippet: "Section 4.1: Mandatory PPE requirements for active manufacturing zones.",
          similarity_score: 0.94
        }
      ];
      let proposedActions = [];

      const lower = question.toLowerCase();
      if (lower.includes('idle') || lower.includes('خمول')) {
        replyText = "Zone C has recorded the highest idle time at 24% of observed worker hours, primarily concentrated around loading bay turnarounds.";
        citations = [
          {
            source_title: "Workforce Spatial Analytics · Current Shift",
            source_type: "analytics_snapshot",
            source_id: "zone-c-shift-report",
            snippet: "Observed dwell time exceeded normal transition limits by 14 minutes.",
            similarity_score: 0.91
          }
        ];
        proposedActions = [
          {
            action_id: `ACT-${Date.now()}`,
            action_type: 'investigate_incident',
            title: 'Investigate Zone C Bottleneck',
            parameters: { zone: 'Zone C', priority: 'medium' }
          }
        ];
      } else if (lower.includes('helmet') || lower.includes('خوذ') || lower.includes('ppe')) {
        replyText = "There have been 4 helmet violations detected today. The latest incident was flagged at 09:42 in Zone B · Press Line (INC-2041).";
        citations = [
          {
            source_title: "PPE Violation Log · Press Line",
            source_type: "incident_record",
            source_id: "INC-2041",
            snippet: "Operator observed without hard hat in overhead crane operational radius.",
            similarity_score: 0.96
          }
        ];
        proposedActions = [
          {
            action_id: `ACT-${Date.now()}`,
            action_type: 'acknowledge_incident',
            title: 'Acknowledge Incident INC-2041',
            parameters: { incident_id: '22222222-2222-2222-2222-222222222222' }
          }
        ];
      } else if (lower.includes('summarize') || lower.includes('ملخص') || lower.includes('week')) {
        replyText = "This week summary: 1,284 net working hours recorded (+3.1% vs last week), PPE compliance is at 94.2%, and 7 total safety incidents were flagged with an average response time of 2m 14s.";
        citations = [
          {
            source_title: "Weekly Platform Safety Digest",
            source_type: "weekly_register",
            source_id: "digest-wk-47",
            snippet: "Plant 1 aggregate telemetry summary covering Nov 17 – 24.",
            similarity_score: 0.88
          }
        ];
      }

      return {
        answer: replyText,
        conversation_id: conversationId || `conv-${Date.now()}`,
        has_sufficient_evidence: true,
        citations,
        proposed_actions: proposedActions
      };
    }

    return apiClient.post('/api/v1/assistant/ask', {
      question,
      conversation_id: conversationId,
      language_preference: language
    });
  },

  /**
   * Backward-compatible sendQuery method for existing chat component
   */
  async sendQuery(query, chatHistory = [], conversationId = null) {
    const res = await this.ask({ question: query, conversationId });
    return {
      reply: res.answer,
      source: res.citations?.[0]?.source_title ? `Source: ${res.citations[0].source_title}` : 'Source: Operix Vision Engine',
      citations: res.citations || [],
      proposedActions: res.proposed_actions || [],
      conversationId: res.conversation_id,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
  },

  /**
   * GET /api/v1/assistant/sources?q=<query>
   * Retrieve source citations for safety knowledge
   */
  async getSources(query) {
    if (isMockEnabled('assistant')) {
      return [
        { title: "Plant Safety SOP v2.4", id: "sop-2.4", match: 0.95 },
        { title: "OSHA Overhead Hazard Standard", id: "osha-1910", match: 0.89 }
      ];
    }
    return apiClient.get(`/api/v1/assistant/sources?q=${encodeURIComponent(query)}`);
  },

  /**
   * DELETE /api/v1/assistant/conversations/{conversation_id}
   * Clears conversation history on server
   */
  async clearConversation(conversationId) {
    if (isMockEnabled('assistant')) {
      return { success: true, message: 'Conversation cleared' };
    }
    return apiClient.delete(`/api/v1/assistant/conversations/${conversationId}`);
  },

  /**
   * GET /api/v1/assistant/health
   */
  async checkHealth() {
    if (isMockEnabled('assistant')) {
      return { status: 'healthy', model: 'operix-rag-v1' };
    }
    return apiClient.get('/api/v1/assistant/health');
  },

  /**
   * POST /api/v1/assistant/actions/execute
   * Execute remediation action (e.g., acknowledge incident, toggle sensor, dispatch alert)
   */
  async executeAction({ actionId, actionType, parameters = {}, confirmedBy = 'User', idempotencyKey = null }) {
    const key = idempotencyKey || `idem-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    
    if (isMockEnabled('assistant')) {
      return {
        action_id: actionId,
        status: 'executed',
        message: `Action '${actionType}' executed successfully.`,
        audit_reference: `AUDIT-${Date.now()}`,
        details: parameters,
        execution_timestamp: new Date().toISOString()
      };
    }

    return apiClient.post('/api/v1/assistant/actions/execute', {
      action_id: actionId,
      action_type: actionType,
      parameters,
      confirmed_by: confirmedBy,
      idempotency_key: key
    });
  }
};

export default assistantService;
