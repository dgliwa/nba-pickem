import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";
import { NbaPickemService } from "./service.js";

const defaultProjectPath = fileURLToPath(new URL("../../", import.meta.url));
const defaultDiscordTarget = "channel:1562522490465554432";
const date = Type.Optional(Type.String({
  pattern: "^\\d{4}-\\d{2}-\\d{2}$",
  description: "NBA report date in YYYY-MM-DD format; defaults to today in America/New_York.",
}));

function serviceFor(api: any, config: Record<string, unknown>): NbaPickemService {
  const stateDir = api.runtime.state.resolveStateDir(process.env);
  const projectPath = typeof config.projectPath === "string" ? config.projectPath : defaultProjectPath;
  return new NbaPickemService({
    projectPath,
    pythonPath: typeof config.pythonPath === "string" ? config.pythonPath : undefined,
    discordTarget: typeof config.discordTarget === "string" ? config.discordTarget : defaultDiscordTarget,
    openclawCommand: typeof config.openclawCommand === "string" ? config.openclawCommand : undefined,
    publicationRoot: join(stateDir, "nba-pickem", "publications"),
  });
}

export default defineToolPlugin({
  id: "nba-pickem",
  name: "NBA Pick'em",
  description: "Generate daily NBA picks, grade prior picks, calculate weekly and season accuracy, and publish deterministic reports to Discord.",
  configSchema: Type.Object({
    projectPath: Type.Optional(Type.String({ description: "Absolute path to the NBA Pick'em repository." })),
    pythonPath: Type.Optional(Type.String({ description: "Package-contained Python launcher; defaults to scripts/openclaw-python." })),
    discordTarget: Type.Optional(Type.String({ pattern: "^channel:[0-9]{10,30}$", description: "Fixed Discord destination for daily pick and performance messages." })),
    openclawCommand: Type.Optional(Type.String({ minLength: 1, maxLength: 500, description: "OpenClaw CLI command used for deterministic Discord delivery." })),
  }, { additionalProperties: false }),
  tools: tool => [
    tool({
      name: "nba_pickem_daily_publish",
      description: "Refresh the current NBA season, generate and persist today's model picks, then idempotently deliver two separate messages to the configured #bets channel: today's picks and prior-day/weekly/season performance. Requires explicit confirmation.",
      parameters: Type.Object({ confirmed: Type.Literal(true), date }, { additionalProperties: false }),
      execute: async ({ date: reportDate }, config, { api, signal }) => serviceFor(api, config).publishDaily(reportDate, signal),
    }),
    tool({
      name: "nba_pickem_report",
      description: "Read today's saved picks plus previous-day results, current-week accuracy, and current-season accuracy without refreshing data or sending Discord messages.",
      parameters: Type.Object({ date }, { additionalProperties: false }),
      execute: async ({ date: reportDate }, config, { api, signal }) => serviceFor(api, config).report(reportDate, signal),
    }),
    tool({
      name: "nba_pickem_publication_status",
      description: "Check whether the picks and performance messages for a date were delivered to #bets, including partial-delivery errors.",
      parameters: Type.Object({ date }, { additionalProperties: false }),
      execute: async ({ date: reportDate }, config, { api, signal }) => {
        signal?.throwIfAborted();
        return serviceFor(api, config).publicationStatus(reportDate);
      },
    }),
  ],
});
