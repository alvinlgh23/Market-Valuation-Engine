import assert from "node:assert/strict";
import { createPythonRuntime } from "../lib/python-runtime.ts";
import { integrateSectorEngineRows } from "../lib/market-research.ts";

const args = ["-B", "model.py", "valuation", "MSFT", "--json"];
for (const [error, code] of [
  [{ code: "ENOENT" }, "EXECUTABLE_NOT_FOUND"],
  [{ stderr: "ModuleNotFoundError: No module named pandas" }, "MISSING_DEPENDENCY"],
  [{ killed: true }, "PROCESS_TIMEOUT"],
  [{ code: 1, stderr: "failed" }, "NONZERO_EXIT"],
  [{ code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER" }, "OUTPUT_LIMIT"],
]) {
  const run = createPythonRuntime(async (_, a) => { if (a[0] === "--version") return { stdout: "Python 3.14", stderr: "" }; throw error; });
  await assert.rejects(() => run(args), e => e.code === code);
}
for (const [output, code] of [["not json", "INVALID_JSON"], ["Python 2.7", "UNSUPPORTED_PYTHON_VERSION"], ["Python 3.9", "UNSUPPORTED_PYTHON_VERSION"]]) {
  const run = createPythonRuntime(async (_, a) => ({ stdout: a[0] === "--version" ? (code.includes("VERSION") ? output : "Python 3.14") : output, stderr: "" }));
  await assert.rejects(() => run(args), e => e.code === code);
}
process.env.CHAINSTOX_PYTHON_EXECUTABLE = "/configured/python";
const seen = [];
const run = createPythonRuntime(async (file, a, options) => { seen.push({ file, a, options }); return { stdout: a[0] === "--version" ? "Python 3.14" : '{"ok":true}', stderr: "" }; });
for (const a of [args, ["-B", "company_research.py", "resolve", "MSFT"], ["-B", "research_system.py", "full", "--json"]]) assert.equal((await run(a)).ok, true);
assert(seen.every(x => x.file === "/configured/python" && x.options.timeout <= 180000 && x.options.maxBuffer > 0));
await assert.rejects(() => run(["-B", "bad.py", "full"]), e => e.code === "UNSUPPORTED_ACTION");
// Checklist 8.1: the judgment card bridge accepts only --summary or one ticker with --json.
assert.equal((await run(["-B", "company_verdict.py", "NVDA", "--json"])).ok, true);
assert.equal((await run(["-B", "company_verdict.py", "--summary"])).ok, true);
for (const bad of [["-B", "company_verdict.py", "--watchlist"], ["-B", "company_verdict.py", "NVDA", "--home-currency"], ["-B", "company_verdict.py", "nvda;rm", "--json"], ["-B", "company_verdict.py", "NVDA", "MSFT", "--json"]]) {
  await assert.rejects(() => run(bad), e => e.code === "UNSUPPORTED_ACTION");
}
delete process.env.CHAINSTOX_PYTHON_EXECUTABLE;
const get = (rows, state) => integrateSectorEngineRows(rows, state).find(s => s.ticker === "SMH");
assert.equal(get([]).rel6m, null);
assert.equal(get([{ ticker: "SMH", rel_6m: .42 }]).rel6m, .42);
assert.equal(get([{ ticker: "SMH", rel_6m: NaN, rel_3m: Infinity }]).rel6m, null);
assert.equal(get([{ ticker: "UNKNOWN", rel_6m: .9 }]).rel6m, null);
assert.equal(get([{ ticker: "SMH", rel_6m: .2 }], "STALE").sourceState, "STALE");
assert.equal(get([{ ticker: "SMH", rel_6m: .1, as_of: "2020-01-01" }, { ticker: "SMH", rel_6m: .3, as_of: "2021-01-01" }]).rel6m, .3);
assert.equal(get([{ ticker: 12, rel_6m: .9 }]).rel6m, null);
assert.equal(get([{ ticker: "SMH", rel_6m: .4 }]).breadthRatio, null);
console.log("Phase 6.2 runtime contracts and sector adapter cases passed.");
