import apiClient, { API_CONFIG } from './apiClient';
import { initialQuickPrompts } from '../data/mockData';

/**
 * Operix AI Vision Assistant Service
 * Connects to FastAPI endpoint `/assistant/chat`
 */
export const assistantService = {
  async getQuickPrompts() {
    if (API_CONFIG.useMock) {
      return [...initialQuickPrompts];
    }
    return apiClient.get('/assistant/prompts');
  },

  async sendQuery(query, chatHistory = []) {
    if (API_CONFIG.useMock) {
      let replyText = "I've analyzed the live plant vision metrics for you.";
      let replySource = "Source: Operix Vision Engine · Plant 1";

      const lower = query.toLowerCase();
      if (lower.includes('idle')) {
        replyText = "Zone C has the highest idle time at 24% of observed worker hours, primarily concentrated around the loading bay turnarounds.";
        replySource = "Source: workforce analytics · Current shift";
      } else if (lower.includes('summarize') || lower.includes('week')) {
        replyText = "This week: 1,284 net working hours recorded (+3.1% vs last week), PPE compliance is at 94.2%, and 7 total incidents were flagged with an average response time of 2m 14s.";
        replySource = "Source: weekly safety register · Nov 8 – 14";
      } else if (lower.includes('helmet') || lower.includes('ppe')) {
        replyText = "There have been 4 helmet violations today. The latest was detected at 09:42 in Zone B · Press Line (INC-2041).";
        replySource = "Source: incident register · Current shift";
      }

      return {
        reply: replyText,
        source: replySource,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
    }

    return apiClient.post('/assistant/chat', { query, history: chatHistory });
  }
};

export default assistantService;
