import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const execute = promisify(execFile);
export type RuntimeCode = "EXECUTABLE_NOT_FOUND" | "UNSUPPORTED_PYTHON_VERSION" | "MISSING_DEPENDENCY" | "PROCESS_TIMEOUT" | "NONZERO_EXIT" | "INVALID_JSON" | "OUTPUT_LIMIT" | "INVALID_INPUT" | "UNSUPPORTED_ACTION";
export class PythonRuntimeError extends Error {
  code: RuntimeCode;
  constructor(code: RuntimeCode, message: string) { super(message); this.code = code; }
}
export function runtimeError(error: unknown) {
  if (error instanceof PythonRuntimeError) return { code: error.code, message: error.message };
  return { code: "NONZERO_EXIT", message: error instanceof Error ? error.message : String(error) };
}
type Executor = (file: string, args: string[], options: { cwd: string; timeout: number; maxBuffer: number }) => Promise<{ stdout: string; stderr: string }>;
export function createPythonRuntime(run: Executor = execute as Executor) {
  const checked = new Map<string, Promise<void>>();
  async function call(executable: string, args: string[], timeout: number) {
    try {
      return await run(executable, args, { cwd: path.resolve(process.cwd(), ".."), timeout, maxBuffer: 20 * 1024 * 1024 });
    } catch (error) {
      const e = error as { code?: string; killed?: boolean; stderr?: string; message?: string };
      const code: RuntimeCode = e.code === "ENOENT" ? "EXECUTABLE_NOT_FOUND"
        : e.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER" ? "OUTPUT_LIMIT"
        : e.killed ? "PROCESS_TIMEOUT"
        : /ModuleNotFoundError|ImportError/.test(e.stderr || "") ? "MISSING_DEPENDENCY" : "NONZERO_EXIT";
      throw new PythonRuntimeError(code, `${code}: ${e.stderr?.trim().split("\n").at(-1) || e.message || "Python execution failed"}`);
    }
  }
  return async function runPythonJson<T>(args: string[], timeout = 180_000): Promise<T> {
    const script = args[1], action = args[2];
    const allowed = script === "model.py" ? ["valuation"] : script === "company_research.py" ? ["resolve", "analyze", "open", "index"] : script === "research_system.py" ? ["full"] : [];
    if (args[0] !== "-B" || !allowed.includes(action)) throw new PythonRuntimeError("UNSUPPORTED_ACTION", "Unsupported research action.");
    const executable = process.env.CHAINSTOX_PYTHON_EXECUTABLE?.trim() || "python3";
    if (!checked.has(executable)) checked.set(executable, call(executable, ["--version"], 10_000).then(({ stdout, stderr }) => {
      const version = /^Python (\d+)\.(\d+)/.exec(`${stdout}${stderr}`.trim());
      if (!version || Number(version[1]) !== 3 || Number(version[2]) < 10) throw new PythonRuntimeError("UNSUPPORTED_PYTHON_VERSION", "Python 3.10 or newer is required.");
    }).catch(error => { checked.delete(executable); throw error; }));
    await checked.get(executable);
    const { stdout } = await call(executable, args, timeout);
    try { return JSON.parse(stdout) as T; }
    catch { throw new PythonRuntimeError("INVALID_JSON", "Python returned invalid JSON."); }
  };
}
export const runPythonJson = createPythonRuntime();
