import { describe, expect, test } from "vitest";
import { formatPicks, formatSummary } from "./format.js";
import { reportFixture } from "./test-fixtures.js";

describe("Discord formatting", () => {
  test("formats picks separately from performance", () => {
    expect(formatPicks(reportFixture())).toContain("NBA Picks — Oct 21, 2026");
    expect(formatPicks(reportFixture())).toContain("Milwaukee Bucks** (62.3%)");
    expect(formatPicks(reportFixture())).not.toContain("This week");

    expect(formatSummary(reportFixture())).toContain("Previous day");
    expect(formatSummary(reportFixture())).toContain("✅ New York Knicks @ Boston Celtics");
    expect(formatSummary(reportFixture())).toContain("5/8 (62.5%)");
    expect(formatSummary(reportFixture())).toContain("31/50 (62.0%)");
  });
});
