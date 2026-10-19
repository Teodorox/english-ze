// Preferências do aparelho (modo de estudo, novos por dia). Se o navegador bloquear
// o armazenamento (aba anônima, por exemplo), o app segue com os valores padrão.

export function loadPref<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : (JSON.parse(value) as T);
  } catch {
    return fallback;
  }
}

export function savePref(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // sem armazenamento: a preferência vale só até recarregar
  }
}
