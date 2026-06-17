const API_URL = import.meta.env.VITE_API_URL ?? "";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const validationMessage = Array.isArray(data.detail) ? data.detail[0]?.msg : null;
    throw new Error(validationMessage || data.detail || "The request could not be completed.");
  }
  return data;
}

export function getJson(path) {
  return request(path);
}

export function postJson(path, body) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

