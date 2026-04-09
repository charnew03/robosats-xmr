const PREFIX = "robosats_xmr_chat_v1_";

export type ChatMessage = {
  id: string;
  pseudonym: string;
  text: string;
  at: string;
};

function key(tradeId: string): string {
  return `${PREFIX}${tradeId}`;
}

export function loadChatMessages(tradeId: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(key(tradeId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (m): m is ChatMessage =>
        typeof m === "object" &&
        m !== null &&
        typeof (m as ChatMessage).id === "string" &&
        typeof (m as ChatMessage).pseudonym === "string" &&
        typeof (m as ChatMessage).text === "string" &&
        typeof (m as ChatMessage).at === "string",
    );
  } catch {
    return [];
  }
}

export function saveChatMessages(tradeId: string, messages: ChatMessage[]): void {
  localStorage.setItem(key(tradeId), JSON.stringify(messages));
}

export function appendChatMessage(tradeId: string, msg: ChatMessage): ChatMessage[] {
  const next = [...loadChatMessages(tradeId), msg];
  saveChatMessages(tradeId, next);
  return next;
}
