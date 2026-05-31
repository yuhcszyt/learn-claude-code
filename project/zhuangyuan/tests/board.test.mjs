import assert from "node:assert/strict";
import { DEFAULT_BOARD, promoteZhuangyuan } from "../board.js";

const firstOpen = promoteZhuangyuan(DEFAULT_BOARD, "杜若衡", 1);

assert.equal(firstOpen.length, 10);
assert.deepEqual(
  firstOpen.map((entry) => entry.name),
  [
    "杜若衡",
    "李文轩",
    "王景行",
    "赵清远",
    "陈怀瑾",
    "林知白",
    "周云舟",
    "沈砚秋",
    "顾明澈",
    "许长安",
  ],
);
assert.equal(firstOpen[0].id, "zhuangyuan-1");
assert.equal(DEFAULT_BOARD[0].name, "李文轩");

const secondOpen = promoteZhuangyuan(firstOpen, "  陆青崖  ", 2);

assert.equal(secondOpen[0].name, "陆青崖");
assert.equal(secondOpen[1].name, "杜若衡");
assert.equal(secondOpen[9].name, "顾明澈");

console.log("project board tests passed");
