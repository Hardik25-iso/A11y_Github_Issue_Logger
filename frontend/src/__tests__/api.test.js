import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getJson, postJson } from "../services/api";

const originalFetch = global.fetch;

function mockFetch(status, body) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("getJson", () => {
  it("returns parsed JSON on success", async () => {
    mockFetch(200, { status: "ok" });
    const result = await getJson("/health");
    expect(result).toEqual({ status: "ok" });
  });

  it("throws with detail message on 4xx", async () => {
    mockFetch(422, { detail: "URL is invalid." });
    await expect(getJson("/api/scan")).rejects.toThrow("URL is invalid.");
  });

  it("extracts first validation message from Pydantic array detail", async () => {
    mockFetch(422, { detail: [{ msg: "Field required", loc: ["body", "url"] }] });
    await expect(getJson("/api/scan")).rejects.toThrow("Field required");
  });

  it("falls back to generic message when detail is absent", async () => {
    mockFetch(500, {});
    await expect(getJson("/api/scan")).rejects.toThrow("The request could not be completed.");
  });
});

describe("postJson", () => {
  it("sends POST with JSON body and Content-Type header", async () => {
    mockFetch(200, { source: "fallback", issues: [] });
    await postJson("/api/scan", { url: "https://example.com" });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/scan"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
        body: JSON.stringify({ url: "https://example.com" }),
      }),
    );
  });

  it("throws on error response", async () => {
    mockFetch(404, { detail: "Repository not found." });
    await expect(postJson("/api/log-issue", {})).rejects.toThrow("Repository not found.");
  });
});
