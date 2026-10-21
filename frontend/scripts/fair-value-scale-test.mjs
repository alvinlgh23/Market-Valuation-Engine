import assert from "node:assert/strict";
import { fairValueCoordinates } from "../lib/fair-value-scale.mjs";

const aligned = fairValueCoordinates({ bear: 100, base: 150, bull: 250, market: 150 });
assert.equal(aligned.positions.market, aligned.positions.base);

const above = fairValueCoordinates({ bear: 50, base: 100, bull: 150, market: 200 });
assert.equal(above.positions.market, 100);
assert.ok(above.positions.bull < above.positions.market);

const uneven = fairValueCoordinates({ bear: 100, base: 120, bull: 300, market: 200 });
assert.ok(uneven.positions.bear < uneven.positions.base);
assert.ok(uneven.positions.base < uneven.positions.market);
assert.ok(uneven.positions.market < uneven.positions.bull);
assert.ok(uneven.positions.base - uneven.positions.bear < uneven.positions.bull - uneven.positions.base);

const below = fairValueCoordinates({ bear: 100, base: 150, bull: 200, market: 50 });
assert.equal(below.positions.market, 0);
assert.ok(below.positions.bear > below.positions.market);

const identical = fairValueCoordinates({ bear: 100, base: 100, bull: 100, market: 100 });
assert.equal(identical.positions.bear, identical.positions.market);
assert.ok(Number.isFinite(identical.positions.base));

const unavailable = fairValueCoordinates({ bear: null, base: null, bull: null, market: null });
assert.equal(unavailable.valid, false);
assert.deepEqual(unavailable.positions, {});

const invalid = fairValueCoordinates({ bear: 150, base: 100, bull: 200, market: 120 });
assert.equal(invalid.valid, false);

console.log("Fair-value coordinate tests passed.");
