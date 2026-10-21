import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, test } from "vitest";
import { reportFixture } from "./test-fixtures.js";
import type { CommandRunner } from "./runner.js";
import { NbaPickemService } from "./service.js";

const roots: string[] = [];
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function fixture(failSecondSend = false) {
  const root = mkdtempSync(join(tmpdir(), "nba-pickem-"));
  roots.push(root);
  const calls: Array<{ command: string; args: string[] }> = [];
  let sends = 0;
  const runner: CommandRunner = async (command, args) => {
    calls.push({ command, args });
    if (args.includes("nba_pickem.openclaw_cli")) return { stdout: JSON.stringify(reportFixture()), stderr: "" };
    sends += 1;
    if (failSecondSend && sends === 2) throw new Error("Discord unavailable");
    return { stdout: JSON.stringify({ ok: true }), stderr: "" };
  };
  const service = new NbaPickemService({
    projectPath: "/repo",
    discordTarget: "channel:1562522490465554432",
    publicationRoot: root,
  }, runner);
  return { calls, service };
}

describe("NbaPickemService", () => {
  test("runs daily pipeline and delivers two idempotent messages", async () => {
    const { calls, service } = fixture();
    const first = await service.publishDaily("2026-10-21");
    const second = await service.publishDaily("2026-10-21");

    expect(first.status).toBe("delivered");
    expect(second.status).toBe("already_delivered");
    expect(calls).toHaveLength(3);
    expect(calls[0].command).toBe("/repo/scripts/openclaw-python");
    expect(calls[0].args).toContain("daily");
    expect(calls.slice(1).every(call => call.args.slice(0, 2).join(" ") === "message send")).toBe(true);
  });

  test("resumes after partial delivery without duplicating picks", async () => {
    const { calls, service } = fixture(true);
    await expect(service.publishDaily("2026-10-21")).rejects.toThrow("Discord unavailable");
    expect(service.publicationStatus("2026-10-21").picksDeliveredAt).toBeTruthy();

    await service.publishDaily("2026-10-21");
    const sends = calls.filter(call => call.args[0] === "message");
    expect(sends).toHaveLength(3);
    expect(service.publicationStatus("2026-10-21").completedAt).toBeTruthy();
  });
});
