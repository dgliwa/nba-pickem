import { join } from "node:path";
import { formatPicks, formatSummary } from "./format.js";
import { PublicationStore } from "./publication-store.js";
import { executeCommand } from "./runner.js";
export class NbaPickemService {
    options;
    runCommand;
    store;
    constructor(options, runCommand = executeCommand) {
        this.options = options;
        this.runCommand = runCommand;
        if (!/^channel:\d{10,30}$/.test(options.discordTarget)) {
            throw new Error("discordTarget must be configured as channel:<Discord channel ID>.");
        }
        this.store = new PublicationStore(options.publicationRoot);
    }
    async report(reportDate, signal) {
        return this.runPython("report", validateDate(reportDate), signal);
    }
    publicationStatus(reportDate) {
        return this.store.read(validateDate(reportDate) ?? easternDate());
    }
    async publishDaily(reportDate, signal) {
        const date = validateDate(reportDate) ?? easternDate();
        const existing = this.store.read(date);
        if (existing.completedAt)
            return { status: "already_delivered", ...existing };
        const report = await this.runPython("daily", date, signal);
        const state = this.store.read(report.report_date);
        try {
            if (!state.picksDeliveredAt) {
                await this.sendDiscord(formatPicks(report), signal);
                state.picksDeliveredAt = new Date().toISOString();
                this.store.write(state);
            }
            if (!state.summaryDeliveredAt) {
                await this.sendDiscord(formatSummary(report), signal);
                state.summaryDeliveredAt = new Date().toISOString();
                this.store.write(state);
            }
            state.completedAt = new Date().toISOString();
            this.store.write(state);
            return {
                status: "delivered",
                reportDate: report.report_date,
                target: this.options.discordTarget,
                picks: report.today.picks.length,
                previousDayPicks: report.previous_day.picks.length,
                weekly: report.weekly,
                season: report.season_performance,
            };
        }
        catch (error) {
            state.errors.push(errorMessage(error));
            this.store.write(state);
            throw error;
        }
    }
    async runPython(command, reportDate, signal) {
        const python = this.options.pythonPath ?? join(this.options.projectPath, "scripts", "openclaw-python");
        const args = ["-m", "nba_pickem.openclaw_cli", command];
        if (reportDate)
            args.push("--date", reportDate);
        const result = await this.runCommand(python, args, {
            cwd: this.options.projectPath,
            timeoutMs: command === "daily" ? 15 * 60_000 : 60_000,
            signal,
        });
        try {
            return JSON.parse(result.stdout.trim());
        }
        catch {
            throw new Error(`NBA Pick'em returned invalid JSON. stderr: ${result.stderr.slice(-1_000)}`);
        }
    }
    async sendDiscord(message, signal) {
        await this.runCommand(this.options.openclawCommand ?? "openclaw", [
            "message", "send",
            "--channel", "discord",
            "--target", this.options.discordTarget,
            "--message", message,
            "--json",
        ], { timeoutMs: 120_000, signal });
    }
}
function validateDate(value) {
    if (value === undefined)
        return undefined;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(`${value}T00:00:00Z`))) {
        throw new Error("date must use YYYY-MM-DD format.");
    }
    return value;
}
function easternDate(now = new Date()) {
    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).formatToParts(now);
    const value = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return `${value.year}-${value.month}-${value.day}`;
}
function errorMessage(error) {
    return error instanceof Error ? error.message : String(error);
}
//# sourceMappingURL=service.js.map