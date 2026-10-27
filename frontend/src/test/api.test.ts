import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../services/api";
import type { Session } from "../types";
const session: Session = {
  session_id: "session123",
  token: "private-token",
  filename: "data.csv",
  sheets: ["Data"],
  expires_at: "",
};
afterEach(() => vi.unstubAllGlobals());
describe("API boundary", () => {
  it("sends the session capability and the current filters for each analysis", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, data: { rows: 4 } }),
      });
    vi.stubGlobal("fetch", fetchMock);
    await api.filter(session, {
      sheet: "Data",
      version: "cleaned",
      filters: { Department: { values: ["Science"] } },
    });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/filter/session123");
    expect(options.headers["X-Session-Token"]).toBe("private-token");
    expect(JSON.parse(options.body)).toEqual({
      sheet: "Data",
      version: "cleaned",
      filters: { Department: { values: ["Science"] } },
    });
  });
  it("exposes safe server validation messages and understandable offline errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({
          ok: false,
          json: async () => ({
            success: false,
            error: { message: "Unknown worksheet." },
          }),
        }),
    );
    await expect(
      api.analyze(session, {
        sheet: "Unknown",
        filters: {},
        version: "original",
      }),
    ).rejects.toThrow("Unknown worksheet.");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("network failure")),
    );
    await expect(api.samples()).rejects.toThrow(
      "Cannot connect to the analytics server",
    );
  });
});
