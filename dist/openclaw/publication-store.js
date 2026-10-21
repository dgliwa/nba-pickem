import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
export class PublicationStore {
    root;
    constructor(root) {
        this.root = root;
    }
    read(reportDate) {
        try {
            return JSON.parse(readFileSync(this.path(reportDate), "utf8"));
        }
        catch {
            return { reportDate, errors: [] };
        }
    }
    write(state) {
        const path = this.path(state.reportDate);
        mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
        const temporary = `${path}.tmp`;
        writeFileSync(temporary, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
        renameSync(temporary, path);
    }
    path(reportDate) {
        return join(this.root, `${reportDate}.json`);
    }
}
//# sourceMappingURL=publication-store.js.map