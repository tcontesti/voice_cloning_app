import { api } from './client'

export interface ConsentText {
  version: string
  text_hash: string
  body_markdown: string
}

export interface Consent {
  id: string
  user_id: string
  version: string
  text_hash: string
  signature_hash: string
  created_at: string
}

export const consentApi = {
  current: () => api.get<ConsentText>('/consent/current'),
  accept: (version: string, text_hash: string) =>
    api.post<Consent>('/consent/accept', { version, text_hash }),
}
