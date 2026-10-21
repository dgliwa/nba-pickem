import { type CommandRunner } from "./runner.js";
import type { DailyReport, PublicationState } from "./types.js";
export interface PickemOptions {
    projectPath: string;
    pythonPath?: string;
    discordTarget: string;
    openclawCommand?: string;
    publicationRoot: string;
}
export declare class NbaPickemService {
    private readonly options;
    private readonly runCommand;
    private readonly store;
    constructor(options: PickemOptions, runCommand?: CommandRunner);
    report(reportDate?: string, signal?: AbortSignal): Promise<DailyReport>;
    publicationStatus(reportDate?: string): PublicationState;
    publishDaily(reportDate?: string, signal?: AbortSignal): Promise<Record<string, unknown>>;
    private runPython;
    private sendDiscord;
}
