export interface AuthUser {
    user_id: string;
    username: string;
}

export interface AuthResponse {
    user: AuthUser | null;
}