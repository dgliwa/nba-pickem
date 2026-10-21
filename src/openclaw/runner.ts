import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export interface CommandResult {
  stdout: string;
  stderr: string;
}

export type CommandRunner = (
  command: string,
  args: string[],
  options: { cwd?: string; timeoutMs: number; signal?: AbortSignal },
) => Promise<CommandResult>;

export const executeCommand: CommandRunner = async (command, args, options) => {
  const result = await execFileAsync(command, args, {
    cwd: options.cwd,
    timeout: options.timeoutMs,
    signal: options.signal,
    maxBuffer: 2 * 1024 * 1024,
    encoding: "utf8",
    windowsHide: true,
  });
  return { stdout: result.stdout, stderr: result.stderr };
};
