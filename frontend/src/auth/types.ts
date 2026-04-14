export type UserRole = 'owner' | 'employee' | 'admin';

export type CurrentUser = {
  id: number;
  email: string;
  name: string;
  surname: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  session_id: number;
  token_type?: 'bearer';
};

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  sessionId: number;
  tokenType: 'bearer';
  user: CurrentUser | null;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  name: string;
  surname: string;
};

export type AuthTokensWithUserResponse = AuthTokens & {
  user: CurrentUser;
};
