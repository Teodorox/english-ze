/** Erro com a mensagem amigável que a API devolve em `detail`. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Disparado quando a sessão expira, para o App voltar à tela de login. */
export const AUTH_REQUIRED_EVENT = "ez:auth-required";

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function api<T>(path: string, { method = "GET", body, signal }: RequestOptions = {}): Promise<T> {
  // Áudio (Blob) vai como está; o resto vai como JSON.
  const isBlob = typeof Blob !== "undefined" && body instanceof Blob;
  const hasBody = body !== undefined;
  const res = await fetch(path, {
    method,
    signal,
    headers: hasBody ? { "Content-Type": isBlob ? body.type || "application/octet-stream" : "application/json" } : undefined,
    body: isBlob ? body : hasBody ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && path !== "/api/login") {
    if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
    throw new ApiError("Faça login", 401);
  }

  if (!res.ok) {
    let message = res.statusText || `Erro ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") message = data.detail;
    } catch {
      // resposta sem JSON: fica a mensagem padrão
    }
    throw new ApiError(message, res.status);
  }

  return (res.status === 204 ? undefined : await res.json()) as T;
}
