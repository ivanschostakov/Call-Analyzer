import { apiFetch } from './http';

export type MentorThreadResponse = {
  id: number;
  owner_user_id: number;
  company_id: number;
  template_id?: number | null;
  title: string;
  created_at: string;
  updated_at: string;
};

export type MentorMessageResponse = {
  id: number;
  thread_id: number;
  role: 'user' | 'assistant';
  content: string;
  analysis_ids: number[];
  selected_columns: string[];
  row_count: number;
  summarized_row_count: number;
  omitted_row_count: number;
  created_at: string;
  updated_at: string;
};

export type MentorThreadDetailResponse = MentorThreadResponse & {
  messages: MentorMessageResponse[];
};

export type MentorMessageRequest = {
  thread_id?: number | null;
  company_id: number;
  template_id: number;
  analysis_ids: number[];
  columns?: string[];
  prompt: string;
};

export type MentorReplyResponse = {
  thread: MentorThreadResponse;
  user_message: MentorMessageResponse;
  assistant_message: MentorMessageResponse;
};

export function listMentorThreads(companyId: number) {
  return apiFetch<MentorThreadResponse[]>({
    url: '/mentor/threads',
    params: { company_id: companyId },
  });
}

export function getMentorThread(threadId: number) {
  return apiFetch<MentorThreadDetailResponse>({
    url: `/mentor/threads/${threadId}`,
  });
}

export function createMentorMessage(payload: MentorMessageRequest) {
  return apiFetch<MentorReplyResponse>({
    url: '/mentor/messages',
    method: 'POST',
    data: payload,
  });
}
