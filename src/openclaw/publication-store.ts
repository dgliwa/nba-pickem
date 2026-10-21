import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import type { PublicationState } from "./types.js";

export class PublicationStore {
  constructor(private readonly root: string) {}

  read(reportDate: string): PublicationState {
    try {
      return JSON.parse(readFileSync(this.path(reportDate), "utf8")) as PublicationState;
    } catch {
      return { reportDate, errors: [] };
    }
  }

  write(state: PublicationState): void {
    const path = this.path(state.reportDate);
    mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
    const temporary = `${path}.tmp`;
    writeFileSync(temporary, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
    renameSync(temporary, path);
  }

  private path(reportDate: string): string {
    return join(this.root, `${reportDate}.json`);
  }
}
