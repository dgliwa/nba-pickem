export interface CommandResult {
    stdout: string;
    stderr: string;
}
export type CommandRunner = (command: string, args: string[], options: {
    cwd?: string;
    timeoutMs: number;
    signal?: AbortSignal;
}) => Promise<CommandResult>;
export declare const executeCommand: CommandRunner;
