const TOKEN_KEY = "wa_admin_token";

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_KEY}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setToken(token: string): void {
  const maxAge = 60 * 60; // 1 hora
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; SameSite=Strict; Max-Age=${maxAge}${secure}`;
}

export function removeToken(): void {
  document.cookie = `${TOKEN_KEY}=; path=/; Max-Age=0`;
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
