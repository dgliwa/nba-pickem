import { readFile, writeFile } from "node:fs/promises";

const path = new URL("../openclaw.plugin.json", import.meta.url);
const manifest = JSON.parse(await readFile(path, "utf8"));
manifest.toolMetadata ??= {};
manifest.toolMetadata.nba_pickem_daily_publish = {
  ...(manifest.toolMetadata.nba_pickem_daily_publish ?? {}),
  sideEffecting: true,
};
await writeFile(path, `${JSON.stringify(manifest, null, 2)}\n`);
