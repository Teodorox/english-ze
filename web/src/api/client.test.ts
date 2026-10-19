import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, AUTH_REQUIRED_EVENT } from "./client";

function mockFetch(status: number, body?: unknown) {
  const fetchMock = vi.fn(async () =>
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api", () => {
  it("devolve o JSON da resposta", async () => {
    mockFetch(200, { streak: 3 });
    await expect(api<{ streak: number }>("/api/stats")).resolves.toEqual({ streak: 3 });
  });

  it("envia o corpo como JSON", async () => {
    const fetchMock = mockFetch(200, { ok: true });
    await api("/api/login", { method: "POST", body: { password: "x" } });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ password: "x" }),
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("usa a mensagem do campo detail nos erros", async () => {
    mockFetch(409, { detail: "Esse card já existe" });
    await expect(api("/api/cards", { method: "POST", body: {} })).rejects.toEqual(
      new ApiError("Esse card já existe", 409),
    );
  });

  it("avisa o app quando a sessão expira", async () => {
    const target = new EventTarget();
    const listener = vi.fn();
    target.addEventListener(AUTH_REQUIRED_EVENT, listener);
    vi.stubGlobal("window", target);
    mockFetch(401, { detail: "Faça login" });

    await expect(api("/api/stats")).rejects.toMatchObject({ status: 401 });
    expect(listener).toHaveBeenCalledOnce();
  });

  it("não trata senha errada no login como sessão expirada", async () => {
    const target = new EventTarget();
    const listener = vi.fn();
    target.addEventListener(AUTH_REQUIRED_EVENT, listener);
    vi.stubGlobal("window", target);
    mockFetch(401, { detail: "Senha incorreta" });

    await expect(api("/api/login", { method: "POST", body: { password: "x" } })).rejects.toEqual(
      new ApiError("Senha incorreta", 401),
    );
    expect(listener).not.toHaveBeenCalled();
  });
});
